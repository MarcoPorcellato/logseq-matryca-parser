"""Literal lexical anchors and bounded, independent sensitivity evidence."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
from collections.abc import Callable, Iterator
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import pytest

from logseq_matryca_parser._lexical_state import _LexicalState
from tests.parser_assurance import lexical_mutation as lex

RawSnapshot = tuple[str, bool, bool, bool | None]
RawAnchor = tuple[tuple[str, ...], tuple[RawSnapshot, ...]]

# Every prefix is handwritten, never captured from the target or model.
ANCHORS: dict[str, RawAnchor] = {
    "A1": (
        ("yaml_open", "yaml_close", "structural"),
        (
            ("normal", True, True, None),
            ("yaml", True, True, None),
            ("normal", False, True, None),
            ("normal", False, True, None),
        ),
    ),
    "A2": (
        ("structural", "code_open", "code_payload", "code_close", "property"),
        (
            ("normal", True, True, None),
            ("normal", False, True, None),
            ("code", False, False, None),
            ("code", False, False, None),
            ("normal", False, True, None),
            ("normal", False, True, None),
        ),
    ),
    "A3": (
        ("structural", "query_open", "query_payload", "query_close", "structural"),
        (
            ("normal", True, True, None),
            ("normal", False, True, None),
            ("query", False, False, None),
            ("query", False, False, None),
            ("normal", False, False, None),
            ("normal", False, True, None),
        ),
    ),
    "A4": (
        ("structural", "drawer_open", "drawer_payload", "drawer_end"),
        (
            ("normal", True, True, None),
            ("normal", False, True, None),
            ("drawer", False, True, None),
            ("drawer", False, True, True),
            ("normal", False, True, False),
        ),
    ),
    "A5": (
        ("structural", "drawer_open", "drawer_bullet"),
        (
            ("normal", True, True, None),
            ("normal", False, True, None),
            ("drawer", False, True, None),
            ("normal", False, True, False),
        ),
    ),
    "A6": (
        ("structural", "plain_continue", "structural", "property"),
        (
            ("normal", True, True, None),
            ("normal", False, True, None),
            ("normal", False, False, None),
            ("normal", False, True, None),
            ("normal", False, True, None),
        ),
    ),
    "A7": (
        ("structural", "query_continue", "query_close"),
        (
            ("normal", True, True, None),
            ("normal", False, True, None),
            ("query", False, False, None),
            ("normal", False, False, None),
        ),
    ),
    "A8": (
        ("pre_node_prose", "structural"),
        (
            ("normal", True, True, None),
            ("normal", False, True, None),
            ("normal", False, True, None),
        ),
    ),
}


def literal_snapshots(anchor: str) -> tuple[Any, ...]:
    return tuple(lex.LexicalSnapshot(*row) for row in ANCHORS[anchor][1])


@pytest.mark.parametrize("anchor", tuple(ANCHORS))
def test_anchor_model_matches_every_handwritten_prefix(anchor: str) -> None:
    """Catch a wrong mode, flag or return in the independent transition table."""
    actual = lex.model_trace(ANCHORS[anchor][0])
    assert actual == literal_snapshots(anchor)


@pytest.mark.parametrize("anchor", tuple(ANCHORS))
def test_anchor_real_state_through_recipe_replay(anchor: str, invocation: dict[str, Any]) -> None:
    """Catch stale flags, wrong modes and drawer returns in the actual class."""
    trace = ANCHORS[anchor][0]
    actual = lex.replay_trace(
        _LexicalState, lex.canonical_trace(trace), budget=invocation["budget"]
    )
    assert actual == literal_snapshots(anchor)
    lex.assert_trace(trace, actual, literal_snapshots(anchor))


def test_anchor_comparison_reports_initial_before_first_action() -> None:
    """Catch initial-state evidence incorrectly labeled as action zero."""
    trace = ANCHORS["A1"][0]
    expected = literal_snapshots("A1")
    actual = (replace(expected[0], mode="yaml"), *expected[1:])
    with pytest.raises(lex.TraceMismatch) as caught:
        lex.assert_trace(trace, actual, expected)
    assert (caught.value.snapshot_index, caught.value.action_index) == (0, None)
    assert (caught.value.action_name, caught.value.field) == ("initial", "mode")


def test_anchor_comparison_reports_first_action_and_field_precedence() -> None:
    """Catch wrong action mapping or comparison that skips the first field."""
    trace = ANCHORS["A1"][0]
    expected = literal_snapshots("A1")
    actual = (
        expected[0],
        replace(expected[1], mode="code", frontmatter_active=False, properties_allowed=False),
        *expected[2:],
    )
    with pytest.raises(lex.TraceMismatch) as caught:
        lex.assert_trace(trace, actual, expected)
    assert (caught.value.snapshot_index, caught.value.action_index) == (1, 0)
    assert (caught.value.action_name, caught.value.field) == ("yaml_open", "mode")


@pytest.mark.parametrize("short_actual", (False, True))
def test_anchor_missing_prefix_is_protocol_error_not_detection(short_actual: bool) -> None:
    """Catch zip truncation silently accepting an incomplete observation."""
    trace = ANCHORS["A1"][0]
    expected = literal_snapshots("A1")
    with pytest.raises(lex.TraceProtocolError):
        lex.assert_trace(
            trace,
            expected[:-1] if short_actual else expected,
            expected if short_actual else expected[:-1],
        )


INVALID_RECIPES = (
    b'{"schema":"lexical_trace_v1","schema":"lexical_trace_v1","actions":["structural"]}',
    b'{"schema":"lexical_trace_v1","actions":["structural"],"extra":true}',
    b'{"schema":"other","actions":["structural"]}',
    b'{"schema":"lexical_trace_v1","actions":[]}',
    b'{"schema":"lexical_trace_v1","actions":["unknown"]}',
    b'{"schema":"lexical_trace_v1","actions":[true]}',
    b'{"schema":"lexical_trace_v1","actions":[1.0]}',
    b'{"schema":"lexical_trace_v1","actions":[NaN]}',
    b'{"schema":"lexical_trace_v1","actions":[Infinity]}',
    b'{"schema":"lexical_trace_v1","actions":"structural"}',
    b'{"schema":"lexical_trace_v1","actions":["code_close"]}',
    b'{"schema":"lexical_trace_v1","actions":["code_open","query_open"]}',
    b'{"schema":"lexical_trace_v1","actions":["structural","yaml_open"]}',
    b'{"schema":"lexical_trace_v1","actions":["structural","pre_node_prose"]}',
    b'{"schema":"lexical_trace_v1","actions":["drawer_open","structural"]}',
    json.dumps({"schema": "lexical_trace_v1", "actions": ["structural"] * 9}).encode(),
    b" " * 513,
    b"\xff",
    b"[]",
    b"null",
)


@pytest.mark.parametrize("raw", INVALID_RECIPES)
def test_admission_rejects_invalid_recipe_before_factory(raw: bytes) -> None:
    """Catch malformed input acceptance or constructing target work too early."""
    calls: list[str] = []

    def factory() -> object:
        calls.append("constructed")
        return object()

    with pytest.raises(ValueError):
        lex.replay_trace(factory, raw)
    assert calls == []


def test_admission_canonical_recipe_retains_exact_actions() -> None:
    """Catch repair/truncation or action loss in replay admission."""
    raw = b'{"schema":"lexical_trace_v1","actions":["structural","plain_continue"]}'
    assert lex.admit_trace(raw) == ("structural", "plain_continue")
    assert json.loads(lex.canonical_trace(("structural", "plain_continue"))) == {
        "schema": "lexical_trace_v1",
        "actions": ["structural", "plain_continue"],
    }


def _record_harness_error(
    state: dict[str, Any],
    error: Exception,
    stage: str,
    mutation_id: lex.MutationID | None = None,
    trace_id: str | None = None,
) -> None:
    """Retain bounded error identity, never raw text or a credited detection."""
    if len(state["harness_errors"]) >= 8:
        raise lex.TraceBudgetExceeded("structured harness-error ceiling exceeded")
    categories = (
        (lex.MutationAdmissionError, "admission"),
        (lex.TraceProtocolError, "protocol"),
        (lex.CloneOwnershipError, "ownership"),
        (lex.CloneAttributionError, "attribution"),
        (lex.TraceAccountingError, "accounting"),
        (lex.TraceBudgetExceeded, "budget"),
        (lex.MutationEvidenceError, "evidence"),
    )
    category = next(
        (value for error_type, value in categories if isinstance(error, error_type)),
        "unexpected",
    )
    known_types = {error_type for error_type, _ in categories}
    state["harness_errors"].append(
        {
            "classification": "INVALID" if category == "admission" else "HARNESS_ERROR",
            "category": category,
            "error_type": type(error).__name__ if type(error) in known_types else "UnexpectedError",
            "stage": stage,
            "mutation_id": mutation_id,
            "trace_id": trace_id,
        }
    )


def _finish_invocation(
    state: dict[str, Any],
    source: lex.AdmittedSource,
    started: float,
    emit: Callable[[str], None] | None,
) -> None:
    """Finalize one invocation; fake controls use the same orchestration."""
    budget = state["budget"]
    gaps = budget.accounting_gaps()
    remaining = [
        lex.variant_module_name(x)
        for x in (None, *lex.MUTATION_IDS)
        if lex.variant_module_name(x) in sys.modules
    ]
    if gaps:
        _record_harness_error(state, lex.TraceAccountingError(), "finalization")
    if remaining:
        _record_harness_error(state, lex.CloneOwnershipError(), "finalization")
    summary = {
        "schema": "s4a_lexical_sensitivity_v1",
        "base_commit": "c40d700ecbe10f8294c5f25c6c0a185ebfd2bdbb",
        "source_state": "not inspected",
        "python": platform.python_version(),
        "platform": platform.system(),
        "source_raw_sha256": source.raw_digest,
        "source_canonical_sha256": source.canonical_digest,
        "helper_sha256": hashlib.sha256(Path(lex.__file__).read_bytes()).hexdigest(),
        "test_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "lock_sha256": hashlib.sha256(
            lex.selected_source_path().parents[2].joinpath("uv.lock").read_bytes()
        ).hexdigest(),
        "counts": {
            "compilations_attempted": budget.compilations,
            "compilations_completed": budget.completed_compilations,
            "trace_attempted": budget.trace_attempted,
            "factory_completed": budget.factory_completed,
            "trace_completed": budget.trace_completed,
            "dispatch_attempted": budget.dispatch_attempted,
            "dispatch_completed": budget.dispatch_completed,
            "baseline_attempted": budget.baseline_attempted,
            "mutant_attempted": budget.mutant_attempted,
            "generated_attempted": budget.generated_attempted,
        },
        "accounting_gaps": gaps,
        "compilation_labels": budget.compilation_labels,
        "mutation_rows": [asdict(row) for row in state["rows"]],
        "harness_errors": state["harness_errors"],
        "generated_recipes": budget.generated_recipes,
        "first_failure": None if budget.first_failure is None else asdict(budget.first_failure),
        "owned_modules_remaining": remaining,
        "elapsed_seconds": time.perf_counter() - started,
    }
    payload = lex.summary_json(summary)
    if emit is not None:
        emit(payload)
    # Preserve diagnostics first, but incomplete work must still fail closed.
    budget.assert_balanced()
    if remaining:
        raise lex.CloneOwnershipError("synthetic identities remain at finalization")
    if state["harness_errors"]:
        raise lex.MutationEvidenceError("invocation contains retained harness errors")


def test_summary_does_not_assert_checkout_state() -> None:
    """Catch a receipt claiming live checkout status without inspecting it."""
    state: dict[str, Any] = {
        "budget": lex.TraceBudget(),
        "rows": [],
        "labels": [],
        "harness_errors": [],
    }
    payloads: list[str] = []
    _finish_invocation(
        state,
        lex.admit_source(lex.read_selected_source()),
        time.perf_counter(),
        payloads.append,
    )
    assert len(payloads) == 1
    summary = json.loads(payloads[0])
    assert summary["source_state"] == "not inspected"
    assert summary["counts"]["trace_attempted"] == 0
    assert summary["counts"]["compilations_attempted"] == 0


@pytest.fixture(scope="module")
def invocation(
    request: pytest.FixtureRequest,
    record_testsuite_property: Callable[[str, object], None],
) -> Iterator[dict[str, Any]]:
    started = time.perf_counter()
    state: dict[str, Any] = {
        "budget": lex.TraceBudget(),
        "rows": [],
        "labels": [],
        "harness_errors": [],
    }
    source = lex.admit_source(lex.read_selected_source())
    yield state

    def emit(payload: str) -> None:
        record_testsuite_property("s4a_lexical_summary", payload)

    _finish_invocation(
        state, source, started, emit if getattr(request.config.option, "xmlpath", None) else None
    )


def test_clone_source_admits_only_hash_bound_lf_or_crlf(monkeypatch: pytest.MonkeyPatch) -> None:
    """Catch permissive source admission or executable work during data validation."""

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("admission must not compile an executable copy")

    monkeypatch.setattr(lex, "_compile_copy", forbidden)
    source = lex.read_selected_source().replace(b"\r\n", b"\n")
    lf = lex.admit_source(source)
    crlf = lex.admit_source(source.replace(b"\n", b"\r\n"))
    assert (
        lf.canonical_digest
        == crlf.canonical_digest
        == ("1b14077d0294861859b4ce26aa4573589d3067b08a342467b6a1e9a9b209344b")
    )
    assert lf.raw_digest != crlf.raw_digest
    for invalid in (b"\xff", source + b"\n", b"x" * 16385, source.replace(b"\n", b"\r", 1)):
        with pytest.raises(lex.MutationAdmissionError):
            lex.admit_source(invalid)


@pytest.mark.parametrize("mutation", ("M1", "M2", "M3", "M4", "M5", "M6"))
def test_mutant_catalog_reverses_only_the_designated_edit(mutation: Any) -> None:
    """Catch a wrong mutation selector, a missing edit or an unauthorized second edit."""
    import ast
    from copy import deepcopy

    original = lex.admit_source(lex.read_selected_source()).tree
    mutated = lex.apply_mutation(original, mutation)
    assert ast.dump(mutated, include_attributes=False) != ast.dump(
        original, include_attributes=False
    )
    lex.validate_mutation(original, mutated, mutation)
    extra = deepcopy(mutated)
    extra.body.append(ast.Pass())
    with pytest.raises(lex.MutationAdmissionError):
        lex.validate_mutation(original, extra, mutation)
    with pytest.raises(lex.MutationAdmissionError):
        lex.validate_mutation(original, original, mutation)


@pytest.mark.parametrize("selector_case", ("missing", "ambiguous", "unknown"))
def test_mutant_selector_rejects_before_executable_compilation(
    selector_case: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Catch zero/multiple selectors or an unknown ID reaching compilation."""
    import ast
    from copy import deepcopy

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("invalid selector must not compile")

    monkeypatch.setattr(lex, "_compile_copy", forbidden)
    tree = lex.admit_source(lex.read_selected_source()).tree
    definition = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "_LexicalState"
    )
    method = next(
        node
        for node in definition.body
        if isinstance(node, ast.FunctionDef) and node.name == "consume_code_line"
    )
    if selector_case == "missing":
        definition.body.remove(method)
    elif selector_case == "ambiguous":
        definition.body.append(deepcopy(method))
    mutation: Any = "unknown" if selector_case == "unknown" else "M1"
    with pytest.raises(lex.MutationAdmissionError):
        lex.apply_mutation(tree, mutation)


@pytest.mark.parametrize("output_kind", ("unchanged", "extra_edit"))
def test_loader_rejects_invalid_mutator_output_before_compilation(
    output_kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Catch loader validation being removed or moved after executable work."""
    import ast
    from copy import deepcopy

    mutator = lex.apply_mutation
    calls: list[str] = []
    budget = lex.TraceBudget()
    missing = object()
    names = tuple(lex.variant_module_name(x) for x in (None, *lex.MUTATION_IDS))
    before = {name: sys.modules.get(name, missing) for name in names}
    assert lex.variant_module_name("M1") not in sys.modules

    def invalid_output(original: ast.Module, mutation_id: lex.MutationID) -> ast.Module:
        assert mutation_id == "M1"
        if output_kind == "unchanged":
            return deepcopy(original)
        changed = mutator(original, mutation_id)
        changed.body.append(ast.Pass())
        return ast.fix_missing_locations(changed)

    def forbidden(*args: object, **kwargs: object) -> object:
        calls.append("compiler reached")
        raise AssertionError("invalid mutator output reached forbidden compilation")

    monkeypatch.setattr(lex, "apply_mutation", invalid_output)
    monkeypatch.setattr(lex, "_compile_copy", forbidden)
    with pytest.raises(lex.MutationAdmissionError):
        with lex.isolated_variant(lex.read_selected_source(), "M1", budget=budget):
            pytest.fail("invalid AST yielded a target factory")
    assert calls == []
    assert budget.compilations == budget.completed_compilations == 0
    assert budget.trace_attempted == budget.dispatch_attempted == 0
    assert all(sys.modules.get(name, missing) is before[name] for name in names)


def test_clone_collision_keeps_foreign_entry_without_compiling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catch overwriting or deleting a module identity not owned by this loader."""
    import sys
    from types import ModuleType

    name = lex.variant_module_name(None)
    assert name not in sys.modules
    sentinel = ModuleType(name)
    sys.modules[name] = sentinel
    calls: list[str] = []

    def forbidden(*args: object, **kwargs: object) -> object:
        calls.append("compiled")
        raise AssertionError("collision must reject before compilation")

    monkeypatch.setattr(lex, "_compile_copy", forbidden)
    try:
        with pytest.raises(lex.CloneOwnershipError):
            with lex.isolated_variant(lex.read_selected_source(), None, budget=lex.TraceBudget()):
                pytest.fail("foreign collision yielded a factory")
        assert sys.modules[name] is sentinel
        assert calls == []
    finally:
        if sys.modules.get(name) is sentinel:
            del sys.modules[name]


def test_clone_body_exception_removes_only_owned_entry(invocation: dict[str, Any]) -> None:
    """Catch a leaked positively owned module after an exceptional context body."""
    import sys

    name = lex.variant_module_name(None)
    assert name not in sys.modules
    with pytest.raises(RuntimeError, match="controlled body failure"):
        with lex.isolated_variant(lex.read_selected_source(), None, budget=invocation["budget"]):
            raise RuntimeError("controlled body failure")
    assert name not in sys.modules


def test_clone_replacement_retained_and_reported_as_harness_error(
    invocation: dict[str, Any],
) -> None:
    """Catch cleanup erasing an external replacement instead of reporting ownership loss."""
    import sys
    from types import ModuleType

    name = lex.variant_module_name(None)
    assert name not in sys.modules
    replacement = ModuleType(name)
    try:
        with pytest.raises(lex.CloneOwnershipError):
            with lex.isolated_variant(
                lex.read_selected_source(), None, budget=invocation["budget"]
            ):
                sys.modules[name] = replacement
        assert sys.modules[name] is replacement
    finally:
        # The fixture, not the loader, owns this deliberately injected sentinel.
        if sys.modules.get(name) is replacement:
            del sys.modules[name]


def test_clone_compilation_ceiling_refuses_tenth_before_compile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catch a loader that checks its compilation ceiling after executable work."""
    import sys

    calls: list[str] = []

    def forbidden(*args: object, **kwargs: object) -> object:
        calls.append("compiled")
        raise AssertionError("tenth executable compilation must not occur")

    monkeypatch.setattr(lex, "_compile_copy", forbidden)
    with pytest.raises(lex.TraceBudgetExceeded):
        with lex.isolated_variant(
            lex.read_selected_source(), None, budget=lex.TraceBudget(compilations=9)
        ):
            pytest.fail("over-budget loader yielded")
    assert calls == []
    assert lex.variant_module_name(None) not in sys.modules


@pytest.mark.parametrize("bad_label", ("filename", "nested", "file"))
def test_clone_attribution_rejects_production_identity_without_target_work(bad_label: str) -> None:
    """Catch source-copy execution falsely attributed to the production pathname."""
    from types import ModuleType

    def inert() -> None:
        pass

    label = "<s4-lexical-copy:unmodified>"
    production = str(lex.selected_source_path())
    if bad_label == "file":
        module = ModuleType("synthetic")
        module.__file__ = production
        with pytest.raises(lex.CloneAttributionError, match="file label"):
            lex.validate_copy_module(module, label)
    else:
        bad = inert.__code__.replace(co_filename=production)
        root = (
            bad
            if bad_label == "filename"
            else inert.__code__.replace(
                co_filename=label, co_consts=(*inert.__code__.co_consts, bad)
            )
        )
        with pytest.raises(lex.CloneAttributionError, match="code filename"):
            lex.validate_copy_code(root, label)


def _collect_mutant_matrix(invocation: dict[str, Any], source: bytes) -> None:
    """Keep one production-used collector available to fake failure controls."""
    rows = invocation["rows"]
    if rows:
        raise lex.MutationEvidenceError("matrix observations must start empty")
    # One admitted unmodified copy first; each mutant is loaded exactly once.
    for mutation in (None, *lex.MUTATION_IDS):
        stage = "setup"
        trace_id: str | None = None
        try:
            with lex.isolated_variant(source, mutation, budget=invocation["budget"]) as factory:
                for trace_id, (trace, _) in ANCHORS.items():
                    stage = "observation"
                    actual = lex.observe_trace(
                        factory,
                        trace,
                        budget=invocation["budget"],
                        phase="baseline" if mutation is None else "mutant",
                    )
                    stage = "comparison"
                    mismatch = None
                    try:
                        lex.assert_trace(trace, actual, literal_snapshots(trace_id))
                    except lex.TraceMismatch as error:
                        mismatch = error
                    if mutation is None:
                        assert mismatch is None, "unmodified copy does not match the literal oracle"
                    else:
                        stage = "classification"
                        if len(rows) >= 48:
                            raise lex.MutationEvidenceError("matrix row ceiling exceeded")
                        rows.append(lex.classify_mutant(mutation, trace_id, mismatch))
                stage = "cleanup"
                trace_id = None
        except Exception as error:
            _record_harness_error(invocation, error, stage, mutation, trace_id)
            raise
    try:
        lex.require_required_witnesses(tuple(rows))
        assert len(rows) == 48
    except Exception as error:
        _record_harness_error(invocation, error, "acceptance")
        raise


def test_clone_baseline_and_mutant_matrix(
    invocation: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Catch each selected fault using the full independent prefix oracle."""
    import sys

    original_module = sys.modules[_LexicalState.__module__]
    original_class = original_module._LexicalState
    source = lex.read_selected_source()
    raw_digest = lex.admit_source(source).raw_digest
    compiler = lex._compile_copy
    labels: list[str] = []

    def observed_compile(tree: Any, label: str) -> Any:
        code = compiler(tree, label)
        lex.validate_copy_code(code, label)
        labels.append(label)
        return code

    monkeypatch.setattr(lex, "_compile_copy", observed_compile)
    _collect_mutant_matrix(invocation, source)
    invocation["labels"] = labels
    try:
        assert len(labels) == 7
        assert set(labels) == {
            "<s4-lexical-copy:unmodified>",
            *(f"<s4-lexical-copy:{x}>" for x in lex.MUTATION_IDS),
        }
        assert invocation["budget"].compilations <= 9
        assert sys.modules[_LexicalState.__module__] is original_module
        assert original_module._LexicalState is original_class is _LexicalState
        assert lex.admit_source(lex.read_selected_source()).raw_digest == raw_digest
        assert not any(lex.variant_module_name(x) in sys.modules for x in (None, *lex.MUTATION_IDS))
    except Exception as error:
        _record_harness_error(invocation, error, "postcheck")
        raise


@pytest.mark.parametrize("wrong_coordinate", ("trace", "stage"))
def test_mutant_required_witness_cannot_be_replaced_by_same_field_elsewhere(
    wrong_coordinate: str,
) -> None:
    """Catch accepting a correct field at the wrong designated trace or action."""
    rows = [
        lex.MutationObservation(mutation, trace, "MATCH", None, None, None, False)
        for mutation in lex.MUTATION_IDS
        for trace in ANCHORS
    ]
    witnesses: tuple[tuple[lex.MutationID, str, int, str, str], ...] = (
        ("M1", "A2", 3, "code_close", "properties_allowed"),
        ("M2", "A3", 3, "query_close", "properties_allowed"),
        ("M3", "A4", 3, "drawer_end", "mode"),
        ("M4", "A6", 2, "structural", "properties_allowed"),
        ("M5", "A7", 1, "query_continue", "mode"),
        ("M6", "A8", 0, "pre_node_prose", "frontmatter_active"),
    )
    for mutation, trace, index, action, field in witnesses:
        position = next(
            i for i, row in enumerate(rows) if row.mutation_id == mutation and row.trace_id == trace
        )
        rows[position] = lex.MutationObservation(
            mutation, trace, "DETECTED", index, action, field, True
        )
    lex.require_required_witnesses(tuple(rows))
    position = next(
        i for i, row in enumerate(rows) if row.mutation_id == "M1" and row.trace_id == "A2"
    )
    if wrong_coordinate == "stage":
        rows[position] = replace(rows[position], action_index=1, action_name="code_open")
    else:
        alternate = next(
            i for i, row in enumerate(rows) if row.mutation_id == "M1" and row.trace_id == "A1"
        )
        rows[position] = lex.MutationObservation("M1", "A2", "MATCH", None, None, None, False)
        rows[alternate] = lex.MutationObservation(
            "M1", "A1", "DETECTED", 3, "code_close", "properties_allowed", True
        )
    with pytest.raises(lex.MutationEvidenceError):
        lex.require_required_witnesses(tuple(rows))


@pytest.mark.parametrize(
    "failure", ("missing_witness", "harness_error", "setup", "protocol", "ownership")
)
def test_matrix_failure_preserves_complete_or_partial_rows_without_target_work(
    failure: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Catch survivor/error evidence disappearing before acceptance or setup failure."""
    from contextlib import contextmanager

    state: dict[str, Any] = {
        "budget": lex.TraceBudget(),
        "rows": [],
        "labels": [],
        "harness_errors": [],
    }
    current: dict[str, Any] = {}
    partial = failure in ("setup", "protocol", "ownership")
    errors = {
        "setup": lex.MutationAdmissionError,
        "protocol": lex.TraceProtocolError,
        "ownership": lex.CloneOwnershipError,
    }

    @contextmanager
    def fake_loader(
        source: bytes, mutation: lex.MutationID | None, *, budget: lex.TraceBudget
    ) -> Iterator[Callable[[], object]]:
        current["mutation"] = mutation
        if mutation == "M2" and partial:
            assert len(state["rows"]) == 8, "rows must already be durable before next setup"
            if failure != "protocol":
                raise errors[failure]("controlled fake setup failure")

        def forbidden_factory() -> object:
            pytest.fail("frozen row controls must not instantiate a target")

        yield forbidden_factory

    def fake_observe(
        factory: Callable[[], object],
        trace: tuple[str, ...],
        *,
        budget: lex.TraceBudget,
        phase: str,
    ) -> tuple[Any, ...]:
        if current["mutation"] == "M2" and failure == "protocol":
            raise lex.TraceProtocolError("controlled fake observation failure")
        trace_id = next(key for key, value in ANCHORS.items() if value[0] == trace)
        return literal_snapshots(trace_id)

    def fake_compare(
        trace: tuple[str, ...], actual: tuple[Any, ...], expected: tuple[Any, ...]
    ) -> None:
        if failure == "harness_error" and current["mutation"] == "M1" and trace == ANCHORS["A2"][0]:
            index = 4
            raise lex.TraceMismatch(
                trace, index, "mode", replace(expected[index], mode="code"), expected[index]
            )
        assert actual == expected

    monkeypatch.setattr(lex, "isolated_variant", fake_loader)
    monkeypatch.setattr(lex, "observe_trace", fake_observe)
    monkeypatch.setattr(lex, "assert_trace", fake_compare)
    expected_error = errors[failure] if partial else lex.MutationEvidenceError
    with pytest.raises(expected_error):
        _collect_mutant_matrix(state, b"frozen control; no executable source")
    assert len(state["rows"]) == (8 if partial else 48)
    assert len(state["harness_errors"]) == 1
    assert state["harness_errors"][0]["classification"] == (
        "INVALID" if failure == "setup" else "HARNESS_ERROR"
    )
    assert state["harness_errors"][0]["stage"] == (
        "observation" if failure == "protocol" else "setup" if partial else "acceptance"
    )
    if failure == "harness_error":
        assert any(row.classification == "HARNESS_ERROR" for row in state["rows"])
    else:
        assert all(row.classification == "MATCH" for row in state["rows"])
    payloads: list[str] = []
    with pytest.raises(lex.MutationEvidenceError):
        _finish_invocation(
            state,
            lex.admit_source(lex.read_selected_source()),
            time.perf_counter(),
            payloads.append,
        )
    assert len(payloads) == 1
    summary = json.loads(payloads[0])
    assert len(summary["mutation_rows"]) == (8 if partial else 48)
    assert summary["harness_errors"] == state["harness_errors"]
    assert summary["counts"]["trace_attempted"] == 0
    assert summary["counts"]["compilations_attempted"] == 0
    assert len(payloads[0].encode("utf-8")) <= 65536


@pytest.mark.parametrize(
    ("counters", "gaps"),
    (
        ({"compilations": 1}, ["compilation"]),
        ({"trace_attempted": 1, "baseline_attempted": 1}, ["factory", "trace"]),
        (
            {
                "trace_attempted": 1,
                "factory_completed": 1,
                "baseline_attempted": 1,
                "dispatch_attempted": 1,
            },
            ["trace", "dispatch"],
        ),
    ),
)
def test_summary_emitted_before_incomplete_accounting_rejection(
    counters: dict[str, int], gaps: list[str]
) -> None:
    """Catch accounting rejection erasing counters and the immutable first failure."""
    budget = lex.TraceBudget(
        compilations=counters.get("compilations", 0),
        trace_attempted=counters.get("trace_attempted", 0),
        factory_completed=counters.get("factory_completed", 0),
        baseline_attempted=counters.get("baseline_attempted", 0),
        dispatch_attempted=counters.get("dispatch_attempted", 0),
    )
    wanted = lex.LexicalSnapshot("normal", False, True, None)
    first = budget.save_first_failure(
        ("structural",),
        0,
        "structural",
        "frontmatter_active",
        replace(wanted, frontmatter_active=True),
        wanted,
    )
    row = lex.MutationObservation("M1", "A1", "MATCH", None, None, None, False)
    state: dict[str, Any] = {
        "budget": budget,
        "rows": [row],
        "labels": [],
        "harness_errors": [],
    }
    payloads: list[str] = []
    with pytest.raises(lex.TraceAccountingError):
        _finish_invocation(
            state,
            lex.admit_source(lex.read_selected_source()),
            time.perf_counter(),
            payloads.append,
        )
    assert len(payloads) == 1
    summary = json.loads(payloads[0])
    assert summary["accounting_gaps"] == gaps
    assert summary["mutation_rows"] == [asdict(row)]
    assert summary["first_failure"] == json.loads(lex.summary_json(asdict(first)))
    assert budget.first_failure is first
    assert summary["harness_errors"][0]["category"] == "accounting"
    assert summary["harness_errors"][0]["classification"] == "HARNESS_ERROR"


def test_summary_emitted_before_registry_rejection(monkeypatch: pytest.MonkeyPatch) -> None:
    """Catch module-identity checks suppressing diagnostics or deleting foreign state."""
    from types import ModuleType

    name = lex.variant_module_name("M6")
    assert name not in sys.modules
    sentinel = ModuleType(name)
    monkeypatch.setitem(sys.modules, name, sentinel)
    state: dict[str, Any] = {
        "budget": lex.TraceBudget(),
        "rows": [],
        "labels": [],
        "harness_errors": [],
    }
    payloads: list[str] = []
    with pytest.raises(lex.CloneOwnershipError):
        _finish_invocation(
            state,
            lex.admit_source(lex.read_selected_source()),
            time.perf_counter(),
            payloads.append,
        )
    assert len(payloads) == 1
    summary = json.loads(payloads[0])
    assert summary["owned_modules_remaining"] == [name]
    assert summary["harness_errors"][0]["category"] == "ownership"
    assert sys.modules[name] is sentinel


def test_budget_evaluation_49_refused_before_factory() -> None:
    """Catch admission of another generated target after the 48-body ceiling."""
    calls: list[str] = []
    budget = lex.TraceBudget(generated_attempted=48)

    def factory() -> object:
        calls.append("constructed")
        return object()

    with pytest.raises(lex.TraceBudgetExceeded):
        lex.observe_trace(factory, ("structural",), budget=budget, phase="generated")
    assert calls == []


def test_budget_ninth_action_refused_before_factory_or_dispatch() -> None:
    """Catch truncating an oversized trace into runnable target work."""
    calls: list[str] = []

    def factory() -> object:
        calls.append("constructed")
        return object()

    with pytest.raises(lex.TraceProtocolError):
        lex.observe_trace(factory, ("structural",) * 9, budget=lex.TraceBudget())
    assert calls == []


def test_budget_attempted_and_completed_dispatches_cannot_be_conflated() -> None:
    """Catch losing a failed call by incrementing completion before dispatch."""

    class FakeState:
        mode = "normal"
        frontmatter_active = True
        properties_allowed = True

        def observe_structural_node(self) -> None:
            raise RuntimeError("controlled fake dispatch")

    budget = lex.TraceBudget()
    with pytest.raises(RuntimeError, match="controlled fake dispatch"):
        lex.observe_trace(FakeState, ("structural",), budget=budget)
    assert (budget.trace_attempted, budget.factory_completed, budget.trace_completed) == (1, 1, 0)
    assert (budget.dispatch_attempted, budget.dispatch_completed) == (1, 0)
    with pytest.raises(lex.TraceAccountingError):
        budget.assert_balanced()


def test_budget_first_failure_is_immutable_and_precedes_later_budget_error() -> None:
    """Catch confirmation/budget handling overwriting the original failure."""
    from dataclasses import FrozenInstanceError

    budget = lex.TraceBudget(generated_attempted=48)
    wanted = lex.LexicalSnapshot("normal", False, True, None)
    observed = lex.LexicalSnapshot("normal", True, True, None)
    first = budget.save_first_failure(
        ("structural",), 0, "structural", "frontmatter_active", observed, wanted
    )
    second = budget.save_first_failure(
        ("property",),
        0,
        "property",
        "properties_allowed",
        lex.LexicalSnapshot("normal", False, False, None),
        wanted,
    )
    assert second is first is budget.first_failure
    assert first.trace == ("structural",)
    with pytest.raises(FrozenInstanceError):
        first.field = "mode"  # type: ignore[misc]
    calls: list[str] = []

    def factory() -> object:
        calls.append("constructed")
        return object()

    with pytest.raises(lex.TraceMismatch) as caught:
        lex.observe_trace(factory, ("property",), budget=budget, phase="generated")
    assert (caught.value.action_name, caught.value.field) == ("structural", "frontmatter_active")
    assert budget.first_failure is first
    assert calls == []


def test_budget_initial_failure_can_be_preserved_without_action_index() -> None:
    """Catch failure recording that assumes every mismatch followed an action."""
    budget = lex.TraceBudget()
    wanted = lex.LexicalSnapshot("normal", True, True, None)
    first = budget.save_first_failure(
        ("structural",), None, "initial", "mode", replace(wanted, mode="yaml"), wanted
    )
    assert first.action_index is None
    assert first.action_name == "initial"


def test_budget_summary_overflow_is_rejected_not_truncated() -> None:
    """Catch output truncation that would silently erase the first failure."""
    with pytest.raises(lex.TraceBudgetExceeded):
        lex.summary_json({"first_failure": "x" * 65537})
    assert json.loads(lex.summary_json({"first_failure": None, "completed": 2})) == {
        "first_failure": None,
        "completed": 2,
    }


def test_generated_lexical_traces_match_independent_prefix_model(
    invocation: dict[str, Any],
) -> None:
    """Catch wrong lexical transitions beyond the fixed anchors, within admitted limits."""
    from hypothesis import Phase, given, settings

    @settings(
        max_examples=32,
        derandomize=True,
        database=None,
        deadline=None,
        phases=(Phase.generate,),
        report_multiple_bugs=False,
        print_blob=False,
        suppress_health_check=(),
    )
    @given(lex.lexical_traces())
    def check(trace: tuple[str, ...]) -> None:
        recipe = lex.canonical_trace(trace)
        assert lex.admit_trace(recipe) == trace
        actual = lex.observe_trace(
            _LexicalState, trace, budget=invocation["budget"], phase="generated"
        )
        expected = lex.model_trace(trace)
        try:
            lex.assert_trace(trace, actual, expected)
        except lex.TraceMismatch as mismatch:
            invocation["budget"].save_first_failure(
                trace,
                mismatch.action_index,
                mismatch.action_name,
                mismatch.field,
                mismatch.actual,
                mismatch.expected,
            )
            raise

    check()
