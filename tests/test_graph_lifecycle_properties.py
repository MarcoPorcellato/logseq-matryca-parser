"""Finite lifecycle recipes and independently calibrated graph expectations."""

from __future__ import annotations

import json
import sys
import tempfile
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import pytest
from hypothesis import Phase, given, note, settings

from logseq_matryca_parser import LogseqGraph
from tests.parser_assurance.graph_lifecycle import (
    Action,
    EvaluationGuard,
    LifecycleObservation,
    ObservedNode,
    ObservedPage,
    PageImage,
    Trace,
    apply_action,
    assert_observation,
    decode_trace,
    encode_trace,
    lifecycle_traces,
    observe_graph,
    relative_owned_path,
    render_sources,
    source_digest,
    source_digest_timeline,
    validate_images,
    validate_trace,
)
from tests.parser_assurance.invariants import walk_nodes
from tests.parser_assurance.projection import project_page

# Authoring literals below do not call the reducer, renderer, observer or parser.
P0 = PageImage(0, True, True, False, 0, "A", ("Alias1A", "Alias1A"), ("Page1",))
P1 = PageImage(1, True, True, False, 0, "A", ("Page0",), ())
P2 = PageImage(2, False, False, False, 0, "A", ("Alias1A",), ())
P3 = PageImage(3, False, False, False, 0, "A", ("Page0",), ())
INITIAL = (P0, P1, P2, P3)
P2_CREATED = replace(P2, present=True, ever_created=True)
P0_EDITED = replace(P0, revision=1)
P0_LINKED = replace(P0_EDITED, root_links=("Alias1B", "Alias1B"), tail_links=("Page2",))
P0_EARLY_LINKED = replace(P0, root_links=("Alias1B", "Alias1B"), tail_links=("Page2",))
P0_CLEARED = replace(P0_LINKED, root_links=())
P1_B = replace(P1, alias_variant="B")
P1_MOVED = replace(P1_B, renamed=True)
P1_MISSING = replace(P1_MOVED, present=False)
P1_B_MISSING = replace(P1_B, present=False)

L1 = Trace(
    INITIAL,
    (
        Action("create", 2),
        Action("edit", 0),
        Action("alias", 1, "B"),
        Action("links", 0, root_links=("Alias1B", "Alias1B"), tail_links=("Page2",)),
        Action("rename", 1),
        Action("delete", 1),
        Action("restore", 1),
        Action("links", 0, root_links=(), tail_links=("Page2",)),
    ),
    "LF",
)
L2 = Trace(
    INITIAL,
    (
        Action("create", 2),
        Action("links", 0, root_links=("Alias1B", "Alias1B"), tail_links=("Page2",)),
        Action("alias", 1, "B"),
        Action("delete", 1),
        Action("edit", 0),
        Action("restore", 1),
        Action("rename", 1),
        Action("links", 0, root_links=(), tail_links=("Page2",)),
    ),
    "CRLF",
)

L1_STATES = (
    INITIAL,
    (P0, P1, P2_CREATED, P3),
    (P0_EDITED, P1, P2_CREATED, P3),
    (P0_EDITED, P1_B, P2_CREATED, P3),
    (P0_LINKED, P1_B, P2_CREATED, P3),
    (P0_LINKED, P1_MOVED, P2_CREATED, P3),
    (P0_LINKED, P1_MISSING, P2_CREATED, P3),
    (P0_LINKED, P1_MOVED, P2_CREATED, P3),
    (P0_CLEARED, P1_MOVED, P2_CREATED, P3),
)
L2_STATES = (
    INITIAL,
    (P0, P1, P2_CREATED, P3),
    (P0_EARLY_LINKED, P1, P2_CREATED, P3),
    (P0_EARLY_LINKED, P1_B, P2_CREATED, P3),
    (P0_EARLY_LINKED, P1_B_MISSING, P2_CREATED, P3),
    (P0_LINKED, P1_B_MISSING, P2_CREATED, P3),
    (P0_LINKED, P1_B, P2_CREATED, P3),
    (P0_LINKED, P1_MOVED, P2_CREATED, P3),
    (P0_CLEARED, P1_MOVED, P2_CREATED, P3),
)
RENAME_INTERMEDIATE = (P0_LINKED, P1_MISSING, P2_CREATED, P3)

_NAMES = (
    "Page0",
    "Page1",
    "Page2",
    "Page3",
    "Moved0",
    "Moved1",
    "Moved2",
    "Moved3",
    "Alias0A",
    "Alias0B",
    "Alias0C",
    "Alias1A",
    "Alias1B",
    "Alias1C",
    "Alias2A",
    "Alias2B",
    "Alias2C",
    "Alias3A",
    "Alias3B",
    "Alias3C",
    "Missing",
)
_PAGE_PROBES = (*_NAMES, *(x.upper() for x in (*_NAMES[:8], "Missing")))
_BACKLINK_PROBES = (*_NAMES, *(x.upper() for x in _NAMES))
_NATIVE_IDS = (
    "00000000-0000-4000-8000-000000000001",
    "00000000-0000-4000-8000-000000000002",
    "00000000-0000-4000-8000-000000000003",
    "00000000-0000-4000-8000-000000000005",
    "00000000-0000-4000-8000-000000000006",
    "00000000-0000-4000-8000-000000000007",
    "00000000-0000-4000-8000-000000000009",
    "00000000-0000-4000-8000-00000000000a",
    "00000000-0000-4000-8000-00000000000b",
    "00000000-0000-4000-8000-00000000000d",
    "00000000-0000-4000-8000-00000000000e",
    "00000000-0000-4000-8000-00000000000f",
)


def _literal_nodes(
    title: str, rows: tuple[tuple[str, str | None, str, tuple[str, ...]], ...]
) -> tuple[ObservedNode, ...]:
    """Assemble supplied literal fields; do not derive graph semantics."""
    return tuple(
        ObservedNode(
            slot=(title, outline),
            relative_source_path=f"pages/{title}.md",
            routed_owner_title=title,
            parser_uuid=parser_id,
            source_uuid=native,
            synthetic_id=native is None,
            content=content,
            line_span=span,
            properties=(("id", native),) if native else (),
            properties_order=("id",) if native else (),
            wikilinks=links,
        )
        for outline, span, (parser_id, native, content, links) in zip(
            ((1,), (1, 1), (2,)),
            ((3, 4), (5, 5), (6, 7)),
            rows,
            strict=True,
        )
    )


_P0_RAW = _literal_nodes(
    "Page0",
    (
        (
            "10000000-0000-5000-8000-000000000001",
            _NATIVE_IDS[0],
            "Root0v0 [[Alias1A]] [[Alias1A]]",
            ("Alias1A", "Alias1A"),
        ),
        ("10000000-0000-5000-8000-000000000002", None, "Child0v0", ()),
        ("10000000-0000-5000-8000-000000000003", _NATIVE_IDS[2], "Tail0 [[Page1]]", ("Page1",)),
    ),
)
_P0_EDITED = _literal_nodes(
    "Page0",
    (
        (
            "10000000-0000-5000-8000-000000000004",
            _NATIVE_IDS[1],
            "Root0v1 [[Alias1A]] [[Alias1A]]",
            ("Alias1A", "Alias1A"),
        ),
        ("10000000-0000-5000-8000-000000000005", None, "Child0v1", ()),
        ("10000000-0000-5000-8000-000000000003", _NATIVE_IDS[2], "Tail0 [[Page1]]", ("Page1",)),
    ),
)
_P0_LINKED = _literal_nodes(
    "Page0",
    (
        (
            "10000000-0000-5000-8000-000000000006",
            _NATIVE_IDS[1],
            "Root0v1 [[Alias1B]] [[Alias1B]]",
            ("Alias1B", "Alias1B"),
        ),
        ("10000000-0000-5000-8000-000000000005", None, "Child0v1", ()),
        ("10000000-0000-5000-8000-000000000007", _NATIVE_IDS[2], "Tail0 [[Page2]]", ("Page2",)),
    ),
)
_P1_RAW = _literal_nodes(
    "Page1",
    (
        ("10000000-0000-5000-8000-000000000008", _NATIVE_IDS[3], "Root1v0 [[Page0]]", ("Page0",)),
        ("10000000-0000-5000-8000-000000000009", None, "Child1v0", ()),
        ("10000000-0000-5000-8000-00000000000a", _NATIVE_IDS[5], "Tail1", ()),
    ),
)
_P1_MOVED = _literal_nodes(
    "Moved1",
    (
        ("10000000-0000-5000-8000-00000000000b", _NATIVE_IDS[3], "Root1v0 [[Page0]]", ("Page0",)),
        ("10000000-0000-5000-8000-00000000000c", None, "Child1v0", ()),
        ("10000000-0000-5000-8000-00000000000d", _NATIVE_IDS[5], "Tail1", ()),
    ),
)
_P2_RAW = _literal_nodes(
    "Page2",
    (
        (
            "10000000-0000-5000-8000-00000000000e",
            _NATIVE_IDS[6],
            "Root2v0 [[Alias1A]]",
            ("Alias1A",),
        ),
        ("10000000-0000-5000-8000-00000000000f", None, "Child2v0", ()),
        ("10000000-0000-5000-8000-000000000010", _NATIVE_IDS[8], "Tail2", ()),
    ),
)


def _literal_observation(
    pages: tuple[tuple[str, str], ...],
    nodes: tuple[ObservedNode, ...],
    routes: dict[str, str],
    backlinks: dict[str, tuple[tuple[str, tuple[int, ...]], ...]],
) -> LifecycleObservation:
    """Complete an explicit observation table, with absent probes defaulting empty."""
    return LifecycleObservation(
        graph_root_matches=True,
        pages=tuple(
            ObservedPage(title, title, f"pages/{title}.md", True, (("alias", alias),), ("alias",))
            for title, alias in pages
        ),
        page_keys=tuple(name for title, alias in pages for name in (title, alias)),
        page_routes=tuple((query, routes.get(query)) for query in _PAGE_PROBES),
        nodes=nodes,
        attached_slots=tuple(node.slot for node in nodes),
        registry=tuple((node.parser_uuid, node.slot) for node in nodes),
        native_lookups=tuple(
            (native, next((node.slot for node in nodes if node.source_uuid == native), None))
            for native in _NATIVE_IDS
        ),
        backlinks=tuple((query, backlinks.get(query.lower(), ())) for query in _BACKLINK_PROBES),
        object_identity_valid=True,
    )


INITIAL_OBSERVATION = _literal_observation(
    (("Page0", "Alias0A"), ("Page1", "Alias1A")),
    (*_P0_RAW, *_P1_RAW),
    {
        "Page0": "Page0",
        "PAGE0": "Page0",
        "Alias0A": "Page0",
        "Page1": "Page1",
        "PAGE1": "Page1",
        "Alias1A": "Page1",
    },
    {
        "page0": (("Page1", (1,)),),
        "alias0a": (("Page1", (1,)),),
        "page1": (("Page0", (1,)), ("Page0", (2,))),
        "alias1a": (("Page0", (1,)), ("Page0", (2,))),
    },
)
ALIAS_OBSERVATION = _literal_observation(
    (("Page0", "Alias0A"), ("Page1", "Alias1B"), ("Page2", "Alias2A")),
    (*_P0_EDITED, *_P1_RAW, *_P2_RAW),
    {
        "Page0": "Page0",
        "PAGE0": "Page0",
        "Alias0A": "Page0",
        "Page1": "Page1",
        "PAGE1": "Page1",
        "Alias1B": "Page1",
        "Page2": "Page2",
        "PAGE2": "Page2",
        "Alias2A": "Page2",
    },
    {
        "page0": (("Page1", (1,)),),
        "alias0a": (("Page1", (1,)),),
        "alias1a": (("Page0", (1,)), ("Page2", (1,))),
        "page1": (("Page0", (2,)),),
        "alias1b": (("Page0", (2,)),),
    },
)
DELETED_OBSERVATION = _literal_observation(
    (("Page0", "Alias0A"), ("Page2", "Alias2A")),
    (*_P0_LINKED, *_P2_RAW),
    {
        "Page0": "Page0",
        "PAGE0": "Page0",
        "Alias0A": "Page0",
        "Page2": "Page2",
        "PAGE2": "Page2",
        "Alias2A": "Page2",
    },
    {
        "alias1b": (("Page0", (1,)),),
        "alias1a": (("Page2", (1,)),),
        "page2": (("Page0", (2,)),),
        "alias2a": (("Page0", (2,)),),
    },
)
RESTORED_OBSERVATION = _literal_observation(
    (("Page0", "Alias0A"), ("Moved1", "Alias1B"), ("Page2", "Alias2A")),
    (*_P0_LINKED, *_P1_MOVED, *_P2_RAW),
    {
        "Page0": "Page0",
        "PAGE0": "Page0",
        "Alias0A": "Page0",
        "Moved1": "Moved1",
        "MOVED1": "Moved1",
        "Alias1B": "Moved1",
        "Page2": "Page2",
        "PAGE2": "Page2",
        "Alias2A": "Page2",
    },
    {
        "page0": (("Moved1", (1,)),),
        "alias0a": (("Moved1", (1,)),),
        "moved1": (("Page0", (1,)),),
        "alias1b": (("Page0", (1,)),),
        "alias1a": (("Page2", (1,)),),
        "page2": (("Page0", (2,)),),
        "alias2a": (("Page0", (2,)),),
    },
)
BASELINES = (
    (INITIAL, INITIAL_OBSERVATION),
    (L1_STATES[3], ALIAS_OBSERVATION),
    (L1_STATES[6], DELETED_OBSERVATION),
    (L1_STATES[7], RESTORED_OBSERVATION),
)


def test_lifecycle_recipe_bounds_and_preconditions() -> None:
    validate_trace(L1)
    validate_trace(L2)
    validate_images(tuple(replace(x, present=False) for x in INITIAL))
    validate_images((P0, P1, P2_CREATED, replace(P3, present=True, ever_created=True)))
    for trace in (
        replace(L1, actions=L1.actions + (Action("edit", 0),)),
        replace(L1, actions=(Action("create", 0),)),
        replace(L1, actions=(Action("restore", 2),)),
        replace(L1, actions=(Action("alias", 1, "A"),)),
        replace(L1, actions=(Action("edit", True),)),
        replace(
            L1, actions=(Action("links", 0, root_links=P0.root_links, tail_links=P0.tail_links),)
        ),
    ):
        with pytest.raises(ValueError):
            validate_trace(trace)


@pytest.mark.parametrize(
    ("trace", "states", "rename_index"), ((L1, L1_STATES, 4), (L2, L2_STATES, 6))
)
def test_lifecycle_transitions_match_handwritten_timelines(
    trace: Trace, states: tuple[tuple[PageImage, ...], ...], rename_index: int
) -> None:
    actual = trace.initial
    assert actual == states[0]
    for index, action in enumerate(trace.actions):
        actual = apply_action(actual, action)
        assert actual == states[index + 1]
        if index == rename_index:
            intermediate = tuple(
                replace(page, present=False) if page.page_id == 1 else page for page in actual
            )
            assert intermediate == RENAME_INTERMEDIATE


def test_lifecycle_renderer_matches_literal_seven_lines() -> None:
    literal = (
        "alias:: Alias0A\n\n- Root0v0 [[Alias1A]] [[Alias1A]]\n"
        "  id:: 00000000-0000-4000-8000-000000000001\n  - Child0v0\n"
        "- Tail0 [[Page1]]\n  id:: 00000000-0000-4000-8000-000000000003\n"
    )
    assert render_sources(INITIAL, "LF")["pages/Page0.md"] == literal
    assert render_sources(INITIAL, "CRLF")["pages/Page0.md"] == literal.replace("\n", "\r\n")


@pytest.mark.parametrize(("images", "observation"), BASELINES)
def test_lifecycle_oracle_accepts_handwritten_observations(
    images: tuple[PageImage, ...], observation: LifecycleObservation
) -> None:
    assert_observation(observation, images)


@pytest.mark.parametrize(
    ("fault", "message"),
    (
        ("alias_owner", "lifecycle.alias_ownership"),
        ("extra_alias", "lifecycle.page_keys"),
        ("stale_content", "lifecycle.node_content"),
        ("stale_native", "lifecycle.native_identity"),
        ("ghost_registry", "lifecycle.registry_membership"),
        ("wrong_backlink", "lifecycle.backlink_sources"),
        ("duplicate_backlink", "lifecycle.backlink_unique"),
        ("detached_backlink", "lifecycle.object_identity"),
    ),
)
def test_lifecycle_oracle_rejects_selected_observation_fault(fault: str, message: str) -> None:
    images, correct = (
        BASELINES[1] if fault in ("extra_alias", "stale_content", "stale_native") else BASELINES[0]
    )
    assert_observation(correct, images)
    if fault == "alias_owner":
        corrupted = replace(
            correct,
            page_routes=tuple(
                (q, "Page1" if q == "Alias0A" else owner) for q, owner in correct.page_routes
            ),
        )
    elif fault == "extra_alias":
        corrupted = replace(correct, page_keys=(*correct.page_keys, "Alias1A"))
    elif fault == "stale_content":
        corrupted = replace(
            correct,
            nodes=(
                replace(correct.nodes[0], content="Root0v0 [[Alias1A]] [[Alias1A]]"),
                *correct.nodes[1:],
            ),
        )
    elif fault == "stale_native":
        corrupted = replace(
            correct,
            nodes=(replace(correct.nodes[0], source_uuid=_NATIVE_IDS[0]), *correct.nodes[1:]),
        )
    elif fault == "ghost_registry":
        corrupted = replace(
            correct, registry=(*correct.registry, ("20000000-0000-5000-8000-000000000001", None))
        )
    elif fault == "wrong_backlink":
        corrupted = replace(
            correct,
            backlinks=tuple(
                (q, (("Page0", (1,)),) if q == "Page0" else slots) for q, slots in correct.backlinks
            ),
        )
    elif fault == "duplicate_backlink":
        corrupted = replace(
            correct,
            backlinks=tuple(
                (q, (*slots, slots[0]) if q == "Page1" else slots) for q, slots in correct.backlinks
            ),
        )
    else:
        corrupted = replace(correct, object_identity_valid=False)
    with pytest.raises(AssertionError) as failure:
        assert_observation(corrupted, images)
    assert str(failure.value) == message


@pytest.mark.parametrize(
    "fault",
    (
        "missing_path",
        "wrong_page_path",
        "wrong_node_path",
        "wrong_page_root",
        "wrong_graph_root",
        "wrong_tree_owner",
    ),
)
def test_lifecycle_oracle_rejects_source_ownership_fault(fault: str) -> None:
    correct = INITIAL_OBSERVATION
    assert_observation(correct, INITIAL)
    if fault == "missing_path":
        corrupted = replace(
            correct,
            pages=(replace(correct.pages[0], relative_source_path=None), *correct.pages[1:]),
        )
    elif fault == "wrong_page_path":
        corrupted = replace(
            correct,
            pages=(
                replace(correct.pages[0], relative_source_path="pages/Page1.md"),
                *correct.pages[1:],
            ),
        )
    elif fault == "wrong_node_path":
        corrupted = replace(
            correct,
            nodes=(
                replace(correct.nodes[0], relative_source_path="pages/Page1.md"),
                *correct.nodes[1:],
            ),
        )
    elif fault == "wrong_page_root":
        corrupted = replace(
            correct, pages=(replace(correct.pages[0], graph_root_matches=False), *correct.pages[1:])
        )
    elif fault == "wrong_graph_root":
        corrupted = replace(correct, graph_root_matches=False)
    else:
        corrupted = replace(
            correct,
            nodes=(replace(correct.nodes[0], routed_owner_title="Page1"), *correct.nodes[1:]),
            object_identity_valid=False,
        )
    with pytest.raises(AssertionError) as failure:
        assert_observation(corrupted, INITIAL)
    assert str(failure.value) == (
        "lifecycle.object_identity" if fault == "wrong_tree_owner" else "lifecycle.source_ownership"
    )


def test_lifecycle_path_capture_does_not_accept_an_outside_basename(tmp_path: Path) -> None:
    root = tmp_path / "owned"
    (root / "pages").mkdir(parents=True)
    selected = root / "pages" / "Page0.md"
    selected.write_text("synthetic sentinel", encoding="utf-8")
    other = tmp_path / "other" / "pages" / "Page0.md"
    other.parent.mkdir(parents=True)
    other.write_text("synthetic sentinel", encoding="utf-8")
    assert relative_owned_path(str(selected), root) == "pages/Page0.md"
    assert relative_owned_path(str(other), root) is None
    assert relative_owned_path(None, root) is None
    assert relative_owned_path(str(root / "pages" / "missing.md"), root) is None


def test_lifecycle_replay_roundtrip_and_source_digest() -> None:
    assert decode_trace(encode_trace(L1)) == L1
    assert decode_trace(encode_trace(L2)) == L2
    timeline = source_digest_timeline(L1)
    assert len(timeline) == 9
    assert timeline[5] != timeline[4]
    assert timeline[5] != timeline[6]
    assert timeline[5] == timeline[7]
    assert "pages/Moved1.md" in render_sources(L1_STATES[5], "LF")
    assert "pages/Page1.md" not in render_sources(L1_STATES[5], "LF")


@pytest.mark.parametrize(
    "fault",
    (
        "unknown",
        "duplicate_field",
        "nan",
        "infinity",
        "exponent_overflow",
        "float",
        "boolean_id",
        "extra_action_argument",
        "create_present",
        "restore_never",
        "rename_twice",
        "ninth_action",
        "expanded_bounds",
        "traversal_token",
        "uppercase_alias",
        "alias_override",
        "native_override",
        "wrong_digest",
        "wrong_hash",
        "oversize",
        "invalid_initial",
    ),
)
def test_lifecycle_replay_rejects_invalid_payload(fault: str) -> None:
    serialized = encode_trace(L1)
    payload = json.loads(serialized)
    if fault == "unknown":
        payload["unrecognized"] = True
    elif fault == "duplicate_field":
        serialized = '{"schema_version":1,' + serialized[1:]
    elif fault in ("nan", "infinity", "exponent_overflow", "float"):
        token = {
            "nan": "NaN",
            "infinity": "Infinity",
            "exponent_overflow": "1e9999",
            "float": "1.0",
        }[fault]
        serialized = serialized.replace('"schema_version":1', '"schema_version":' + token)
    elif fault == "boolean_id":
        payload["actions"][0]["page_id"] = True
    elif fault == "extra_action_argument":
        payload["actions"][0]["alias_variant"] = "B"
    elif fault == "create_present":
        payload["actions"][0]["page_id"] = 0
    elif fault == "restore_never":
        payload["actions"][0]["kind"] = "restore"
    elif fault == "rename_twice":
        payload["actions"][5]["kind"] = "rename"
    elif fault == "ninth_action":
        payload["actions"].append(payload["actions"][1])
    elif fault == "expanded_bounds":
        payload["bounds"]["max_actions"] = 9
    elif fault in ("traversal_token", "uppercase_alias"):
        payload["actions"][3]["root_links"] = [
            "../outside" if fault == "traversal_token" else "ALIAS1B"
        ]
    elif fault in ("alias_override", "native_override"):
        payload["initial"][0]["aliases" if fault == "alias_override" else "native_uuid"] = (
            "duplicate"
        )
    elif fault == "wrong_digest":
        payload["source_digest_timeline"][5] = "0" * 64
    elif fault == "wrong_hash":
        payload["helper_sha256"] = "0" * 64
    elif fault == "oversize":
        serialized += " " * (16 * 1024)
    else:
        payload["initial"][0]["present"] = False
    if fault not in (
        "duplicate_field",
        "nan",
        "infinity",
        "exponent_overflow",
        "float",
        "oversize",
    ):
        serialized = json.dumps(payload)
    with pytest.raises(ValueError):
        decode_trace(serialized)


def test_lifecycle_evaluation_guard_rejects_before_work() -> None:
    calls: list[int] = []

    def callback() -> None:
        calls.append(1)

    guard = EvaluationGuard()
    for _ in range(24):
        guard.run(callback)
    with pytest.raises(RuntimeError, match="^lifecycle.evaluation_budget$"):
        guard.run(callback)
    assert len(calls) == 24


@pytest.mark.parametrize(
    "stage",
    (
        "trace_recipe_admission",
        "temporary_directory_admission",
        "trace_admission",
        "temporary_directory_cleanup",
    ),
)
def test_harness_evidence_captures_failure_without_graph_work(stage: str) -> None:
    evidence = InvocationEvidence()
    evidence.stage = stage
    evidence.replay = encode_trace(L1)

    def fail() -> None:
        raise RuntimeError("synthetic harness failure")

    with pytest.raises(RuntimeError, match="^synthetic harness failure$"):
        evidence.run(fail)
    counts = json.loads(evidence.counts())
    assert counts["first_failure_kind"] == "harness"
    assert counts["first_failure"] == {
        "stage": stage,
        "failure_type": "RuntimeError",
        "replay": evidence.replay,
    }
    assert counts["source_bindings"]["baseline_revision"] == (
        "de03c154f55073e469a619728815bef7d83d6299"
    )
    assert all(
        counts[key] == 0
        for key in (
            "trace_evaluations",
            "actions",
            "reloads",
            "directory_loads",
            "accounted_page_parses",
            "observed_stages",
        )
    )


def test_harness_evidence_records_budget_refusal_without_callback() -> None:
    evidence = InvocationEvidence()
    evidence.stage = "evaluation_admission"
    evidence.replay = encode_trace(L1)
    guard = EvaluationGuard()
    calls: list[int] = []

    def callback() -> None:
        calls.append(1)

    for _ in range(24):
        guard.run(callback)

    def refused() -> None:
        guard.run(callback)

    with pytest.raises(RuntimeError, match="^lifecycle.evaluation_budget$"):
        evidence.run(refused)
    counts = json.loads(evidence.counts())
    assert len(calls) == guard.evaluations == 24
    assert counts["trace_evaluations"] == 0
    assert counts["first_failure_kind"] == "harness"
    assert counts["first_failure"]["stage"] == "evaluation_admission"
    assert counts["first_failure"]["failure_type"] == "RuntimeError"


def test_harness_evidence_retains_first_failure_across_later_callbacks() -> None:
    evidence = InvocationEvidence()
    evidence.stage = "temporary_directory_cleanup"
    evidence.replay = encode_trace(L1)

    def fail() -> None:
        raise RuntimeError("first failure")

    with pytest.raises(RuntimeError, match="^first failure$"):
        evidence.run(fail)
    first = json.loads(evidence.counts())["first_failure"]
    evidence.stage = "trace_admission"
    evidence.replay = encode_trace(L2)

    def succeed() -> None:
        return None

    evidence.run(succeed)

    def fail_again() -> None:
        raise ValueError("later synthetic confirmation failure")

    with pytest.raises(ValueError, match="^later synthetic confirmation failure$"):
        evidence.run(fail_again)
    counts = json.loads(evidence.counts())
    assert counts["first_failure_kind"] == "harness"
    assert counts["first_failure"] == first
    assert counts["trace_evaluations"] == 0


def test_harness_evidence_retains_graph_failure_when_cleanup_also_fails() -> None:
    evidence = InvocationEvidence()
    replay = encode_trace(L1)
    graph_failure = TraceRun(
        replay,
        action_index=2,
        stage="incremental_model",
        status="failed",
        failure_type="AssertionError",
    )

    def graph_then_cleanup_fail() -> None:
        # A handwritten accounting record calibrates provenance without a graph.
        _TRACE_RUNS.append(graph_failure)
        evidence.stage = "temporary_directory_cleanup"
        raise OSError("synthetic cleanup failure")

    with pytest.raises(OSError, match="^synthetic cleanup failure$"):
        evidence.run(graph_then_cleanup_fail)
    first = json.loads(evidence.counts())["first_failure"]
    assert first == asdict(graph_failure)
    graph_failure.stage = "later mutation must not rewrite preserved evidence"
    evidence.stage = "evaluation_admission"

    def later_failure() -> None:
        raise RuntimeError("later synthetic refusal")

    with pytest.raises(RuntimeError, match="^later synthetic refusal$"):
        evidence.run(later_failure)
    counts = json.loads(evidence.counts())
    assert counts["first_failure_kind"] == "graph_trace"
    assert counts["first_failure"] == first
    assert counts["trace_evaluations"] == 1
    assert counts["actions"] == counts["reloads"] == counts["directory_loads"] == 0


def test_harness_evidence_retains_admission_failure_when_cleanup_also_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence = InvocationEvidence()
    evidence.replay = encode_trace(L1)

    @contextmanager
    def cleanup_failure(*, prefix: str) -> Iterator[str]:
        assert prefix == "matryca-lifecycle-"
        try:
            yield "synthetic-owned-directory"
        finally:
            raise OSError("later synthetic cleanup failure")

    def admission_failure(trace: Trace, graph_root: Path) -> None:
        assert trace == L1
        assert graph_root == Path("synthetic-owned-directory") / "graph"
        raise ValueError("earlier synthetic admission failure")

    # Replace only test-local work and the directory context. No directory is
    # created, real cleanup attempted, or production parser/graph invoked.
    monkeypatch.setattr(tempfile, "TemporaryDirectory", cleanup_failure)
    monkeypatch.setattr(sys.modules[__name__], "run_trace", admission_failure)

    def execute() -> None:
        _run_owned_trace(L1, evidence)

    with pytest.raises(OSError, match="^later synthetic cleanup failure$"):
        evidence.run(execute)
    counts = json.loads(evidence.counts())
    assert counts["first_failure_kind"] == "harness"
    assert counts["first_failure"] == {
        "stage": "trace_admission",
        "failure_type": "ValueError",
        "replay": evidence.replay,
    }
    assert all(
        counts[key] == 0
        for key in (
            "trace_evaluations",
            "actions",
            "reloads",
            "directory_loads",
            "accounted_page_parses",
            "observed_stages",
        )
    )


@dataclass
class TraceRun:
    """Source-level operation accounting, not instrumented parser telemetry."""

    replay: str
    actions: int = 0
    reloads: int = 0
    directory_loads: int = 0
    accounted_page_parses: int = 0
    observed_stages: int = 0
    action_index: int | None = None
    stage: str = "admission"
    status: str = "running"
    failure_type: str | None = None
    elapsed_seconds: float = 0.0


# A pytest process owns this append-only in-memory evidence. Confirmations append;
# they cannot overwrite the earliest failure or reset the property's guard.
_TRACE_RUNS: list[TraceRun] = []


@dataclass(frozen=True)
class HarnessFailure:
    """A source-safe outer failure, never a fabricated graph evaluation."""

    stage: str
    failure_type: str
    replay: str | None


class InvocationEvidence:
    """Retain the first graph or outer-harness failure across confirmations."""

    def __init__(self) -> None:
        self.start = len(_TRACE_RUNS)
        self.stage = "harness_admission"
        self.replay: str | None = None
        self.first_failure: TraceRun | HarnessFailure | None = None

    def run(self, callback: Callable[[], None]) -> None:
        start = len(_TRACE_RUNS)
        try:
            callback()
        except BaseException as failure:
            if self.first_failure is None:
                graph_failure = next(
                    (run for run in _TRACE_RUNS[start:] if run.status != "pass"), None
                )
                # The inner trace failed before cleanup; preserve its finalized
                # stage/accounting even if cleanup raised a different exception.
                self.first_failure = (
                    replace(graph_failure)
                    if graph_failure is not None
                    else HarnessFailure(self.stage, type(failure).__name__, self.replay)
                )
            raise

    def counts(self) -> str:
        return _trace_counts(self.start, self.first_failure)


def _trace_counts(start: int, first_failure: TraceRun | HarnessFailure | None = None) -> str:
    runs = _TRACE_RUNS[start:]
    failures = [run for run in runs if run.status != "pass"]
    if first_failure is None and failures:
        first_failure = failures[0]
    replay = runs[0].replay if runs else first_failure.replay if first_failure else None
    metadata = json.loads(replay) if replay is not None else {}
    return json.dumps(
        {
            "source_bindings": {
                key: metadata[key]
                for key in ("baseline_revision", "helper_sha256", "test_sha256", "lock_sha256")
                if key in metadata
            },
            "trace_evaluations": len(runs),
            "actions": sum(run.actions for run in runs),
            "reloads": sum(run.reloads for run in runs),
            "directory_loads": sum(run.directory_loads for run in runs),
            "accounted_page_parses": sum(run.accounted_page_parses for run in runs),
            "observed_stages": sum(run.observed_stages for run in runs),
            "elapsed_seconds": sum(run.elapsed_seconds for run in runs),
            "first_failure_kind": (
                "harness"
                if isinstance(first_failure, HarnessFailure)
                else "graph_trace"
                if first_failure is not None
                else None
            ),
            "first_failure": asdict(first_failure) if first_failure is not None else None,
        },
        sort_keys=True,
    )


def _assert_history(graph: LogseqGraph, observed: LifecycleObservation, history: set[str]) -> None:
    current = {node.parser_uuid for node in observed.nodes}
    assert all(graph.get_node_by_uuid(previous) is None for previous in history - current), (
        "lifecycle.historical_identity"
    )
    history.update(current)


def run_trace(trace: Trace, graph_root: Path) -> None:
    """Execute only admitted finite sources under one newly owned root."""
    replay = encode_trace(trace)
    assert decode_trace(replay) == trace
    assert graph_root.is_absolute() and not graph_root.exists(), "lifecycle.fresh_root"
    result = TraceRun(replay)
    _TRACE_RUNS.append(result)
    started = time.monotonic()
    images = trace.initial
    history: set[str] = set()
    timeline = source_digest_timeline(trace)

    def observed_stage(
        graph: LogseqGraph, expected: tuple[PageImage, ...], stage: str
    ) -> LifecycleObservation:
        result.stage = stage
        result.observed_stages += 1
        observation = observe_graph(graph, graph_root)
        assert_observation(observation, expected)
        _assert_history(graph, observation, history)
        return observation

    def load(expected: tuple[PageImage, ...]) -> LogseqGraph:
        result.directory_loads += 1
        result.accounted_page_parses += sum(page.present for page in expected)
        assert result.directory_loads <= 9 and result.accounted_page_parses <= 44, (
            "lifecycle.operation_budget"
        )
        return LogseqGraph.load_directory(graph_root)

    def reload(graph: LogseqGraph, path: Path) -> None:
        result.reloads += 1
        result.accounted_page_parses += int(path.is_file())
        assert result.reloads <= 16 and result.accounted_page_parses <= 44, (
            "lifecycle.operation_budget"
        )
        graph.invalidate_and_reload_page(path)

    def assert_disk(expected: tuple[PageImage, ...], digest: str) -> None:
        sources = render_sources(expected, trace.newline)
        assert sorted(path.name for path in (graph_root / "pages").iterdir()) == sorted(
            Path(path).name for path in sources
        ), "lifecycle.disk_membership"
        actual = {path: (graph_root / path).read_bytes().decode("utf-8") for path in sources}
        assert actual == sources and source_digest(actual) == digest, "lifecycle.source_digest"

    try:
        (graph_root / "pages").mkdir(parents=True, exist_ok=False)
        for relative, source in render_sources(images, trace.newline).items():
            (graph_root / relative).write_bytes(source.encode("utf-8"))
        assert_disk(images, timeline[0])
        result.stage = "initial_load"
        graph = load(images)
        observed_stage(graph, images, "initial_model")
        for index, action in enumerate(trace.actions):
            result.action_index = index
            result.actions += 1
            before = images[action.page_id]
            images = apply_action(images, action)
            after = images[action.page_id]
            previous_path = graph_root / "pages" / f"{before.title}.md"
            current_path = graph_root / "pages" / f"{after.title}.md"
            result.stage = "source_change"
            if action.kind == "rename":
                assert not current_path.exists(), "lifecycle.rename_destination"
                previous_path.rename(current_path)
            elif action.kind == "delete":
                previous_path.unlink()
            else:
                source = render_sources(images, trace.newline)[f"pages/{after.title}.md"]
                current_path.write_bytes(source.encode("utf-8"))
            assert_disk(images, timeline[index + 1])
            if action.kind == "rename":
                result.stage = "rename_old_reload"
                reload(graph, previous_path)
                intermediate = tuple(
                    replace(page, present=False) if page.page_id == action.page_id else page
                    for page in images
                )
                observed_stage(graph, intermediate, "rename_old_purged_model")
                # Both graph stages share the completed filesystem rename digest.
                assert_disk(images, timeline[index + 1])
            result.stage = "current_reload"
            reload(graph, current_path)
            observed_stage(graph, images, "incremental_model")
            result.stage = "cold_load"
            cold = load(images)
            observed_stage(cold, images, "cold_model")
            result.stage = "exact_cold_parity"
            incremental_pages = {
                page.title: project_page(page, profile="exact_parse_v1")
                for page in graph.iter_canonical_pages()
            }
            cold_pages = {
                page.title: project_page(page, profile="exact_parse_v1")
                for page in cold.iter_canonical_pages()
            }
            assert incremental_pages == cold_pages, "lifecycle.cold_parity"
            # Recheck returned current objects, never cross-graph object identity.
            for page in graph.iter_canonical_pages():
                assert all(
                    graph.get_node_by_uuid(node.uuid) is node
                    for node in walk_nodes(page.root_nodes)
                ), "lifecycle.object_identity"
        result.status = "pass"
    except BaseException as failure:
        result.status = "failed"
        result.failure_type = type(failure).__name__
        raise
    finally:
        result.elapsed_seconds = time.monotonic() - started


@pytest.mark.parametrize(
    "trace", (L1, L2), ids=("alias-before-links-LF", "links-before-alias-CRLF")
)
def test_fixed_lifecycle_trace_matches_model_before_cold_graph(
    trace: Trace,
    tmp_path: Path,
    record_property: Callable[[str, object], None],
) -> None:
    evidence = InvocationEvidence()

    def admitted() -> None:
        evidence.stage = "trace_recipe_admission"
        evidence.replay = encode_trace(trace)
        evidence.stage = "trace_admission"
        run_trace(trace, tmp_path / "graph")

    try:
        evidence.run(admitted)
    finally:
        record_property("lifecycle_counts", evidence.counts())


def _run_owned_trace(trace: Trace, evidence: InvocationEvidence) -> None:
    evidence.stage = "temporary_directory_admission"
    with tempfile.TemporaryDirectory(prefix="matryca-lifecycle-") as directory:

        def admitted() -> None:
            evidence.stage = "trace_admission"
            run_trace(trace, Path(directory) / "graph")

        # Capture admission before context exit can replace its exception.
        evidence.run(admitted)
        evidence.stage = "temporary_directory_cleanup"


def test_generated_lifecycle_traces_match_independent_model(
    record_property: Callable[[str, object], None],
) -> None:
    guard = EvaluationGuard()
    evidence = InvocationEvidence()

    @settings(
        max_examples=16,
        derandomize=True,
        database=None,
        deadline=None,
        print_blob=True,
        phases=(Phase.generate,),
        report_multiple_bugs=False,
        suppress_health_check=(),
    )
    @given(lifecycle_traces())
    def exercise(trace: Trace) -> None:
        def bounded_body() -> None:
            evidence.stage = "trace_recipe_admission"
            evidence.replay = None
            evidence.replay = encode_trace(trace)
            note(evidence.replay)
            evidence.stage = "evaluation_admission"

            def admitted() -> None:
                _run_owned_trace(trace, evidence)

            guard.run(admitted)
            evidence.stage = "hypothesis_execution"

        evidence.run(bounded_body)

    try:
        evidence.stage = "hypothesis_execution"
        evidence.run(exercise)
    finally:
        record_property("lifecycle_counts", evidence.counts())
        record_property("lifecycle_guard_admissions", guard.evaluations)
