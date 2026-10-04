"""Parser-free controls for the bounded composite Markdown assurance harness."""

from __future__ import annotations

import hashlib
import importlib.machinery
import json
import subprocess
import sys
import types
from collections.abc import Iterator
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, cast

import pytest
from hypothesis import given, settings

from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage
from logseq_matryca_parser.logos_parser import StackMachineParser
from tests.parser_assurance import composite_properties as composite

_REVISION_PROBE = composite._revision
_CAPTURE_SOURCE_CONTEXT = composite._capture_source_context
_IMPLEMENTATION_MANIFEST = composite.implementation_manifest
_MODULE_ORIGINS_ARE_LOCAL = composite._module_origins_are_local


@pytest.fixture(autouse=True)
def forbid_parser_and_real_processes(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    parser_calls: list[str] = []
    process_calls: list[str] = []

    def forbidden_parse(*_args: object, **_kwargs: object) -> None:
        parser_calls.append("StackMachineParser.parse")
        raise AssertionError("parser execution forbidden in harness tests")

    def forbidden_run(*_args: object, **_kwargs: object) -> None:
        process_calls.append("subprocess.run")
        raise AssertionError("real subprocess execution forbidden in harness tests")

    monkeypatch.setattr(StackMachineParser, "parse", forbidden_parse)
    monkeypatch.setattr(composite.subprocess, "run", forbidden_run)
    monkeypatch.setattr(composite, "_revision", lambda *_args, **_kwargs: composite.BASELINE_REVISION)
    monkeypatch.setattr(composite.platform, "platform", lambda: "parser-free-test-platform")
    yield
    assert parser_calls == []
    assert process_calls == []


def _literal_expected() -> tuple[composite.ExpectedBlock, ...]:
    child = composite.ExpectedBlock(
        index=1, depth=1,
        content="DOING [#B] item-1 caffè [[Target]] #topic\n    continuation-1 東京",
        line_start=4, line_end=6, task_status="DOING", task_priority="B",
        properties=(("literal-key", "kept"),), scheduled_at=None, deadline_at=None,
        wikilinks=("Target",), tags=("B", "topic"), refs=("Target", "B", "topic"), children=(),
    )
    first_root = composite.ExpectedBlock(
        index=0, depth=0,
        content=("TODO [#A] item-0 caffè [[Target]] #topic SCHEDULED: <2026-04-30 Thu> "
                 "DEADLINE: <2026-05-01 Fri>\n  continuation-0 caffè"),
        line_start=1, line_end=3, task_status="TODO", task_priority="A",
        properties=(
            ("literal-key", "kept"), ("scheduled", "<2026-04-30 Thu>"),
            ("scheduled_journal_day", 20260430), ("scheduled_iso", "2026-04-30T00:00:00"),
            ("deadline", "<2026-05-01 Fri>"), ("deadline_journal_day", 20260501),
            ("deadline_iso", "2026-05-01T00:00:00"),
        ),
        scheduled_at=1777507200, deadline_at=1777593600,
        wikilinks=("Target",), tags=("A", "topic"), refs=("Target", "A", "topic"),
        children=(child,),
    )
    second_root = composite.ExpectedBlock(
        index=2, depth=0,
        content="DONE [#C] item-2 caffè [[Target]] #topic\n  continuation-2 naïve",
        line_start=7, line_end=9, task_status="DONE", task_priority="C",
        properties=(("literal-key", "kept"),), scheduled_at=None, deadline_at=None,
        wikilinks=("Target",), tags=("C", "topic"), refs=("Target", "C", "topic"), children=(),
    )
    return first_root, second_root


_LITERAL_SOURCE = (
    "- TODO [#A] item-0 caffè [[Target]] #topic SCHEDULED: <2026-04-30 Thu> "
    "DEADLINE: <2026-05-01 Fri>\n"
    "  literal-key:: kept\n"
    "  continuation-0 caffè\n"
    "  - DOING [#B] item-1 caffè [[Target]] #topic\n"
    "    literal-key:: kept\n"
    "    continuation-1 東京\n"
    "- DONE [#C] item-2 caffè [[Target]] #topic\n"
    "  literal-key:: kept\n"
    "  continuation-2 naïve\n"
)


def _literal_page(expected: tuple[composite.ExpectedBlock, ...]) -> LogseqPage:
    def build(
        want: composite.ExpectedBlock, *, parent: LogseqNode | None,
        left: LogseqNode | None, sibling_position: int,
    ) -> LogseqNode:
        uuid = f"block-{want.index + 1}"
        parent_path = parent.path if parent else []
        parent_outline = parent.outline_path if parent else []
        node = LogseqNode(
            uuid=uuid, source_uuid=None, synthetic_id=True, content=want.content,
            clean_text=want.content, indent_level=want.depth, properties=dict(want.properties),
            wikilinks=list(want.wikilinks), tags=list(want.tags), refs=list(want.refs),
            task_status=want.task_status, task_priority=want.task_priority,
            scheduled_at=want.scheduled_at, deadline_at=want.deadline_at,
            parent_id=parent.uuid if parent else None, left_id=left.uuid if left else None,
            path=[*parent_path, uuid], line_start=want.line_start, line_end=want.line_end,
            outline_path=[*parent_outline, sibling_position + 1], children=[],
        )
        children: list[LogseqNode] = []
        for position, child_want in enumerate(want.children):
            left_child = children[-1] if children else None
            children.append(build(child_want, parent=node, left=left_child,
                                  sibling_position=position))
        return node.model_copy(update={"children": children})

    roots: list[LogseqNode] = []
    for position, root_want in enumerate(expected):
        left_root = roots[-1] if roots else None
        roots.append(build(root_want, parent=None, left=left_root, sibling_position=position))
    return LogseqPage(title="composite-literal", raw_content=_LITERAL_SOURCE, root_nodes=roots)


def _replace_node(page: LogseqPage, path: tuple[int, ...], field: str, value: object) -> LogseqPage:
    def update(nodes: list[LogseqNode], depth: int) -> list[LogseqNode]:
        index = path[depth]
        node = nodes[index]
        if depth == len(path) - 1:
            changed = node.model_copy(update={field: value})
        else:
            changed = node.model_copy(update={"children": update(node.children, depth + 1)})
        return [changed if offset == index else current for offset, current in enumerate(nodes)]

    return page.model_copy(update={"root_nodes": update(page.root_nodes, 0)})


def test_literal_recipe_and_model_are_independent_hand_checked_fixtures() -> None:
    recipe = composite.Recipe.literal_example()
    case = composite.build_case(recipe)
    expected = _literal_expected()
    assert case.source == _LITERAL_SOURCE
    assert case.expected == expected
    composite.assert_matches_model(_literal_page(expected), expected)


_INDEPENDENT_SCHEDULE_EPOCHS = {
    "2026-04-30 Thu": 1_777_507_200,
    "2026-08-20 Thu": 1_787_184_000,
}
_INDEPENDENT_DEADLINE_EPOCHS = {
    "2026-05-01 Fri": 1_777_593_600,
    "2026-08-22 Sat": 1_787_356_800,
}


def test_supported_epoch_dates_have_independent_fixed_expectations() -> None:
    assert set(composite.SCHEDULED_DATES) == set(_INDEPENDENT_SCHEDULE_EPOCHS)
    assert set(composite.DEADLINE_DATES) == set(_INDEPENDENT_DEADLINE_EPOCHS)


@pytest.mark.parametrize("scheduled", tuple(_INDEPENDENT_SCHEDULE_EPOCHS))
def test_build_case_schedule_epoch_matches_independent_literal(scheduled: str) -> None:
    recipe = replace(
        composite.Recipe.literal_example(), scheduled=scheduled,
        deadline="2026-05-01 Fri",
    )
    case = composite.build_case(recipe)
    assert case.expected[0].scheduled_at == _INDEPENDENT_SCHEDULE_EPOCHS[scheduled]


@pytest.mark.parametrize("deadline", tuple(_INDEPENDENT_DEADLINE_EPOCHS))
def test_build_case_deadline_epoch_matches_independent_literal(deadline: str) -> None:
    recipe = replace(
        composite.Recipe.literal_example(), scheduled="2026-04-30 Thu",
        deadline=deadline,
    )
    case = composite.build_case(recipe)
    assert case.expected[0].deadline_at == _INDEPENDENT_DEADLINE_EPOCHS[deadline]


@pytest.mark.parametrize(
    "changes",
    [
        {"seed": True}, {"shape": "private text"}, {"task": "UNKNOWN"},
        {"priority": "D"}, {"scheduled": "2026-04-30"}, {"deadline": "2026-05-01 Sat"},
        {"literal": ""}, {"reference": "arbitrary input"}, {"tag": "#hidden"},
        {"unicode": "private text"}, {"newline": "cr"},
    ],
)
def test_recipe_replay_rejects_unbounded_or_unknown_values(changes: dict[str, object]) -> None:
    payload = asdict(composite.Recipe.literal_example())
    payload.update(changes)
    with pytest.raises(ValueError):
        composite.recipe_from_json(json.dumps(payload))


def test_recipe_collection_is_bounded_unique_and_precedes_execution() -> None:
    recipes = composite.collect_recipes(seed=104, limit=4)
    assert len(recipes) <= 4
    assert len(set(recipes)) == len(recipes)
    assert all(composite.build_case(recipe).source_bytes <= 16_384 for recipe in recipes)


@pytest.mark.parametrize(
    ("path", "field", "value", "assertion_id"),
    [
        ((0,), "task_status", "DONE", "model.task_status"),
        ((0,), "properties", {"literal-key": "wrong"}, "model.properties"),
        ((0,), "wikilinks", ["Other"], "model.wikilinks"),
        ((0,), "line_end", 999, "model.line_span"),
        ((0,), "parent_id", "not-the-parent", "model.parent_id"),
    ],
)
def test_oracle_controls_reject_only_the_selected_field_corruption(
    path: tuple[int, ...], field: str, value: object, assertion_id: str,
    ) -> None:
    expected = _literal_expected()
    page = _literal_page(expected)
    composite.assert_matches_model(page, expected)
    corrupted = _replace_node(page, path, field, value)
    assert len(corrupted.root_nodes) == len(page.root_nodes)
    assert corrupted.root_nodes[1].uuid == page.root_nodes[1].uuid
    with pytest.raises(AssertionError, match=assertion_id):
        composite.assert_matches_model(corrupted, expected)


def test_test_only_oracle_mutation_is_sensitive_and_restored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = _literal_expected()
    page = _literal_page(expected)
    corrupted = _replace_node(page, (0,), "task_status", "DONE")
    original = composite._check
    before = hashlib.sha256(Path(composite.__file__).read_bytes()).hexdigest()

    def insensitive_to_task(condition: bool, identifier: str) -> None:
        if identifier != "model.task_status":
            original(condition, identifier)

    with monkeypatch.context() as context:
        context.setattr(composite, "_check", insensitive_to_task)
        composite.assert_matches_model(corrupted, expected)
    with pytest.raises(AssertionError, match="model.task_status"):
        composite.assert_matches_model(corrupted, expected)
    after = hashlib.sha256(Path(composite.__file__).read_bytes()).hexdigest()
    assert before == after


def test_worker_envelope_preserves_partial_stage_and_rejects_impossible_states() -> None:
    case = composite.build_case(composite.Recipe.literal_example())
    good = composite.worker_envelope(case)
    assert composite.parse_worker_envelope(good, case).classification == "parsed"
    roundtrip_failure = {
        **good, "classification": "semantic_roundtrip_failure", "exception_type": "SemanticRoundtripMismatch",
        "model_checked": True, "roundtrip_checked": False,
        "semantic_differences": [{"field": "properties", "outline_path": [1]}],
    }
    parsed = composite.parse_worker_envelope(roundtrip_failure, case)
    assert parsed.classification == "semantic_roundtrip_failure"
    assert parsed.model_checked is True and parsed.roundtrip_checked is False
    assert parsed.worker_envelope == roundtrip_failure
    for bad in (
        {**good, "model_checked": False},
        {**good, "roundtrip_checked": False},
        {**roundtrip_failure, "model_checked": False},
        {**good, "classification": "timeout", "roundtrip_checked": True},
        {**good, "classification": "unknown"},
        {**good, "classification": []},
        {key: value for key, value in good.items() if key != "roundtrip_checked"},
        {**good, "source_sha256": "0" * 64},
        {**good, "case_id": "other"},
    ):
        with pytest.raises(ValueError):
            composite.parse_worker_envelope(bad, case)


def test_worker_provenance_schema_and_origin_mismatches_reject_before_use() -> None:
    case = composite.build_case(composite.Recipe.literal_example())
    context = composite._capture_source_context()
    good = composite.worker_envelope(case, context)
    different_runtime = dict(context)
    different_runtime["runtime_descriptor"] = {
        **cast(dict[str, object], context["runtime_descriptor"]), "python_version": "other",
    }
    with pytest.raises(ValueError, match="provenance"):
        composite.parse_worker_envelope(good, case, different_runtime)
    for bad in (
        {**good, "schema_version": True},
        {key: value for key, value in good.items() if key != "exception_type"},
        {**good, "provenance_sha256": "0" * 64},
        {**good, "module_origins_local": False},
        {**good, "source_bytes": float(case.source_bytes)},
        {**good, "model_checked": False},
        {**good, "exception_type": "UnexpectedError"},
        {**good, "semantic_differences": [{"field": "content", "outline_path": [1]}]},
        {**good, "runtime_descriptor": context["runtime_descriptor"]},
    ):
        with pytest.raises(ValueError):
            composite.parse_worker_envelope(bad, case, context)


def test_run_case_keeps_sanitized_worker_envelope_separate_from_parent_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = composite.build_case(composite.Recipe.literal_example())
    raw = composite.worker_envelope(case)
    raw.update(classification="semantic_roundtrip_failure",
               exception_type="SemanticRoundtripMismatch", model_checked=True,
               roundtrip_checked=False,
               semantic_differences=[{"field": "properties", "outline_path": [1]}])
    completed = subprocess.CompletedProcess(["python", "-m", "worker"], 0,
                                             json.dumps(raw), "secret child stderr")
    monkeypatch.setattr(composite.subprocess, "run", lambda *_args, **_kwargs: completed)
    result = composite.run_case(case)
    assert result.classification == "semantic_roundtrip_failure"
    assert result.worker_envelope == raw
    assert "secret child stderr" not in repr(result)


@pytest.mark.parametrize(
    ("classification", "exception_type", "model_checked", "roundtrip_checked"),
    [
        ("expected_parser_error", "BlockReferenceError", False, False),
        ("unexpected_exception", "ValueError", False, False),
        ("invariant_failure", "AssertionError", False, False),
        ("runner_failure", "OSError", False, False),
        ("timeout", None, False, False),
    ],
)
def test_valid_fail_closed_stage_states_remain_classified(
    classification: str, exception_type: str | None, model_checked: bool,
    roundtrip_checked: bool,
) -> None:
    case = composite.build_case(composite.Recipe.literal_example())
    envelope = {
        **composite.worker_envelope(case), "classification": classification,
        "exception_type": exception_type, "model_checked": model_checked,
        "roundtrip_checked": roundtrip_checked,
    }
    result = composite.parse_worker_envelope(envelope, case)
    assert result.classification == classification
    assert result.model_checked is model_checked
    assert result.roundtrip_checked is roundtrip_checked


def test_semantic_difference_report_contains_only_allowlisted_fields_and_outline_numbers() -> None:
    before = {"page": {"title": "x", "root_nodes": [{"content": "secret-a", "children": []}]}}
    after = {"page": {"title": "x", "root_nodes": [{"content": "secret-b", "children": []}]}}
    differences = composite.semantic_difference_report(before, after)
    assert differences == ({"field": "content", "outline_path": [1]},)
    assert "secret-a" not in repr(differences) and "secret-b" not in repr(differences)


def test_semantic_difference_validator_rejects_values_paths_and_unknown_fields() -> None:
    case = composite.build_case(composite.Recipe.literal_example())
    envelope = composite.worker_envelope(case)
    envelope.update(classification="semantic_roundtrip_failure",
                    exception_type="SemanticRoundtripMismatch", model_checked=True,
                    roundtrip_checked=False)
    for item in (
        {"field": "secret property name", "outline_path": [1]},
        {"field": "content", "outline_path": ["private path"]},
        {"field": "content", "outline_path": [True]},
        {"field": "content", "outline_path": list(range(1, 11))},
        {"field": "content", "outline_path": [1], "value": "must not escape"},
    ):
        envelope["semantic_differences"] = [item]
        with pytest.raises(ValueError):
            composite.parse_worker_envelope(envelope, case)


def test_timeout_and_launch_error_are_source_free_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    case = composite.build_case(composite.Recipe.literal_example())
    attempts: list[list[str]] = []

    def timeout(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        attempts.append(argv)
        raise subprocess.TimeoutExpired(argv, 3.0)

    monkeypatch.setattr(composite.subprocess, "run", timeout)
    assert composite.run_case(case).classification == "timeout"
    assert len(attempts) == 1

    def launch_error(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        attempts.append(argv)
        raise OSError("secret path and arbitrary details")

    monkeypatch.setattr(composite.subprocess, "run", launch_error)
    result = composite.run_case(case)
    assert result.classification == "runner_failure"
    assert result.exception_type == "OSError"
    assert "secret path" not in repr(result)
    assert len(attempts) == 2

    def malformed(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        attempts.append(argv)
        return subprocess.CompletedProcess(argv, 0, "not json", "private stderr")

    monkeypatch.setattr(composite.subprocess, "run", malformed)
    invalid = composite.run_case(case)
    assert invalid.classification == "runner_failure"
    assert invalid.exception_type == "InvalidWorkerEnvelope"
    assert invalid.worker_envelope is None
    assert len(attempts) == 3


def test_child_denies_optimized_runtime_before_parser(monkeypatch: pytest.MonkeyPatch) -> None:
    case = composite.build_case(composite.Recipe.literal_example())
    monkeypatch.setattr(composite, "_optimized_runtime", lambda: True)
    envelope = composite.child_runtime_gate(case)
    assert envelope is not None
    assert envelope["classification"] == "runner_failure"
    assert envelope["exception_type"] == "OptimizedPythonDenied"
    assert envelope["model_checked"] is False and envelope["roundtrip_checked"] is False
    request = {"recipe": asdict(composite.Recipe.literal_example()),
               "context": composite._capture_source_context()}
    direct_worker = composite._worker(json.dumps(request))
    assert direct_worker["classification"] == "runner_failure"
    assert direct_worker["exception_type"] == "OptimizedPythonDenied"


def test_worker_rechecks_context_after_stubbed_evaluation(monkeypatch: pytest.MonkeyPatch) -> None:
    case = composite.build_case(composite.Recipe.literal_example())
    context = composite._capture_source_context()
    changed = dict(context)
    changed["revision"] = "f" * 40
    captures = iter((context, changed))
    monkeypatch.setattr(composite, "_capture_source_context", lambda: next(captures))
    monkeypatch.setattr(
        composite, "_evaluate_worker", lambda _case, _base, _context: composite.worker_envelope(
            case, context,
        ),
    )
    request = json.dumps({"recipe": asdict(case.recipe), "context": context}, sort_keys=True)
    result = composite._worker(request)
    assert result["classification"] == "runner_failure"
    assert result["exception_type"] == "SourceProvenanceMismatch"
    assert result["qualification_status"] == "unqualified-source-drift"
    assert result["model_checked"] is False and result["roundtrip_checked"] is False


def test_campaign_stops_after_first_failed_child_and_cli_uses_nested_result(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    seen: list[str] = []

    def fail_first(case: composite.Case, **_kwargs: object) -> composite.Result:
        seen.append(case.case_id)
        return composite.Result(case.case_id, case.recipe.seed, case.recipe, case.source_sha256,
                               case.source_bytes, "invariant_failure", "AssertionError", False, False)

    monkeypatch.setattr(composite, "run_case", fail_first)
    monkeypatch.setattr(composite, "_revision", lambda: composite.BASELINE_REVISION)
    failed = composite.run_profile("smoke")
    assert len(seen) == 1
    assert failed["children_run"] == 1
    failed_results = cast(list[dict[str, Any]], failed["results"])
    assert failed_results[0]["result"]["classification"] == "invariant_failure"

    success_record = {
        "schema_version": composite.SCHEMA_VERSION, "qualification": composite.QUALIFICATION_LEVEL,
        "qualification_status": "qualified", "profile": "smoke", "children_run": 1,
        "results": [{"schema_version": composite.SCHEMA_VERSION,
                     "qualification": composite.QUALIFICATION_LEVEL,
                     "qualification_status": "qualified",
                     "result": {"schema_version": composite.SCHEMA_VERSION,
                                "classification": "parsed", "model_checked": True,
                                "roundtrip_checked": True}}],
    }
    monkeypatch.setattr(composite, "run_profile", lambda *_args, **_kwargs: success_record)
    assert composite.main(["--profile", "smoke"]) == 0
    assert "Traceback" not in capsys.readouterr().out

    failure_record = {
        **success_record,
        "results": [{"schema_version": composite.SCHEMA_VERSION,
                     "qualification": composite.QUALIFICATION_LEVEL,
                     "qualification_status": "qualified",
                     "result": {"schema_version": composite.SCHEMA_VERSION,
                                "classification": "semantic_roundtrip_failure",
                                "model_checked": True, "roundtrip_checked": False}}],
    }
    monkeypatch.setattr(composite, "run_profile", lambda *_args, **_kwargs: failure_record)
    assert composite.main(["--profile", "smoke"]) == 1
    malformed_record = {**success_record, "results": [{"other": {}}]}
    monkeypatch.setattr(composite, "run_profile", lambda *_args, **_kwargs: malformed_record)
    assert composite.main(["--profile", "smoke"]) == 1
    assert "Traceback" not in capsys.readouterr().out


def test_custom_seed_broad_campaign_stays_within_120_including_edges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_seed = 987654
    collection_calls: list[tuple[int, int]] = []

    def collect(*, seed: int, limit: int) -> tuple[composite.Recipe, ...]:
        collection_calls.append((seed, limit))
        return tuple(
            replace(composite.Recipe.literal_example(), seed=seed,
                    task=composite.TASKS[index % len(composite.TASKS)],
                    priority=composite.PRIORITIES[(index // 6) % 3],
                    literal=composite.LITERALS[(index // 18) % len(composite.LITERALS)],
                    reference=composite.REFERENCES[(index // 54) % len(composite.REFERENCES)],
                    tag=composite.TAGS[(index // 162) % len(composite.TAGS)],
                    unicode=composite.UNICODE[(index // 486) % len(composite.UNICODE)],
                    newline=composite.NEWLINES[(index // 1944) % 2])
            for index in range(limit)
        )

    def parsed(case: composite.Case, **_kwargs: object) -> composite.Result:
        return composite.Result(case.case_id, case.recipe.seed, case.recipe, case.source_sha256,
                                case.source_bytes, "parsed", None, True, True)

    monkeypatch.setattr(composite, "collect_recipes", collect)
    monkeypatch.setattr(composite, "run_case", parsed)
    monkeypatch.setattr(composite, "_revision", lambda: composite.BASELINE_REVISION)
    receipt = composite.run_profile("broad", seed_value=target_seed)
    assert collection_calls == [(target_seed, 117)]
    assert receipt["child_budget"] == 120 and receipt["children_run"] == 120
    results = cast(list[dict[str, Any]], receipt["results"])
    assert len(results) == 120
    assert receipt["campaign_seeds"] == [target_seed]
    assert any(item["recipe"]["shape"] == "mixed-32" for item in results)
    assert any(item["recipe"]["shape"] == "nested" for item in results)


def test_receipt_replay_binds_head_manifest_and_nested_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = composite.build_case(composite.Recipe.literal_example())
    entry = _receipt_entry(case, monkeypatch)
    context = composite._capture_source_context()
    entry["worker_envelope"] = composite.worker_envelope(case, context)
    result_data = cast(dict[str, object], entry["result"])
    monkeypatch.setattr(composite, "_revision", lambda: composite.BASELINE_REVISION)
    monkeypatch.setattr(composite, "run_case", lambda selected, **_kwargs: composite.Result(
        selected.case_id, selected.recipe.seed, selected.recipe, selected.source_sha256,
        selected.source_bytes, "parsed", None, True, True,
    ))
    assert composite.replay_receipt_entry(entry).classification == "parsed"
    with pytest.raises(ValueError, match="provenance"):
        composite.replay_receipt_entry({**entry, "revision": "f" * 40})
    with pytest.raises(ValueError, match="provenance"):
        composite.replay_receipt_entry({**entry, "implementation_manifest": {"changed": "0" * 64}})
    with pytest.raises(ValueError, match="nested result identity"):
        composite.replay_receipt_entry({**entry, "result": {**result_data, "case_id": "other"}})
    with pytest.raises(ValueError, match="source digest"):
        composite.replay_receipt_entry({**entry, "result": {**result_data, "source_sha256": "0" * 64}})
    worker = composite.worker_envelope(case)
    with pytest.raises(ValueError, match="nested worker identity"):
        composite.replay_receipt_entry({**entry, "worker_envelope": {
            **worker, "classification": "semantic_roundtrip_failure",
            "exception_type": "SemanticRoundtripMismatch", "model_checked": True,
            "roundtrip_checked": False,
            "semantic_differences": [{"field": "properties", "outline_path": [1]}],
        }})
    monkeypatch.setattr(composite, "_revision", _REVISION_PROBE)


def test_replay_post_child_drift_returns_attempt_with_original_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = composite.build_case(composite.Recipe.literal_example())
    entry = _receipt_entry(case, monkeypatch)
    context = composite._capture_source_context()
    entry["worker_envelope"] = composite.worker_envelope(case, context)

    def drifted(selected: composite.Case, **_kwargs: object) -> composite.Result:
        return composite.Result(
            selected.case_id, selected.recipe.seed, selected.recipe, selected.source_sha256,
            selected.source_bytes, "parsed", None, True, True,
            qualification_status="unqualified-source-drift", source_context=context,
        )

    monkeypatch.setattr(composite, "run_case", drifted)
    result = composite.replay_receipt_entry(entry)
    assert result.classification == "parsed"
    assert result.qualification_status == "unqualified-source-drift"
    assert result.source_context == context


def test_exact_diagnostic_accepts_only_recorded_recipe_and_is_one_case(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts: list[str] = []

    def failure(
        case: composite.Case, *, timeout_seconds: float, **_kwargs: object,
    ) -> composite.Result:
        assert timeout_seconds == composite.MAX_TIMEOUT_SECONDS
        attempts.append(case.case_id)
        return composite.Result(case.case_id, case.recipe.seed, case.recipe, case.source_sha256,
                               case.source_bytes, "semantic_roundtrip_failure",
                               "SemanticRoundtripMismatch", True, False)

    monkeypatch.setattr(composite, "run_case", failure)
    monkeypatch.setattr(composite, "_revision", lambda: composite.BASELINE_REVISION)
    recipe = json.dumps(asdict(composite.Recipe.literal_example()), sort_keys=True)
    entry = composite.run_exact_diagnostic(recipe)
    assert len(attempts) == 1
    results = cast(list[dict[str, Any]], entry["results"])
    assert results[0]["source_sha256"] == composite.DIAGNOSTIC_SOURCE_SHA256
    assert results[0]["source_bytes"] == composite.DIAGNOSTIC_SOURCE_BYTES
    assert results[0]["result"]["classification"] == "semantic_roundtrip_failure"
    assert results[0]["worker_envelope"] is None
    initial_context = {
        "revision": entry["current_revision"],
        "implementation_manifest": entry["implementation_manifest"],
        "runtime_descriptor": entry["runtime_descriptor"],
    }

    def post_drift(case: composite.Case, *, timeout_seconds: float, **_kwargs: object) -> composite.Result:
        assert timeout_seconds == composite.MAX_TIMEOUT_SECONDS
        attempts.append(case.case_id)
        return composite.Result(
            case.case_id, case.recipe.seed, case.recipe, case.source_sha256, case.source_bytes,
            "parsed", None, True, True, qualification_status="unqualified-source-drift",
            source_context=initial_context,
        )

    monkeypatch.setattr(composite, "run_case", post_drift)
    drifted = composite.run_exact_diagnostic(recipe)
    assert len(attempts) == 2
    assert drifted["qualification_status"] == "unqualified-source-drift"
    drifted_results = cast(list[dict[str, Any]], drifted["results"])
    assert drifted_results[0]["revision"] == entry["current_revision"]
    assert drifted_results[0]["qualification_status"] == "unqualified-source-drift"
    unrelated = json.dumps(asdict(replace(composite.Recipe.literal_example(), task="DONE")))
    with pytest.raises(ValueError, match="exact diagnostic recipe"):
        composite.run_exact_diagnostic(unrelated)


def test_source_inventory_is_complete_sorted_and_rejects_bad_selected_files(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    for directory in (
        "src/logseq_matryca_parser", "tests/parser_assurance", "tests",
    ):
        (root / directory).mkdir(parents=True, exist_ok=True)
    required = (
        "tests/__init__.py", "tests/test_parser_composite_properties.py",
        "pyproject.toml", "uv.lock",
    )
    for relative in required:
        (root / relative).write_text("selected\n", encoding="utf-8")
    for relative in (
        "src/logseq_matryca_parser/__init__.py",
        "src/logseq_matryca_parser/logseq_paths.py",
        "tests/parser_assurance/__init__.py",
        "tests/parser_assurance/worker.py",
    ):
        (root / relative).write_text("source\n", encoding="utf-8")

    manifest = composite.implementation_manifest(root)
    assert list(manifest) == sorted(manifest)
    assert set(required).issubset(manifest)
    assert "src/logseq_matryca_parser/logseq_paths.py" in manifest
    assert "tests/parser_assurance/worker.py" in manifest
    original = manifest["src/logseq_matryca_parser/logseq_paths.py"]
    (root / "src/logseq_matryca_parser/logseq_paths.py").write_text("changed\n", encoding="utf-8")
    assert composite.implementation_manifest(root)[
        "src/logseq_matryca_parser/logseq_paths.py"
    ] != original

    (root / "src/logseq_matryca_parser/added.py").write_text("new\n", encoding="utf-8")
    added = composite.implementation_manifest(root)
    assert "src/logseq_matryca_parser/added.py" in added
    (root / "src/logseq_matryca_parser/added.py").unlink()
    assert "src/logseq_matryca_parser/added.py" not in composite.implementation_manifest(root)

    (root / "tests/parser_assurance/missing.py").symlink_to(tmp_path / "outside.py")
    with pytest.raises(ValueError, match="symlink"):
        composite.implementation_manifest(root)
    (root / "tests/parser_assurance/missing.py").unlink()
    (root / "uv.lock").unlink()
    with pytest.raises(ValueError, match="required manifest file"):
        composite.implementation_manifest(root)


def test_revision_probe_is_root_bound_and_invalid_head_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    root = tmp_path / "selected-repo"
    root.mkdir()
    seen: list[dict[str, object]] = []

    def probe(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        seen.append({"argv": argv, **kwargs})
        return subprocess.CompletedProcess(argv, 0, f"{root}\n{'a' * 40}\n", "")

    monkeypatch.setattr(composite, "_revision", _REVISION_PROBE)
    monkeypatch.setattr(composite.subprocess, "run", probe)
    assert composite._revision(root) == "a" * 40
    assert seen[0]["cwd"] == root
    assert cast(float, seen[0]["timeout"]) <= 1.0
    assert "--show-toplevel" in cast(list[str], seen[0]["argv"])
    monkeypatch.setattr(
        composite.subprocess, "run",
        lambda argv, **_kwargs: subprocess.CompletedProcess(argv, 0, f"{tmp_path}\n{'a' * 40}", ""),
    )
    with pytest.raises(ValueError, match="root mismatch"):
        composite._revision(root, required=True)

    for stdout in ("unavailable\n", "A" * 40, "g" * 40, "a" * 39):
        monkeypatch.setattr(
            composite.subprocess, "run",
            lambda argv, _stdout=stdout, **_kwargs: subprocess.CompletedProcess(
                argv, 0, f"{root}\n{_stdout}", "",
            ),
        )
        with pytest.raises(ValueError, match="revision"):
            composite._revision(root, required=True)
    for error in (OSError("git unavailable"), subprocess.TimeoutExpired(["git"], 1.0)):
        def failed_probe(
            argv: list[str], _error: Exception = error, **_kwargs: object,
        ) -> subprocess.CompletedProcess[str]:
            raise _error

        monkeypatch.setattr(composite.subprocess, "run", failed_probe)
        with pytest.raises(ValueError, match="revision probe"):
            composite._revision(root, required=True)


def test_schema_two_receipt_and_invalid_preflight_never_launch_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = composite.build_case(composite.Recipe.literal_example())
    attempts: list[object] = []
    monkeypatch.setattr(composite, "run_case", lambda selected, **_kw: attempts.append(selected))
    entry = _receipt_entry(case, monkeypatch)
    assert entry["schema_version"] == 3
    assert entry["qualification"] == "source-qualified-developmental-v1"

    with pytest.raises(ValueError, match="schema"):
        composite.replay_receipt_entry({**entry, "schema_version": 2})
    with pytest.raises(ValueError, match="qualification"):
        composite.replay_receipt_entry({**entry, "qualification": "unknown"})
    assert attempts == []


def _receipt_entry(
    case: composite.Case, monkeypatch: pytest.MonkeyPatch,
) -> dict[str, object]:
    context = composite._capture_source_context()
    result_data = {
        "schema_version": composite.SCHEMA_VERSION,
        "case_id": case.case_id, "seed": case.recipe.seed, "recipe": asdict(case.recipe),
        "source_sha256": case.source_sha256, "source_bytes": case.source_bytes,
        "classification": "parsed", "exception_type": None, "model_checked": True,
        "roundtrip_checked": True, "semantic_differences": [],
    }
    monkeypatch.setattr(composite, "_capture_source_context", lambda: context)
    return {
        "schema_version": 3, "qualification": composite.QUALIFICATION_LEVEL,
        "qualification_status": "qualified",
        "recipe": asdict(case.recipe), "source_sha256": case.source_sha256,
        "source_bytes": case.source_bytes, "revision": context["revision"],
        "implementation_manifest": context["implementation_manifest"],
        "runtime_descriptor": context["runtime_descriptor"],
        "provenance_sha256": composite._provenance_sha256(context),
        "result": result_data, "worker_envelope": None,
    }


@pytest.mark.parametrize("bad_value", [True, 104.0])
def test_nested_numeric_equivalents_rejected_before_child(
    monkeypatch: pytest.MonkeyPatch, bad_value: object,
) -> None:
    case = composite.build_case(composite.Recipe.literal_example())
    entry = _receipt_entry(case, monkeypatch)
    result_data = cast(dict[str, object], entry["result"])
    attempts: list[object] = []
    monkeypatch.setattr(composite, "run_case", lambda selected, **_kw: attempts.append(selected))
    with pytest.raises(ValueError):
        composite.replay_receipt_entry({**entry, "result": {**result_data, "seed": bad_value}})
    with pytest.raises(ValueError):
        composite.replay_receipt_entry({**entry, "result": {
            **result_data, "source_bytes": bad_value,
        }})
    assert attempts == []


def test_missing_worker_evidence_cannot_qualify_parser_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = composite.build_case(composite.Recipe.literal_example())
    entry = _receipt_entry(case, monkeypatch)
    attempts: list[object] = []
    monkeypatch.setattr(composite, "run_case", lambda selected, **_kw: attempts.append(selected))
    with pytest.raises(ValueError, match="worker"):
        composite.replay_receipt_entry(entry)
    assert attempts == []


def test_child_process_exit_uses_canonical_failure_and_cwd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = composite.build_case(composite.Recipe.literal_example())
    for returncode in (1, -9):
        seen: list[dict[str, object]] = []

        def child(
            argv: list[str], _returncode: int = returncode, _seen: list[dict[str, object]] = seen,
            **kwargs: object,
        ) -> subprocess.CompletedProcess[str]:
            _seen.append({"argv": argv, **kwargs})
            return subprocess.CompletedProcess(argv, _returncode, "", "private stderr")

        monkeypatch.setattr(composite.subprocess, "run", child)
        result = composite.run_case(case)
        assert result.exception_type == "ChildProcessExit"
        assert result.model_checked is False and result.roundtrip_checked is False
        assert result.worker_envelope is None
        assert seen[0]["cwd"] == Path(composite.__file__).parents[2]


def test_campaign_drift_before_launch_is_zero_and_after_child_stops_next(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_context = composite._capture_source_context()
    calls: list[str] = []
    monkeypatch.setattr(composite, "run_case", lambda case, **_kw: calls.append(case.case_id))
    monkeypatch.setattr(composite, "implementation_manifest", lambda *_args: real_context["implementation_manifest"])
    captures = {"count": 0}

    # A context change between campaign capture and per-child preflight denies before launch.
    def drift_before() -> dict[str, object]:
        captures["count"] += 1
        context = dict(real_context)
        if captures["count"] >= 2:
            context["revision"] = "f" * 40
        return context

    monkeypatch.setattr(composite, "_capture_source_context", drift_before)
    receipt = composite.run_profile("smoke")
    assert receipt["children_run"] == 0
    assert calls == []


def test_post_child_drift_preserves_attempt_and_stops_campaign(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = composite._capture_source_context()
    attempts: list[str] = []
    captures = {"count": 0}

    def context_with_post_drift() -> dict[str, object]:
        captures["count"] += 1
        current = dict(original)
        if captures["count"] >= 2:
            current["revision"] = "f" * 40
        return current

    case = composite.build_case(composite.Recipe.literal_example())
    child_envelope = composite.worker_envelope(case, original)

    def child(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        attempts.append("child")
        return subprocess.CompletedProcess(argv, 0, json.dumps(child_envelope), "")

    monkeypatch.setattr(composite, "_capture_source_context", context_with_post_drift)
    monkeypatch.setattr(composite.subprocess, "run", child)
    result = composite.run_case(case, expected_context=original)
    assert len(attempts) == 1
    assert result.classification == "parsed"
    assert result.qualification_status == "unqualified-source-drift"

    profile_attempts: list[str] = []
    def drifted(case: composite.Case, **_kwargs: object) -> composite.Result:
        profile_attempts.append(case.case_id)
        return composite.Result(
            case.case_id, case.recipe.seed, case.recipe, case.source_sha256, case.source_bytes,
            "parsed", None, True, True, qualification_status="unqualified-source-drift",
        )

    monkeypatch.setattr(composite, "_capture_source_context", lambda: original)
    monkeypatch.setattr(composite, "run_case", drifted)
    receipt = composite.run_profile("smoke")
    assert len(profile_attempts) == 1
    assert receipt["children_run"] == 1
    assert receipt["qualification_status"] == "unqualified-source-drift"
    records = cast(list[dict[str, Any]], receipt["results"])
    assert records[0]["revision"] == original["revision"]
    assert records[0]["qualification_status"] == "unqualified-source-drift"


def test_runtime_and_worker_origin_mismatch_are_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = composite.build_case(composite.Recipe.literal_example())
    expected = composite._capture_source_context()
    monkeypatch.setattr(composite, "_capture_source_context", lambda: expected)
    monkeypatch.setattr(composite, "_module_origins_are_local", lambda: False)
    calls: list[object] = []
    monkeypatch.setattr(composite.subprocess, "run", lambda *args, **kwargs: calls.append(args))
    with pytest.raises(ValueError, match="origin"):
        composite.run_case(case, expected_context=expected)
    assert calls == []


def test_receipt_strict_keys_types_and_runtime_identity_reject_before_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = composite.build_case(composite.Recipe.literal_example())
    entry = _receipt_entry(case, monkeypatch)
    context = composite._capture_source_context()
    entry["worker_envelope"] = composite.worker_envelope(case, context)
    attempts: list[object] = []
    monkeypatch.setattr(composite, "run_case", lambda selected, **_kw: attempts.append(selected))
    result_data = cast(dict[str, object], entry["result"])

    invalid_entries = [
        {key: value for key, value in entry.items() if key != "schema_version"},
        {**entry, "schema_version": True},
        {**entry, "schema_version": 3.0},
        {**entry, "qualification": "unknown"},
        {**entry, "runtime_descriptor": {**cast(dict[str, object], entry["runtime_descriptor"]),
                                         "python_version": "other"}},
        {**entry, "worker_envelope": {**cast(dict[str, object], entry["worker_envelope"]),
                                       "extra": "unexpected"}},
    ]
    for invalid in invalid_entries:
        with pytest.raises(ValueError):
            composite.replay_receipt_entry(invalid)

    for nested in (
        {key: value for key, value in result_data.items() if key != "exception_type"},
        {**result_data, "extra": None},
        {**result_data, "schema_version": True},
        {**result_data, "seed": 104.0},
        {**result_data, "source_bytes": True},
        {**result_data, "recipe": {**asdict(case.recipe), "seed": True}},
    ):
        with pytest.raises(ValueError):
            composite.replay_receipt_entry({**entry, "result": nested})
    assert attempts == []


def _install_module_origin_topology(
    monkeypatch: pytest.MonkeyPatch, root: Path, *, spec_name: str | None,
    spec_missing: bool = False, origin: Path | None = None,
) -> None:
    modules = {
        "logseq_matryca_parser": "src/logseq_matryca_parser/__init__.py",
        "logseq_matryca_parser.logos_core": "src/logseq_matryca_parser/logos_core.py",
        "logseq_matryca_parser.logos_parser": "src/logseq_matryca_parser/logos_parser.py",
        "logseq_matryca_parser.logseq_markdown": "src/logseq_matryca_parser/logseq_markdown.py",
        "tests": "tests/__init__.py",
        "tests.parser_assurance": "tests/parser_assurance/__init__.py",
        "tests.parser_assurance.adversarial": "tests/parser_assurance/adversarial.py",
        "tests.parser_assurance.invariants": "tests/parser_assurance/invariants.py",
        "tests.parser_assurance.projection": "tests/parser_assurance/projection.py",
    }
    for relative in modules.values():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    for name, relative in modules.items():
        module = types.ModuleType(name)
        module.__file__ = str(root / relative)
        module.__spec__ = importlib.machinery.ModuleSpec(
            name, loader=None, origin=str(root / relative),
        )
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.delitem(
        sys.modules, "tests.parser_assurance.composite_properties", raising=False,
    )
    main_origin = origin or root / "tests/parser_assurance/composite_properties.py"
    if not main_origin.exists() and origin is None:
        main_origin.parent.mkdir(parents=True, exist_ok=True)
        main_origin.touch()
    main_module = types.ModuleType("__main__")
    main_module.__file__ = str(main_origin)
    if not spec_missing:
        main_module.__spec__ = importlib.machinery.ModuleSpec(
            spec_name or "missing.spec", loader=None, origin=str(main_origin),
        )
    monkeypatch.setitem(sys.modules, "__main__", main_module)


@pytest.mark.parametrize(
    ("spec_name", "spec_missing", "origin", "expected"),
    [
        ("tests.parser_assurance.composite_properties", False, None, True),
        ("wrong.module", False, None, False),
        (None, True, None, False),
        ("tests.parser_assurance.composite_properties", False, Path("/missing/worker.py"), False),
    ],
)
def test_module_origin_gate_models_python_m_entry_topology(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, spec_name: str | None,
    spec_missing: bool, origin: Path | None, expected: bool,
) -> None:
    _install_module_origin_topology(
        monkeypatch, tmp_path, spec_name=spec_name, spec_missing=spec_missing, origin=origin,
    )
    assert composite._module_origins_are_local(tmp_path) is expected


def test_module_origin_gate_rejects_existing_outside_root_main_source(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    outside_source = tmp_path / "outside-composite.py"
    outside_source.touch()
    _install_module_origin_topology(
        monkeypatch, root, spec_name="tests.parser_assurance.composite_properties",
        origin=outside_source,
    )
    assert composite._module_origins_are_local(root) is False


def test_worker_admits_local_main_module_when_canonical_name_is_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    context = composite._capture_source_context()
    _install_module_origin_topology(
        monkeypatch, tmp_path, spec_name="tests.parser_assurance.composite_properties",
    )
    monkeypatch.setattr(composite, "_capture_source_context", lambda: context)
    monkeypatch.setattr(
        composite, "_module_origins_are_local",
        lambda root=None: _origin_gate_for_test(root, tmp_path),
    )
    monkeypatch.setattr(
        composite, "_evaluate_worker",
        lambda case, _base, selected: composite.worker_envelope(case, selected),
    )
    request = json.dumps({"recipe": asdict(composite.Recipe.literal_example()), "context": context})
    result = composite._worker(request)
    assert result["classification"] == "parsed"
    assert result["qualification_status"] == "qualified"


def _origin_gate_for_test(_root: Path | None, selected_root: Path) -> bool:
    return _MODULE_ORIGINS_ARE_LOCAL(selected_root)


@pytest.mark.parametrize("post_failure", [ValueError("revision unavailable"),
                                            PermissionError("manifest unreadable"),
                                            RuntimeError("runtime metadata unavailable")])
@pytest.mark.parametrize("outcome", ["parsed", "timeout", "exit", "launch"])
def test_post_attempt_context_probe_failure_retains_unqualified_result(
    monkeypatch: pytest.MonkeyPatch, post_failure: Exception, outcome: str,
) -> None:
    context = composite._capture_source_context()
    case = composite.build_case(composite.Recipe.literal_example())
    expected_envelope = composite.worker_envelope(case, context)
    captures = {"count": 0}
    attempts: list[str] = []

    def source_context() -> dict[str, object]:
        captures["count"] += 1
        if captures["count"] == 2:
            raise post_failure
        return context

    def transport(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        attempts.append("child")
        if outcome == "timeout":
            raise subprocess.TimeoutExpired(argv, 3.0)
        if outcome == "launch":
            raise FileNotFoundError("private executable path")
        if outcome == "exit":
            return subprocess.CompletedProcess(argv, 1, "", "private stderr")
        return subprocess.CompletedProcess(argv, 0, json.dumps(expected_envelope), "")

    monkeypatch.setattr(composite, "_capture_source_context", source_context)
    monkeypatch.setattr(composite.subprocess, "run", transport)
    result = composite.run_case(case, expected_context=context)
    assert attempts == ["child"]
    assert result.qualification_status == "unqualified-source-drift"
    assert result.source_context == context
    if outcome == "parsed":
        assert result.classification == "parsed"
        assert result.worker_envelope == expected_envelope
    else:
        assert result.worker_envelope is None
    if outcome == "timeout":
        assert result.classification == "timeout"
    if outcome == "exit":
        assert result.exception_type == "ChildProcessExit"
    if outcome == "launch":
        assert result.exception_type == "OSError"


@pytest.mark.parametrize("boundary", ["profile", "diagnostic"])
def test_post_probe_failure_keeps_one_attempt_at_receipt_boundary(
    monkeypatch: pytest.MonkeyPatch, boundary: str,
) -> None:
    context = composite._capture_source_context()
    case = composite.build_case(composite.Recipe.literal_example())
    envelope = composite.worker_envelope(case, context)
    captures = {"count": 0}
    attempts: list[str] = []

    def context_then_failure() -> dict[str, object]:
        captures["count"] += 1
        terminal_probe = 4 if boundary == "profile" else 3
        if captures["count"] == terminal_probe:
            raise PermissionError("post-child metadata probe failed")
        return context

    def child(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        attempts.append("child")
        return subprocess.CompletedProcess(argv, 0, json.dumps(envelope), "")

    monkeypatch.setattr(composite, "_capture_source_context", context_then_failure)
    monkeypatch.setattr(composite.subprocess, "run", child)
    if boundary == "profile":
        receipt = composite.run_profile("smoke")
    else:
        recipe = json.dumps(asdict(composite.Recipe.literal_example()), sort_keys=True)
        receipt = composite.run_exact_diagnostic(recipe)
    assert attempts == ["child"]
    assert receipt["children_run"] == 1
    assert receipt["qualification_status"] == "unqualified-source-drift"
    records = cast(list[dict[str, Any]], receipt["results"])
    assert len(records) == 1
    assert records[0]["qualification_status"] == "unqualified-source-drift"
    assert records[0]["revision"] == context["revision"]
    assert composite._receipt_success(receipt) is False


@pytest.mark.parametrize("error", [OSError("detail"), FileNotFoundError("secret path"),
                                    PermissionError("private permissions")])
def test_launch_oserror_subclasses_normalize_and_replay_without_worker(
    monkeypatch: pytest.MonkeyPatch, error: OSError,
) -> None:
    case = composite.build_case(composite.Recipe.literal_example())
    context = composite._capture_source_context()
    attempts: list[str] = []

    def fail_launch(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        attempts.append("transport")
        raise error

    monkeypatch.setattr(composite.subprocess, "run", fail_launch)
    result = composite.run_case(case, expected_context=context)
    assert attempts == ["transport"]
    assert result.exception_type == "OSError"
    assert result.model_checked is False and result.roundtrip_checked is False
    assert result.worker_envelope is None
    assert str(error) not in repr(result)

    entry = _receipt_entry(case, monkeypatch)
    nested = cast(dict[str, object], entry["result"])
    nested.update(classification="runner_failure", exception_type="OSError",
                  model_checked=False, roundtrip_checked=False)
    replay_calls: list[str] = []

    def replay_transport(selected: composite.Case, **_kwargs: object) -> composite.Result:
        replay_calls.append(selected.case_id)
        return result

    monkeypatch.setattr(composite, "run_case", replay_transport)
    replayed = composite.replay_receipt_entry(entry)
    assert replay_calls == [case.case_id]
    assert replayed.exception_type == "OSError"
    receipt = {"schema_version": 3, "qualification": composite.QUALIFICATION_LEVEL,
               "qualification_status": "qualified", "results": [composite._result_record(
                   result, context=context,
               )]}
    assert composite._receipt_success(receipt) is False


@pytest.mark.parametrize("returncode", [1, -9])
def test_child_exit_result_roundtrips_through_replay_boundary(
    monkeypatch: pytest.MonkeyPatch, returncode: int,
) -> None:
    case = composite.build_case(composite.Recipe.literal_example())
    context = composite._capture_source_context()
    monkeypatch.setattr(
        composite.subprocess, "run",
        lambda argv, **_kwargs: subprocess.CompletedProcess(argv, returncode, "", "secret stderr"),
    )
    result = composite.run_case(case, expected_context=context)
    assert result.exception_type == "ChildProcessExit"
    entry = _receipt_entry(case, monkeypatch)
    nested = cast(dict[str, object], entry["result"])
    nested.update(classification="runner_failure", exception_type="ChildProcessExit",
                  model_checked=False, roundtrip_checked=False)
    monkeypatch.setattr(composite, "run_case", lambda _case, **_kwargs: result)
    replayed = composite.replay_receipt_entry(entry)
    assert replayed.exception_type == "ChildProcessExit"
    assert replayed.model_checked is False and replayed.roundtrip_checked is False
    receipt = {"schema_version": 3, "qualification": composite.QUALIFICATION_LEVEL,
               "qualification_status": "qualified", "results": [composite._result_record(
                   result, context=context,
               )]}
    assert composite._receipt_success(receipt) is False


def _synthetic_manifest_root(root: Path) -> Path:
    files = (
        "src/logseq_matryca_parser/__init__.py", "src/logseq_matryca_parser/nested/mod.py",
        "tests/__init__.py", "tests/parser_assurance/__init__.py",
        "tests/parser_assurance/nested/worker.py", "tests/test_parser_composite_properties.py",
        "pyproject.toml", "uv.lock",
    )
    for relative in files:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("selected\n", encoding="utf-8")
    return root


@pytest.mark.parametrize("failure_root", [
    "src/logseq_matryca_parser", "src/logseq_matryca_parser/nested",
])
def test_manifest_rejects_root_and_nested_walk_failures_before_campaign(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, failure_root: str,
) -> None:
    root = _synthetic_manifest_root(tmp_path / "repo")
    original_walk = composite.os.walk

    def failing_walk(path: str | Path, *, followlinks: bool, onerror: Any = None) -> Any:
        if failure_root == "src/logseq_matryca_parser" and Path(path) == root / failure_root:
            assert callable(onerror)
            onerror(PermissionError("simulated unreadable directory"))
            return iter(())
        if failure_root.endswith("/nested") and Path(path) == root / "src/logseq_matryca_parser":
            assert callable(onerror)

            def failed_nested_walk() -> Iterator[tuple[str, list[str], list[str]]]:
                yield str(path), ["nested"], ["logos_core.py", "logos_parser.py", "logseq_markdown.py"]
                onerror(PermissionError("simulated unreadable nested directory"))

            return failed_nested_walk()
        return original_walk(path, followlinks=followlinks, onerror=onerror)

    monkeypatch.setattr(composite.os, "walk", failing_walk)
    with pytest.raises(ValueError, match="inventory traversal"):
        composite.implementation_manifest(root)

    calls: list[str] = []
    monkeypatch.setattr(composite, "_revision", lambda: composite.BASELINE_REVISION)
    monkeypatch.setattr(composite, "runtime_descriptor", composite.runtime_descriptor)
    monkeypatch.setattr(composite, "implementation_manifest", lambda: _IMPLEMENTATION_MANIFEST(root))
    monkeypatch.setattr(composite, "run_case", lambda case, **_kwargs: calls.append(case.case_id))
    with pytest.raises(ValueError, match="source context probe"):
        composite.run_profile("smoke")
    assert calls == []


def test_manifest_rejects_selected_file_read_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    root = _synthetic_manifest_root(tmp_path / "repo")
    target = root / "uv.lock"
    original_read_bytes = Path.read_bytes

    def unreadable(path: Path) -> bytes:
        if path == target:
            raise PermissionError("simulated unreadable file")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", unreadable)
    with pytest.raises(ValueError, match="invalid required manifest file"):
        composite.implementation_manifest(root)


def test_runtime_descriptor_rejects_unknown_metadata_and_optional_versions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    descriptor = composite.runtime_descriptor()
    for key in (
        "python_implementation", "python_version", "os_family", "os_release", "machine",
        "hypothesis_version", "pydantic_version", "pydantic_core_version",
    ):
        for value in ("unknown", "   ", "unavailable"):
            with pytest.raises(ValueError, match="runtime descriptor"):
                composite._validate_runtime_descriptor({**descriptor, key: value})
    for version in ("unknown", "  ", "unavailable"):
        with pytest.raises(ValueError, match="optional runtime"):
            composite._validate_runtime_descriptor({
                **descriptor, "langchain_core": {"present": True, "version": version},
            })
    absent = {**descriptor, "langchain_core": {"present": False, "version": None}}
    assert composite._validate_runtime_descriptor(absent) == absent
    for optimization in (True, 0.0, -1, 1):
        with pytest.raises(ValueError, match="optimization"):
            composite._validate_runtime_descriptor({**descriptor, "optimization": optimization})


def test_equal_unknown_runtime_provider_rejects_capture_and_replay_before_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = composite.build_case(composite.Recipe.literal_example())
    entry = _receipt_entry(case, monkeypatch)
    monkeypatch.setattr(composite, "_capture_source_context", _CAPTURE_SOURCE_CONTEXT)
    unknown = {**composite.runtime_descriptor(), "python_version": "unknown"}
    monkeypatch.setattr(composite, "runtime_descriptor", lambda: unknown)
    calls: list[object] = []
    monkeypatch.setattr(composite, "run_case", lambda selected, **_kw: calls.append(selected))
    with pytest.raises(ValueError, match="source context probe"):
        composite._capture_source_context()
    with pytest.raises(ValueError, match="source context probe"):
        composite.replay_receipt_entry(entry)
    assert calls == []


@settings(max_examples=12, derandomize=True, database=None, deadline=None)
@given(recipe=composite.recipe_strategy())
def test_generated_recipe_shapes_are_finite_and_valid(recipe: composite.Recipe) -> None:
    case = composite.build_case(recipe)
    assert case.source_bytes <= 16_384
    assert len(composite._flatten_expected(case.expected)) <= 32
    assert max(block.depth for block in composite._flatten_expected(case.expected)) <= 8
    assert "((" not in case.source and "id::" not in case.source
    assert "SCHEDULED: <" in case.source and "DEADLINE: <" in case.source
