"""Bounded valid-only Markdown recipe generator with an independent child oracle."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, Final, cast

import hypothesis
import pydantic
import pydantic_core
from hypothesis import Phase, given, settings
from hypothesis import seed as hypothesis_seed
from hypothesis import strategies as st

from logseq_matryca_parser.exceptions import LogseqParserError
from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage
from logseq_matryca_parser.logos_parser import StackMachineParser
from logseq_matryca_parser.logseq_markdown import serialize_logseq_page
from tests.parser_assurance.adversarial import (
    IDENTITY_POLICY,
    Classification,
)
from tests.parser_assurance.invariants import assert_tree_invariants, walk_nodes
from tests.parser_assurance.projection import project_page

SCHEMA_VERSION: Final = 3
QUALIFICATION_LEVEL: Final = "source-qualified-developmental-v1"
BASELINE_REVISION: Final = "0e2b0187ddc54abd92f6a50e7dbde5166e474ffd"
MAX_BLOCKS: Final = 32
MAX_DEPTH: Final = 8
MAX_SOURCE_BYTES: Final = 16_384
MAX_TIMEOUT_SECONDS: Final = 3.0
MAX_DIFFERENCES: Final = 128
SMOKE_CHILD_CAP: Final = 4
BROAD_CHILD_CAP: Final = 120
BROAD_SEEDS: Final = (104, 417, 911)
DIAGNOSTIC_SOURCE_SHA256: Final = "5ce0ba81caa920ed9ea1d1e245d078d942d91d3a1b18b3cea86a35a97c1597c3"
DIAGNOSTIC_SOURCE_BYTES: Final = 329
CLASSIFICATIONS: Final = frozenset({
    "parsed", "expected_parser_error", "unexpected_exception", "invariant_failure",
    "semantic_roundtrip_failure", "timeout", "runner_failure",
})
SHAPES: Final = {
    "root-child-sibling": (0, 1, 0),
    "siblings": (0, 0, 0),
    "nested": (0, 1, 2, 3, 4, 5, 6, 7, 8),
    "mixed-8": (0, 1, 2, 3, 4, 5, 6, 7),
    "wide-32": (0,) * 32,
    "mixed-32": (0, 1, 2, 2, 3, 3, 4, 1, 2, 3, 0, 1, 1, 2, 3, 4,
                 4, 5, 2, 3, 0, 1, 2, 3, 3, 4, 5, 6, 0, 1, 2, 0),
}
TASKS: Final = ("TODO", "DOING", "DONE", "LATER", "NOW", "CANCELED")
PRIORITIES: Final = ("A", "B", "C")
SCHEDULED_DATES: Final = ("2026-04-30 Thu", "2026-08-20 Thu")
DEADLINE_DATES: Final = ("2026-05-01 Fri", "2026-08-22 Sat")
# These UTC epochs are independent literals, not computed by parser helpers.
SCHEDULED_EPOCHS: Final = {"2026-04-30 Thu": 1_777_507_200, "2026-08-20 Thu": 1_787_184_000}
DEADLINE_EPOCHS: Final = {"2026-05-01 Fri": 1_777_593_600, "2026-08-22 Sat": 1_787_356_800}
LITERALS: Final = ("kept", "plain-value", "cafe-42")
REFERENCES: Final = ("Target", "Résumé", "Topic page")
TAGS: Final = ("topic", "work", "caffè")
UNICODE: Final = ("caffè", "東京", "naïve", "🙂")
NEWLINES: Final = ("lf", "crlf")
TASK_BY_INDEX: Final = ("TODO", "DOING", "DONE")
PRIORITY_BY_INDEX: Final = ("A", "B", "C")
TOKEN_BY_INDEX: Final = ("caffè", "東京", "naïve", "🙂")
SEMANTIC_FIELDS: Final = frozenset({
    "source_uuid", "synthetic_id", "content", "clean_text", "indent_level", "properties",
    "properties_order", "wikilinks", "tags", "assets", "block_refs", "refs", "task_status",
    "task_priority", "scheduled_at", "deadline_at", "repeater", "outline_path", "created_at",
    "updated_at", "parent_outline_path", "left_outline_path", "children",
})
PAGE_FIELDS: Final = frozenset({
    "title", "properties", "properties_order", "refs", "created_at", "updated_at",
    "namespace_chain", "tab_size",
})
REQUIRED_MANIFEST_FILES: Final = (
    "src/logseq_matryca_parser/__init__.py", "tests/__init__.py",
    "tests/parser_assurance/__init__.py", "tests/test_parser_composite_properties.py",
    "pyproject.toml", "uv.lock",
)
WORKER_ENVELOPE_KEYS: Final = frozenset({
    "schema_version", "case_id", "recipe_sha256", "source_sha256", "source_bytes",
    "classification", "exception_type", "model_checked", "roundtrip_checked",
    "semantic_differences", "provenance_sha256", "module_origins_local", "qualification_status",
})
RESULT_KEYS: Final = frozenset({
    "schema_version", "case_id", "seed", "recipe", "source_sha256", "source_bytes",
    "classification", "exception_type", "model_checked", "roundtrip_checked",
    "semantic_differences",
})
PARENT_FAILURES: Final = frozenset({
    ("timeout", None), ("runner_failure", "OSError"),
    ("runner_failure", "InvalidWorkerEnvelope"), ("runner_failure", "ChildProcessExit"),
})


@dataclass(frozen=True)
class Recipe:
    """Validated finite choices; never accepts free-form source or paths."""

    seed: int
    shape: str
    task: str
    priority: str
    scheduled: str
    deadline: str
    literal: str
    reference: str
    tag: str
    unicode: str
    newline: str

    @classmethod
    def literal_example(cls) -> Recipe:
        return cls(104, "root-child-sibling", "TODO", "A", "2026-04-30 Thu",
                   "2026-05-01 Fri", "kept", "Target", "topic", "caffè", "lf")


@dataclass(frozen=True)
class ExpectedBlock:
    """One independently specified block and its own source-line ledger."""

    index: int
    depth: int
    content: str
    line_start: int
    line_end: int
    task_status: str
    task_priority: str
    properties: tuple[tuple[str, object], ...]
    scheduled_at: int | None
    deadline_at: int | None
    wikilinks: tuple[str, ...]
    tags: tuple[str, ...]
    refs: tuple[str, ...]
    children: tuple[ExpectedBlock, ...]


@dataclass(frozen=True)
class Case:
    case_id: str
    recipe: Recipe
    source: str
    expected: tuple[ExpectedBlock, ...]

    @property
    def source_sha256(self) -> str:
        return hashlib.sha256(self.source.encode("utf-8")).hexdigest()

    @property
    def source_bytes(self) -> int:
        return len(self.source.encode("utf-8"))


@dataclass(frozen=True)
class Result:
    case_id: str
    seed: int
    recipe: Recipe
    source_sha256: str
    source_bytes: int
    classification: Classification
    exception_type: str | None
    model_checked: bool
    roundtrip_checked: bool
    semantic_differences: tuple[dict[str, object], ...] = ()
    worker_envelope: dict[str, object] | None = None
    qualification_status: str = "qualified"
    source_context: dict[str, object] | None = None


def _validate(recipe: Recipe) -> None:
    if type(recipe.seed) is not int or not 0 <= recipe.seed <= 2**32 - 1:
        raise ValueError("seed outside finite range")
    choices = (
        (recipe.shape, SHAPES), (recipe.task, TASKS), (recipe.priority, PRIORITIES),
        (recipe.scheduled, SCHEDULED_DATES), (recipe.deadline, DEADLINE_DATES),
        (recipe.literal, LITERALS), (recipe.reference, REFERENCES), (recipe.tag, TAGS),
        (recipe.unicode, UNICODE), (recipe.newline, NEWLINES),
    )
    for value, vocabulary in choices:
        if not isinstance(value, str) or value not in vocabulary:
            raise ValueError("unknown finite recipe vocabulary")
    depths = SHAPES[recipe.shape]
    if not 1 <= len(depths) <= MAX_BLOCKS or max(depths) > MAX_DEPTH:
        raise ValueError("shape exceeds block or depth budget")
    if depths[0] != 0 or any(
        depth > previous + 1 for previous, depth in zip(depths, depths[1:], strict=False)
    ):
        raise ValueError("shape is not a valid preorder outline")


def recipe_from_json(raw: str) -> Recipe:
    """Reject extra fields, free text, booleans-as-integers, and invalid choices."""
    payload = json.loads(raw)
    if not isinstance(payload, dict) or set(payload) != {field.name for field in fields(Recipe)}:
        raise ValueError("invalid recipe fields")
    recipe = Recipe(**payload)
    _validate(recipe)
    return recipe


def recipe_strategy() -> st.SearchStrategy[Recipe]:
    """Construct valid combinations directly, with no rejection-heavy filter."""
    return st.builds(
        Recipe,
        seed=st.integers(min_value=0, max_value=2**32 - 1),
        shape=st.sampled_from(("root-child-sibling", "siblings", "nested", "mixed-8")),
        task=st.sampled_from(TASKS), priority=st.sampled_from(PRIORITIES),
        scheduled=st.sampled_from(SCHEDULED_DATES), deadline=st.sampled_from(DEADLINE_DATES),
        literal=st.sampled_from(LITERALS), reference=st.sampled_from(REFERENCES),
        tag=st.sampled_from(TAGS), unicode=st.sampled_from(UNICODE),
        newline=st.sampled_from(NEWLINES),
    )


def _node_values(recipe: Recipe, index: int) -> tuple[str, str, str, str]:
    if index == 0:
        return recipe.task, recipe.priority, recipe.scheduled, recipe.deadline
    return TASK_BY_INDEX[index % len(TASK_BY_INDEX)], PRIORITY_BY_INDEX[index % 3], "", ""


def build_case(recipe: Recipe) -> Case:
    """Render a case and its line ledger before any parser is invoked."""
    _validate(recipe)
    newline = "\n" if recipe.newline == "lf" else "\r\n"
    depths = SHAPES[recipe.shape]
    children: dict[int, list[int]] = {index: [] for index in range(len(depths))}
    roots: list[int] = []
    stack: list[int] = []
    for index, depth in enumerate(depths):
        while len(stack) > depth:
            stack.pop()
        if depth == 0:
            roots.append(index)
        else:
            children[stack[-1]].append(index)
        stack.append(index)

    lines: list[str] = []
    ledger: dict[int, tuple[str, int, int, str, str, str, str]] = {}

    def append(index: int, depth: int) -> None:
        task, priority, scheduled, deadline = _node_values(recipe, index)
        token = TOKEN_BY_INDEX[index % len(TOKEN_BY_INDEX)]
        heading = f"{task} [#{priority}] item-{index} {recipe.unicode} [[{recipe.reference}]] #{recipe.tag}"
        if scheduled:
            heading += f" SCHEDULED: <{scheduled}> DEADLINE: <{deadline}>"
        start = len(lines) + 1
        lines.extend((f"{'  ' * depth}- {heading}",
                      f"{'  ' * (depth + 1)}literal-key:: {recipe.literal}",
                      f"{'  ' * (depth + 1)}continuation-{index} {token}"))
        end = len(lines)
        ledger[index] = (f"{heading}\n{'  ' * (depth + 1)}continuation-{index} {token}", start, end,
                         task, priority, scheduled, deadline)
        for child in children[index]:
            append(child, depth + 1)

    for root in roots:
        append(root, 0)

    def expected(index: int) -> ExpectedBlock:
        content, start, end, task, priority, scheduled, deadline = ledger[index]
        properties: list[tuple[str, object]] = [("literal-key", recipe.literal)]
        if scheduled:
            properties.extend((
                ("scheduled", f"<{scheduled}>"),
                ("scheduled_journal_day", int(scheduled[:10].replace("-", ""))),
                ("scheduled_iso", scheduled[:10] + "T00:00:00"),
                ("deadline", f"<{deadline}>"),
                ("deadline_journal_day", int(deadline[:10].replace("-", ""))),
                ("deadline_iso", deadline[:10] + "T00:00:00"),
            ))
        # The parser's documented hashtag scan includes the visible [#priority] marker.
        refs = (recipe.reference, priority, recipe.tag)
        return ExpectedBlock(
            index=index, depth=depths[index], content=content,
            line_start=start, line_end=end, task_status=task, task_priority=priority,
            properties=tuple(properties),
            scheduled_at=SCHEDULED_EPOCHS[scheduled] if scheduled else None,
            deadline_at=DEADLINE_EPOCHS[deadline] if deadline else None,
            wikilinks=(recipe.reference,), tags=(priority, recipe.tag), refs=refs,
            children=tuple(expected(child) for child in children[index]),
        )

    source = newline.join(lines) + newline
    if len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
        raise ValueError("generated source exceeds byte budget")
    recipe_digest = hashlib.sha256(json.dumps(asdict(recipe), sort_keys=True).encode()).hexdigest()
    return Case(f"composite-v{SCHEMA_VERSION}-{recipe_digest}", recipe, source,
                tuple(expected(root) for root in roots))


def _check(condition: bool, identifier: str) -> None:
    if not condition:
        raise AssertionError(identifier)


def assert_matches_model(page: LogseqPage, expected: tuple[ExpectedBlock, ...]) -> None:
    """Compare observable block semantics and own source spans to the independent model."""
    actual_nodes = page.root_nodes

    def assert_siblings(
        actual: list[LogseqNode], wants: tuple[ExpectedBlock, ...], parent: LogseqNode | None,
    ) -> None:
        _check(len(actual) == len(wants), "model.sibling_count")
        for position, (node, want) in enumerate(zip(actual, wants, strict=True)):
            _check(node.content == want.content, "model.content")
            _check(node.indent_level == want.depth, "model.indent_level")
            _check((node.line_start, node.line_end) == (want.line_start, want.line_end), "model.line_span")
            _check(node.task_status == want.task_status, "model.task_status")
            _check(node.task_priority == want.task_priority, "model.task_priority")
            _check(node.properties == dict(want.properties), "model.properties")
            _check(node.scheduled_at == want.scheduled_at, "model.scheduled_at")
            _check(node.deadline_at == want.deadline_at, "model.deadline_at")
            _check(node.wikilinks == list(want.wikilinks), "model.wikilinks")
            _check(node.tags == list(want.tags), "model.tags")
            _check(node.refs == list(want.refs), "model.refs")
            _check(node.left_id == (actual[position - 1].uuid if position else None), "model.left_id")
            _check(node.parent_id == (parent.uuid if parent is not None else None), "model.parent_id")
            _check(len(node.children) == len(want.children), "model.child_count")
            assert_siblings(node.children, want.children, node)

    assert_siblings(actual_nodes, expected, None)
    flat_expected = _flatten_expected(expected)
    flat_actual = list(walk_nodes(actual_nodes))
    _check(len(flat_actual) == len(flat_expected), "model.preorder_count")
    _check(len(flat_actual) <= MAX_BLOCKS, "model.block_budget")
    _check(all(want.depth <= MAX_DEPTH for want in flat_expected), "model.depth_budget")
    assert_tree_invariants(page)


def _flatten_expected(blocks: tuple[ExpectedBlock, ...]) -> list[ExpectedBlock]:
    flattened: list[ExpectedBlock] = []
    for block in blocks:
        flattened.append(block)
        flattened.extend(_flatten_expected(block.children))
    return flattened


def semantic_difference_report(before: dict[str, Any], after: dict[str, Any]) -> tuple[dict[str, object], ...]:
    """Return bounded mismatch field names and numeric outline coordinates only."""
    differences: list[dict[str, object]] = []

    def add(field: str, outline_path: tuple[int, ...]) -> None:
        if len(differences) < MAX_DIFFERENCES:
            differences.append({"field": field, "outline_path": list(outline_path)})

    def compare_nodes(old_nodes: object, new_nodes: object, prefix: tuple[int, ...]) -> None:
        if not isinstance(old_nodes, list) or not isinstance(new_nodes, list):
            add("children", prefix)
            return
        if len(old_nodes) != len(new_nodes):
            add("children", prefix)
        for index, (old_node, new_node) in enumerate(zip(old_nodes, new_nodes, strict=False), start=1):
            path = (*prefix, index)
            if not isinstance(old_node, dict) or not isinstance(new_node, dict):
                add("children", path)
                continue
            for key in sorted(SEMANTIC_FIELDS - {"children"}):
                if old_node.get(key) != new_node.get(key):
                    add(key, path)
            compare_nodes(old_node.get("children", []), new_node.get("children", []), path)

    old_page = before.get("page", {})
    new_page = after.get("page", {})
    if isinstance(old_page, dict) and isinstance(new_page, dict):
        for key in sorted(PAGE_FIELDS):
            if old_page.get(key) != new_page.get(key):
                add(f"page.{key}", ())
        old_roots = old_page.get("root_nodes", [])
        new_roots = new_page.get("root_nodes", [])
        compare_nodes(old_roots, new_roots, ())
    return tuple(differences)


def worker_envelope(
    case: Case, context: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build a valid example protocol envelope for tests without launching a child."""
    selected_context = context if context is not None else _capture_source_context()
    return {
        "schema_version": SCHEMA_VERSION,
        "case_id": case.case_id,
        "recipe_sha256": _recipe_sha256(case.recipe),
        "source_sha256": case.source_sha256,
        "source_bytes": case.source_bytes,
        "classification": "parsed",
        "exception_type": None,
        "model_checked": True,
        "roundtrip_checked": True,
        "semantic_differences": [],
        "provenance_sha256": _provenance_sha256(selected_context),
        "module_origins_local": _module_origins_are_local(),
        "qualification_status": "qualified",
    }


def _recipe_sha256(recipe: Recipe) -> str:
    return hashlib.sha256(json.dumps(asdict(recipe), sort_keys=True).encode()).hexdigest()


def parse_worker_envelope(
    raw: object, case: Case, expected_context: dict[str, object] | None = None,
) -> Result:
    """Strictly bind child evidence to exact identity, finite recipe, and source digest."""
    if not isinstance(raw, dict) or set(raw) != WORKER_ENVELOPE_KEYS:
        raise ValueError("invalid worker envelope fields")
    if type(raw["schema_version"]) is not int or raw["schema_version"] != SCHEMA_VERSION:
        raise ValueError("worker schema mismatch")
    if raw["case_id"] != case.case_id or raw["recipe_sha256"] != _recipe_sha256(case.recipe):
        raise ValueError("worker identity mismatch")
    digest = raw["source_sha256"]
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("malformed source digest")
    if digest != case.source_sha256 or type(raw["source_bytes"]) is not int or raw["source_bytes"] != case.source_bytes:
        raise ValueError("worker source mismatch")
    classification = raw["classification"]
    if not isinstance(classification, str) or classification not in CLASSIFICATIONS:
        raise ValueError("unknown worker classification")
    error_type = raw["exception_type"]
    if error_type is not None and (
        not isinstance(error_type, str) or len(error_type) > 64 or not error_type.isidentifier()
    ):
        raise ValueError("invalid worker exception type")
    model_checked, roundtrip_checked = raw["model_checked"], raw["roundtrip_checked"]
    if type(model_checked) is not bool or type(roundtrip_checked) is not bool:
        raise ValueError("invalid worker check flags")
    provenance = raw["provenance_sha256"]
    if not isinstance(provenance, str) or not _valid_digest(provenance):
        raise ValueError("invalid worker provenance digest")
    if expected_context is not None and provenance != _provenance_sha256(expected_context):
        raise ValueError("worker provenance mismatch")
    if type(raw["module_origins_local"]) is not bool or raw["module_origins_local"] is not True:
        raise ValueError("worker module origin mismatch")
    qualification_status = raw["qualification_status"]
    if qualification_status not in {"qualified", "unqualified-source-drift"}:
        raise ValueError("worker qualification status is invalid")
    differences = _validate_semantic_differences(raw["semantic_differences"])
    if not _valid_stage_state(classification, error_type, model_checked, roundtrip_checked, differences):
        raise ValueError("worker classification and stage flags conflict")
    safe_envelope = {
        "schema_version": SCHEMA_VERSION, "case_id": case.case_id,
        "recipe_sha256": _recipe_sha256(case.recipe), "source_sha256": case.source_sha256,
        "source_bytes": case.source_bytes, "classification": classification,
        "exception_type": error_type, "model_checked": model_checked,
        "roundtrip_checked": roundtrip_checked,
        "semantic_differences": [dict(item) for item in differences],
        "provenance_sha256": provenance,
        "module_origins_local": True,
        "qualification_status": qualification_status,
    }
    return Result(case.case_id, case.recipe.seed, case.recipe, case.source_sha256, case.source_bytes,
                  cast(Classification, classification), error_type, model_checked, roundtrip_checked,
                  differences, safe_envelope, qualification_status)  # type: ignore[arg-type]


def _validate_semantic_differences(raw: object) -> tuple[dict[str, object], ...]:
    if not isinstance(raw, list) or len(raw) > MAX_DIFFERENCES:
        raise ValueError("invalid semantic-difference list")
    validated: list[dict[str, object]] = []
    for entry in raw:
        if not isinstance(entry, dict) or set(entry) != {"field", "outline_path"}:
            raise ValueError("invalid semantic-difference entry")
        field, outline_path = entry["field"], entry["outline_path"]
        if not isinstance(field, str) or field not in SEMANTIC_FIELDS | {
            f"page.{item}" for item in PAGE_FIELDS
        }:
            raise ValueError("unknown semantic-difference field")
        if (
            not isinstance(outline_path, list)
            or len(outline_path) > MAX_DEPTH + 1
            or any(type(position) is not int or not 1 <= position <= MAX_BLOCKS
                   for position in outline_path)
        ):
            raise ValueError("invalid semantic-difference coordinates")
        validated.append({"field": field, "outline_path": list(outline_path)})
    return tuple(validated)


def _valid_stage_state(
    classification: str,
    error_type: str | None,
    model_checked: bool,
    roundtrip_checked: bool,
    differences: tuple[dict[str, object], ...],
) -> bool:
    if error_type is not None and (len(error_type) > 64 or not error_type.isidentifier()):
        return False
    if classification == "parsed":
        return model_checked and roundtrip_checked and error_type is None and not differences
    if classification == "semantic_roundtrip_failure":
        return model_checked and not roundtrip_checked and error_type is not None and (
            error_type != "SemanticRoundtripMismatch" or bool(differences)
        )
    if classification == "timeout":
        return not model_checked and not roundtrip_checked and error_type is None and not differences
    if classification in {"expected_parser_error", "unexpected_exception", "invariant_failure", "runner_failure"}:
        return not model_checked and not roundtrip_checked and error_type is not None and not differences
    return False


def _worker(recipe_raw: str) -> dict[str, object]:
    """Reconstruct source/model in child and emit no source or exception message."""
    request = json.loads(recipe_raw)
    if not isinstance(request, dict) or set(request) != {"recipe", "context"}:
        raise ValueError("invalid worker request fields")
    recipe = request["recipe"]
    if not isinstance(recipe, dict):
        raise ValueError("invalid worker recipe")
    case = build_case(recipe_from_json(json.dumps(recipe, sort_keys=True)))
    expected_context = _validate_source_context(request["context"])
    actual_context = _capture_source_context()
    base = worker_envelope(case, actual_context)
    if actual_context != expected_context or not _module_origins_are_local():
        base.update(classification="runner_failure", exception_type="SourceProvenanceMismatch",
                    model_checked=False, roundtrip_checked=False)
        return base
    result = _evaluate_worker(case, base, actual_context)
    try:
        final_context = _capture_source_context()
        local_origins = _module_origins_are_local()
    except ValueError:
        final_context = {}
        local_origins = False
    if final_context != expected_context or not local_origins:
        result.update(
            classification="runner_failure", exception_type="SourceProvenanceMismatch",
            model_checked=False, roundtrip_checked=False, semantic_differences=[],
            qualification_status="unqualified-source-drift",
        )
    return result


def _evaluate_worker(
    case: Case, base: dict[str, object], context: dict[str, object],
) -> dict[str, object]:
    base.update({"model_checked": False, "roundtrip_checked": False,
                 "classification": "runner_failure", "exception_type": None,
                 "semantic_differences": []})
    denial = child_runtime_gate(case, context)
    if denial is not None:
        return denial
    try:
        page = StackMachineParser().parse(case.source, page_title="composite-generated")
    except LogseqParserError as error:
        base.update(classification="expected_parser_error", exception_type=_safe_exception_name(error))
        return base
    except Exception as error:
        base.update(classification="unexpected_exception", exception_type=_safe_exception_name(error))
        return base
    try:
        assert_matches_model(page, case.expected)
        base["model_checked"] = True
    except Exception as error:
        base.update(classification="invariant_failure", exception_type=_safe_exception_name(error))
        return base
    try:
        rendered = serialize_logseq_page(page)
        reparsed = StackMachineParser().parse(rendered, page_title=page.title)
        assert_tree_invariants(reparsed)
        reparsed_projection = project_page(
            reparsed, profile="semantic_roundtrip_v1", identity_policy=IDENTITY_POLICY
        )
        source_projection = project_page(
            page, profile="semantic_roundtrip_v1", identity_policy=IDENTITY_POLICY
        )
        if reparsed_projection != source_projection:
            differences = semantic_difference_report(source_projection, reparsed_projection)
            base.update(classification="semantic_roundtrip_failure",
                        exception_type="SemanticRoundtripMismatch",
                        semantic_differences=list(differences))
            return base
        base.update(classification="parsed", exception_type=None, roundtrip_checked=True)
    except Exception as error:
        base.update(classification="semantic_roundtrip_failure",
                    exception_type=_safe_exception_name(error))
    return base


def _optimized_runtime() -> bool:
    return sys.flags.optimize != 0


def _safe_exception_name(error: Exception) -> str:
    name = type(error).__name__
    return name if name.isidentifier() and len(name) <= 64 else "UnknownException"


def child_runtime_gate(
    case: Case, context: dict[str, object] | None = None,
) -> dict[str, object] | None:
    """Return a source-free denial envelope before parser access in optimized Python."""
    if not _optimized_runtime():
        return None
    envelope = worker_envelope(case, context)
    envelope.update(classification="runner_failure", exception_type="OptimizedPythonDenied",
                    model_checked=False, roundtrip_checked=False)
    return envelope


def _worker_main() -> int:
    try:
        envelope = _worker(sys.stdin.read())
    except Exception as error:
        envelope = {"schema_version": SCHEMA_VERSION, "case_id": "", "recipe_sha256": "",
                    "source_sha256": "", "source_bytes": 0, "classification": "runner_failure",
                    "exception_type": _safe_exception_name(error), "model_checked": False,
                    "roundtrip_checked": False, "semantic_differences": [],
                    "provenance_sha256": "0" * 64, "module_origins_local": False,
                    "qualification_status": "unqualified-source-drift"}
    print(json.dumps(envelope, sort_keys=True))
    return 0


def run_case(
    case: Case, *, timeout_seconds: float = MAX_TIMEOUT_SECONDS,
    expected_context: dict[str, object] | None = None,
) -> Result:
    """Run exactly one fresh child with the same three-second bounded envelope."""
    if not 0 < timeout_seconds <= MAX_TIMEOUT_SECONDS:
        raise ValueError("timeout must be positive and no greater than three seconds")
    selected_context = expected_context or _capture_source_context()
    before = _capture_source_context()
    if before != selected_context:
        raise ValueError("source context drift before child")
    if not _module_origins_are_local():
        raise ValueError("repository-local module origin check failed")
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "tests.parser_assurance.composite_properties", "--worker"],
            input=json.dumps({"recipe": asdict(case.recipe), "context": selected_context}, sort_keys=True), text=True,
            capture_output=True, check=False, timeout=timeout_seconds,
            cwd=Path(__file__).resolve().parents[2],
        )
    except subprocess.TimeoutExpired:
        result = Result(case.case_id, case.recipe.seed, case.recipe, case.source_sha256, case.source_bytes,
                        "timeout", None, False, False)
    except OSError:
        result = Result(case.case_id, case.recipe.seed, case.recipe, case.source_sha256, case.source_bytes,
                        "runner_failure", "OSError", False, False)
    else:
        if completed.returncode != 0:
            result = Result(case.case_id, case.recipe.seed, case.recipe, case.source_sha256,
                            case.source_bytes, "runner_failure", "ChildProcessExit", False, False)
        else:
            try:
                payload = json.loads(completed.stdout)
                result = parse_worker_envelope(payload, case, selected_context)
            except (json.JSONDecodeError, ValueError, TypeError):
                result = Result(case.case_id, case.recipe.seed, case.recipe, case.source_sha256,
                                case.source_bytes, "runner_failure", "InvalidWorkerEnvelope", False, False)
    try:
        after = _capture_source_context()
    except Exception:
        return replace_result_qualification(result, "unqualified-source-drift", selected_context)
    if after != selected_context:
        return replace_result_qualification(result, "unqualified-source-drift", selected_context)
    return replace_result_qualification(result, result.qualification_status, selected_context)


def replace_result_qualification(
    result: Result, status: str, source_context: dict[str, object] | None = None,
) -> Result:
    return Result(
        result.case_id, result.seed, result.recipe, result.source_sha256, result.source_bytes,
        result.classification, result.exception_type, result.model_checked, result.roundtrip_checked,
        result.semantic_differences, result.worker_envelope, status,
        source_context if source_context is not None else result.source_context,
    )


def _collect_for_seed(seed_value: int, limit: int) -> tuple[Recipe, ...]:
    collected: list[Recipe] = []

    @settings(max_examples=limit * 8, derandomize=True, database=None, deadline=None,
              phases=(Phase.generate,))
    @hypothesis_seed(seed_value)
    @given(recipe=recipe_strategy())
    def collect(recipe: Recipe) -> None:
        selected = Recipe(seed_value, recipe.shape, recipe.task, recipe.priority, recipe.scheduled,
                          recipe.deadline, recipe.literal, recipe.reference, recipe.tag,
                          recipe.unicode, recipe.newline)
        if len(collected) < limit and selected not in collected:
            collected.append(selected)

    collect()
    return tuple(collected)


def collect_recipes(*, seed: int, limit: int) -> tuple[Recipe, ...]:
    """Collect, validate, deduplicate, and cap recipes before launching children."""
    if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
        raise ValueError("seed outside finite range")
    if type(limit) is not int or not 1 <= limit <= BROAD_CHILD_CAP:
        raise ValueError("per-seed recipe cap must be between one and one hundred twenty")
    recipes = _collect_for_seed(seed, limit)
    for recipe in recipes:
        _validate(recipe)
    return recipes


def implementation_manifest(root: Path | None = None) -> dict[str, str]:
    """Hash sorted selected local Python sources and fixed project declarations."""
    selected_root = (root or Path(__file__).resolve().parents[2]).resolve(strict=True)
    package = selected_root / "src/logseq_matryca_parser"
    assurance = selected_root / "tests/parser_assurance"
    if not package.is_dir() or not assurance.is_dir():
        raise ValueError("required source roots are missing")
    selected: set[str] = set(REQUIRED_MANIFEST_FILES)
    def fail_traversal(error: OSError) -> None:
        raise ValueError("source inventory traversal failed") from error

    for directory in (package, assurance):
        try:
            for current, dirnames, filenames in os.walk(
                directory, followlinks=False, onerror=fail_traversal,
            ):
                current_path = Path(current)
                if current_path.is_symlink():
                    raise ValueError("symlink in selected source root")
                for dirname in dirnames:
                    if (current_path / dirname).is_symlink():
                        raise ValueError("symlink in selected source root")
                for filename in filenames:
                    path = current_path / filename
                    if path.is_symlink():
                        raise ValueError("symlink in selected source root")
                    if path.suffix == ".py":
                        selected.add(path.relative_to(selected_root).as_posix())
        except OSError as error:
            raise ValueError("source inventory traversal failed") from error
    digests: dict[str, str] = {}
    for relative in sorted(selected):
        path = selected_root / relative
        try:
            path.relative_to(selected_root)
            if path.is_symlink() or not path.is_file():
                raise ValueError("selected manifest path is not a local regular file")
            resolved = path.resolve(strict=True)
            resolved.relative_to(selected_root)
            for parent in path.parents:
                if parent == selected_root:
                    break
                if parent.is_symlink():
                    raise ValueError("symlink in selected manifest path")
            digests[relative] = hashlib.sha256(resolved.read_bytes()).hexdigest()
        except (OSError, ValueError) as error:
            raise ValueError(f"invalid required manifest file: {relative}") from error
    return digests


def _valid_digest(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _valid_revision(value: object) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(
        character in "0123456789abcdef" for character in value
    )


def _revision(root: Path | None = None, *, required: bool = True) -> str:
    """Read exact HEAD from selected repository root under a bounded probe."""
    selected_root = (root or Path(__file__).resolve().parents[2]).resolve(strict=True)
    try:
        result = subprocess.run(
            ["git", "-C", str(selected_root), "rev-parse", "--show-toplevel", "HEAD"],
            cwd=selected_root, text=True,
                                capture_output=True, check=True, timeout=1.0)
    except (OSError, subprocess.SubprocessError) as error:
        if required:
            raise ValueError("repository revision probe failed") from error
        return ""
    lines = result.stdout.splitlines()
    if len(lines) != 2 or Path(lines[0]).resolve() != selected_root:
        if required:
            raise ValueError("repository revision root mismatch")
        return ""
    value = lines[1].strip()
    if not _valid_revision(value):
        if required:
            raise ValueError("repository revision is malformed")
        return ""
    return value


def runtime_descriptor() -> dict[str, object]:
    """Return selected exact runtime compatibility metadata, not byte attestation."""
    try:
        langchain_version: str | None = importlib.metadata.version("langchain-core")
    except importlib.metadata.PackageNotFoundError:
        langchain_version = None
    return {
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "optimization": sys.flags.optimize,
        "os_family": os.name,
        "os_release": platform.release(),
        "machine": platform.machine(),
        "hypothesis_version": hypothesis.__version__,
        "pydantic_version": pydantic.__version__,
        "pydantic_core_version": pydantic_core.__version__,
        "langchain_core": {"present": langchain_version is not None, "version": langchain_version},
    }


def _validate_runtime_descriptor(value: object) -> dict[str, object]:
    keys = {
        "python_implementation", "python_version", "optimization", "os_family", "os_release",
        "machine", "hypothesis_version", "pydantic_version", "pydantic_core_version", "langchain_core",
    }
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError("runtime descriptor fields are invalid")
    for key in keys - {"optimization", "langchain_core"}:
        if not _meaningful_runtime_text(value[key]):
            raise ValueError("runtime descriptor value is unavailable")
    if type(value["optimization"]) is not int or value["optimization"] != 0:
        raise ValueError("runtime optimization is not qualified")
    optional = value["langchain_core"]
    if not isinstance(optional, dict) or set(optional) != {"present", "version"}:
        raise ValueError("optional runtime descriptor is invalid")
    if type(optional["present"]) is not bool:
        raise ValueError("optional runtime presence is invalid")
    version = optional["version"]
    if optional["present"] and not _meaningful_runtime_text(version):
        raise ValueError("optional runtime version is inconsistent")
    if not optional["present"] and version is not None:
        raise ValueError("optional runtime version is inconsistent")
    return dict(value)


def _meaningful_runtime_text(value: object) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip().casefold()
    return normalized not in {"", "unknown", "unavailable", "not available", "n/a", "none"}


def _module_origins_are_local(root: Path | None = None) -> bool:
    selected_root = (root or Path(__file__).resolve().parents[2]).resolve()
    modules = {
        "logseq_matryca_parser": "src/logseq_matryca_parser/__init__.py",
        "logseq_matryca_parser.logos_core": "src/logseq_matryca_parser/logos_core.py",
        "logseq_matryca_parser.logos_parser": "src/logseq_matryca_parser/logos_parser.py",
        "logseq_matryca_parser.logseq_markdown": "src/logseq_matryca_parser/logseq_markdown.py",
        "tests": "tests/__init__.py",
        "tests.parser_assurance": "tests/parser_assurance/__init__.py",
        "tests.parser_assurance.composite_properties":
            "tests/parser_assurance/composite_properties.py",
        "tests.parser_assurance.adversarial": "tests/parser_assurance/adversarial.py",
        "tests.parser_assurance.invariants": "tests/parser_assurance/invariants.py",
        "tests.parser_assurance.projection": "tests/parser_assurance/projection.py",
    }
    for module_name, relative in modules.items():
        module = sys.modules.get(module_name)
        if module is None and module_name == "tests.parser_assurance.composite_properties":
            module = sys.modules.get("__main__")
            spec = getattr(module, "__spec__", None) if module is not None else None
            if getattr(spec, "name", None) != module_name:
                return False
            spec_origin = getattr(spec, "origin", None)
            if not isinstance(spec_origin, str):
                return False
            try:
                if Path(spec_origin).resolve(strict=True) != (selected_root / relative).resolve(strict=True):
                    return False
            except (OSError, ValueError):
                return False
        origin = getattr(module, "__file__", None) if module is not None else None
        if not isinstance(origin, str):
            return False
        try:
            if Path(origin).resolve(strict=True) != (selected_root / relative).resolve(strict=True):
                return False
        except (OSError, ValueError):
            return False
    return True


def _validate_source_context(value: object) -> dict[str, object]:
    keys = {"revision", "implementation_manifest", "runtime_descriptor"}
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError("source context fields are invalid")
    if not _valid_revision(value["revision"]):
        raise ValueError("source context revision is invalid")
    manifest = value["implementation_manifest"]
    if not isinstance(manifest, dict) or not manifest or list(manifest) != sorted(manifest):
        raise ValueError("source context manifest is invalid")
    if any(not isinstance(path, str) or not isinstance(digest, str) or not _valid_digest(digest)
           for path, digest in manifest.items()):
        raise ValueError("source context manifest digest is invalid")
    return {
        "revision": value["revision"],
        "implementation_manifest": dict(manifest),
        "runtime_descriptor": _validate_runtime_descriptor(value["runtime_descriptor"]),
    }


def _capture_source_context() -> dict[str, object]:
    try:
        context = {
            "revision": _revision(),
            "implementation_manifest": implementation_manifest(),
            "runtime_descriptor": runtime_descriptor(),
        }
        return _validate_source_context(context)
    except Exception as error:
        raise ValueError("source context probe failed") from error


def _provenance_sha256(context: dict[str, object]) -> str:
    validated = _validate_source_context(context)
    rendered = json.dumps(validated, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def run_profile(profile: str, *, seed_value: int | None = None) -> dict[str, object]:
    """Run one smoke/broad campaign, fail first, never retry or minimize."""
    if profile not in {"smoke", "broad"}:
        raise ValueError("unknown campaign profile")
    context = _capture_source_context()
    campaign_seeds: tuple[int, ...]
    if profile == "smoke":
        campaign_seeds = (104 if seed_value is None else seed_value,)
        candidates = [
            Recipe.literal_example(),
            Recipe(104, "nested", "NOW", "C", "2026-08-20 Thu", "2026-08-22 Sat",
                   "plain-value", "Résumé", "caffè", "🙂", "crlf"),
            Recipe(104, "mixed-32", "CANCELED", "B", "2026-04-30 Thu", "2026-05-01 Fri",
                   "cafe-42", "Topic page", "work", "東京", "crlf"),
        ]
        candidates.extend(collect_recipes(seed=campaign_seeds[0], limit=1))
        cap = SMOKE_CHILD_CAP
    else:
        campaign_seeds = (seed_value,) if seed_value is not None else BROAD_SEEDS
        cap = BROAD_CHILD_CAP
        per_seed = 39 if len(campaign_seeds) == 3 else cap - 3
        candidates = [Recipe.literal_example(),
                      Recipe(104, "nested", "NOW", "C", "2026-08-20 Thu", "2026-08-22 Sat",
                             "plain-value", "Résumé", "caffè", "🙂", "crlf"),
                      Recipe(104, "mixed-32", "CANCELED", "B", "2026-04-30 Thu", "2026-05-01 Fri",
                             "cafe-42", "Topic page", "work", "東京", "crlf")]
        candidates.extend(recipe for actual_seed in campaign_seeds
                          for recipe in collect_recipes(seed=actual_seed, limit=per_seed))
    selected: list[Recipe] = []
    seen: set[Recipe] = set()
    for recipe in candidates:
        if recipe not in seen and len(selected) < cap:
            _validate(recipe)
            seen.add(recipe)
            selected.append(recipe)
    results: list[Result] = []
    preflight_rejection: str | None = None
    for recipe in selected:
        case = build_case(recipe)
        try:
            if _capture_source_context() != context:
                preflight_rejection = "source context drift before child"
                break
        except ValueError:
            preflight_rejection = "source context unavailable before child"
            break
        try:
            result = run_case(case, expected_context=context)
        except ValueError:
            preflight_rejection = "source context unavailable before child"
            break
        results.append(result)
        if result.qualification_status != "qualified" or result.classification != "parsed" \
                or not result.model_checked or not result.roundtrip_checked:
            break
    return {
        "schema_version": SCHEMA_VERSION,
        "qualification": QUALIFICATION_LEVEL,
        "qualification_status": "qualified" if all(
            result.qualification_status == "qualified" for result in results
        ) and preflight_rejection is None else "unqualified-source-drift",
        "profile": profile,
        "campaign_seeds": list(campaign_seeds),
        "child_budget": cap,
        "children_run": len(results),
        "baseline_revision": BASELINE_REVISION,
        "current_revision": context["revision"],
        "implementation_manifest": context["implementation_manifest"],
        "runtime_descriptor": context["runtime_descriptor"],
        "provenance_sha256": _provenance_sha256(context),
        "preflight_rejection": preflight_rejection,
        "results": [_result_record(result, context=context) for result in results],
    }


def _result_record(result: Result, *, context: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "qualification": QUALIFICATION_LEVEL,
        "qualification_status": result.qualification_status,
        "recipe": asdict(result.recipe),
        "source_sha256": result.source_sha256,
        "source_bytes": result.source_bytes,
        "revision": context["revision"],
        "implementation_manifest": context["implementation_manifest"],
        "runtime_descriptor": context["runtime_descriptor"],
        "provenance_sha256": _provenance_sha256(context),
        "result": {
            "schema_version": SCHEMA_VERSION,
            "case_id": result.case_id, "seed": result.seed,
            "recipe": asdict(result.recipe), "source_sha256": result.source_sha256,
            "source_bytes": result.source_bytes, "classification": result.classification,
            "exception_type": result.exception_type, "model_checked": result.model_checked,
            "roundtrip_checked": result.roundtrip_checked,
            "semantic_differences": [dict(item) for item in result.semantic_differences],
        },
        "worker_envelope": result.worker_envelope,
    }


def replay_receipt_entry(entry: object) -> Result:
    """Replay one schema-3 entry only under matching source and runtime context."""
    keys = {
        "schema_version", "qualification", "qualification_status", "recipe", "source_sha256",
        "source_bytes", "revision", "implementation_manifest", "runtime_descriptor",
        "provenance_sha256", "result", "worker_envelope",
    }
    if not isinstance(entry, dict) or set(entry) != keys:
        raise ValueError("invalid receipt entry")
    if type(entry["schema_version"]) is not int or entry["schema_version"] != SCHEMA_VERSION:
        raise ValueError("receipt schema mismatch")
    if entry["qualification"] != QUALIFICATION_LEVEL:
        raise ValueError("receipt qualification mismatch")
    if entry["qualification_status"] != "qualified":
        raise ValueError("receipt qualification status is not qualified")
    recorded_context = _validate_source_context({
        "revision": entry["revision"],
        "implementation_manifest": entry["implementation_manifest"],
        "runtime_descriptor": entry["runtime_descriptor"],
    })
    if entry["provenance_sha256"] != _provenance_sha256(recorded_context):
        raise ValueError("receipt provenance mismatch")
    current_context = _capture_source_context()
    if recorded_context != current_context:
        raise ValueError("source or runtime context mismatch")
    if not _module_origins_are_local():
        raise ValueError("repository-local module origin check failed")
    recipe = recipe_from_json(json.dumps(entry["recipe"], sort_keys=True))
    case = build_case(recipe)
    if not _valid_digest(entry["source_sha256"]) or entry["source_sha256"] != case.source_sha256 \
            or type(entry["source_bytes"]) is not int or entry["source_bytes"] != case.source_bytes:
        raise ValueError("source digest mismatch")
    result = entry["result"]
    if not isinstance(result, dict) or set(result) != RESULT_KEYS:
        raise ValueError("nested result fields mismatch")
    if type(result["schema_version"]) is not int or result["schema_version"] != SCHEMA_VERSION:
        raise ValueError("nested result schema mismatch")
    nested_recipe = recipe_from_json(json.dumps(result["recipe"], sort_keys=True))
    if result["case_id"] != case.case_id or type(result["seed"]) is not int \
            or result["seed"] != case.recipe.seed or nested_recipe != case.recipe:
        raise ValueError("nested result identity mismatch")
    if result["source_sha256"] != case.source_sha256 or type(result["source_bytes"]) is not int \
            or result["source_bytes"] != case.source_bytes:
        raise ValueError("nested result source digest mismatch")
    classification = result["classification"]
    error_type = result["exception_type"]
    model_checked, roundtrip_checked = result["model_checked"], result["roundtrip_checked"]
    differences = _validate_semantic_differences(result["semantic_differences"])
    if (
        not isinstance(classification, str) or classification not in CLASSIFICATIONS
        or (error_type is not None and (
            not isinstance(error_type, str) or len(error_type) > 64 or not error_type.isidentifier()
        ))
        or type(model_checked) is not bool or type(roundtrip_checked) is not bool
        or not _valid_stage_state(classification, error_type, model_checked, roundtrip_checked, differences)
    ):
        raise ValueError("nested result stage identity mismatch")
    worker_envelope = entry["worker_envelope"]
    if worker_envelope is not None:
        parsed_worker = parse_worker_envelope(worker_envelope, case, recorded_context)
        if classification != parsed_worker.classification \
                or model_checked is not parsed_worker.model_checked \
                or roundtrip_checked is not parsed_worker.roundtrip_checked \
                or error_type != parsed_worker.exception_type \
                or differences != parsed_worker.semantic_differences \
                or parsed_worker.qualification_status != "qualified":
            raise ValueError("nested worker identity mismatch")
    elif (classification, error_type) not in PARENT_FAILURES:
        raise ValueError("worker evidence required for parser-stage result")
    return run_case(case, expected_context=recorded_context)


def run_exact_diagnostic(recipe_raw: str) -> dict[str, object]:
    """Run only the one approved source-free literal recipe, exactly once."""
    recipe = recipe_from_json(recipe_raw)
    if recipe != Recipe.literal_example():
        raise ValueError("recipe does not match the exact diagnostic recipe")
    case = build_case(recipe)
    if case.source_sha256 != DIAGNOSTIC_SOURCE_SHA256 or case.source_bytes != DIAGNOSTIC_SOURCE_BYTES:
        raise ValueError("diagnostic source identity mismatch")
    context = _capture_source_context()
    try:
        result = run_case(case, timeout_seconds=MAX_TIMEOUT_SECONDS, expected_context=context)
        preflight_rejection = None
    except ValueError:
        result = None
        preflight_rejection = "source context unavailable before child"
    return {
        "schema_version": SCHEMA_VERSION,
        "qualification": QUALIFICATION_LEVEL,
        "qualification_status": (
            result.qualification_status if result is not None else "unqualified-source-drift"
        ),
        "profile": "diagnostic",
        "campaign_seeds": [recipe.seed],
        "child_budget": 1,
        "children_run": 1 if result is not None else 0,
        "baseline_revision": BASELINE_REVISION,
        "current_revision": context["revision"],
        "implementation_manifest": context["implementation_manifest"],
        "runtime_descriptor": context["runtime_descriptor"],
        "provenance_sha256": _provenance_sha256(context),
        "preflight_rejection": preflight_rejection,
        "results": [_result_record(result, context=context)] if result is not None else [],
    }


def _receipt_success(receipt: object) -> bool:
    if not isinstance(receipt, dict) or not isinstance(receipt.get("results"), list) \
            or type(receipt.get("schema_version")) is not int \
            or receipt.get("schema_version") != SCHEMA_VERSION \
            or receipt.get("qualification") != QUALIFICATION_LEVEL \
            or receipt.get("qualification_status") != "qualified":
        return False
    results = receipt["results"]
    return bool(results) and all(
        isinstance(entry, dict)
        and entry.get("schema_version") == SCHEMA_VERSION
        and entry.get("qualification") == QUALIFICATION_LEVEL
        and entry.get("qualification_status") == "qualified"
        and isinstance(entry.get("result"), dict)
        and entry["result"].get("schema_version") == SCHEMA_VERSION
        and entry["result"].get("classification") == "parsed"
        and entry["result"].get("model_checked") is True
        and entry["result"].get("roundtrip_checked") is True
        for entry in results
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--profile", choices=("smoke", "broad"), default="smoke")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--diagnostic-recipe", help="Run the one approved exact recipe")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.worker:
        return _worker_main()
    try:
        receipt = (
            run_exact_diagnostic(args.diagnostic_recipe)
            if args.diagnostic_recipe is not None
            else run_profile(args.profile, seed_value=args.seed)
        )
    except ValueError:
        receipt = {"schema_version": SCHEMA_VERSION, "profile": "invalid-request", "results": []}
    rendered = json.dumps(receipt, sort_keys=True)
    if args.output is not None:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if _receipt_success(receipt) else 1


if __name__ == "__main__":
    raise SystemExit(main())
