"""Bounded parser-executing mixed Markdown slice (S4b) over the composite recipe vocabulary.

A small, parser-free selection of valid-only recipes runs sequentially, one existing fresh composite
child per case. The worker's qualification bit never covers this driver file; the parent binds it
with sampled origin/digest gates only (no claim against edit-and-restore races or loaded code).
"""

from __future__ import annotations

import hashlib
import importlib.machinery
import inspect
import json
import re
import shutil
import stat
import sys
import types
from collections.abc import Callable, Iterator, Sequence
from dataclasses import FrozenInstanceError, asdict, dataclass, replace
from itertools import product
from pathlib import Path
from typing import Any, Final, Literal, Protocol, cast, get_args

import pytest
from hypothesis import HealthCheck, Phase, Verbosity, given, settings
from hypothesis import seed as hypothesis_seed
from hypothesis import strategies as st
from hypothesis.database import InMemoryExampleDatabase

from logseq_matryca_parser.logos_parser import StackMachineParser
from tests.parser_assurance import composite_properties as composite

SELECTED_SHAPES: Final = ("root-child-sibling", "siblings")
RECIPE_SEED: Final = 104
MAX_SELECTED: Final = 32
MAX_BODY_CALLS: Final = 48
MAX_NODES: Final = 3
MAX_DEPTH: Final = 1
MAX_SOURCE_BYTES: Final = 2048
DRIVER_RELATIVE: Final = "tests/test_parser_mixed_markdown_properties.py"
SUMMARY_SCHEMA: Final = "s4b_mixed_markdown_summary_v1"
QUALIFICATIONS: Final = frozenset({"qualified", "unqualified-source-drift"})
SUMMARY_KEYS: Final = frozenset({
    "schema", "driver_sha256", "helper_sha256", "lock_sha256", "worker_provenance_sha256",
    "cases", "counts", "outcome",
})
COUNT_KEYS: Final = frozenset({
    "body_calls", "duplicates", "dropped_at_cap", "selected", "attempted", "launched",
    "max_parser_calls_bound",
})
CASE_KEYS: Final = frozenset({"recipe_sha256", "source_sha256", "classification", "qualification"})
OUTCOME_KEYS: Final = frozenset({
    "stop_reason", "first_non_pass_index", "drift_stage", "qualified_success",
})
HELPER_MANIFEST_KEY: Final = "tests/parser_assurance/composite_properties.py"
LOCK_MANIFEST_KEY: Final = "uv.lock"

DriverStatus = Literal["intact", "drift", "unavailable"]
StopReason = Literal[
    "complete", "first-non-pass", "launch-refused", "driver-drift-before-child",
    "driver-drift-after-child", "driver-drift-at-boundary",
]
DriftStage = Literal["before-child", "after-child", "boundary"]
Check = Callable[["DriverBinding"], DriverStatus]
STOP_REASONS: Final = frozenset(get_args(StopReason))
DRIFT_STAGES: Final = frozenset(get_args(DriftStage))


class SelectionError(ValueError):
    """The collector could not produce an in-domain selection (fail closed, never skipped)."""


class DomainViolation(SelectionError):
    """A built case left the S4b domain: seed, shape, nodes, depth or source bytes."""


class BodyBudgetExceeded(RuntimeError):
    """The independent generated-body ceiling was reached; no further body work is admitted."""


class DriverProvenanceError(RuntimeError):
    """Driver origin or digest evidence is unavailable or inadmissible; `reason` is a fixed code."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"driver provenance inadmissible: {reason}")
        self.reason = reason


class Launch(Protocol):
    def __call__(
        self, case: composite.Case, *, expected_context: dict[str, object] | None = None,
    ) -> composite.Result: ...


@dataclass
class _BodyBudget:
    """Counts admitted generated bodies independently of Hypothesis; refuses before any work."""

    admitted: int = 0

    def admit(self) -> None:
        if self.admitted >= MAX_BODY_CALLS:
            raise BodyBudgetExceeded("generated body-call ceiling reached")
        self.admitted += 1


@dataclass(frozen=True)
class Accounting:
    generated: int
    duplicates: int
    dropped_at_cap: int
    selected: int


@dataclass(frozen=True)
class Selection:
    cases: tuple[composite.Case, ...]
    accounting: Accounting


@dataclass(frozen=True)
class DriverBinding:
    origin: Path
    sha256: str
    root: Path
    anchor: Path


@dataclass(frozen=True)
class Drift:
    stage: DriftStage
    index: int | None
    status: str


@dataclass(frozen=True)
class Outcome:
    """`attempted` reached the pre-launch gate; `launched` handed a case to `launch`."""

    attempted: int
    launched: int
    results: tuple[composite.Result, ...]
    first_non_pass: composite.Result | None
    drift: Drift | None
    stop_reason: StopReason

    @property
    def qualified_success(self) -> bool:
        return (
            self.stop_reason == "complete" and self.drift is None and self.first_non_pass is None
            and self.attempted == self.launched == len(self.results)
            and all(_is_pass(result) for result in self.results)
        )


@dataclass(frozen=True)
class Invocation:
    binding: DriverBinding
    context: dict[str, object]
    selection: Selection
    outcome: Outcome
    summary: dict[str, object] | None
    summary_error: str | None = None


COLLECTION_SETTINGS: Final = settings(
    max_examples=32, derandomize=True, database=None, deadline=None, phases=(Phase.generate,),
    report_multiple_bugs=False, print_blob=False, suppress_health_check=(),
)


def selected_recipes() -> st.SearchStrategy[composite.Recipe]:
    """Finite composite vocabulary restricted to two shapes and seed metadata 104; no filtering."""
    return st.builds(
        composite.Recipe, seed=st.just(RECIPE_SEED), shape=st.sampled_from(SELECTED_SHAPES),
        task=st.sampled_from(composite.TASKS), priority=st.sampled_from(composite.PRIORITIES),
        scheduled=st.sampled_from(composite.SCHEDULED_DATES),
        deadline=st.sampled_from(composite.DEADLINE_DATES),
        literal=st.sampled_from(composite.LITERALS),
        reference=st.sampled_from(composite.REFERENCES), tag=st.sampled_from(composite.TAGS),
        unicode=st.sampled_from(composite.UNICODE), newline=st.sampled_from(composite.NEWLINES),
    )


_SETTING_FIELDS: Final = (
    "backend", "database", "deadline", "derandomize", "max_examples", "phases", "print_blob",
    "report_multiple_bugs", "stateful_step_count", "suppress_health_check", "verbosity",
)


def _require_applied_settings(test: object) -> None:
    """Fail closed unless the decorated test carries exactly the approved settings and no seed.

    Reads Hypothesis's own markers on the wrapped test, so a loosened, replaced or extra
    `settings`, a `seed` override or a missing marker is refused before any body runs.
    """
    applied = getattr(test, "_hypothesis_internal_use_settings", None)
    differs = applied is None or any(
        getattr(applied, name) != getattr(COLLECTION_SETTINGS, name) for name in _SETTING_FIELDS
    )
    if (
        differs
        or getattr(test, "_hypothesis_internal_use_seed", "unset") is not None
        or getattr(test, "_hypothesis_internal_use_reproduce_failure", "unset") is not None
    ):
        raise SelectionError("collector Hypothesis configuration differs from the approved design")


def enforce_domain(case: composite.Case) -> None:
    nodes = composite._flatten_expected(case.expected)
    checks = (
        ("seed", type(case.recipe.seed) is int and case.recipe.seed == RECIPE_SEED),
        ("shape", case.recipe.shape in SELECTED_SHAPES),
        ("nodes", 1 <= len(nodes) <= MAX_NODES),
        ("depth", max((block.depth for block in nodes), default=0) <= MAX_DEPTH),
        ("bytes", case.source_bytes <= MAX_SOURCE_BYTES),
    )
    violated = [name for name, holds in checks if not holds]
    if violated:
        raise DomainViolation(f"selected domain violated: {','.join(violated)}")


def collect_selected_cases(*, budget: _BodyBudget | None = None) -> Selection:
    """Collect at most 32 source-distinct cases (baseline first) with no parser call."""
    body_budget = _BodyBudget() if budget is None else budget
    baseline = composite.build_case(composite.Recipe.literal_example())
    enforce_domain(baseline)
    cases = [baseline]
    seen = {baseline.source_sha256}
    counts = {"generated": 0, "duplicates": 0, "dropped_at_cap": 0}

    @COLLECTION_SETTINGS
    @given(recipe=selected_recipes())
    def collect(recipe: composite.Recipe) -> None:
        body_budget.admit()
        counts["generated"] += 1
        composite._validate(recipe)
        case = composite.build_case(recipe)
        enforce_domain(case)
        if case.source_sha256 in seen:
            counts["duplicates"] += 1
        elif len(cases) >= MAX_SELECTED:
            counts["dropped_at_cap"] += 1
        else:
            seen.add(case.source_sha256)
            cases.append(case)

    _require_applied_settings(collect)
    collect()
    if len(cases) < 2:
        raise SelectionError("no genuinely generated non-baseline source was selected")
    return Selection(tuple(cases), Accounting(
        counts["generated"], counts["duplicates"], counts["dropped_at_cap"], len(cases),
    ))


def _read_origin_digest(origin: Path) -> str:
    if origin.is_symlink():
        raise DriverProvenanceError("symlink")
    if not stat.S_ISREG(origin.lstat().st_mode):
        raise DriverProvenanceError("not-regular")
    return hashlib.sha256(origin.read_bytes()).hexdigest()


def _validate_topology(origin: Path, root: Path, anchor: Path, admitted: Path | None) -> Path:
    """Shared by admission and every later gate; returns the resolved origin.

    Requires a nonsymlinked leaf, `<root>/tests` not a symlink, `root` equal to the root derived
    from the composite helper (`anchor`), and the resolved origin equal to `<root>/tests/<this
    file>` and, after admission, to the admitted path. Symlinks in ancestors of `root` are
    allowed. Raises DriverProvenanceError for an inadmissible topology, OSError when unreadable.
    """
    if origin.is_symlink():
        raise DriverProvenanceError("symlink")
    if (root / "tests").is_symlink():
        raise DriverProvenanceError("tests-symlink")
    selected_root = root.resolve(strict=True)
    if selected_root != anchor.resolve(strict=True):
        raise DriverProvenanceError("root")
    resolved = origin.resolve(strict=True)
    if resolved != selected_root / DRIVER_RELATIVE or (
        admitted is not None and resolved != admitted
    ):
        raise DriverProvenanceError("path")
    return resolved


def admit_driver(
    *, module: types.ModuleType | None = None, repo_root: Path | None = None,
    helper_root: Path | None = None,
) -> DriverBinding:
    """Admit this module's origin: a regular, nonsymlinked file at the expected path.

    Topology rules are in `_validate_topology`; `helper_root` defaults to the root derived from
    the composite helper's location. Symlinks above the repository root are not rejected, and
    every check is a sampled read, not protection against edit-and-restore races.
    """
    selected = sys.modules[__name__] if module is None else module
    file_origin = getattr(selected, "__file__", None)
    spec_origin = getattr(getattr(selected, "__spec__", None), "origin", None)
    if not isinstance(file_origin, str) or not isinstance(spec_origin, str):
        raise DriverProvenanceError("origin-unavailable")
    if Path(file_origin) != Path(spec_origin):
        raise DriverProvenanceError("origin-mismatch")
    try:
        root = Path(__file__).resolve().parents[1] if repo_root is None else repo_root
        anchor = Path(composite.__file__).resolve().parents[2] if helper_root is None else helper_root
        resolved = _validate_topology(Path(file_origin), root, anchor, None)
        digest = _read_origin_digest(resolved)
        return DriverBinding(
            resolved, digest, root.resolve(strict=True), anchor.resolve(strict=True),
        )
    except DriverProvenanceError:
        raise
    except (OSError, RuntimeError) as error:
        raise DriverProvenanceError("unreadable") from error


def check_driver(binding: DriverBinding) -> DriverStatus:
    """Recheck topology/digest; unreadable or looping resolution is unavailable evidence."""
    try:
        resolved = _validate_topology(binding.origin, binding.root, binding.anchor, binding.origin)
        digest = _read_origin_digest(resolved)
    except DriverProvenanceError:
        return "drift"
    except (OSError, RuntimeError):
        return "unavailable"
    return "intact" if digest == binding.sha256 else "drift"


def _is_pass(result: composite.Result) -> bool:
    return (
        result.classification == "parsed" and result.model_checked is True
        and result.roundtrip_checked is True and result.qualification_status == "qualified"
        and result.exception_type is None and result.semantic_differences == ()
    )


def _passes(result: composite.Result, case: composite.Case) -> bool:
    bound = (result.case_id, result.source_sha256, result.recipe) == (
        case.case_id, case.source_sha256, case.recipe,
    )
    return bound and _is_pass(result)


def run_selected(
    cases: Sequence[composite.Case], *, binding: DriverBinding, context: dict[str, object],
    launch: Launch = composite.run_case, check: Check = check_driver,
) -> Outcome:
    """Sequential, one child per case, stop at the first non-pass or driver-evidence failure."""
    if not 1 <= len(cases) <= MAX_SELECTED:
        raise ValueError("selected case count must be between 1..32")
    if len({case.source_sha256 for case in cases}) != len(cases):
        raise ValueError("selected sources must be distinct")
    for case in cases:
        enforce_domain(case)
    results: list[composite.Result] = []
    first: composite.Result | None = None
    drift: Drift | None = None
    reason: StopReason = "complete"
    attempted = launched = 0
    for index, case in enumerate(cases):
        attempted += 1
        status = check(binding)
        if status != "intact":
            drift, reason = Drift("before-child", index, status), "driver-drift-before-child"
            break
        launched += 1
        try:
            result = launch(case, expected_context=context)
        except ValueError:
            reason = "launch-refused"
            break
        status = check(binding)
        if status != "intact":
            drift = Drift("after-child", index, status)
            result = composite.replace_result_qualification(
                result, "unqualified-source-drift", context,
            )
        results.append(result)
        if drift is not None:
            first, reason = result, "driver-drift-after-child"
            break
        if not _passes(result, case):
            first, reason = result, "first-non-pass"
            break
    if drift is None:
        status = check(binding)
        if status != "intact":
            drift = Drift("boundary", None, status)
            reason = "driver-drift-at-boundary" if reason == "complete" else reason
    return Outcome(attempted, launched, tuple(results), first, drift, reason)


def _manifest_digest(context: dict[str, object], key: str) -> str:
    manifest = context.get("implementation_manifest")
    digest = manifest.get(key) if isinstance(manifest, dict) else None
    if not isinstance(digest, str) or not composite._valid_digest(digest):
        raise ValueError("summary frozen-context digest is unavailable")
    return digest


def build_summary(
    selection: Selection, outcome: Outcome, *, binding: DriverBinding, context: dict[str, object],
) -> dict[str, object]:
    """Source-free parent evidence from frozen values only; it never rereads the filesystem."""
    accounting = selection.accounting
    cases: list[dict[str, object]] = []
    for index, case in enumerate(selection.cases):
        observed = outcome.results[index] if index < len(outcome.results) else None
        cases.append({
            "recipe_sha256": composite._recipe_sha256(case.recipe),
            "source_sha256": case.source_sha256,
            "classification": None if observed is None else observed.classification,
            "qualification": None if observed is None else observed.qualification_status,
        })
    first_index = None if outcome.first_non_pass is None else outcome.results.index(
        outcome.first_non_pass,
    )
    return {
        "schema": SUMMARY_SCHEMA,
        "driver_sha256": binding.sha256,
        "helper_sha256": _manifest_digest(context, HELPER_MANIFEST_KEY),
        "lock_sha256": _manifest_digest(context, LOCK_MANIFEST_KEY),
        "worker_provenance_sha256": composite._provenance_sha256(context),
        "cases": cases,
        "counts": {
            "body_calls": accounting.generated, "duplicates": accounting.duplicates,
            "dropped_at_cap": accounting.dropped_at_cap, "selected": accounting.selected,
            "attempted": outcome.attempted, "launched": outcome.launched,
            # Source-derived upper bound (two parses per child), not measured telemetry.
            "max_parser_calls_bound": 2 * outcome.launched,
        },
        "outcome": {
            "stop_reason": outcome.stop_reason, "first_non_pass_index": first_index,
            "drift_stage": None if outcome.drift is None else outcome.drift.stage,
            "qualified_success": outcome.qualified_success,
        },
    }


def _count(value: object) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("summary count is invalid")
    return value


def _summary_digest(value: object) -> str:
    if not isinstance(value, str) or not composite._valid_digest(value):
        raise ValueError("summary digest is invalid")
    return value


def validate_summary(summary: object) -> dict[str, object]:
    """Reject unknown/missing keys, wrong types, free text and inconsistent accounting."""
    if not isinstance(summary, dict) or set(summary) != SUMMARY_KEYS:
        raise ValueError("summary fields are invalid")
    if summary["schema"] != SUMMARY_SCHEMA:
        raise ValueError("summary schema mismatch")
    for key in ("driver_sha256", "helper_sha256", "lock_sha256", "worker_provenance_sha256"):
        _summary_digest(summary[key])
    counts, outcome, cases = summary["counts"], summary["outcome"], summary["cases"]
    if not isinstance(counts, dict) or set(counts) != COUNT_KEYS:
        raise ValueError("summary count fields are invalid")
    if not isinstance(outcome, dict) or set(outcome) != OUTCOME_KEYS:
        raise ValueError("summary outcome fields are invalid")
    if not isinstance(cases, list):
        raise ValueError("summary cases are invalid")
    generated, duplicates, dropped, selected, attempted, launched, bound = (
        _count(counts[key]) for key in (
            "body_calls", "duplicates", "dropped_at_cap", "selected", "attempted", "launched",
            "max_parser_calls_bound",
        )
    )
    if not 2 <= selected <= MAX_SELECTED or generated > MAX_BODY_CALLS:
        raise ValueError("summary budget exceeded")
    if generated != duplicates + dropped + selected - 1 or len(cases) != selected:
        raise ValueError("summary accounting is inconsistent")
    if not launched <= attempted <= selected or bound != 2 * launched:
        raise ValueError("summary launch accounting is inconsistent")
    sources: set[str] = set()
    seen_result: list[bool] = []
    for entry in cases:
        if not isinstance(entry, dict) or set(entry) != CASE_KEYS:
            raise ValueError("summary case fields are invalid")
        _summary_digest(entry["recipe_sha256"])
        sources.add(_summary_digest(entry["source_sha256"]))
        classification, qualification = entry["classification"], entry["qualification"]
        if (classification is None) != (qualification is None):
            raise ValueError("summary case result is inconsistent")
        if classification is not None and (
            classification not in composite.CLASSIFICATIONS or qualification not in QUALIFICATIONS
        ):
            raise ValueError("summary case classification is invalid")
        seen_result.append(classification is not None)
    observed = sum(seen_result)
    if seen_result != [True] * observed + [False] * (selected - observed):
        raise ValueError("summary observed results are not a prefix")
    if len(sources) != selected or observed > launched:
        raise ValueError("summary case set is inconsistent")
    reason, first, stage = outcome["stop_reason"], outcome["first_non_pass_index"], outcome[
        "drift_stage"
    ]
    success = outcome["qualified_success"]
    if reason not in STOP_REASONS or type(success) is not bool:
        raise ValueError("summary outcome is invalid")
    if stage is not None and stage not in DRIFT_STAGES:
        raise ValueError("summary drift stage is invalid")
    if first is not None and not (type(first) is int and first == observed - 1):
        raise ValueError("summary first non-pass index is not the last observed result")
    if stage not in {
        "complete": (None,), "first-non-pass": (None, "boundary"),
        "launch-refused": (None, "boundary"), "driver-drift-before-child": ("before-child",),
        "driver-drift-after-child": ("after-child",), "driver-drift-at-boundary": ("boundary",),
    }[reason]:
        raise ValueError("summary drift stage is inconsistent with the stop reason")
    clean = [e["classification"] == "parsed" and e["qualification"] == "qualified"
             for e in cases[:observed]]
    consistent = {
        "complete": attempted == launched == observed == selected and first is None and all(clean),
        "driver-drift-at-boundary": attempted == launched == observed == selected
        and first is None and all(clean),
        "first-non-pass": attempted == launched == observed >= 1 and first == observed - 1
        and all(clean[:-1]),
        "driver-drift-after-child": attempted == launched == observed >= 1
        and first == observed - 1 and all(clean[:-1])
        and cases[observed - 1]["qualification"] == "unqualified-source-drift",
        "driver-drift-before-child": attempted == launched + 1 and observed == launched
        and first is None and all(clean),
        "launch-refused": attempted == launched >= 1 and observed == launched - 1
        and first is None and all(clean),
    }[reason]
    if not consistent:
        raise ValueError(f"summary {reason} state is inconsistent")
    if success != (reason == "complete"):
        raise ValueError("summary qualified-success flag is inconsistent")
    return summary


def execute_invocation(
    *, module: types.ModuleType | None = None, repo_root: Path | None = None,
    helper_root: Path | None = None,
    collect: Callable[[], Selection] = collect_selected_cases,
    capture: Callable[[], dict[str, object]] = composite._capture_source_context,
    launch: Launch = composite.run_case, check: Check = check_driver,
) -> Invocation:
    """Admit the driver before anything else; collect; run; summarize."""
    binding = admit_driver(module=module, repo_root=repo_root, helper_root=helper_root)
    context = capture()
    selection = collect()
    outcome = run_selected(
        selection.cases, binding=binding, context=context, launch=launch, check=check,
    )
    try:
        summary: dict[str, object] | None = build_summary(
            selection, outcome, binding=binding, context=context,
        )
    except ValueError:  # frozen evidence invalid: keep the outcome, record no summary
        return Invocation(binding, context, selection, outcome, None, "summary-evidence-invalid")
    return Invocation(binding, context, selection, outcome, summary)


def _describe(result: composite.Result | None) -> str:
    if result is None:
        return "no preserved result"
    return (
        f"first non-pass: classification={result.classification} "
        f"exception_type={result.exception_type} qualification={result.qualification_status} "
        f"model_checked={result.model_checked} roundtrip_checked={result.roundtrip_checked} "
        f"differences={list(result.semantic_differences)} "
        f"recipe={json.dumps(asdict(result.recipe), sort_keys=True)} "
        f"source_sha256={result.source_sha256}"
    )


def _collect_without_parser() -> Selection:
    parse_calls: list[str] = []

    def forbidden_parse(*_args: object, **_kwargs: object) -> None:
        parse_calls.append("StackMachineParser.parse")
        raise AssertionError("parser execution forbidden during collection")

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(StackMachineParser, "parse", forbidden_parse)
        selection = collect_selected_cases()
    assert parse_calls == []
    return selection


@pytest.fixture
def forbid_parser_and_real_processes(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    parser_calls: list[str] = []
    process_calls: list[str] = []

    def forbidden_parse(*_args: object, **_kwargs: object) -> None:
        parser_calls.append("StackMachineParser.parse")
        raise AssertionError("parser execution forbidden in S4b controls")

    def forbidden_run(*_args: object, **_kwargs: object) -> None:
        process_calls.append("subprocess.run")
        raise AssertionError("real subprocess execution forbidden in S4b controls")

    monkeypatch.setattr(StackMachineParser, "parse", forbidden_parse)
    monkeypatch.setattr(composite.subprocess, "run", forbidden_run)
    monkeypatch.setattr(composite, "_revision", lambda *_a, **_k: composite.BASELINE_REVISION)
    yield
    assert parser_calls == []
    assert process_calls == []


parser_free = pytest.mark.usefixtures("forbid_parser_and_real_processes")
_WORKER_ARGV: Final = ("-m", "tests.parser_assurance.composite_properties", "--worker")


@pytest.fixture(scope="module")
def selection() -> Selection:
    return _collect_without_parser()


def _passing(case: composite.Case, context: dict[str, object] | None = None) -> composite.Result:
    return composite.Result(
        case.case_id, case.recipe.seed, case.recipe, case.source_sha256, case.source_bytes,
        "parsed", None, True, True, source_context=context,
    )


class _FakeLaunch:
    """Records every launch; a signature without `timeout_seconds` proves the default is kept."""

    def __init__(
        self, mutate: Callable[[int, composite.Result], composite.Result] | None = None,
    ) -> None:
        self.cases: list[composite.Case] = []
        self.contexts: list[dict[str, object] | None] = []
        self.mutate = mutate

    def __call__(
        self, case: composite.Case, *, expected_context: dict[str, object] | None = None,
    ) -> composite.Result:
        index = len(self.cases)
        self.cases.append(case)
        self.contexts.append(expected_context)
        result = _passing(case, expected_context)
        return result if self.mutate is None else self.mutate(index, result)


def _refusing_launch(
    case: composite.Case, *, expected_context: dict[str, object] | None = None,
) -> composite.Result:
    raise ValueError("source context drift before child")


class _ScriptedCheck:
    """Returns exactly the scripted driver statuses; any extra gate is a test failure."""

    def __init__(self, *statuses: DriverStatus) -> None:
        self.statuses = list(statuses)
        self.calls = 0

    @classmethod
    def intact(cls, count: int, *then: DriverStatus) -> _ScriptedCheck:
        ok: DriverStatus = "intact"
        return cls(*[ok] * count, *then)

    def __call__(self, binding: DriverBinding) -> DriverStatus:
        self.calls += 1
        assert self.statuses, "unexpected extra driver check"
        return self.statuses.pop(0)


_BINDING = DriverBinding(Path("driver.py"), "0" * 64, Path("."), Path("."))
_CONTEXT: dict[str, object] = {"revision": "a" * 40}


def _validated_summary(chosen: Selection, outcome: Outcome) -> dict[str, object]:
    return validate_summary(build_summary(
        chosen, outcome, binding=admit_driver(), context=composite._capture_source_context(),
    ))


def _fake_repo(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    (root / "tests").mkdir(parents=True)
    driver = root / DRIVER_RELATIVE
    driver.write_text("# fake driver\n", encoding="utf-8")
    return root, driver


def _fake_module(
    origin: Path | None, *, spec_origin: Path | None = None, spec: bool = True,
) -> types.ModuleType:
    module = types.ModuleType("tests.fake_s4b_driver")
    module.__file__ = None if origin is None else str(origin)
    module.__spec__ = importlib.machinery.ModuleSpec(
        module.__name__, None, origin=str(spec_origin or origin),
    ) if spec else None
    return module


def _require_symlinks(directory: Path) -> None:
    probe = directory / "symlink-probe"
    try:
        probe.symlink_to(directory, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links unavailable on this platform")
    probe.unlink()


def _replace_tests_with_same_byte_symlink(root: Path) -> None:
    shutil.copytree(root / "tests", root / "tests_copy")
    shutil.rmtree(root / "tests")
    (root / "tests").symlink_to(root / "tests_copy", target_is_directory=True)


def _small_selection(count: int) -> Selection:
    """Controlled finite selection of distinct in-domain recipes; no refill or new seeds."""
    recipes = [
        replace(composite.Recipe.literal_example(), task=task, priority=priority)
        for task, priority in product(composite.TASKS, composite.PRIORITIES)
    ]
    cases = tuple(composite.build_case(recipe) for recipe in recipes[:count])
    assert len(cases) == count and len({case.source_sha256 for case in cases}) == count
    for case in cases:
        enforce_domain(case)
    return Selection(cases, Accounting(count, 1, 0, count))


def _context_with(**manifest: str | None) -> dict[str, object]:
    """A valid captured context whose named manifest digests are replaced (None removes one)."""
    base = composite._capture_source_context()
    files = dict(cast(dict[str, str], base["implementation_manifest"]))
    for key, digest in manifest.items():
        if digest is None:
            del files[key]
        else:
            files[key] = digest
    return {**base, "implementation_manifest": files}


def _edited(
    summary: dict[str, object], *changes: tuple[tuple[str | int, ...], object],
) -> dict[str, object]:
    clone: dict[str, object] = json.loads(json.dumps(summary))
    for path, value in changes:
        node: Any = clone
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value
    return clone


@parser_free
def test_design_constants_and_hypothesis_settings_are_exact() -> None:
    assert (SELECTED_SHAPES, RECIPE_SEED, MAX_SELECTED, MAX_BODY_CALLS) == (
        ("root-child-sibling", "siblings"), 104, 32, 48,
    )
    assert (MAX_NODES, MAX_DEPTH, MAX_SOURCE_BYTES) == (3, 1, 2048)
    assert composite.MAX_TIMEOUT_SECONDS == 3.0
    effective = COLLECTION_SETTINGS
    assert effective.max_examples == 32 and effective.derandomize is True
    assert effective.database is None and effective.deadline is None
    assert effective.phases == (Phase.generate,) and effective.report_multiple_bugs is False
    assert effective.print_blob is False and tuple(effective.suppress_health_check) == ()
    assert inspect.signature(composite.run_case).parameters["timeout_seconds"].default == 3.0


@parser_free
def test_default_wiring_launches_real_children_and_checks_the_real_driver() -> None:
    orchestrated = inspect.signature(execute_invocation).parameters
    assert {name: parameter.default for name, parameter in orchestrated.items()} == {
        "module": None, "repo_root": None, "helper_root": None, "collect": collect_selected_cases,
        "capture": composite._capture_source_context, "launch": composite.run_case,
        "check": check_driver,
    }
    runner = inspect.signature(run_selected).parameters
    assert runner["launch"].default is composite.run_case
    assert runner["check"].default is check_driver
    assert orchestrated["launch"].default is runner["launch"].default
    assert orchestrated["check"].default is runner["check"].default


def _applied(applied: settings, *, seeded: bool = False) -> Callable[[], None]:
    @applied
    @given(recipe=selected_recipes())
    def probe(recipe: composite.Recipe) -> None: ...

    return hypothesis_seed(7)(probe) if seeded else probe


@parser_free
@pytest.mark.parametrize("change", [
    {"max_examples": 40}, {"derandomize": False}, {"deadline": 200},
    {"database": InMemoryExampleDatabase()}, {"phases": (Phase.generate, Phase.shrink)},
    {"report_multiple_bugs": True}, {"print_blob": True},
    {"suppress_health_check": (HealthCheck.too_slow,)}, {"verbosity": Verbosity.verbose},
    {"stateful_step_count": 10}, "seed", "undecorated",
])
def test_applied_settings_guard_refuses_any_loosening_seed_or_missing_marker(
    change: dict[str, Any] | str,
) -> None:
    _require_applied_settings(_applied(COLLECTION_SETTINGS))
    equal_copy = settings(
        max_examples=32, derandomize=True, database=None, deadline=None,
        phases=(Phase.generate,), report_multiple_bugs=False, print_blob=False,
        suppress_health_check=(),
    )
    _require_applied_settings(_applied(equal_copy))
    if change == "undecorated":
        target: object = _applied
    elif change == "seed":
        target = _applied(COLLECTION_SETTINGS, seeded=True)
    else:
        assert isinstance(change, dict)
        target = _applied(settings(COLLECTION_SETTINGS, **change))
    with pytest.raises(SelectionError, match="differs from the approved design"):
        _require_applied_settings(target)


@parser_free
@pytest.mark.parametrize("function", [selected_recipes, collect_selected_cases])
def test_selection_source_has_no_seed_assume_filter_reject_or_second_settings(
    function: Callable[..., object],
) -> None:
    source = inspect.getsource(function)
    assert "@COLLECTION_SETTINGS" in source or function is selected_recipes
    for forbidden in (r"\bseed\(", r"\bassume\(", r"\.filter\(", r"\breject\(",
                      r"\bsettings\(", r"\bflatmap\("):
        assert re.search(forbidden, source) is None, forbidden


@parser_free
def test_collector_checks_its_inner_test_settings_before_any_body_runs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_guard, seen = _require_applied_settings, []

    def recording(test: object) -> None:
        seen.append(test)
        real_guard(test)

    monkeypatch.setitem(globals(), "_require_applied_settings", recording)
    assert 0 < collect_selected_cases().accounting.generated <= COLLECTION_SETTINGS.max_examples
    assert len(seen) == 1 and callable(seen[0])

    def refusing(_test: object) -> None:
        raise SelectionError("controlled refusal")

    monkeypatch.setitem(globals(), "_require_applied_settings", refusing)
    budget = _BodyBudget()
    with pytest.raises(SelectionError, match="controlled refusal"):
        collect_selected_cases(budget=budget)
    assert budget.admitted == 0


@parser_free
def test_baseline_is_inside_the_selected_domain_and_hand_calibrated() -> None:
    baseline = composite.build_case(composite.Recipe.literal_example())
    enforce_domain(baseline)
    assert baseline.recipe.seed == RECIPE_SEED and baseline.recipe.shape in SELECTED_SHAPES
    assert baseline.source_sha256 == composite.DIAGNOSTIC_SOURCE_SHA256


@parser_free
@pytest.mark.parametrize("violation", ["seed", "shape", "nodes", "depth", "bytes"])
def test_domain_enforcement_rejects_each_single_violation(violation: str) -> None:
    case = composite.build_case(composite.Recipe.literal_example())
    changed = {
        "seed": replace(case, recipe=replace(case.recipe, seed=417)),
        "shape": replace(case, recipe=replace(case.recipe, shape="nested")),
        "nodes": replace(case, expected=case.expected * 2),
        "depth": replace(case, expected=(replace(case.expected[0], depth=2), *case.expected[1:])),
        "bytes": replace(case, source=case.source + "x" * MAX_SOURCE_BYTES),
    }[violation]
    enforce_domain(case)
    with pytest.raises(DomainViolation, match=f": {violation}$"):
        enforce_domain(changed)


@parser_free
def test_body_budget_admits_48_and_refuses_49_before_work() -> None:
    budget = _BodyBudget()
    for _ in range(MAX_BODY_CALLS):
        budget.admit()
    assert budget.admitted == 48
    with pytest.raises(BodyBudgetExceeded):
        budget.admit()
    assert budget.admitted == 48


@parser_free
def test_collector_refuses_49th_body_before_any_collection_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    work: list[str] = []
    build, validate = composite.build_case, composite._validate

    def counted_build(recipe: composite.Recipe) -> composite.Case:
        work.append("build")
        return build(recipe)

    def counted_validate(recipe: composite.Recipe) -> None:
        work.append("validate")
        validate(recipe)

    monkeypatch.setattr(composite, "build_case", counted_build)
    monkeypatch.setattr(composite, "_validate", counted_validate)
    with pytest.raises(BodyBudgetExceeded):
        collect_selected_cases(budget=_BodyBudget(admitted=MAX_BODY_CALLS))
    assert work == ["build", "validate"]  # only the baseline; no generated body did any work


@parser_free
def test_collector_selection_is_bounded_distinct_in_domain_and_accounted() -> None:
    budget = _BodyBudget()
    chosen = collect_selected_cases(budget=budget)
    cases, accounting = chosen.cases, chosen.accounting
    assert cases[0] == composite.build_case(composite.Recipe.literal_example())
    assert 2 <= len(cases) <= MAX_SELECTED and accounting.selected == len(cases)
    assert len({case.source_sha256 for case in cases}) == len(cases)
    assert len({case.recipe for case in cases}) == len(cases)
    for case in cases:
        enforce_domain(case)
        assert case.recipe.seed == 104 and case.recipe.shape in SELECTED_SHAPES
        assert len(composite._flatten_expected(case.expected)) <= 3
        assert max(block.depth for block in composite._flatten_expected(case.expected)) <= 1
        assert case.source_bytes <= 2048
    assert any(case.recipe != cases[0].recipe for case in cases[1:])
    assert accounting.generated == budget.admitted <= MAX_SELECTED
    assert accounting.generated == (
        accounting.duplicates + accounting.dropped_at_cap + accounting.selected - 1
    )
    assert {case.recipe.shape for case in cases} <= set(SELECTED_SHAPES)


@parser_free
def test_collector_cap_branch_drops_surplus_sources_and_keeps_accounting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    finite = [case.recipe for case in _small_selection(18).cases]
    monkeypatch.setitem(globals(), "selected_recipes", lambda: st.sampled_from(finite))
    monkeypatch.setitem(globals(), "MAX_SELECTED", 10)
    capped = collect_selected_cases()
    accounting = capped.accounting
    assert accounting.selected == len(capped.cases) == 10
    assert capped.cases[0].recipe == composite.Recipe.literal_example()
    assert {case.recipe for case in capped.cases} <= set(finite)
    assert accounting.dropped_at_cap > 0 and accounting.duplicates >= 1
    assert accounting.generated == (
        accounting.duplicates + accounting.dropped_at_cap + accounting.selected - 1
    )
    assert len({case.source_sha256 for case in capped.cases}) == 10


@parser_free
def test_collector_is_deterministic_across_calls() -> None:
    first, second = collect_selected_cases(), collect_selected_cases()
    assert [case.recipe for case in first.cases] == [case.recipe for case in second.cases]
    assert first.accounting == second.accounting


@parser_free
def test_collector_fails_closed_without_a_generated_non_baseline_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline_only = st.just(composite.Recipe.literal_example())
    monkeypatch.setitem(globals(), "selected_recipes", lambda: baseline_only)
    with pytest.raises(SelectionError, match="non-baseline"):
        collect_selected_cases()


@parser_free
def test_collector_fails_closed_on_out_of_domain_generated_recipe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outside = replace(composite.Recipe.literal_example(), shape="nested")
    monkeypatch.setitem(globals(), "selected_recipes", lambda: st.just(outside))
    with pytest.raises(DomainViolation):
        collect_selected_cases()


@parser_free
def test_driver_admission_binds_regular_nonsymlinked_repository_origin(tmp_path: Path) -> None:
    root, driver = _fake_repo(tmp_path)
    binding = admit_driver(module=_fake_module(driver), repo_root=root, helper_root=root)
    assert binding.origin == driver.resolve()
    assert binding.sha256 == hashlib.sha256(driver.read_bytes()).hexdigest()
    real = admit_driver()
    assert Path(__file__).resolve().parents[1] == Path(composite.__file__).resolve().parents[2]
    assert real.origin == Path(__file__).resolve()
    assert real.sha256 == hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    assert check_driver(real) == "intact"


@parser_free
@pytest.mark.parametrize("kind", [
    "symlink", "directory", "outside-root", "wrong-name", "missing", "unreadable",
    "origin-mismatch", "no-spec", "no-file", "root-mismatch", "tests-symlink",
])
def test_driver_admission_rejects_before_collection_capture_and_launch(
    kind: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, driver = _fake_repo(tmp_path)
    other = root / "tests" / "test_other.py"
    other.write_text("# other\n", encoding="utf-8")
    outside = tmp_path / "outside" / "test_parser_mixed_markdown_properties.py"
    outside.parent.mkdir()
    outside.write_text("# outside\n", encoding="utf-8")
    module = _fake_module(driver)
    expected = {
        "symlink": "symlink", "directory": "not-regular", "outside-root": "path",
        "wrong-name": "path", "missing": "unreadable", "unreadable": "unreadable",
        "origin-mismatch": "origin-mismatch", "no-spec": "origin-unavailable",
        "no-file": "origin-unavailable", "root-mismatch": "root", "tests-symlink": "tests-symlink",
    }[kind]
    helper_root = root
    if kind == "symlink":
        driver.unlink()
        try:
            driver.symlink_to(other)
        except OSError:
            pytest.skip("symbolic links unavailable on this platform")
    elif kind == "directory":
        driver.unlink()
        driver.mkdir()
    elif kind == "outside-root":
        module = _fake_module(outside)
    elif kind == "wrong-name":
        module = _fake_module(other)
    elif kind == "missing":
        driver.unlink()
    elif kind == "unreadable":
        def unreadable(_self: Path) -> bytes:
            raise PermissionError("controlled unreadable origin")

        monkeypatch.setattr(Path, "read_bytes", unreadable)
    elif kind == "root-mismatch":
        helper_root = tmp_path / "other-root"
        helper_root.mkdir()
    elif kind == "tests-symlink":
        (root / "tests").rename(root / "real_tests")
        try:
            (root / "tests").symlink_to(root / "real_tests", target_is_directory=True)
        except OSError:
            pytest.skip("symbolic links unavailable on this platform")
    elif kind == "origin-mismatch":
        module = _fake_module(driver, spec_origin=other)
    elif kind == "no-spec":
        module = _fake_module(driver, spec=False)
    else:
        module = _fake_module(None)
    calls: list[str] = []
    launch = _FakeLaunch()

    def collect() -> Selection:
        calls.append("collect")
        raise AssertionError("collection must not run")

    def capture() -> dict[str, object]:
        calls.append("capture")
        raise AssertionError("context capture must not run")

    with pytest.raises(DriverProvenanceError) as caught:
        execute_invocation(
            module=module, repo_root=root, helper_root=helper_root, collect=collect,
            capture=capture, launch=launch,
        )
    assert caught.value.reason == expected
    assert calls == [] and launch.cases == []


@parser_free
def test_driver_check_reports_intact_drift_and_unavailable(tmp_path: Path) -> None:
    root, driver = _fake_repo(tmp_path)
    binding = admit_driver(module=_fake_module(driver), repo_root=root, helper_root=root)
    assert check_driver(binding) == "intact"
    driver.write_text("# edited driver\n", encoding="utf-8")
    assert check_driver(binding) == "drift"
    driver.unlink()
    assert check_driver(binding) == "unavailable"
    target = root / "tests" / "target.py"
    target.write_text("# fake driver\n", encoding="utf-8")
    try:
        driver.symlink_to(target)
    except OSError:
        pytest.skip("symbolic links unavailable on this platform")
    assert hashlib.sha256(target.read_bytes()).hexdigest() == binding.sha256
    assert check_driver(binding) == "drift"


@parser_free
@pytest.mark.parametrize("variant", ["explicit-root", "default-root", "default-helper"])
def test_driver_admission_normalizes_resolution_runtime_error(
    tmp_path: Path, variant: str,
) -> None:
    root, driver = _fake_repo(tmp_path)
    target = (
        Path(__file__) if variant == "default-root" else
        Path(composite.__file__) if variant == "default-helper" else root
    )
    resolve = Path.resolve
    events: list[str] = []

    def resolution_loop(path: Path, strict: bool = False) -> Path:
        if path == target:
            raise RuntimeError("controlled symlink-resolution loop")
        return resolve(path, strict=strict)

    def forbidden_capture() -> dict[str, object]:
        events.append("capture")
        raise AssertionError("inadmissible driver must not capture")

    def forbidden_collect() -> Selection:
        events.append("collect")
        raise AssertionError("inadmissible driver must not collect")

    launch = _FakeLaunch()
    with pytest.raises(DriverProvenanceError) as caught:
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(Path, "resolve", resolution_loop)
            execute_invocation(
                module=_fake_module(driver),
                repo_root=None if variant == "default-root" else root,
                helper_root=None if variant == "default-helper" else root,
                capture=forbidden_capture, collect=forbidden_collect, launch=launch,
            )
    assert caught.value.reason == "unreadable"
    assert events == [] and launch.cases == []


@parser_free
@pytest.mark.parametrize("stage", ["before-child", "after-child", "boundary"])
def test_resolution_runtime_error_preserves_driver_gate_stop_and_outcome(
    tmp_path: Path, stage: str,
) -> None:
    root, driver = _fake_repo(tmp_path)
    binding = admit_driver(module=_fake_module(driver), repo_root=root, helper_root=root)
    cases, launch = _small_selection(2).cases, _FakeLaunch()
    resolve = Path.resolve
    enabled, checks = stage == "before-child", 0

    def resolution_loop(path: Path, strict: bool = False) -> Path:
        if enabled and path == binding.root:
            raise RuntimeError("controlled symlink-resolution loop")
        return resolve(path, strict=strict)

    def checked(selected: DriverBinding) -> DriverStatus:
        nonlocal enabled, checks
        checks += 1
        if stage == "boundary" and checks == 5:
            enabled = True
        return check_driver(selected)

    def controlled_launch(
        case: composite.Case, *, expected_context: dict[str, object] | None = None,
    ) -> composite.Result:
        nonlocal enabled
        result = launch(case, expected_context=expected_context)
        if stage == "after-child":
            enabled = True
        return result

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(Path, "resolve", resolution_loop)
        outcome = run_selected(
            cases, binding=binding, context=_CONTEXT, launch=controlled_launch, check=checked,
        )
    expected_count = {"before-child": 0, "after-child": 1, "boundary": 2}[stage]
    assert launch.cases == list(cases[:expected_count])
    assert outcome.launched == len(outcome.results) == expected_count
    assert checks == {"before-child": 1, "after-child": 2, "boundary": 5}[stage]
    assert outcome.drift == {
        "before-child": Drift("before-child", 0, "unavailable"),
        "after-child": Drift("after-child", 0, "unavailable"),
        "boundary": Drift("boundary", None, "unavailable"),
    }[stage]
    assert not outcome.qualified_success
    assert all(result.source_context is _CONTEXT for result in outcome.results)
    if stage == "after-child":
        (saved,) = outcome.results
        assert outcome.first_non_pass is saved and saved.recipe == cases[0].recipe
        assert saved.classification == "parsed" and saved.model_checked is True
        assert saved.roundtrip_checked is True and saved.exception_type is None
        assert saved.semantic_differences == ()
        assert saved.qualification_status == "unqualified-source-drift"
        assert outcome.stop_reason == "driver-drift-after-child"
    else:
        assert outcome.first_non_pass is None
        assert all(_is_pass(result) for result in outcome.results)
        assert outcome.stop_reason == {
            "before-child": "driver-drift-before-child", "boundary": "driver-drift-at-boundary",
        }[stage]


@parser_free
def test_same_byte_tests_directory_symlink_is_not_intact_at_a_driver_gate(tmp_path: Path) -> None:
    _require_symlinks(tmp_path)
    root, driver = _fake_repo(tmp_path)
    binding = admit_driver(module=_fake_module(driver), repo_root=root, helper_root=root)
    assert check_driver(binding) == "intact"
    _replace_tests_with_same_byte_symlink(root)
    assert hashlib.sha256(driver.read_bytes()).hexdigest() == binding.sha256
    assert (root / "tests").is_symlink() and check_driver(binding) == "drift"


@parser_free
def test_same_byte_tests_directory_symlink_denies_the_next_launch(
    selection: Selection, tmp_path: Path,
) -> None:
    _require_symlinks(tmp_path)
    root, driver = _fake_repo(tmp_path)
    binding = admit_driver(module=_fake_module(driver), repo_root=root, helper_root=root)
    _replace_tests_with_same_byte_symlink(root)
    launch = _FakeLaunch()
    outcome = run_selected(
        selection.cases, binding=binding, context=_CONTEXT, launch=launch, check=check_driver,
    )
    assert launch.cases == [] and (outcome.attempted, outcome.launched) == (1, 0)
    assert outcome.drift == Drift("before-child", 0, "drift") and outcome.results == ()
    assert outcome.stop_reason == "driver-drift-before-child" and not outcome.qualified_success


@parser_free
def test_same_byte_tests_directory_symlink_after_a_child_preserves_it_as_unqualified(
    selection: Selection, tmp_path: Path,
) -> None:
    _require_symlinks(tmp_path)
    root, driver = _fake_repo(tmp_path)
    binding = admit_driver(module=_fake_module(driver), repo_root=root, helper_root=root)
    launch = _FakeLaunch()

    def swapping_launch(
        case: composite.Case, *, expected_context: dict[str, object] | None = None,
    ) -> composite.Result:
        result = launch(case, expected_context=expected_context)
        _replace_tests_with_same_byte_symlink(root)
        return result

    outcome = run_selected(
        selection.cases, binding=binding, context=_CONTEXT, launch=swapping_launch,
        check=check_driver,
    )
    (attempt,) = outcome.results
    assert launch.cases == [selection.cases[0]] and outcome.first_non_pass is attempt
    assert (attempt.classification, attempt.model_checked) == ("parsed", True)
    assert attempt.qualification_status == "unqualified-source-drift"
    assert attempt.source_context is _CONTEXT
    assert outcome.drift == Drift("after-child", 0, "drift") and not outcome.qualified_success
    assert outcome.stop_reason == "driver-drift-after-child"


@parser_free
def test_symlinks_above_the_repository_root_remain_admitted(tmp_path: Path) -> None:
    _require_symlinks(tmp_path)
    (tmp_path / "real").mkdir()
    root, driver = _fake_repo(tmp_path / "real")
    (tmp_path / "alias").symlink_to(tmp_path / "real", target_is_directory=True)
    aliased = tmp_path / "alias" / "repo"
    binding = admit_driver(
        module=_fake_module(aliased / DRIVER_RELATIVE), repo_root=aliased, helper_root=root,
    )
    assert binding.origin == driver.resolve() and check_driver(binding) == "intact"


@parser_free
@pytest.mark.parametrize("status", ["drift", "unavailable"])
def test_drift_before_first_child_denies_launch(selection: Selection, status: DriverStatus) -> None:
    launch, check = _FakeLaunch(), _ScriptedCheck(status)
    outcome = run_selected(
        selection.cases, binding=_BINDING, context=_CONTEXT, launch=launch, check=check,
    )
    assert launch.cases == [] and (outcome.attempted, outcome.launched) == (1, 0)
    assert outcome.results == () and outcome.first_non_pass is None
    assert outcome.drift == Drift("before-child", 0, status)
    assert outcome.stop_reason == "driver-drift-before-child"
    assert not outcome.qualified_success and check.calls == 1
    _validated_summary(selection, outcome)


@parser_free
def test_drift_before_second_child_denies_that_launch_only(selection: Selection) -> None:
    launch, check = _FakeLaunch(), _ScriptedCheck("intact", "intact", "drift")
    outcome = run_selected(
        selection.cases, binding=_BINDING, context=_CONTEXT, launch=launch, check=check,
    )
    assert launch.cases == [selection.cases[0]] and (outcome.attempted, outcome.launched) == (2, 1)
    assert len(outcome.results) == 1 and _is_pass(outcome.results[0])
    assert outcome.drift == Drift("before-child", 1, "drift") and not outcome.qualified_success
    _validated_summary(selection, outcome)


@parser_free
def test_drift_after_child_preserves_unqualified_attempt_with_original_context(
    selection: Selection,
) -> None:
    launch, check = _FakeLaunch(), _ScriptedCheck("intact", "drift")
    outcome = run_selected(
        selection.cases, binding=_BINDING, context=_CONTEXT, launch=launch, check=check,
    )
    assert launch.cases == [selection.cases[0]] and (outcome.attempted, outcome.launched) == (1, 1)
    (attempt,) = outcome.results
    assert outcome.first_non_pass is attempt and attempt.source_context is _CONTEXT
    assert attempt.qualification_status == "unqualified-source-drift"
    assert (attempt.classification, attempt.model_checked, attempt.roundtrip_checked) == (
        "parsed", True, True,
    )
    assert attempt.recipe == selection.cases[0].recipe and not _is_pass(attempt)
    assert outcome.drift == Drift("after-child", 0, "drift")
    assert outcome.stop_reason == "driver-drift-after-child" and not outcome.qualified_success
    assert check.calls == 2 and launch.contexts == [_CONTEXT]
    with pytest.raises(FrozenInstanceError):
        attempt.qualification_status = "qualified"  # type: ignore[misc]
    assert _validated_summary(selection, outcome)["outcome"] == {
        "stop_reason": "driver-drift-after-child", "first_non_pass_index": 0,
        "drift_stage": "after-child", "qualified_success": False,
    }


@parser_free
def test_drift_after_non_pass_child_keeps_classification_and_denies_qualification(
    selection: Selection,
) -> None:
    def timed_out(_index: int, result: composite.Result) -> composite.Result:
        return replace(
            result, classification="timeout", model_checked=False, roundtrip_checked=False,
        )

    outcome = run_selected(
        selection.cases, binding=_BINDING, context=_CONTEXT, launch=_FakeLaunch(timed_out),
        check=_ScriptedCheck("intact", "unavailable"),
    )
    (attempt,) = outcome.results
    assert attempt.classification == "timeout" and outcome.first_non_pass is attempt
    assert attempt.qualification_status == "unqualified-source-drift"
    assert outcome.drift == Drift("after-child", 0, "unavailable") and outcome.launched == 1


@parser_free
def test_boundary_drift_is_recorded_without_rewriting_observed_results(
    selection: Selection,
) -> None:
    check = _ScriptedCheck.intact(2 * len(selection.cases), "drift")
    outcome = run_selected(
        selection.cases, binding=_BINDING, context=_CONTEXT, launch=_FakeLaunch(), check=check,
    )
    assert outcome.launched == len(selection.cases) and check.statuses == []
    assert all(_is_pass(result) for result in outcome.results)
    assert outcome.drift == Drift("boundary", None, "drift")
    assert outcome.stop_reason == "driver-drift-at-boundary" and not outcome.qualified_success
    _validated_summary(selection, outcome)


@parser_free
def test_cadence_checks_before_and_after_every_child_and_at_the_boundary(
    selection: Selection,
) -> None:
    events: list[str] = []
    launch, check = _FakeLaunch(), _ScriptedCheck.intact(2 * len(selection.cases) + 1)

    def traced_check(binding: DriverBinding) -> DriverStatus:
        events.append("check")
        return check(binding)

    def traced_launch(
        case: composite.Case, *, expected_context: dict[str, object] | None = None,
    ) -> composite.Result:
        events.append("launch")
        return launch(case, expected_context=expected_context)

    outcome = run_selected(
        selection.cases, binding=_BINDING, context=_CONTEXT, launch=traced_launch,
        check=traced_check,
    )
    assert events == ["check", "launch", "check"] * len(selection.cases) + ["check"]
    assert outcome.qualified_success and outcome.stop_reason == "complete"
    assert outcome.attempted == outcome.launched == len(selection.cases) <= MAX_SELECTED
    assert launch.cases == list(selection.cases)
    assert launch.contexts == [_CONTEXT] * len(selection.cases)
    assert check.statuses == []


@parser_free
def test_execute_invocation_fake_wired_runs_admit_capture_collect_run_in_order(
    selection: Selection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    bindings: list[DriverBinding] = []
    real_admit, context = admit_driver, composite._capture_source_context()
    launch = _FakeLaunch()

    def traced_admit(
        *, module: types.ModuleType | None = None, repo_root: Path | None = None,
        helper_root: Path | None = None,
    ) -> DriverBinding:
        events.append("admit")
        return real_admit(module=module, repo_root=repo_root, helper_root=helper_root)

    def capture() -> dict[str, object]:
        events.append("capture")
        return context

    def collect() -> Selection:
        events.append("collect")
        return selection

    def traced_launch(
        case: composite.Case, *, expected_context: dict[str, object] | None = None,
    ) -> composite.Result:
        events.append("launch")
        return launch(case, expected_context=expected_context)

    def traced_check(binding: DriverBinding) -> DriverStatus:
        events.append("check")
        bindings.append(binding)
        return "intact"

    monkeypatch.setitem(globals(), "admit_driver", traced_admit)
    invocation = execute_invocation(
        collect=collect, capture=capture, launch=traced_launch, check=traced_check,
    )
    count = len(selection.cases)
    assert events == ["admit", "capture", "collect", *["check", "launch", "check"] * count, "check"]
    assert invocation.context is context and invocation.selection is selection
    assert launch.cases == list(selection.cases)
    assert all(seen is context for seen in launch.contexts) and len(launch.contexts) == count
    assert all(result.source_context is context for result in invocation.outcome.results)
    assert len(bindings) == 2 * count + 1 and all(b is invocation.binding for b in bindings)
    assert invocation.binding.origin == Path(__file__).resolve()
    assert invocation.outcome.qualified_success
    assert validate_summary(invocation.summary) is invocation.summary


@parser_free
@pytest.mark.parametrize("damage", ["changed", "unavailable"])
def test_summary_keeps_frozen_digests_when_helper_or_lock_changes_after_a_child(
    selection: Selection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, damage: str,
) -> None:
    root, driver = _fake_repo(tmp_path)
    helper, lock = root / HELPER_MANIFEST_KEY, root / LOCK_MANIFEST_KEY
    helper.parent.mkdir(parents=True)
    helper.write_text("# helper\n", encoding="utf-8")
    lock.write_text("# lock\n", encoding="utf-8")
    digests = tuple(hashlib.sha256(path.read_bytes()).hexdigest() for path in (helper, lock))
    context = _context_with(**{HELPER_MANIFEST_KEY: digests[0], LOCK_MANIFEST_KEY: digests[1]})
    monkeypatch.setattr(composite, "__file__", str(helper))
    inner = _FakeLaunch(lambda _index, result: _timeout(result))

    def damaging_launch(
        case: composite.Case, *, expected_context: dict[str, object] | None = None,
    ) -> composite.Result:
        result = inner(case, expected_context=expected_context)
        for path in (helper, lock):
            if damage == "changed":
                path.write_text("# changed after the child\n", encoding="utf-8")
            else:
                path.unlink()
        return result

    invocation = execute_invocation(
        module=_fake_module(driver), repo_root=root, helper_root=root,
        collect=lambda: selection, capture=lambda: context, launch=damaging_launch,
        check=_ScriptedCheck.intact(3),
    )
    assert invocation.summary_error is None and invocation.summary is not None
    summary = validate_summary(invocation.summary)
    assert (summary["helper_sha256"], summary["lock_sha256"]) == digests
    assert summary["worker_provenance_sha256"] == composite._provenance_sha256(context)
    outcome = invocation.outcome
    (attempt,) = outcome.results
    assert invocation.context is context and attempt.source_context is context
    assert outcome.first_non_pass is attempt and attempt.classification == "timeout"
    assert outcome.stop_reason == "first-non-pass" and outcome.launched == 1


@parser_free
@pytest.mark.parametrize("defect", ["no-helper", "no-lock", "bad-helper", "bad-lock"])
def test_missing_or_invalid_frozen_digests_fail_closed_but_keep_the_outcome(
    selection: Selection, defect: str,
) -> None:
    key = HELPER_MANIFEST_KEY if defect.endswith("helper") else LOCK_MANIFEST_KEY
    context = _context_with(**{key: None if defect.startswith("no") else "not-a-digest"})
    launch = _FakeLaunch()
    invocation = execute_invocation(
        collect=lambda: selection, capture=lambda: context, launch=launch,
        check=_ScriptedCheck.intact(2 * len(selection.cases) + 1),
    )
    assert invocation.summary is None and invocation.summary_error == "summary-evidence-invalid"
    assert invocation.context is context and invocation.outcome.qualified_success
    assert launch.cases == list(selection.cases)
    assert all(result.source_context is context for result in invocation.outcome.results)
    assert invocation.binding.origin == Path(__file__).resolve()


def _timeout(result: composite.Result) -> composite.Result:
    return replace(result, classification="timeout", model_checked=False, roundtrip_checked=False)


def _runner_failure(result: composite.Result) -> composite.Result:
    return replace(
        result, classification="runner_failure", exception_type="ChildProcessExit",
        model_checked=False, roundtrip_checked=False,
    )


def _roundtrip_failure(result: composite.Result) -> composite.Result:
    return replace(
        result, classification="semantic_roundtrip_failure",
        exception_type="SemanticRoundtripMismatch", roundtrip_checked=False,
        semantic_differences=({"field": "properties", "outline_path": [1]},),
    )


def _unqualified(result: composite.Result) -> composite.Result:
    return replace(result, qualification_status="unqualified-source-drift")


@parser_free
@pytest.mark.parametrize("failure", [_timeout, _runner_failure, _roundtrip_failure, _unqualified])
@pytest.mark.parametrize("where", ["first", "middle", "last"])
@pytest.mark.parametrize("size", [None, 2, 7])
def test_first_non_pass_is_preserved_unchanged_and_stops_immediately(
    selection: Selection, size: int | None, where: str,
    failure: Callable[[composite.Result], composite.Result],
) -> None:
    chosen = selection if size is None else _small_selection(size)
    cases = chosen.cases
    position = {"first": 1, "middle": (len(cases) + 1) // 2, "last": len(cases)}[where]
    launch = _FakeLaunch(lambda index, result: failure(result) if index == position - 1 else result)
    check = _ScriptedCheck.intact(2 * position + 1)
    outcome = run_selected(cases, binding=_BINDING, context=_CONTEXT, launch=launch, check=check)
    bad_case = cases[position - 1]
    assert launch.cases == list(cases[:position])
    assert (outcome.attempted, outcome.launched) == (position, position)
    assert len(outcome.results) == position and outcome.results[-1] is outcome.first_non_pass
    assert outcome.first_non_pass == failure(_passing(bad_case, _CONTEXT))
    assert outcome.first_non_pass is not None and outcome.first_non_pass.recipe == bad_case.recipe
    assert all(_is_pass(result) for result in outcome.results[:-1])
    assert outcome.stop_reason == "first-non-pass" and outcome.drift is None
    assert not outcome.qualified_success and check.statuses == []
    with pytest.raises(FrozenInstanceError):
        outcome.first_non_pass.classification = "parsed"  # type: ignore[misc]
    assert _validated_summary(chosen, outcome)["outcome"] == {
        "stop_reason": "first-non-pass", "first_non_pass_index": position - 1,
        "drift_stage": None, "qualified_success": False,
    }


@parser_free
def test_result_for_a_different_case_is_not_a_pass(selection: Selection) -> None:
    def foreign(index: int, result: composite.Result) -> composite.Result:
        return _passing(selection.cases[1]) if index == 0 else result

    launch = _FakeLaunch(foreign)
    outcome = run_selected(
        selection.cases, binding=_BINDING, context=_CONTEXT, launch=launch,
        check=_ScriptedCheck("intact", "intact", "intact"),
    )
    assert outcome.stop_reason == "first-non-pass" and len(launch.cases) == 1
    assert outcome.first_non_pass is not None and _is_pass(outcome.first_non_pass)


@parser_free
def test_launch_refusal_stops_without_a_result_or_second_launch(selection: Selection) -> None:
    outcome = run_selected(
        selection.cases, binding=_BINDING, context=_CONTEXT, launch=_refusing_launch,
        check=_ScriptedCheck("intact", "intact"),
    )
    assert (outcome.attempted, outcome.launched) == (1, 1)
    assert outcome.results == () and outcome.stop_reason == "launch-refused"
    assert not outcome.qualified_success
    _validated_summary(selection, outcome)


@parser_free
@pytest.mark.parametrize("stop", ["first-non-pass", "launch-refused"])
def test_boundary_drift_after_an_earlier_stop_keeps_that_stop_reason(
    selection: Selection, stop: str,
) -> None:
    refused = stop == "launch-refused"
    launch: Launch = _refusing_launch if refused else _FakeLaunch(lambda _i, r: _timeout(r))
    check = _ScriptedCheck.intact(1 if refused else 2, "drift")
    outcome = run_selected(
        selection.cases, binding=_BINDING, context=_CONTEXT, launch=launch, check=check,
    )
    assert outcome.stop_reason == stop and outcome.drift == Drift("boundary", None, "drift")
    assert (outcome.attempted, outcome.launched) == (1, 1) and check.statuses == []
    assert not outcome.qualified_success
    if refused:
        assert outcome.results == () and outcome.first_non_pass is None
    else:
        (attempt,) = outcome.results
        assert outcome.first_non_pass is attempt and attempt.classification == "timeout"
        assert attempt.qualification_status == "qualified"
    _validated_summary(selection, outcome)


@parser_free
def test_pass_predicate_is_sensitive_to_each_pass_field(selection: Selection) -> None:
    passing = _passing(selection.cases[0], _CONTEXT)
    assert _is_pass(passing)
    corrupted = {
        "classification": replace(passing, classification="semantic_roundtrip_failure"),
        "model_checked": replace(passing, model_checked=False),
        "roundtrip_checked": replace(passing, roundtrip_checked=False),
        "qualification_status": replace(passing, qualification_status="unqualified-source-drift"),
        "exception_type": replace(passing, exception_type="ValueError"),
        "semantic_differences": replace(
            passing, semantic_differences=({"field": "content", "outline_path": [1]},),
        ),
    }
    assert set(corrupted) == {
        "classification", "model_checked", "roundtrip_checked", "qualification_status",
        "exception_type", "semantic_differences",
    }
    for field, result in corrupted.items():
        assert not _is_pass(result), field
        assert not _passes(result, selection.cases[0]), field
    assert _passes(passing, selection.cases[0])


@parser_free
def test_runner_rejects_oversized_empty_duplicate_or_out_of_domain_selections_up_front(
    selection: Selection,
) -> None:
    known = {case.source_sha256 for case in selection.cases}
    extras = [
        case for case in (
            composite.build_case(replace(
                composite.Recipe.literal_example(), unicode=glyph, tag=tag, newline=newline,
                reference=reference,
            ))
            for glyph, tag, newline, reference in product(
                composite.UNICODE, composite.TAGS, composite.NEWLINES, composite.REFERENCES,
            )
        ) if case.source_sha256 not in known
    ]
    oversized = [*selection.cases, *extras][: MAX_SELECTED + 1]
    assert len(oversized) == MAX_SELECTED + 1
    assert len({case.source_sha256 for case in oversized}) == MAX_SELECTED + 1
    for case in oversized:
        enforce_domain(case)
    nested = composite.build_case(replace(composite.Recipe.literal_example(), shape="nested"))
    first = selection.cases[0]
    for message, batch in (
        ("between 1..32", oversized), ("between 1..32", []), ("distinct", [first, first]),
        ("selected domain", [first, nested]),
    ):
        launch, check = _FakeLaunch(), _ScriptedCheck()
        with pytest.raises(ValueError, match=message):
            run_selected(batch, binding=_BINDING, context=_CONTEXT, launch=launch, check=check)
        assert launch.cases == [] and check.calls == 0


@parser_free
def test_summary_is_source_free_strict_keyed_and_hash_bound(selection: Selection) -> None:
    context = composite._capture_source_context()
    binding = admit_driver()
    outcome = run_selected(
        selection.cases, binding=binding, context=context, launch=_FakeLaunch(),
        check=_ScriptedCheck.intact(2 * len(selection.cases) + 1),
    )
    summary = validate_summary(build_summary(selection, outcome, binding=binding, context=context))
    manifest = context["implementation_manifest"]
    assert isinstance(manifest, dict)
    root = Path(__file__).resolve().parents[1]
    assert summary["driver_sha256"] == hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    assert summary["helper_sha256"] == manifest["tests/parser_assurance/composite_properties.py"]
    assert summary["lock_sha256"] == manifest["uv.lock"]
    assert summary["lock_sha256"] == hashlib.sha256((root / "uv.lock").read_bytes()).hexdigest()
    assert summary["worker_provenance_sha256"] == composite._provenance_sha256(context)
    entries = summary["cases"]
    assert isinstance(entries, list)
    for entry, case in zip(entries, selection.cases, strict=True):
        assert entry == {
            "recipe_sha256": composite._recipe_sha256(case.recipe),
            "source_sha256": case.source_sha256, "classification": "parsed",
            "qualification": "qualified",
        }
    counts = summary["counts"]
    assert isinstance(counts, dict)
    assert counts["body_calls"] == selection.accounting.generated
    assert counts["selected"] == counts["launched"] == counts["attempted"] == len(selection.cases)
    assert counts["max_parser_calls_bound"] == 2 * counts["launched"] <= 64
    rendered = json.dumps(summary, sort_keys=True, ensure_ascii=False)
    for case in selection.cases:
        assert all(line.strip() not in rendered for line in case.source.splitlines())
    sentinels = ("caffè", "item-", "[[", "SCHEDULED", "literal-key")
    assert not any(text in rendered for text in sentinels)
    assert summary["outcome"] == {
        "stop_reason": "complete", "first_non_pass_index": None, "drift_stage": None,
        "qualified_success": True,
    }


@parser_free
def test_summary_validator_rejects_unknown_missing_or_inconsistent_evidence(
    selection: Selection,
) -> None:
    context, binding = composite._capture_source_context(), admit_driver()
    outcome = run_selected(
        selection.cases, binding=binding, context=context, launch=_FakeLaunch(),
        check=_ScriptedCheck.intact(2 * len(selection.cases) + 1),
    )
    good = build_summary(selection, outcome, binding=binding, context=context)
    validate_summary(good)

    def edited(path: tuple[str, ...], value: object) -> dict[str, object]:
        clone: dict[str, object] = json.loads(json.dumps(good))
        node: dict[str, object] = clone
        for key in path[:-1]:
            child = node[key]
            assert isinstance(child, dict)
            node = child
        node[path[-1]] = value
        return clone

    broken: list[dict[str, object] | object] = [
        None, [], {**good, "extra": 1}, {k: v for k, v in good.items() if k != "lock_sha256"},
        edited(("schema",), "other"), edited(("driver_sha256",), "G" * 64),
        edited(("helper_sha256",), "a" * 63), edited(("counts", "extra"), 1),
        edited(("counts", "launched"), True), edited(("counts", "duplicates"), -1),
        edited(("counts", "body_calls"), MAX_BODY_CALLS + 1),
        edited(("counts", "max_parser_calls_bound"), 2 * len(selection.cases) + 1),
        edited(("counts", "selected"), len(selection.cases) + 1),
        edited(("outcome", "extra"), 1), edited(("outcome", "stop_reason"), "free text"),
        edited(("outcome", "qualified_success"), 1), edited(("outcome", "drift_stage"), "later"),
        edited(("outcome", "first_non_pass_index"), 0), edited(("cases",), "not a list"),
        edited(("outcome", "drift_stage"), "boundary"),
        edited(("outcome", "stop_reason"), "first-non-pass"),
    ]
    for candidate in broken:
        with pytest.raises(ValueError):
            validate_summary(candidate)
    entries = good["cases"]
    assert isinstance(entries, list)
    for mutate in (
        lambda entry: entry.update(extra="x"), lambda entry: entry.pop("qualification"),
        lambda entry: entry.update(source_sha256="z" * 64),
        lambda entry: entry.update(classification="unknown"),
        lambda entry: entry.update(classification=None),
        lambda entry: entry.update(qualification="maybe"),
    ):
        clone: dict[str, object] = json.loads(json.dumps(good))
        cloned_entries = clone["cases"]
        assert isinstance(cloned_entries, list)
        mutate(cloned_entries[0])
        with pytest.raises(ValueError):
            validate_summary(clone)


def _refuse_third(index: int, result: composite.Result) -> composite.Result:
    if index == 2:
        raise ValueError("controlled launch refusal")
    return result


def _timeout_second(index: int, result: composite.Result) -> composite.Result:
    return _timeout(result) if index == 1 else result


def _summary_bases() -> dict[str, dict[str, object]]:
    """Valid five-case summaries, one per terminal state `run_selected` can produce."""
    chosen, context = _small_selection(5), composite._capture_source_context()
    scenarios: dict[str, tuple[Launch, _ScriptedCheck]] = {
        "complete": (_FakeLaunch(), _ScriptedCheck.intact(11)),
        "first-non-pass": (_FakeLaunch(_timeout_second), _ScriptedCheck.intact(5)),
        "after-child": (_FakeLaunch(), _ScriptedCheck.intact(5, "drift")),
        "before-child": (_FakeLaunch(), _ScriptedCheck.intact(4, "drift")),
        "launch-refused": (_FakeLaunch(_refuse_third), _ScriptedCheck.intact(6)),
        "boundary-after-stop": (_FakeLaunch(_timeout_second), _ScriptedCheck.intact(4, "drift")),
        "boundary-complete": (_FakeLaunch(), _ScriptedCheck.intact(10, "drift")),
    }
    bases: dict[str, dict[str, object]] = {}
    for name, (launch, check) in scenarios.items():
        outcome = run_selected(
            chosen.cases, binding=_BINDING, context=context, launch=launch, check=check,
        )
        bases[name] = validate_summary(
            build_summary(chosen, outcome, binding=_BINDING, context=context),
        )
    return bases


@parser_free
def test_summary_bases_cover_every_terminal_state_and_validate() -> None:
    reasons = {
        name: cast(dict[str, object], base["outcome"])["stop_reason"]
        for name, base in _summary_bases().items()
    }
    assert reasons == {
        "complete": "complete", "first-non-pass": "first-non-pass",
        "after-child": "driver-drift-after-child", "before-child": "driver-drift-before-child",
        "launch-refused": "launch-refused", "boundary-after-stop": "first-non-pass",
        "boundary-complete": "driver-drift-at-boundary",
    }


_MALFORMED: Final = (
    ("first-non-pass", (("cases", 0, "classification"), None),
     (("cases", 0, "qualification"), None), "not a prefix"),
    ("first-non-pass", (("cases", 4, "classification"), "parsed"),
     (("cases", 4, "qualification"), "qualified"), "not a prefix"),
    ("first-non-pass", (("outcome", "first_non_pass_index"), 0), None, "first non-pass index"),
    ("first-non-pass", (("outcome", "first_non_pass_index"), True), None, "first non-pass index"),
    ("first-non-pass", (("outcome", "first_non_pass_index"), None), None, "first-non-pass state"),
    ("first-non-pass", (("cases", 0, "classification"), "timeout"), None, "first-non-pass state"),
    ("first-non-pass", (("outcome", "qualified_success"), True), None, "qualified-success flag"),
    ("complete", (("outcome", "qualified_success"), False), None, "qualified-success flag"),
    ("complete", (("outcome", "first_non_pass_index"), 4), None, "complete state"),
    ("complete", (("cases", 2, "qualification"), "unqualified-source-drift"), None,
     "complete state"),
    ("complete", (("cases", 4, "classification"), None), (("cases", 4, "qualification"), None),
     "complete state"),
    ("complete", (("outcome", "drift_stage"), "boundary"), None, "drift stage is inconsistent"),
    ("before-child", (("counts", "attempted"), 2), None, "driver-drift-before-child state"),
    ("before-child", (("outcome", "first_non_pass_index"), 1), None,
     "driver-drift-before-child state"),
    ("before-child", (("outcome", "drift_stage"), "after-child"), None,
     "drift stage is inconsistent"),
    ("after-child", (("cases", 2, "qualification"), "qualified"), None,
     "driver-drift-after-child state"),
    ("after-child", (("outcome", "first_non_pass_index"), None), None,
     "driver-drift-after-child state"),
    ("after-child", (("outcome", "drift_stage"), "before-child"), None,
     "drift stage is inconsistent"),
    ("launch-refused", (("counts", "launched"), 2), (("counts", "max_parser_calls_bound"), 4),
     "launch-refused state"),
    ("launch-refused", (("outcome", "first_non_pass_index"), 1), None, "launch-refused state"),
    ("launch-refused", (("outcome", "drift_stage"), "after-child"), None,
     "drift stage is inconsistent"),
    ("boundary-after-stop", (("outcome", "stop_reason"), "driver-drift-at-boundary"), None,
     "driver-drift-at-boundary state"),
    ("boundary-after-stop", (("outcome", "drift_stage"), "before-child"), None,
     "drift stage is inconsistent"),
    ("boundary-complete", (("outcome", "stop_reason"), "complete"), None,
     "drift stage is inconsistent"),
    ("boundary-complete", (("outcome", "qualified_success"), True), None,
     "qualified-success flag"),
    ("boundary-complete", (("outcome", "first_non_pass_index"), 4), None,
     "driver-drift-at-boundary state"),
)


@parser_free
@pytest.mark.parametrize(("base", "change", "second", "message"), _MALFORMED)
def test_summary_validator_rejects_each_prefix_and_terminal_state_violation(
    base: str, change: tuple[tuple[str | int, ...], object],
    second: tuple[tuple[str | int, ...], object] | None, message: str,
) -> None:
    good = _summary_bases()[base]
    validate_summary(good)
    changes = (change,) if second is None else (change, second)
    with pytest.raises(ValueError, match=message):
        validate_summary(_edited(good, *changes))


def _assert_complete_invocation(invocation: Invocation) -> dict[str, object]:
    """Size-agnostic success shape: any valid 2..32 selection, every launched case a clean pass."""
    outcome, chosen = invocation.outcome, invocation.selection
    assert outcome.first_non_pass is None, _describe(outcome.first_non_pass)
    assert outcome.drift is None and outcome.stop_reason == "complete"
    assert check_driver(invocation.binding) == "intact"
    assert outcome.attempted == outcome.launched == len(outcome.results) == len(chosen.cases)
    assert 2 <= outcome.launched <= MAX_SELECTED and outcome.qualified_success
    assert all(_is_pass(result) for result in outcome.results)
    assert [result.case_id for result in outcome.results] == [case.case_id for case in chosen.cases]
    assert invocation.summary is not None and invocation.summary_error is None
    summary = validate_summary(invocation.summary)
    counts = cast(dict[str, int], summary["counts"])
    assert counts["selected"] == counts["launched"] == len(chosen.cases)
    assert counts["max_parser_calls_bound"] == 2 * len(chosen.cases)
    return summary


@parser_free
@pytest.mark.parametrize("size", [None, 2, 7])
def test_complete_invocation_shape_accepts_any_valid_selection_size(
    selection: Selection, size: int | None,
) -> None:
    chosen = selection if size is None else _small_selection(size)
    invocation = execute_invocation(
        collect=lambda: chosen, launch=_FakeLaunch(),
        check=_ScriptedCheck.intact(2 * len(chosen.cases) + 1),
    )
    summary = _assert_complete_invocation(invocation)
    assert cast(dict[str, int], summary["counts"])["launched"] == len(chosen.cases)


def test_selected_mixed_markdown_recipes_pass_model_and_roundtrip_in_fresh_children(
    request: pytest.FixtureRequest, record_testsuite_property: Callable[[str, object], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Real execution: admit driver, collect parser-free, then one real child per selected case."""
    real_run, argvs = composite.subprocess.run, []

    def spy(*args: Any, **kwargs: Any) -> Any:  # passthrough: records, never replaces
        argvs.append([str(part) for part in args[0]] if args and isinstance(args[0], list) else [])
        return real_run(*args, **kwargs)

    monkeypatch.setattr(composite.subprocess, "run", spy)
    invocation = execute_invocation(collect=_collect_without_parser)
    outcome, chosen, context = invocation.outcome, invocation.selection, invocation.context
    summary = None if invocation.summary is None else validate_summary(invocation.summary)
    if summary is not None and getattr(request.config.option, "xmlpath", None):
        # Evidence first, even for a failing run.
        record_testsuite_property("s4b_mixed_markdown_summary", json.dumps(summary, sort_keys=True))
    summary = _assert_complete_invocation(invocation)
    children = [argv for argv in argvs if argv[1:] == list(_WORKER_ARGV)]
    assert len(children) == outcome.launched and all(argv[0] == sys.executable for argv in children)
    for case, result in zip(chosen.cases, outcome.results, strict=True):
        envelope = result.worker_envelope
        assert envelope is not None and set(envelope) == composite.WORKER_ENVELOPE_KEYS
        assert envelope["provenance_sha256"] == composite._provenance_sha256(context)
        assert envelope["module_origins_local"] is True
        assert envelope["qualification_status"] == "qualified"
        assert envelope["recipe_sha256"] == composite._recipe_sha256(case.recipe)
        assert envelope["source_sha256"] == case.source_sha256
        assert result.source_context is context
    # The summary carries frozen-context digests; this independent post-run read detects drift.
    root = invocation.binding.root
    assert summary["helper_sha256"] == hashlib.sha256(
        Path(composite.__file__).read_bytes()).hexdigest()
    assert summary["lock_sha256"] == hashlib.sha256((root / "uv.lock").read_bytes()).hexdigest()
