"""Finite, test-only lifecycle model, source-safe replay and graph observation.

Expected facts come from authored images, never from a production parser or
indexing helper. Observation records retain duplicates and invalid sentinels.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Literal, cast
from uuid import UUID

from hypothesis import strategies as st

from logseq_matryca_parser import LogseqGraph
from logseq_matryca_parser.logos_core import LogseqNode
from tests.parser_assurance.invariants import assert_tree_invariants, walk_nodes

ActionKind = Literal["create", "edit", "alias", "links", "rename", "delete", "restore"]
AliasVariant = Literal["A", "B", "C"]
Newline = Literal["LF", "CRLF"]
Slot = tuple[str, tuple[int, ...]]

CANONICAL_NAMES = tuple(f"{prefix}{index}" for prefix in ("Page", "Moved") for index in range(4))
ALIASES = tuple(f"Alias{index}{variant}" for index in range(4) for variant in ("A", "B", "C"))
BASE_NAMES = (*CANONICAL_NAMES, *ALIASES, "Missing")
SOURCE_TOKENS = (*BASE_NAMES, *(name.upper() for name in CANONICAL_NAMES))
PAGE_PROBES = (*BASE_NAMES, *(name.upper() for name in (*CANONICAL_NAMES, "Missing")))
BACKLINK_PROBES = (*BASE_NAMES, *(name.upper() for name in BASE_NAMES))
NATIVE_IDS = (
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
BASELINE_REVISION = "de03c154f55073e469a619728815bef7d83d6299"
_KINDS: tuple[ActionKind, ...] = ("create", "edit", "alias", "links", "rename", "delete", "restore")
_REPLAY_CAP = 16 * 1024
_BOUNDS = {
    "page_count": 4,
    "max_actions": 8,
    "nodes_per_page": 3,
    "outline_depth": 1,
    "root_links": 3,
    "tail_links": 1,
    "file_bytes": 1024,
    "vault_bytes": 4096,
    "max_evaluations": 24,
    "max_reload_calls": 16,
    "max_directory_loads": 9,
    "max_accounted_page_parses": 44,
    "hypothesis": {
        "max_examples": 16,
        "derandomize": True,
        "database": None,
        "deadline": None,
        "print_blob": True,
        "phases": ["generate"],
        "report_multiple_bugs": False,
        "suppress_health_check": [],
    },
}


@dataclass(frozen=True)
class PageImage:
    page_id: int
    present: bool
    ever_created: bool
    renamed: bool
    revision: int
    alias_variant: AliasVariant
    root_links: tuple[str, ...]
    tail_links: tuple[str, ...]

    @property
    def title(self) -> str:
        return f"{'Moved' if self.renamed else 'Page'}{self.page_id}"

    @property
    def alias(self) -> str:
        return f"Alias{self.page_id}{self.alias_variant}"


@dataclass(frozen=True)
class Action:
    kind: ActionKind
    page_id: int
    alias_variant: AliasVariant | None = None
    root_links: tuple[str, ...] = ()
    tail_links: tuple[str, ...] = ()


@dataclass(frozen=True)
class Trace:
    initial: tuple[PageImage, ...]
    actions: tuple[Action, ...]
    newline: Newline


INITIAL_IMAGES = (
    PageImage(0, True, True, False, 0, "A", ("Alias1A", "Alias1A"), ("Page1",)),
    PageImage(1, True, True, False, 0, "A", ("Page0",), ()),
    PageImage(2, False, False, False, 0, "A", ("Alias1A",), ()),
    PageImage(3, False, False, False, 0, "A", ("Page0",), ()),
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _validate_links(root: tuple[str, ...], tail: tuple[str, ...]) -> None:
    _require(type(root) is tuple and type(tail) is tuple, "links must be tuples")
    _require(len(root) <= 3 and len(tail) <= 1, "link count exceeds recipe")
    _require(
        all(type(token) is str and token in SOURCE_TOKENS for token in (*root, *tail)),
        "invalid link token",
    )


def validate_images(images: tuple[PageImage, ...]) -> None:
    """Validate all four retained images, including absent and empty states."""
    _require(type(images) is tuple and len(images) == 4, "exactly four images required")
    for index, page in enumerate(images):
        _require(type(page) is PageImage, "invalid image type")
        _require(type(page.page_id) is int and page.page_id == index, "invalid authoring ID")
        _require(
            all(type(flag) is bool for flag in (page.present, page.ever_created, page.renamed)),
            "invalid image flags",
        )
        _require(not page.present or page.ever_created, "present image must have existed")
        _require(type(page.revision) is int and page.revision in (0, 1), "invalid revision")
        _require(
            type(page.alias_variant) is str and page.alias_variant in ("A", "B", "C"),
            "invalid alias variant",
        )
        _validate_links(page.root_links, page.tail_links)
        if not page.ever_created:
            _require(page == INITIAL_IMAGES[index], "never-created image changed")


def apply_action(images: tuple[PageImage, ...], action: Action) -> tuple[PageImage, ...]:
    """Reduce a legal action without consulting a graph or filesystem."""
    validate_images(images)
    _require(
        type(action) is Action and type(action.kind) is str and action.kind in _KINDS,
        "invalid action kind",
    )
    _require(type(action.page_id) is int and 0 <= action.page_id <= 3, "invalid action ID")
    _validate_links(action.root_links, action.tail_links)
    _require(action.kind == "alias" or action.alias_variant is None, "unused alias argument")
    _require(
        action.kind == "links" or not (action.root_links or action.tail_links),
        "unused link argument",
    )
    page = images[action.page_id]
    if action.kind == "create":
        _require(not page.ever_created, "create requires never-created image")
        updated = replace(page, present=True, ever_created=True)
    elif action.kind == "restore":
        _require(page.ever_created and not page.present, "restore requires absent previous image")
        updated = replace(page, present=True)
    else:
        _require(page.present, "action requires present image")
        if action.kind == "edit":
            updated = replace(page, revision=1 - page.revision)
        elif action.kind == "alias":
            _require(
                type(action.alias_variant) is str and action.alias_variant in ("A", "B", "C"),
                "invalid alias action",
            )
            _require(action.alias_variant != page.alias_variant, "alias action must change")
            updated = replace(page, alias_variant=cast(AliasVariant, action.alias_variant))
        elif action.kind == "links":
            _require(
                (action.root_links, action.tail_links) != (page.root_links, page.tail_links),
                "links action must change",
            )
            updated = replace(page, root_links=action.root_links, tail_links=action.tail_links)
        elif action.kind == "rename":
            _require(not page.renamed, "rename is allowed only once")
            updated = replace(page, renamed=True)
        else:
            updated = replace(page, present=False)
    result = tuple(
        updated if index == action.page_id else image for index, image in enumerate(images)
    )
    validate_images(result)
    return result


def validate_trace(trace: Trace) -> None:
    _require(type(trace) is Trace, "invalid trace type")
    validate_images(trace.initial)
    _require(trace.initial == INITIAL_IMAGES, "initial images must match recipe")
    _require(type(trace.newline) is str and trace.newline in ("LF", "CRLF"), "invalid newline")
    _require(type(trace.actions) is tuple and 1 <= len(trace.actions) <= 8, "invalid action count")
    current = trace.initial
    render_sources(current, trace.newline)
    for action in trace.actions:
        current = apply_action(current, action)
        render_sources(current, trace.newline)


def render_sources(images: tuple[PageImage, ...], newline: Newline) -> dict[str, str]:
    """Render only the selected seven-line ASCII grammar."""
    validate_images(images)
    _require(newline in ("LF", "CRLF"), "invalid newline")
    separator = "\n" if newline == "LF" else "\r\n"
    result: dict[str, str] = {}
    for page in images:
        if not page.present:
            continue
        root = f"Root{page.page_id}v{page.revision}" + "".join(
            f" [[{token}]]" for token in page.root_links
        )
        tail = f"Tail{page.page_id}" + "".join(f" [[{token}]]" for token in page.tail_links)
        lines = (
            f"alias:: {page.alias}",
            "",
            f"- {root}",
            f"  id:: {NATIVE_IDS[3 * page.page_id + page.revision]}",
            f"  - Child{page.page_id}v{page.revision}",
            f"- {tail}",
            f"  id:: {NATIVE_IDS[3 * page.page_id + 2]}",
        )
        source = separator.join(lines) + separator
        _require(len(source.encode("utf-8")) <= 1024, "file byte budget")
        result[f"pages/{page.title}.md"] = source
    _require(
        sum(len(source.encode("utf-8")) for source in result.values()) <= 4096, "vault byte budget"
    )
    return result


def source_digest(sources: dict[str, str]) -> str:
    """Bind paths and source bytes unambiguously, including an empty source map."""
    digest = hashlib.sha256()
    for path, source in sorted(sources.items()):
        path_bytes, source_bytes = path.encode("ascii"), source.encode("utf-8")
        digest.update(len(path_bytes).to_bytes(4, "big"))
        digest.update(path_bytes)
        digest.update(len(source_bytes).to_bytes(8, "big"))
        digest.update(source_bytes)
    return digest.hexdigest()


def source_digest_timeline(trace: Trace) -> tuple[str, ...]:
    validate_trace(trace)
    images = trace.initial
    timeline = [source_digest(render_sources(images, trace.newline))]
    for action in trace.actions:
        images = apply_action(images, action)
        timeline.append(source_digest(render_sources(images, trace.newline)))
    return tuple(timeline)


def _producer_hashes() -> dict[str, str]:
    root = Path(__file__).resolve().parents[2]
    return {
        "helper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "test_sha256": hashlib.sha256(
            (root / "tests/test_graph_lifecycle_properties.py").read_bytes()
        ).hexdigest(),
        "lock_sha256": hashlib.sha256((root / "uv.lock").read_bytes()).hexdigest(),
    }


def encode_trace(trace: Trace) -> str:
    """Encode finite authoring metadata, not source text or environment paths."""
    validate_trace(trace)
    payload = {
        "schema_version": 1,
        "recipe": "ascii-page-lifecycle-v1",
        "baseline_revision": BASELINE_REVISION,
        **_producer_hashes(),
        "bounds": _BOUNDS,
        "initial": [asdict(page) for page in trace.initial],
        "actions": [asdict(action) for action in trace.actions],
        "newline": trace.newline,
        "source_digest_timeline": source_digest_timeline(trace),
    }
    serialized = json.dumps(payload, allow_nan=False, sort_keys=True, separators=(",", ":"))
    _require(len(serialized.encode("utf-8")) <= _REPLAY_CAP, "replay byte budget")
    return serialized


def _reject_float(token: str) -> None:
    raise ValueError(f"float or nonfinite token forbidden: {token}")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        _require(key not in result, "duplicate JSON field")
        result[key] = value
    return result


def _object(value: object, keys: set[str]) -> dict[str, object]:
    _require(type(value) is dict, "JSON object required")
    result = cast(dict[str, object], value)
    _require(set(result) == keys, "unknown or missing JSON fields")
    return result


def _list(value: object) -> list[object]:
    _require(type(value) is list, "JSON list required")
    return cast(list[object], value)


def _tokens(value: object) -> tuple[str, ...]:
    items = _list(value)
    _require(all(type(item) is str for item in items), "string tokens required")
    return tuple(cast(str, item) for item in items)


def _same_json_types(actual: object, expected: object) -> bool:
    """Equality alone would admit bool-as-int in immutable profile fields."""
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            return False
        return all(_same_json_types(actual[key], value) for key, value in expected.items())
    if isinstance(expected, list):
        return (
            isinstance(actual, list)
            and len(actual) == len(expected)
            and all(
                _same_json_types(left, right) for left, right in zip(actual, expected, strict=True)
            )
        )
    return bool(actual == expected)


def decode_trace(serialized: str) -> Trace:
    """Admit the complete finite recipe and bindings before any source writes."""
    _require(
        type(serialized) is str and len(serialized.encode("utf-8")) <= _REPLAY_CAP,
        "replay byte budget",
    )
    try:
        value: object = json.loads(
            serialized,
            parse_float=_reject_float,
            parse_constant=_reject_float,
            object_pairs_hook=_unique_object,
        )
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("invalid replay JSON") from exc
    hashes = _producer_hashes()
    payload = _object(
        value,
        {
            "schema_version",
            "recipe",
            "baseline_revision",
            *hashes,
            "bounds",
            "initial",
            "actions",
            "newline",
            "source_digest_timeline",
        },
    )
    _require(
        type(payload["schema_version"]) is int and payload["schema_version"] == 1, "schema mismatch"
    )
    _require(
        payload["recipe"] == "ascii-page-lifecycle-v1"
        and payload["baseline_revision"] == BASELINE_REVISION,
        "recipe identity mismatch",
    )
    _require(
        all(payload[key] == digest for key, digest in hashes.items()), "producer hash mismatch"
    )
    _require(_same_json_types(payload["bounds"], _BOUNDS), "profile bounds mismatch")
    images = []
    for item in _list(payload["initial"]):
        page = _object(
            item,
            {
                "page_id",
                "present",
                "ever_created",
                "renamed",
                "revision",
                "alias_variant",
                "root_links",
                "tail_links",
            },
        )
        images.append(
            PageImage(
                cast(int, page["page_id"]),
                cast(bool, page["present"]),
                cast(bool, page["ever_created"]),
                cast(bool, page["renamed"]),
                cast(int, page["revision"]),
                cast(AliasVariant, page["alias_variant"]),
                _tokens(page["root_links"]),
                _tokens(page["tail_links"]),
            )
        )
    actions = []
    for item in _list(payload["actions"]):
        action = _object(item, {"kind", "page_id", "alias_variant", "root_links", "tail_links"})
        actions.append(
            Action(
                cast(ActionKind, action["kind"]),
                cast(int, action["page_id"]),
                cast(AliasVariant | None, action["alias_variant"]),
                _tokens(action["root_links"]),
                _tokens(action["tail_links"]),
            )
        )
    trace = Trace(tuple(images), tuple(actions), cast(Newline, payload["newline"]))
    validate_trace(trace)
    timeline = _list(payload["source_digest_timeline"])
    _require(tuple(timeline) == source_digest_timeline(trace), "source digest timeline mismatch")
    return trace


@st.composite
def lifecycle_traces(draw: st.DrawFn) -> Trace:
    """Draw legal finite alternatives; no rejection filtering or graph input."""
    images: tuple[PageImage, ...] = INITIAL_IMAGES
    actions = []
    count = draw(st.integers(min_value=1, max_value=8))
    for _ in range(count):
        choices: list[tuple[ActionKind, int]] = []
        for page in images:
            if not page.ever_created:
                choices.append(("create", page.page_id))
            elif not page.present:
                choices.append(("restore", page.page_id))
            else:
                present_kinds: tuple[ActionKind, ...] = ("edit", "alias", "links", "delete")
                choices.extend((kind, page.page_id) for kind in present_kinds)
                if not page.renamed:
                    choices.append(("rename", page.page_id))
        kind, page_id = draw(st.sampled_from(choices))
        page = images[page_id]
        if kind == "alias":
            variant = draw(
                st.sampled_from(tuple(v for v in ("A", "B", "C") if v != page.alias_variant))
            )
            action = Action(kind, page_id, cast(AliasVariant, variant))
        elif kind == "links":
            root = tuple(draw(st.lists(st.sampled_from(SOURCE_TOKENS), max_size=3)))
            tail = tuple(draw(st.lists(st.sampled_from(SOURCE_TOKENS), max_size=1)))
            if (root, tail) == (page.root_links, page.tail_links):
                root = () if root else ("Missing",)
            action = Action(kind, page_id, root_links=root, tail_links=tail)
        else:
            action = Action(kind, page_id)
        images = apply_action(images, action)
        actions.append(action)
    trace = Trace(INITIAL_IMAGES, tuple(actions), draw(st.sampled_from(("LF", "CRLF"))))
    validate_trace(trace)
    return trace


class EvaluationGuard:
    """Count all admitted trace bodies, including failure confirmations."""

    def __init__(self) -> None:
        self.evaluations = 0

    def run(self, callback: Callable[[], None]) -> None:
        if self.evaluations >= 24:
            raise RuntimeError("lifecycle.evaluation_budget")
        self.evaluations += 1
        callback()


@dataclass(frozen=True)
class ObservedPage:
    title: str
    basename: str
    relative_source_path: str | None
    graph_root_matches: bool
    properties: tuple[tuple[str, object], ...]
    properties_order: tuple[str, ...]


@dataclass(frozen=True)
class ObservedNode:
    slot: Slot
    relative_source_path: str | None
    routed_owner_title: str | None
    parser_uuid: str
    source_uuid: str | None
    synthetic_id: bool
    content: str
    line_span: tuple[int | None, int | None]
    properties: tuple[tuple[str, object], ...]
    properties_order: tuple[str, ...]
    wikilinks: tuple[str, ...]


@dataclass(frozen=True)
class LifecycleObservation:
    graph_root_matches: bool
    pages: tuple[ObservedPage, ...]
    page_keys: tuple[str, ...]
    page_routes: tuple[tuple[str, str | None], ...]
    nodes: tuple[ObservedNode, ...]
    attached_slots: tuple[Slot | None, ...]
    registry: tuple[tuple[str, Slot | None], ...]
    native_lookups: tuple[tuple[str, Slot | None], ...]
    backlinks: tuple[tuple[str, tuple[Slot | None, ...]], ...]
    object_identity_valid: bool


def relative_owned_path(source_path: str | None, root: Path) -> str | None:
    if source_path is None or not Path(source_path).is_absolute():
        return None
    try:
        source = Path(source_path).resolve(strict=True)
        relative = source.relative_to(root.resolve(strict=True))
        return relative.as_posix() if source.is_file() else None
    except (OSError, RuntimeError, ValueError):
        return None


def _root_matches(path: str | Path | None, root: Path) -> bool:
    try:
        return path is not None and Path(path).resolve(strict=True) == root.resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        return False


def observe_graph(graph: LogseqGraph, graph_root: Path) -> LifecycleObservation:
    """Capture actual results without receiving or repairing an expected model."""
    pages = tuple(graph.iter_canonical_pages())
    page_ids = {id(page): page.title for page in pages}
    node_slots: dict[int, Slot] = {}
    records = []
    identity = all(id(page) in page_ids for page in graph.pages.values())
    for page in pages:
        assert_tree_invariants(page)
        for node in walk_nodes(page.root_nodes):
            slot = (page.title, tuple(node.outline_path))
            node_slots[id(node)] = slot
            owner = graph.page_for_node(node)
            identity = identity and owner is page and graph.get_node_by_uuid(node.uuid) is node
            records.append(
                ObservedNode(
                    slot,
                    relative_owned_path(node.source_path, graph_root),
                    page_ids.get(id(owner)) if owner is not None else None,
                    node.uuid,
                    node.source_uuid,
                    node.synthetic_id,
                    node.content,
                    (node.line_start, node.line_end),
                    tuple(node.properties.items()),
                    tuple(node.properties_order),
                    tuple(node.wikilinks),
                )
            )

    def captured_slot(node: LogseqNode | None) -> Slot | None:
        nonlocal identity
        if node is None:
            return None
        slot = node_slots.get(id(node))
        identity = identity and slot is not None
        return slot

    routes = []
    for query in PAGE_PROBES:
        routed = graph.get_page(query)
        title = page_ids.get(id(routed)) if routed is not None else None
        identity = identity and (routed is None or title is not None)
        routes.append((query, title))
    attached = tuple(captured_slot(node) for node in graph.iter_attached_nodes())
    # Narrow private read: a public iterator can legitimately hide a ghost.
    registry = tuple((key, captured_slot(node)) for key, node in graph._node_registry.items())
    native = tuple((key, captured_slot(graph.get_node_by_embed_ref(key))) for key in NATIVE_IDS)
    backlinks = tuple(
        (query, tuple(captured_slot(node) for node in graph.get_backlinks(query)))
        for query in BACKLINK_PROBES
    )
    return LifecycleObservation(
        _root_matches(graph.graph_path, graph_root),
        tuple(
            ObservedPage(
                page.title,
                Path(page.source_path).stem if page.source_path else "",
                relative_owned_path(page.source_path, graph_root),
                _root_matches(page.graph_root, graph_root),
                tuple(page.properties.items()),
                tuple(page.properties_order),
            )
            for page in pages
        ),
        tuple(graph.pages),
        tuple(routes),
        tuple(records),
        attached,
        registry,
        native,
        backlinks,
        identity,
    )


def assert_observation(observed: LifecycleObservation, images: tuple[PageImage, ...]) -> None:
    """Check authored semantics first, without predicting parser UUID bytes."""
    validate_images(images)
    active = tuple(page for page in images if page.present)
    titles = {page.title: page for page in active}
    aliases = {page.alias: page.title for page in active}
    assert Counter(observed.page_keys) == Counter((*titles, *aliases)), "lifecycle.page_keys"
    assert Counter(page.title for page in observed.pages) == Counter(titles.keys()), (
        "lifecycle.page_keys"
    )
    routes = {
        query: aliases.get(query)
        or next((title for title in titles if title.lower() == query.lower()), None)
        for query in PAGE_PROBES
    }
    assert Counter(observed.page_routes) == Counter(routes.items()), "lifecycle.alias_ownership"
    assert observed.graph_root_matches, "lifecycle.source_ownership"
    for observed_page in observed.pages:
        assert (
            observed_page.graph_root_matches
            and observed_page.relative_source_path == f"pages/{observed_page.title}.md"
        ), "lifecycle.source_ownership"
        assert observed_page.basename == observed_page.title, "lifecycle.source_ownership"
        assert observed_page.properties == (
            ("alias", titles[observed_page.title].alias),
        ) and observed_page.properties_order == ("alias",), "lifecycle.page_properties"
    for node in observed.nodes:
        assert node.relative_source_path == f"pages/{node.slot[0]}.md", "lifecycle.source_ownership"

    # Model facts deliberately do not call the renderer or observation adapter.
    expected: dict[Slot, tuple[str, str | None, tuple[str, ...], tuple[int, int]]] = {}
    for page in active:
        expected[(page.title, (1,))] = (
            f"Root{page.page_id}v{page.revision}"
            + "".join(f" [[{token}]]" for token in page.root_links),
            NATIVE_IDS[3 * page.page_id + page.revision],
            page.root_links,
            (3, 4),
        )
        expected[(page.title, (1, 1))] = (f"Child{page.page_id}v{page.revision}", None, (), (5, 5))
        expected[(page.title, (2,))] = (
            f"Tail{page.page_id}" + "".join(f" [[{token}]]" for token in page.tail_links),
            NATIVE_IDS[3 * page.page_id + 2],
            page.tail_links,
            (6, 7),
        )
    assert Counter(node.slot for node in observed.nodes) == Counter(expected.keys()), (
        "lifecycle.node_slots"
    )
    for title in titles:
        assert tuple(node.slot[1] for node in observed.nodes if node.slot[0] == title) == (
            (1,),
            (1, 1),
            (2,),
        ), "lifecycle.node_slots"
    parser_ids = []
    for node in observed.nodes:
        content, native, links, span = expected[node.slot]
        assert node.content == content, "lifecycle.node_content"
        assert node.source_uuid == native and node.synthetic_id is (native is None), (
            "lifecycle.native_identity"
        )
        assert node.line_span == span and node.wikilinks == links, "lifecycle.node_fields"
        assert node.properties == (
            (("id", native),) if native else ()
        ) and node.properties_order == (("id",) if native else ()), "lifecycle.node_fields"
        try:
            valid_uuid = str(UUID(node.parser_uuid)) == node.parser_uuid
        except (ValueError, AttributeError):
            valid_uuid = False
        assert valid_uuid and node.parser_uuid != native, "lifecycle.parser_identity"
        parser_ids.append(node.parser_uuid)
    assert len(set(parser_ids)) == len(parser_ids), "lifecycle.parser_identity"
    native_routes = {
        native: slot for slot, (_, native, _, _) in expected.items() if native is not None
    }
    assert Counter(observed.native_lookups) == Counter(
        (key, native_routes.get(key)) for key in NATIVE_IDS
    ), "lifecycle.native_identity"
    assert Counter(observed.attached_slots) == Counter(expected.keys()), (
        "lifecycle.registry_membership"
    )
    assert Counter(observed.registry) == Counter(
        (node.parser_uuid, node.slot) for node in observed.nodes
    ), "lifecycle.registry_membership"
    assert observed.object_identity_valid and all(
        node.routed_owner_title == node.slot[0] for node in observed.nodes
    ), "lifecycle.object_identity"

    expected_backlinks: dict[str, set[Slot]] = {}
    for page in active:
        for position, tokens in (((1,), page.root_links), ((2,), page.tail_links)):
            slot = (page.title, position)
            for token in tokens:
                keys = {token.lower()}
                owner = aliases.get(token) or next(
                    (title for title in titles if title.lower() == token.lower()), None
                )
                if owner is not None:
                    keys.update((owner.lower(), titles[owner].alias.lower()))
                for key in keys:
                    expected_backlinks.setdefault(key, set()).add(slot)
    assert Counter(query for query, _ in observed.backlinks) == Counter(BACKLINK_PROBES), (
        "lifecycle.backlink_sources"
    )
    for _, slots in observed.backlinks:
        assert len(slots) == len(set(slots)), "lifecycle.backlink_unique"
    for query, slots in observed.backlinks:
        assert Counter(slots) == Counter(expected_backlinks.get(query.lower(), set())), (
            "lifecycle.backlink_sources"
        )
