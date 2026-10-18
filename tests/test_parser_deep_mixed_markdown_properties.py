"""S4c: bounded generated deep/branching Markdown over the existing composite oracle."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import stat
import sys
import types
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Protocol

import pytest
from hypothesis import Phase, given, settings
from hypothesis import strategies as st

from logseq_matryca_parser.logos_parser import StackMachineParser
from tests.parser_assurance import composite_properties as composite

ANCHORS = (
    composite.Recipe(104, "nested", "NOW", "C", "2026-08-20 Thu", "2026-08-22 Sat",
                     "plain-value", "Résumé", "caffè", "🙂", "crlf"),
    composite.Recipe(104, "mixed-32", "CANCELED", "B", "2026-04-30 Thu", "2026-05-01 Fri",
                     "cafe-42", "Topic page", "work", "東京", "crlf"),
)
REAL_TEST = "test_deep_mixed_recipes_pass_in_observed_fresh_workers"
Deliver = Callable[[Callable[[composite.Recipe], None]], None]
MAX_SELECTED = 8
MAX_BODY_CALLS = 12
COLLECTION_SETTINGS = settings(
    max_examples=8, derandomize=True, database=None, deadline=None, phases=(Phase.generate,),
    report_multiple_bugs=False, print_blob=False, suppress_health_check=(),
)
SETTING_FIELDS = (
    "backend", "database", "deadline", "derandomize", "max_examples", "phases", "print_blob",
    "report_multiple_bugs", "stateful_step_count", "suppress_health_check", "verbosity",
)
DRIVER_RELATIVE = "tests/test_parser_deep_mixed_markdown_properties.py"


class SelectionError(ValueError):
    """Selection is outside the approved bounded domain."""


class BodyBudgetExceeded(SelectionError):
    """Call thirteen is refused before any new recipe work."""


class DriverProvenanceError(RuntimeError):
    """A fixed reason identifies inadmissible or unavailable driver evidence."""


class Launch(Protocol):
    def __call__(
        self, case: composite.Case, *, expected_context: dict[str, object] | None = None,
    ) -> composite.Result: ...


@dataclass(frozen=True)
class Selection:
    cases: tuple[composite.Case, ...]
    body_calls: int
    duplicates: int
    dropped_at_cap: int


@dataclass(frozen=True)
class DriverBinding:
    origin: Path
    root: Path
    anchor: Path
    resolved: Path
    sha256: str


@dataclass(frozen=True)
class GateFailure:
    stage: str
    index: int | None
    status: str


@dataclass
class StartEvidence:
    """Controls never qualify; real mode needs positively observed process creation."""

    control: bool = True
    total: int = 0
    available: bool = True
    active: bool = False

    @property
    def count(self) -> int | None:
        if self.control:
            return 0
        return self.total if self.available and self.active else None

    def record(self, process: Any, argv: object, cwd: object, root: Path) -> None:
        """Called only after construction; controls cannot manufacture positive telemetry."""
        if self.control:
            return
        if not self.active:
            self.available = False
            return
        if not isinstance(argv, (list, tuple)):
            self.available = False
            return
        if "--worker" not in argv:
            return  # In particular, the existing helper's bounded Git revision probes.
        if (
            list(argv) != [sys.executable, *WORKER_TAIL]
            or not isinstance(cwd, (str, Path))
            or Path(cwd).resolve(strict=True) != root.resolve(strict=True)
            or type(process.pid) is not int or process.pid <= 0
        ):
            self.available = False
            return
        self.total += 1


@dataclass(frozen=True)
class Outcome:
    attempted: int = 0
    handed_off: int = 0
    actual_child_starts: int | None = 0
    results: tuple[composite.Result, ...] = ()
    first_non_pass_index: int | None = None
    gates: tuple[GateFailure, ...] = ()
    stop_reason: str = "complete"
    control: bool = True
    start_problem: bool = False
    selected: int = 0

    @property
    def qualified_success(self) -> bool:
        return (
            not self.control and not self.start_problem and not self.gates
            and self.stop_reason == "complete" and self.first_non_pass_index is None
            and self.actual_child_starts == self.handed_off == self.attempted
            == len(self.results) == self.selected
            and self.selected >= 3
        )


@dataclass(frozen=True)
class Invocation:
    binding: DriverBinding
    context: dict[str, object]
    selection: Selection
    outcome: Outcome
    summary: dict[str, Any] | None = None
    summary_error: str | None = None


def make_start_observer(
    original: Callable[..., Any], starts: StartEvidence, root: Path,
) -> Callable[..., Any]:
    def observe(*args: Any, **kwargs: Any) -> Any:
        process = original(*args, **kwargs)
        try:
            starts.record(process, args[0] if args else kwargs.get("args"), kwargs.get("cwd"), root)
        except Exception:
            # The original process must reach subprocess.run's context manager and cleanup.
            # Unknown observation denies qualification only after the callback has reaped it.
            starts.available = False
        return process
    return observe


@contextmanager
def observed_workers(starts: StartEvidence, root: Path) -> Iterator[None]:
    """Install a passthrough only for this invocation; preserve normal subprocess cleanup."""
    if starts.active or starts.control:
        raise ValueError("fresh real-mode observer required")
    original = composite.subprocess.Popen
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(composite.subprocess, "Popen", make_start_observer(original, starts, root))
        starts.active = True
        try:
            yield
        finally:
            starts.active = False


def build_summary(invocation: Invocation) -> dict[str, Any]:
    """Use frozen invocation values only; no source reread and no Markdown/path/PID output."""
    binding, context, selection, outcome = (
        invocation.binding, invocation.context, invocation.selection, invocation.outcome,
    )
    manifest = context.get("implementation_manifest")
    if not isinstance(manifest, dict):
        raise ValueError("frozen manifest unavailable")
    helper = manifest.get("tests/parser_assurance/composite_properties.py")
    lock = manifest.get("uv.lock")
    if not all(isinstance(value, str) and composite._valid_digest(value) for value in (helper, lock)):
        raise ValueError("frozen manifest digest unavailable")
    cases = []
    for index, case in enumerate(selection.cases):
        observed = outcome.results[index] if index < len(outcome.results) else None
        cases.append({
            "recipe_sha256": composite._recipe_sha256(case.recipe),
            "source_sha256": case.source_sha256, "shape": case.recipe.shape,
            "kind": "anchor" if index < 2 else "generated",
            "classification": None if observed is None else observed.classification,
            "original_qualification": None if observed is None else observed.qualification_status,
            "passes": None if observed is None else (
                result_passes(observed, case) and observed.source_context is context
            ),
        })
    return {
        "schema": "s4c_deep_mixed_markdown_summary_v1", "driver_sha256": binding.sha256,
        "helper_sha256": helper, "lock_sha256": lock,
        "worker_provenance_sha256": composite._provenance_sha256(context),
        "anchor_shapes": {shape: sum(c.recipe.shape == shape for c in selection.cases[:2])
                          for shape in ("nested", "mixed-32")},
        "generated_shapes": {shape: sum(c.recipe.shape == shape for c in selection.cases[2:])
                             for shape in ("nested", "mixed-32")},
        "counts": {
            "selected": len(selection.cases), "body_calls": selection.body_calls,
            "duplicates": selection.duplicates, "dropped_at_cap": selection.dropped_at_cap,
            "attempted": outcome.attempted, "handed_off": outcome.handed_off,
            "actual_child_starts": outcome.actual_child_starts,
            # Source-derived callback bound, not measured parser-call telemetry.
            "max_parser_calls_bound": 2 * outcome.handed_off,
        },
        "cases": cases,
        "outcome": {
            "stop_reason": outcome.stop_reason, "first_non_pass_index": outcome.first_non_pass_index,
            "drift_stage": None if not outcome.gates else outcome.gates[0].stage,
            "drift_status": None if not outcome.gates else outcome.gates[0].status,
            "control": outcome.control, "observation_available": outcome.actual_child_starts is not None,
            "start_problem": outcome.start_problem, "qualified_success": outcome.qualified_success,
        },
    }


def validate_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """Validate source-free reporting, prefix accounting and honest real qualification."""
    def require(condition: bool) -> None:
        if not condition:
            raise ValueError("summary evidence inconsistent")

    def count(value: object) -> int:
        require(type(value) is int and value >= 0)  # type: ignore[operator]
        return value  # type: ignore[return-value]

    def digest(value: object) -> str:
        require(isinstance(value, str) and composite._valid_digest(value))
        return str(value)

    require(set(summary) == {
        "schema", "driver_sha256", "helper_sha256", "lock_sha256", "worker_provenance_sha256",
        "anchor_shapes", "generated_shapes", "counts", "cases", "outcome",
    })
    require(summary["schema"] == "s4c_deep_mixed_markdown_summary_v1")
    for key in ("driver_sha256", "helper_sha256", "lock_sha256", "worker_provenance_sha256"):
        digest(summary[key])
    counts, terminal, cases = summary["counts"], summary["outcome"], summary["cases"]
    require(isinstance(counts, dict) and set(counts) == {
        "selected", "body_calls", "duplicates", "dropped_at_cap", "attempted", "handed_off",
        "actual_child_starts", "max_parser_calls_bound",
    })
    require(isinstance(terminal, dict) and set(terminal) == {
        "stop_reason", "first_non_pass_index", "drift_stage", "drift_status", "control",
        "observation_available", "start_problem", "qualified_success",
    })
    selected, bodies, duplicates, drops, attempted, handed, bound = (count(counts[key]) for key in (
        "selected", "body_calls", "duplicates", "dropped_at_cap", "attempted", "handed_off",
        "max_parser_calls_bound",
    ))
    require(3 <= selected <= 8 and bodies <= 12 and bodies == duplicates + drops + selected - 2)
    require((drops == 0 or selected == 8) and handed <= attempted <= selected and bound == 2 * handed)
    for key in ("control", "observation_available", "start_problem", "qualified_success"):
        require(type(terminal[key]) is bool)
    actual = counts["actual_child_starts"]
    require(terminal["observation_available"] == (actual is not None))
    if actual is not None:
        require(count(actual) <= handed)
    require(not terminal["control"] or actual == 0)
    require(isinstance(cases, list) and len(cases) == selected)
    sources: set[str] = set()
    observed: list[bool] = []
    passes: list[bool] = []
    for index, entry in enumerate(cases):
        require(isinstance(entry, dict) and set(entry) == {
            "recipe_sha256", "source_sha256", "shape", "kind", "classification",
            "original_qualification", "passes",
        })
        digest(entry["recipe_sha256"])
        sources.add(digest(entry["source_sha256"]))
        require(entry["shape"] in {"nested", "mixed-32"})
        require(entry["kind"] == ("anchor" if index < 2 else "generated"))
        seen = entry["classification"] is not None
        observed.append(seen)
        if seen:
            require(entry["classification"] in composite.CLASSIFICATIONS)
            require(entry["original_qualification"] in {"qualified", "unqualified-source-drift"})
            require(type(entry["passes"]) is bool)
            passes.append(entry["passes"])
            require(not entry["passes"] or (
                entry["classification"] == "parsed" and entry["original_qualification"] == "qualified"
            ))
        else:
            require(entry["passes"] is None and entry["original_qualification"] is None)
    size = sum(observed)
    require(len(sources) == selected and size <= handed)
    require(observed == [True] * size + [False] * (selected - size))
    for key, subset in (("anchor_shapes", cases[:2]), ("generated_shapes", cases[2:])):
        shapes = summary[key]
        require(isinstance(shapes, dict) and set(shapes) == {"nested", "mixed-32"})
        require(all(count(shapes[shape]) == sum(case["shape"] == shape for case in subset)
                    for shape in shapes))
    require(summary["anchor_shapes"] == {"nested": 1, "mixed-32": 1})
    reason, first, stage, status = (terminal[key] for key in (
        "stop_reason", "first_non_pass_index", "drift_stage", "drift_status",
    ))
    require(reason in {"complete", "first-non-pass", "launch-refused", "driver-gate", "start-evidence"})
    require((stage is None) == (status is None))
    require(stage is None or stage in {"after-collection", "before-child", "after-child", "boundary"})
    require(status is None or status in {"drift", "unavailable"})
    require(first is None or (type(first) is int and first == size - 1))
    if reason == "complete":
        require(attempted == handed == size == selected and first is None and all(passes) and stage is None)
    elif reason == "first-non-pass":
        require(attempted == handed == size >= 1 and first == size - 1
                and all(passes[:-1]) and not passes[-1])
    elif reason == "launch-refused":
        require(attempted == handed >= 1 and size == handed - 1 and first is None and all(passes))
    else:
        require(first is None and all(passes))
        require((attempted == handed == size) or (attempted == handed + 1 and size == handed))
        require(stage is not None if reason == "driver-gate" else terminal["start_problem"] and not terminal["control"])
    expected_success = (
        reason == "complete" and not terminal["control"] and not terminal["start_problem"]
        and stage is None and actual == selected and terminal["observation_available"]
    )
    require(terminal["qualified_success"] == expected_success)
    return summary


def admit_driver(
    *, module: types.ModuleType | None = None, repo_root: Path | None = None,
    helper_root: Path | None = None,
) -> DriverBinding:
    selected = sys.modules[__name__] if module is None else module
    file_origin = getattr(selected, "__file__", None)
    spec_origin = getattr(getattr(selected, "__spec__", None), "origin", None)
    if not isinstance(file_origin, str) or not isinstance(spec_origin, str):
        raise DriverProvenanceError("origin-unavailable")
    if Path(file_origin) != Path(spec_origin):
        raise DriverProvenanceError("origin-mismatch")
    try:
        root = Path(__file__).resolve(strict=True).parents[1] if repo_root is None else repo_root
        anchor = Path(composite.__file__).resolve(strict=True).parents[2] if helper_root is None else helper_root
        origin = Path(file_origin)
        resolved, digest = driver_snapshot(origin, root, anchor)
        return DriverBinding(origin, root, anchor, resolved, digest)
    except DriverProvenanceError:
        raise
    except (OSError, RuntimeError) as error:
        raise DriverProvenanceError("origin-unavailable") from error


def driver_snapshot(origin: Path, root: Path, anchor: Path) -> tuple[Path, str]:
    if origin.is_symlink() or (root / "tests").is_symlink():
        raise DriverProvenanceError("symlink")
    if not stat.S_ISREG(origin.lstat().st_mode):
        raise DriverProvenanceError("not-regular")
    selected_root = root.resolve(strict=True)
    if selected_root != anchor.resolve(strict=True):
        raise DriverProvenanceError("root-mismatch")
    resolved = origin.resolve(strict=True)
    if resolved != selected_root / DRIVER_RELATIVE:
        raise DriverProvenanceError("unexpected-path")
    return resolved, hashlib.sha256(origin.read_bytes()).hexdigest()


def check_driver(binding: DriverBinding) -> str:
    try:
        resolved, digest = driver_snapshot(binding.origin, binding.root, binding.anchor)
    except DriverProvenanceError:
        return "drift"
    except (OSError, RuntimeError):
        return "unavailable"
    return "intact" if (resolved, digest) == (binding.resolved, binding.sha256) else "drift"


def driver_status(check: Callable[[DriverBinding], str], binding: DriverBinding) -> str:
    try:
        status = check(binding)
    except (OSError, RuntimeError):
        return "unavailable"
    return status if status in {"intact", "drift", "unavailable"} else "unavailable"


def result_passes(result: composite.Result, case: composite.Case) -> bool:
    return (
        (result.case_id, result.seed, result.recipe, result.source_sha256, result.source_bytes)
        == (case.case_id, case.recipe.seed, case.recipe, case.source_sha256, case.source_bytes)
        and result.classification == "parsed" and result.model_checked is True
        and result.roundtrip_checked is True and result.qualification_status == "qualified"
        and result.exception_type is None and result.semantic_differences == ()
    )


def run_selected(
    selection: Selection, *, binding: DriverBinding, context: dict[str, object],
    starts: StartEvidence, launch: Launch = composite.run_case,
    check: Callable[[DriverBinding], str] = check_driver,
    initial_gate: GateFailure | None = None,
) -> Outcome:
    validate_selection(selection)
    if starts.total != 0:
        raise ValueError("process observer must belong to this invocation")
    results: list[composite.Result] = []
    gates = [] if initial_gate is None else [initial_gate]
    attempted = handed = 0
    first: int | None = None
    start_problem = False
    reason = "complete" if initial_gate is None else "driver-gate"
    if initial_gate is None:
        for index, case in enumerate(selection.cases):
            attempted += 1
            status = driver_status(check, binding)
            if status != "intact":
                gates.append(GateFailure("before-child", index, status))
                reason = "driver-gate"
                break
            before = starts.count
            if not starts.control and before is None:
                start_problem, reason = True, "start-evidence"
                break
            handed += 1
            refused = False
            try:
                result = launch(case, expected_context=context)
            except (ValueError, OSError, RuntimeError):
                refused = True
            else:
                # Retain the original immutable result/context before any later check.
                results.append(result)
                if not result_passes(result, case) or result.source_context is not context:
                    first = index
            status = driver_status(check, binding)
            if status != "intact":
                gates.append(GateFailure("after-child", index, status))
            after = starts.count
            start_problem = not starts.control and (
                before is None or after is None or after - before != 1 or after > handed
            )
            if first is not None:
                reason = "first-non-pass"
            elif refused:
                reason = "launch-refused"
            elif gates:
                reason = "driver-gate"
            elif start_problem:
                reason = "start-evidence"
            else:
                continue
            break
    status = driver_status(check, binding)
    if status != "intact":
        gates.append(GateFailure("boundary", None, status))
        if reason == "complete":
            reason = "driver-gate"
    return Outcome(attempted, handed, starts.count, tuple(results), first, tuple(gates), reason,
                   starts.control, start_problem, len(selection.cases))


def execute_invocation(
    *, collect: Callable[[], Selection] = lambda: collect_selected_cases(),
    launch: Launch = composite.run_case,
    check: Callable[[DriverBinding], str] = check_driver,
    starts: StartEvidence | None = None,
) -> Invocation:
    binding, context = admit_driver(), composite._capture_source_context()
    status = driver_status(check, binding)
    if status != "intact":
        raise DriverProvenanceError("before-collection-" + status)
    selection = collect()
    validate_selection(selection)
    status = driver_status(check, binding)
    initial = None if status == "intact" else GateFailure("after-collection", None, status)
    invocation = Invocation(binding, context, selection, run_selected(
        selection, binding=binding, context=context,
        starts=StartEvidence() if starts is None else starts, launch=launch, check=check,
        initial_gate=initial,
    ))
    summary: dict[str, Any] | None = None
    try:
        summary = build_summary(invocation)
        validate_summary(summary)
    except ValueError:
        return replace(invocation, summary=summary, summary_error="summary-evidence-invalid")
    return replace(invocation, summary=summary)


def collect_selected_cases(deliver: Deliver | None = None) -> Selection:
    """Admit two anchors, then partition each generated body before any parser work."""
    cases = [admit_case(recipe) for recipe in ANCHORS]
    seen = {case.source_sha256 for case in cases}
    if len(seen) != 2:
        raise SelectionError("anchors must be source-distinct")
    body_calls = duplicates = dropped = 0

    def accept(recipe: composite.Recipe) -> None:
        nonlocal body_calls, duplicates, dropped
        if body_calls >= MAX_BODY_CALLS:
            raise BodyBudgetExceeded("body ceiling reached before new case work")
        body_calls += 1
        case = admit_case(recipe)
        if case.source_sha256 in seen:
            duplicates += 1
        elif len(cases) >= MAX_SELECTED:
            dropped += 1
        else:
            seen.add(case.source_sha256)
            cases.append(case)

    (generate_recipes if deliver is None else deliver)(accept)
    selected = Selection(tuple(cases), body_calls, duplicates, dropped)
    validate_selection(selected)
    return selected


def require_applied_settings(test: object) -> None:
    """Fail closed on changed/missing applied settings or seed/reproduction overrides.

    These markers belong to the Hypothesis version pinned by the lock; absence is a refusal,
    not evidence that an upstream replacement is equivalent.
    """
    applied = getattr(test, "_hypothesis_internal_use_settings", None)
    if (
        not isinstance(applied, settings)
        or any(getattr(applied, field) != getattr(COLLECTION_SETTINGS, field)
               for field in SETTING_FIELDS)
        or getattr(test, "_hypothesis_internal_use_seed", "missing") is not None
        or getattr(test, "_hypothesis_internal_use_reproduce_failure", "missing") is not None
    ):
        raise SelectionError("applied settings or seed markers differ")


def generate_recipes(accept: Callable[[composite.Recipe], None]) -> None:
    strategy = st.builds(
        composite.Recipe, seed=st.just(104), shape=st.sampled_from(("nested", "mixed-32")),
        task=st.sampled_from(composite.TASKS), priority=st.sampled_from(composite.PRIORITIES),
        scheduled=st.sampled_from(composite.SCHEDULED_DATES),
        deadline=st.sampled_from(composite.DEADLINE_DATES), literal=st.sampled_from(composite.LITERALS),
        reference=st.sampled_from(composite.REFERENCES), tag=st.sampled_from(composite.TAGS),
        unicode=st.sampled_from(composite.UNICODE), newline=st.sampled_from(composite.NEWLINES),
    )

    @COLLECTION_SETTINGS
    @given(recipe=strategy)
    def collect(recipe: composite.Recipe) -> None:
        accept(recipe)

    require_applied_settings(collect)
    collect()


def enforce_domain(case: composite.Case) -> None:
    try:
        composite._validate(case.recipe)
    except ValueError as error:
        raise SelectionError("selected recipe outside finite vocabulary") from error
    nodes = composite._flatten_expected(case.expected)
    if (
        type(case.recipe.seed) is not int or case.recipe.seed != 104
        or case.recipe.shape not in {"nested", "mixed-32"}
        or not 1 <= len(nodes) <= 32 or max(block.depth for block in nodes) > 8
        or case.source_bytes > 16_384
    ):
        raise SelectionError("case outside deep mixed domain")


def admit_case(recipe: composite.Recipe) -> composite.Case:
    try:
        composite._validate(recipe)
        case = composite.build_case(recipe)
        enforce_domain(case)
        return case
    except ValueError as error:
        raise SelectionError("recipe or built case outside domain") from error


def validate_selection(selection: Selection) -> None:
    size = len(selection.cases)
    if size < 3:
        raise SelectionError("no generated non-anchor source selected")
    if (
        size > MAX_SELECTED or selection.body_calls > MAX_BODY_CALLS
        or any(type(value) is not int or value < 0 for value in (
            selection.body_calls, selection.duplicates, selection.dropped_at_cap,
        ))
        or selection.body_calls != selection.duplicates + selection.dropped_at_cap + size - 2
        or tuple(case.recipe for case in selection.cases[:2]) != ANCHORS
        or len({case.source_sha256 for case in selection.cases}) != size
        or (selection.dropped_at_cap > 0 and size != MAX_SELECTED)
    ):
        raise SelectionError("selection accounting or anchors invalid")
    for case in selection.cases:
        enforce_domain(case)


@pytest.fixture(autouse=True)
def no_target_in_controls(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch,
) -> Iterator[None]:
    if request.node.name == REAL_TEST:
        yield
        return
    attempts: list[str] = []

    def deny(*_args: object, **_kwargs: object) -> None:
        attempts.append("forbidden-target-entry")
        raise AssertionError("parser and process creation forbidden in S4c controls")

    monkeypatch.setattr(StackMachineParser, "parse", deny)
    monkeypatch.setattr(composite.subprocess, "run", deny)
    monkeypatch.setattr(composite.subprocess, "Popen", deny)
    monkeypatch.setattr(composite, "_revision", lambda *_a, **_k: composite.BASELINE_REVISION)
    yield
    assert attempts == []


def deliver_recipes(recipes: tuple[composite.Recipe, ...]) -> Deliver:
    def deliver(accept: Callable[[composite.Recipe], None]) -> None:
        for recipe in recipes:
            accept(recipe)
    return deliver


def non_anchor(task: str = "TODO") -> composite.Recipe:
    return replace(ANCHORS[0], task=task, literal="kept")


def test_collect_retains_both_anchors_and_accepts_one_generated_shape() -> None:
    selected = collect_selected_cases(deliver_recipes((non_anchor(),)))
    assert [case.recipe for case in selected.cases[:2]] == list(ANCHORS)
    assert [case.recipe.shape for case in selected.cases] == ["nested", "mixed-32", "nested"]
    assert selected.body_calls == 1
    assert selected.duplicates == selected.dropped_at_cap == 0


def test_collect_accounts_duplicates_before_cap_and_each_unselected_drop() -> None:
    generated = tuple(non_anchor(task) for task in composite.TASKS)
    dropped = replace(ANCHORS[1], task="TODO")
    selected = collect_selected_cases(deliver_recipes((ANCHORS[0], *generated, dropped, dropped)))
    assert len(selected.cases) == 8
    assert len({case.source_sha256 for case in selected.cases}) == 8
    assert (selected.body_calls, selected.duplicates, selected.dropped_at_cap) == (9, 1, 2)
    assert selected.body_calls == selected.duplicates + selected.dropped_at_cap + len(selected.cases) - 2


def test_collect_rejects_without_a_generated_non_anchor() -> None:
    with pytest.raises(SelectionError, match="non-anchor"):
        collect_selected_cases(deliver_recipes(ANCHORS * 2))


def test_body_thirteen_is_refused_before_building(monkeypatch: pytest.MonkeyPatch) -> None:
    built: list[composite.Recipe] = []
    original = composite.build_case

    def counted(recipe: composite.Recipe) -> composite.Case:
        built.append(recipe)
        return original(recipe)

    monkeypatch.setattr(composite, "build_case", counted)
    with pytest.raises(BodyBudgetExceeded):
        collect_selected_cases(deliver_recipes((non_anchor(),) * 13))
    assert len(built) == 14  # Two anchors plus twelve admitted bodies; never body thirteen.


@pytest.mark.parametrize("recipe", [
    replace(ANCHORS[0], seed=105), replace(ANCHORS[0], shape="siblings"),
    replace(ANCHORS[0], task="NOT-A-TASK"),
])
def test_collect_refuses_recipes_outside_domain(recipe: composite.Recipe) -> None:
    with pytest.raises(SelectionError):
        collect_selected_cases(deliver_recipes((recipe,)))


@pytest.mark.parametrize("change", ["bytes", "nodes", "depth"])
def test_collect_refuses_built_case_outside_caps(
    monkeypatch: pytest.MonkeyPatch, change: str,
) -> None:
    original = composite.build_case

    def oversized(recipe: composite.Recipe) -> composite.Case:
        case = original(recipe)
        if recipe == ANCHORS[0]:
            return case
        if change == "bytes":
            return replace(case, source="x" * 16_385)
        block = replace(case.expected[0], children=(), depth=9 if change == "depth" else 0)
        return replace(case, expected=(block,) * (33 if change == "nodes" else 1))

    monkeypatch.setattr(composite, "build_case", oversized)
    with pytest.raises(SelectionError):
        collect_selected_cases(deliver_recipes((non_anchor(),)))


@pytest.mark.parametrize("field,value", [
    ("max_examples", 9), ("derandomize", False), ("phases", (Phase.generate, Phase.shrink)),
    ("print_blob", True), ("report_multiple_bugs", True),
])
def test_applied_settings_refuse_changes_before_body(field: str, value: Any) -> None:
    calls: list[bool] = []

    @settings(COLLECTION_SETTINGS, **{field: value})
    @given(value=st.just(1))
    def collect(value: int) -> None:
        calls.append(True)

    with pytest.raises(SelectionError, match="settings"):
        require_applied_settings(collect)
    assert calls == []


@pytest.mark.parametrize("field", [
    "_hypothesis_internal_use_seed", "_hypothesis_internal_use_reproduce_failure",
])
def test_applied_settings_refuse_seed_or_reproduction(field: str) -> None:
    @COLLECTION_SETTINGS
    @given(value=st.just(1))
    def collect(value: int) -> None:
        raise AssertionError("body must not run")

    setattr(collect, field, 104)
    with pytest.raises(SelectionError, match="settings"):
        require_applied_settings(collect)


@pytest.fixture
def chosen() -> Selection:
    return collect_selected_cases(deliver_recipes(tuple(non_anchor(t) for t in ("TODO", "DONE"))))


def passing(case: composite.Case, context: dict[str, object] | None) -> composite.Result:
    return composite.Result(
        case.case_id, case.recipe.seed, case.recipe, case.source_sha256, case.source_bytes,
        "parsed", None, True, True, source_context=context,
    )


class FakeLaunch:
    def __init__(
        self, fail_at: int | None = None,
        mutate: Callable[[composite.Result], composite.Result] = lambda value: value,
    ) -> None:
        self.cases: list[composite.Case] = []
        self.contexts: list[dict[str, object] | None] = []
        self.fail_at, self.mutate = fail_at, mutate

    def __call__(
        self, case: composite.Case, *, expected_context: dict[str, object] | None = None,
    ) -> composite.Result:
        index = len(self.cases)
        self.cases.append(case)
        self.contexts.append(expected_context)
        result = passing(case, expected_context)
        return self.mutate(result) if index == self.fail_at else result


def scripted_check(statuses: list[str]) -> Callable[[DriverBinding], str]:
    pending = iter(statuses)

    def check(binding: DriverBinding) -> str:
        return next(pending)
    return check


CORRUPT_RESULTS: tuple[dict[str, Any], ...] = (
    {"classification": "invariant_failure"}, {"model_checked": False},
    {"roundtrip_checked": False}, {"qualification_status": "unqualified-source-drift"},
    {"exception_type": "InjectedFailure"}, {"semantic_differences": ({"field": "content"},)},
    {"case_id": "wrong-case"}, {"source_sha256": "0" * 64}, {"seed": 105},
    {"recipe": ANCHORS[1]},
)


@pytest.mark.parametrize("index", [0, 2, 3])
@pytest.mark.parametrize("change", CORRUPT_RESULTS)
def test_first_corrupt_outcome_stops_prefix_and_keeps_exact_context(
    chosen: Selection, index: int, change: dict[str, Any],
) -> None:
    fake = FakeLaunch(index, lambda result: replace(result, **change))
    invocation = execute_invocation(collect=lambda: chosen, launch=fake)
    outcome = invocation.outcome
    assert outcome.attempted == outcome.handed_off == len(fake.cases) == index + 1
    assert outcome.first_non_pass_index == index and outcome.stop_reason == "first-non-pass"
    assert len(outcome.results) == index + 1
    assert outcome.results[-1].source_context is invocation.context
    assert fake.contexts == [invocation.context] * (index + 1)
    assert outcome.actual_child_starts == 0 and not outcome.qualified_success


def test_fake_complete_prefix_never_claims_real_starts_or_qualification(chosen: Selection) -> None:
    invocation = execute_invocation(collect=lambda: chosen, launch=FakeLaunch())
    outcome = invocation.outcome
    assert outcome.stop_reason == "complete"
    assert outcome.attempted == outcome.handed_off == len(outcome.results) == 4
    assert outcome.actual_child_starts == 0 and not outcome.qualified_success


def test_refusal_has_one_handoff_zero_starts_and_no_result(chosen: Selection) -> None:
    def refuse(
        case: composite.Case, *, expected_context: dict[str, object] | None = None,
    ) -> composite.Result:
        raise ValueError("source context refused before process creation")

    outcome = execute_invocation(collect=lambda: chosen, launch=refuse).outcome
    assert (outcome.attempted, outcome.handed_off, outcome.actual_child_starts) == (1, 1, 0)
    assert outcome.results == () and outcome.stop_reason == "launch-refused"
    assert not outcome.qualified_success


@pytest.mark.parametrize("available", [True, False])
def test_real_mode_missing_or_unknown_start_stops_after_preserving_result(
    chosen: Selection, available: bool,
) -> None:
    fake = FakeLaunch()
    starts = StartEvidence(control=False, active=True)

    def launch(
        case: composite.Case, *, expected_context: dict[str, object] | None = None,
    ) -> composite.Result:
        result = fake(case, expected_context=expected_context)
        starts.available = available
        return result

    invocation = execute_invocation(
        collect=lambda: chosen, launch=launch, starts=starts,
    )
    outcome = invocation.outcome
    assert len(outcome.results) == len(fake.cases) == 1
    assert outcome.results[0].source_context is invocation.context
    assert outcome.actual_child_starts == (0 if available else None)
    assert outcome.start_problem and outcome.stop_reason == "start-evidence"
    assert not outcome.qualified_success


@pytest.mark.parametrize("fault", ["drift", "unavailable"])
@pytest.mark.parametrize("stage,position,attempted,handed,observed", [
    ("after-collection", 1, 0, 0, 0), ("before-child", 2, 1, 0, 0),
    ("after-child", 3, 1, 1, 1), ("boundary", 10, 4, 4, 4),
])
def test_driver_gate_denies_without_overwriting_observed_prefix(
    chosen: Selection, fault: str, stage: str, position: int,
    attempted: int, handed: int, observed: int,
) -> None:
    statuses = ["intact"] * 11
    statuses[position] = fault
    invocation = execute_invocation(
        collect=lambda: chosen, launch=FakeLaunch(), check=scripted_check(statuses),
    )
    outcome = invocation.outcome
    assert (outcome.attempted, outcome.handed_off, len(outcome.results)) == (attempted, handed, observed)
    assert outcome.gates[0].stage == stage and outcome.gates[0].status == fault
    assert not outcome.qualified_success
    assert all(result.source_context is invocation.context for result in outcome.results)


@pytest.mark.parametrize("fault", ["drift", "unavailable"])
def test_before_collection_gate_refuses_collection_itself(chosen: Selection, fault: str) -> None:
    collected: list[bool] = []

    def collect() -> Selection:
        collected.append(True)
        return chosen

    with pytest.raises(DriverProvenanceError, match="before-collection"):
        execute_invocation(collect=collect, launch=FakeLaunch(), check=lambda _binding: fault)
    assert collected == []


def test_final_gate_does_not_replace_earlier_semantic_failure(chosen: Selection) -> None:
    invocation = execute_invocation(
        collect=lambda: chosen, launch=FakeLaunch(0, lambda r: replace(r, classification="timeout")),
        check=scripted_check(["intact"] * 4 + ["unavailable"]),
    )
    outcome = invocation.outcome
    assert outcome.stop_reason == "first-non-pass" and outcome.first_non_pass_index == 0
    assert outcome.results[0].classification == "timeout"
    assert outcome.results[0].source_context is invocation.context
    assert outcome.gates == (GateFailure("boundary", None, "unavailable"),)


def fixture_driver(tmp_path: Path) -> tuple[types.ModuleType, Path]:
    root = tmp_path / "repo"
    origin = root / DRIVER_RELATIVE
    origin.parent.mkdir(parents=True)
    origin.write_text("# synthetic driver\n", encoding="utf-8")
    module = types.ModuleType("synthetic_s4c_driver")
    module.__file__ = str(origin)
    module.__spec__ = importlib.util.spec_from_file_location(module.__name__, origin)
    return module, root


def test_driver_digest_change_is_drift(tmp_path: Path) -> None:
    module, root = fixture_driver(tmp_path)
    binding = admit_driver(module=module, repo_root=root, helper_root=root)
    assert check_driver(binding) == "intact"
    Path(str(module.__file__)).write_text("# changed\n", encoding="utf-8")
    assert check_driver(binding) == "drift"


@pytest.mark.parametrize("kind", ["missing-origin", "origin-mismatch", "root-mismatch", "path", "directory"])
def test_driver_refuses_inadmissible_origin(tmp_path: Path, kind: str) -> None:
    module, root = fixture_driver(tmp_path)
    anchor = root
    if kind == "missing-origin":
        module.__spec__ = None
    elif kind == "origin-mismatch":
        module.__file__ = str(root / "elsewhere.py")
    elif kind == "root-mismatch":
        anchor = tmp_path
    elif kind == "path":
        other = root / "other.py"
        other.write_text("# other\n", encoding="utf-8")
        module.__file__ = str(other)
        module.__spec__ = importlib.util.spec_from_file_location(module.__name__, other)
    else:
        origin = Path(str(module.__file__))
        origin.unlink()
        origin.mkdir()
    with pytest.raises(DriverProvenanceError):
        admit_driver(module=module, repo_root=root, helper_root=anchor)


@pytest.mark.parametrize("error", [OSError, RuntimeError])
def test_resolution_failure_is_normalized_at_admission_and_recheck(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: type[Exception],
) -> None:
    module, root = fixture_driver(tmp_path)
    binding = admit_driver(module=module, repo_root=root, helper_root=root)

    def unavailable(*_args: object, **_kwargs: object) -> Path:
        raise error("resolution unavailable")

    monkeypatch.setattr(Path, "resolve", unavailable)
    assert check_driver(binding) == "unavailable"
    with pytest.raises(DriverProvenanceError, match="unavailable"):
        admit_driver(module=module, repo_root=root, helper_root=root)


WORKER_TAIL = ("-m", "tests.parser_assurance.composite_properties", "--worker")


def test_failed_constructor_keeps_starts_zero() -> None:
    starts = StartEvidence(control=False, active=True)

    def refused(*_args: object, **_kwargs: object) -> Any:
        raise OSError("construction refused")

    wrapped = make_start_observer(refused, starts, Path.cwd())
    with pytest.raises(OSError):
        wrapped([sys.executable, *WORKER_TAIL], cwd=Path.cwd())
    assert starts.count == 0


def test_observation_error_cannot_prevent_return_to_subprocess_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = object()
    starts = StartEvidence(control=False, active=True)

    def unavailable(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("observer bookkeeping unavailable after successful constructor")

    monkeypatch.setattr(starts, "record", unavailable)
    wrapped = make_start_observer(lambda *_a, **_k: process, starts, Path.cwd())
    try:
        returned = wrapped([sys.executable, *WORKER_TAIL], cwd=Path.cwd())
    except RuntimeError:
        pytest.fail("observation error interrupted normal subprocess cleanup ownership")
    assert returned is process
    assert starts.count is None and starts.total == 0


@pytest.mark.parametrize("kind", ["interpreter", "cwd", "pid", "pid-unavailable"])
def test_wrong_or_unavailable_worker_observation_is_unknown_not_zero(kind: str) -> None:
    starts = StartEvidence(control=False, active=True)
    root = Path(__file__).resolve().parents[1]
    argv = [sys.executable, *WORKER_TAIL]
    cwd = root
    process: Any = types.SimpleNamespace(pid=123)
    if kind == "interpreter":
        argv[0] = "foreign-python"
    elif kind == "cwd":
        cwd = root.parent
    elif kind == "pid":
        process.pid = 0
    else:
        process = object()
    wrapped = make_start_observer(lambda *_a, **_k: process, starts, root)
    assert wrapped(argv, cwd=cwd) is process
    assert starts.count is None and starts.total == 0


def test_controls_cannot_turn_a_fake_process_into_actual_start() -> None:
    starts = StartEvidence()
    root = Path.cwd()
    starts.record(types.SimpleNamespace(pid=123), [sys.executable, *WORKER_TAIL], root, root)
    assert starts.count == 0


def test_provenance_git_process_is_not_counted_as_a_worker() -> None:
    starts = StartEvidence(control=False, active=True)
    starts.record(types.SimpleNamespace(pid=123), ["git", "rev-parse", "HEAD"], Path.cwd(), Path.cwd())
    assert starts.count == 0


@pytest.mark.parametrize("error", [OSError, RuntimeError])
@pytest.mark.parametrize("position,stage", [
    (0, "before-collection"), (1, "after-collection"), (2, "before-child"),
    (3, "after-child"), (10, "boundary"),
])
def test_resolution_failure_at_every_gate_is_denied_without_new_target_work(
    chosen: Selection, monkeypatch: pytest.MonkeyPatch,
    error: type[Exception], position: int, stage: str,
) -> None:
    calls = 0
    fake = FakeLaunch()

    def check(binding: DriverBinding) -> str:
        nonlocal calls
        index, calls = calls, calls + 1
        if index != position:
            return check_driver(binding)

        def unavailable(*_args: object, **_kwargs: object) -> Path:
            raise error("resolution failed at sampled gate")

        with monkeypatch.context() as patch:
            patch.setattr(Path, "resolve", unavailable)
            return check_driver(binding)

    if position == 0:
        with pytest.raises(DriverProvenanceError, match="before-collection"):
            execute_invocation(collect=lambda: chosen, launch=fake, check=check)
        assert fake.cases == []
    else:
        invocation = execute_invocation(collect=lambda: chosen, launch=fake, check=check)
        assert invocation.outcome.gates[0].stage == stage
        assert invocation.outcome.gates[0].status == "unavailable"
        assert not invocation.outcome.qualified_success
        assert all(result.source_context is invocation.context for result in invocation.outcome.results)


def make_symlink(link: Path, target: Path, *, directory: bool = False) -> None:
    try:
        link.symlink_to(target, target_is_directory=directory)
    except OSError as error:
        pytest.skip(f"symlink creation unavailable on this native platform: {type(error).__name__}")


@pytest.mark.parametrize("kind", ["leaf", "tests"])
def test_same_byte_symlink_topology_is_rejected(tmp_path: Path, kind: str) -> None:
    module, root = fixture_driver(tmp_path)
    binding = admit_driver(module=module, repo_root=root, helper_root=root)
    origin = Path(str(module.__file__))
    if kind == "leaf":
        other = root / "other.py"
        origin.rename(other)
        make_symlink(origin, other)
    else:
        other = root / "tests-real"
        origin.parent.rename(other)
        make_symlink(origin.parent, other, directory=True)
    assert hashlib.sha256(origin.read_bytes()).hexdigest() == binding.sha256
    assert check_driver(binding) == "drift"
    with pytest.raises(DriverProvenanceError):
        admit_driver(module=module, repo_root=root, helper_root=root)


def test_symlink_above_repo_root_remains_admitted(tmp_path: Path) -> None:
    module, root = fixture_driver(tmp_path)
    alias = tmp_path / "alias"
    make_symlink(alias, root, directory=True)
    module.__file__ = str(alias / DRIVER_RELATIVE)
    module.__spec__ = importlib.util.spec_from_file_location(module.__name__, module.__file__)
    binding = admit_driver(module=module, repo_root=alias, helper_root=root)
    assert check_driver(binding) == "intact"


def test_unobserved_starts_are_not_qualified_by_a_passing_fake_result(chosen: Selection) -> None:
    invocation = execute_invocation(
        collect=lambda: chosen, launch=FakeLaunch(), starts=StartEvidence(control=False, active=True),
    )
    summary = build_summary(invocation)
    assert summary["counts"]["actual_child_starts"] == 0
    assert summary["counts"]["handed_off"] == 1
    assert summary["outcome"]["qualified_success"] is False


def test_summary_truthfully_distinguishes_anchors_generated_shapes_and_control_execution(
    chosen: Selection,
) -> None:
    invocation = execute_invocation(collect=lambda: chosen, launch=FakeLaunch())
    summary = validate_summary(build_summary(invocation))
    assert summary["anchor_shapes"] == {"nested": 1, "mixed-32": 1}
    assert summary["generated_shapes"] == {"nested": 2, "mixed-32": 0}
    assert summary["counts"] == {
        "selected": 4, "body_calls": 2, "duplicates": 0, "dropped_at_cap": 0,
        "attempted": 4, "handed_off": 4, "actual_child_starts": 0,
        "max_parser_calls_bound": 8,
    }
    assert summary["outcome"]["control"] is True
    assert summary["outcome"]["qualified_success"] is False
    assert all(case["passes"] is True for case in summary["cases"])


@pytest.mark.parametrize("corruption", [
    "equation", "starts", "unknown", "prefix", "shapes", "qualification", "digest", "extra-key",
])
def test_summary_validation_refuses_inconsistent_or_falsely_qualified_evidence(
    chosen: Selection, corruption: str,
) -> None:
    summary = build_summary(execute_invocation(collect=lambda: chosen, launch=FakeLaunch()))
    if corruption == "equation":
        summary["counts"]["duplicates"] = 1
    elif corruption == "starts":
        summary["counts"]["actual_child_starts"] = 5
    elif corruption == "unknown":
        summary["counts"]["actual_child_starts"] = None
    elif corruption == "prefix":
        summary["cases"][0]["passes"] = None
    elif corruption == "shapes":
        summary["generated_shapes"]["mixed-32"] = 1
    elif corruption == "qualification":
        summary["outcome"]["qualified_success"] = True
    elif corruption == "digest":
        summary["driver_sha256"] = "invalid"
    else:
        summary["unexpected"] = "free text"
    with pytest.raises(ValueError):
        validate_summary(summary)


def test_real_mode_without_installed_observer_is_unknown_before_handoff(chosen: Selection) -> None:
    starts = StartEvidence(control=False)
    fake = FakeLaunch()
    outcome = execute_invocation(collect=lambda: chosen, launch=fake, starts=starts).outcome
    assert outcome.actual_child_starts is None
    assert fake.cases == [] and outcome.handed_off == 0
    assert outcome.stop_reason == "start-evidence" and not outcome.qualified_success


def test_summary_failure_preserves_first_outcome_context_and_zero_real_starts(
    chosen: Selection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = build_summary

    def corrupted(invocation: Invocation) -> dict[str, Any]:
        summary = original(invocation)
        summary["counts"]["actual_child_starts"] = 2
        return summary

    monkeypatch.setattr(sys.modules[__name__], "build_summary", corrupted)
    invocation = execute_invocation(
        collect=lambda: chosen, launch=FakeLaunch(0, lambda r: replace(r, classification="timeout")),
    )
    assert invocation.summary_error == "summary-evidence-invalid"
    assert invocation.outcome.results[0].classification == "timeout"
    assert invocation.outcome.results[0].source_context is invocation.context
    assert invocation.outcome.actual_child_starts == 0


def test_missing_frozen_digest_retains_original_outcome_without_reprobe(
    chosen: Selection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = composite._capture_source_context()
    manifest = context["implementation_manifest"]
    assert isinstance(manifest, dict)
    del manifest["uv.lock"]
    monkeypatch.setattr(composite, "_capture_source_context", lambda: context)
    invocation = execute_invocation(
        collect=lambda: chosen, launch=FakeLaunch(0, lambda r: replace(r, classification="timeout")),
    )
    assert invocation.summary is None and invocation.summary_error == "summary-evidence-invalid"
    assert invocation.outcome.results[0].source_context is context
    assert invocation.outcome.results[0].classification == "timeout"


def test_default_generation_is_parser_free_and_completes_approved_accounting() -> None:
    selection = collect_selected_cases()
    assert selection.body_calls <= 12
    assert 3 <= len(selection.cases) <= 8
    assert selection.body_calls == selection.duplicates + selection.dropped_at_cap + len(selection.cases) - 2
    assert tuple(case.recipe for case in selection.cases[:2]) == ANCHORS


def test_invalid_selected_recipe_is_refused_before_any_handoff(chosen: Selection) -> None:
    cases = list(chosen.cases)
    cases[2] = replace(cases[2], recipe=replace(cases[2].recipe, task="NOT-A-TASK"))
    fake = FakeLaunch()
    with pytest.raises(SelectionError):
        execute_invocation(collect=lambda: replace(chosen, cases=tuple(cases)), launch=fake)
    assert fake.cases == []


def test_invocation_checks_before_after_collection_and_each_handoff(chosen: Selection) -> None:
    events: list[str] = []

    def collect() -> Selection:
        events.append("collect")
        return chosen

    def check(binding: DriverBinding) -> str:
        events.append("check")
        return check_driver(binding)

    def launch(
        case: composite.Case, *, expected_context: dict[str, object] | None = None,
    ) -> composite.Result:
        events.append("handoff")
        return passing(case, expected_context)

    invocation = execute_invocation(collect=collect, check=check, launch=launch)
    assert events == ["check", "collect", "check"] + ["check", "handoff", "check"] * 4 + ["check"]
    assert invocation.outcome.actual_child_starts == 0
    assert not invocation.outcome.qualified_success


def collect_without_target() -> Selection:
    attempts: list[str] = []

    def deny(*_args: object, **_kwargs: object) -> None:
        attempts.append("target-entry-during-collection")
        raise AssertionError("collection must not parse or create a process")

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(StackMachineParser, "parse", deny)
        patch.setattr(composite.subprocess, "run", deny)
        patch.setattr(composite.subprocess, "Popen", deny)
        selection = collect_selected_cases()
    assert attempts == []
    return selection


def test_deep_mixed_recipes_pass_in_observed_fresh_workers(
    request: pytest.FixtureRequest,
    record_testsuite_property: Callable[[str, object], None],
) -> None:
    """The only real-worker test: collect first, then observe the unchanged child per case."""
    starts = StartEvidence(control=False)
    root = Path(__file__).resolve(strict=True).parents[1]
    with observed_workers(starts, root):
        try:
            invocation = execute_invocation(collect=collect_without_target, starts=starts)
        except (DriverProvenanceError, SelectionError, ValueError) as error:
            if getattr(request.config.option, "xmlpath", None):
                record_testsuite_property("s4c_admission_denial", type(error).__name__)
            raise
    outcome, selection = invocation.outcome, invocation.selection
    # Preserve source-free evidence and the first exact synthetic failing recipe BEFORE assertions.
    if getattr(request.config.option, "xmlpath", None):
        if invocation.summary is not None:
            record_testsuite_property("s4c_deep_mixed_markdown_summary", json.dumps(invocation.summary, sort_keys=True))
        if invocation.summary_error is not None:
            record_testsuite_property("s4c_summary_error", invocation.summary_error)
        if outcome.first_non_pass_index is not None:
            result = outcome.results[outcome.first_non_pass_index]
            record_testsuite_property("s4c_first_failure_recipe", json.dumps(asdict(result.recipe), sort_keys=True))
    assert invocation.summary_error is None and invocation.summary is not None
    summary = validate_summary(invocation.summary)
    assert outcome.qualified_success, json.dumps(summary, sort_keys=True)
    assert not outcome.control
    assert 3 <= len(selection.cases) <= 8
    assert outcome.actual_child_starts == outcome.handed_off == outcome.attempted == len(selection.cases)
    assert len(outcome.results) == len(selection.cases)
    assert check_driver(invocation.binding) == "intact"
    for case, result in zip(selection.cases, outcome.results, strict=True):
        assert result_passes(result, case)
        assert result.source_context is invocation.context
        envelope = result.worker_envelope
        assert envelope is not None and set(envelope) == composite.WORKER_ENVELOPE_KEYS
        assert envelope["provenance_sha256"] == composite._provenance_sha256(invocation.context)
        assert envelope["module_origins_local"] is True and envelope["qualification_status"] == "qualified"
        assert envelope["recipe_sha256"] == composite._recipe_sha256(case.recipe)
        assert envelope["source_sha256"] == case.source_sha256
    assert summary["driver_sha256"] == hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    assert summary["helper_sha256"] == hashlib.sha256(Path(composite.__file__).read_bytes()).hexdigest()
    assert summary["lock_sha256"] == hashlib.sha256((root / "uv.lock").read_bytes()).hexdigest()
