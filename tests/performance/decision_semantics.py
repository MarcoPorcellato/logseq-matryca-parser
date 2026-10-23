"""Pure metadata and private small-fixture semantics, never workload admission."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn
from uuid import NAMESPACE_DNS, uuid5

if TYPE_CHECKING:
    from logseq_matryca_parser.graph import LogseqGraph
    from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage

type PropertyRows = tuple[tuple[str, tuple[str, ...]], ...]
type NodeKey = tuple[str, tuple[int, ...]]

PAGE_FIELDS = (
    "title", "logical_source", "raw_content_sha256", "properties", "properties_order",
    "refs", "namespace_chain", "root_uuids", "created_at", "updated_at", "tab_size",
)
NODE_FIELDS = (
    "key", "logical_source", "uuid", "source_uuid", "synthetic_id", "content", "clean_text",
    "indent_level", "line_start", "line_end", "properties", "properties_order", "wikilinks",
    "tags", "assets", "block_refs", "refs", "task_status", "task_priority", "repeater",
    "scheduled_at", "deadline_at", "created_at", "updated_at", "parent_id", "left_id",
    "path", "outline_path", "child_uuids",
)


def _require_source_digest(value: object) -> str:
    if type(value) is not str:
        raise TypeError("invalid small workload input")
    if (len(value) != 64 or value == "0" * 64
            or any(character not in "0123456789abcdef" for character in value)):
        raise ValueError("invalid small workload input")
    return value


def semantic_contract_payload(*, semantic_source_sha256: str) -> dict[str, object]:
    """Describe fixed meanings without constructing an expected or observed graph."""
    return {
        "schema": "matryca-small-full-load-semantics", "schema_version": 1,
        "source_sha256": _require_source_digest(semantic_source_sha256),
        "profile": "semantic_roundtrip_v1",
        "identity_policy": {"synthetic_uuid": "stable", "source_uuid": "absent",
                            "relations": "direct_ids"},
        "page_fields": list(PAGE_FIELDS), "node_fields": list(NODE_FIELDS),
        "supplemental_policy": "exact_ranges_and_owned_logical_sources_v1",
        "identity_formula": "source_uuid5_dns_sha256_v1",
        "container_policy": "closed_small_fixture_v1",
    }


@dataclass(frozen=True, slots=True)
class PageRow:
    title: str
    logical_source: str
    raw_content_sha256: str
    properties: PropertyRows
    properties_order: tuple[str, ...]
    refs: tuple[str, ...]
    namespace_chain: tuple[str, ...]
    root_uuids: tuple[str, ...]
    created_at: int | None
    updated_at: int | None
    tab_size: int


@dataclass(frozen=True, slots=True)
class NodeRow:
    key: NodeKey
    logical_source: str
    uuid: str
    source_uuid: str | None
    synthetic_id: bool
    content: str
    clean_text: str
    indent_level: int
    line_start: int
    line_end: int
    properties: PropertyRows
    properties_order: tuple[str, ...]
    wikilinks: tuple[str, ...]
    tags: tuple[str, ...]
    assets: tuple[str, ...]
    block_refs: tuple[str, ...]
    refs: tuple[str, ...]
    task_status: str | None
    task_priority: str | None
    repeater: str | None
    scheduled_at: int | None
    deadline_at: int | None
    created_at: int | None
    updated_at: int | None
    parent_id: str | None
    left_id: str | None
    path: tuple[str, ...]
    outline_path: tuple[int, ...]
    child_uuids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SmallGraphProjection:
    pages: tuple[PageRow, ...]
    nodes: tuple[NodeRow, ...]
    page_index: tuple[tuple[str, str], ...]
    source_page_index: tuple[tuple[str, str], ...]
    lower_titles: tuple[tuple[str, str], ...]
    node_index: tuple[str, ...]
    backlinks: tuple[tuple[str, tuple[str, ...]], ...]


def _titles() -> tuple[str, ...]:
    return ("runtime-evidence-deep", *(f"runtime-evidence-page-{i:04d}" for i in range(1, 96)))


def _alias(index: int) -> str:
    return f"runtime-evidence-alias-{index:04d}"


def _expected_uuid(title: str, line: int, parent: str | None, content: str) -> str:
    # Independent arithmetic over the closed source grammar, not a Parser helper.
    payload = f"{title}:{line}:{parent if parent is not None else 'root'}:{content}"
    return str(uuid5(NAMESPACE_DNS, sha256(payload.encode("utf-8")).hexdigest()))


def _expected_node(
    title: str, content: str, line: int, indent: int, outline: tuple[int, ...],
    identity: str, parent: str | None, left: str | None, ancestry: tuple[str, ...],
    children: tuple[str, ...], links: tuple[str, ...] = (), tags: tuple[str, ...] = (),
) -> NodeRow:
    return NodeRow(
        key=(title, outline), logical_source=f"pages/{title}.md", uuid=identity,
        source_uuid=None, synthetic_id=True, content=content, clean_text=content,
        indent_level=indent, line_start=line, line_end=line, properties=(),
        properties_order=(), wikilinks=links, tags=tags, assets=(), block_refs=(),
        refs=(*links, *tags), task_status=None, task_priority=None, repeater=None,
        scheduled_at=None, deadline_at=None, created_at=None, updated_at=None,
        parent_id=parent, left_id=left, path=ancestry, outline_path=outline,
        child_uuids=children,
    )


def expected_small_graph() -> SmallGraphProjection:
    """Derive all rows from literal grammar; never import Parser or generator code."""
    pages: list[PageRow] = []
    nodes: list[NodeRow] = []
    first_ordinary: list[str] = []
    for page_index, title in enumerate(_titles()):
        if page_index == 0:
            identities: list[str] = []
            raw_lines: list[str] = []
            for depth in range(1024):
                content = f"chain-{depth:04d}"
                identities.append(_expected_uuid(
                    title, depth + 1, identities[-1] if identities else None, content,
                ))
                raw_lines.append("  " * (depth + 1) + "- " + content + "\n")
            for depth, identity in enumerate(identities):
                nodes.append(_expected_node(
                    title, f"chain-{depth:04d}", depth + 1, depth, (1,) * (depth + 1),
                    identity, identities[depth - 1] if depth else None, None,
                    tuple(identities[:depth + 1]),
                    (identities[depth + 1],) if depth < 1023 else (),
                ))
            pages.append(PageRow(
                title, f"pages/{title}.md", sha256("".join(raw_lines).encode("utf-8")).hexdigest(),
                (), (), (), (), (identities[0],), None, None, 2,
            ))
            continue
        target = (f"runtime-evidence-page-{page_index + 1:04d}" if page_index < 95
                  else "runtime-evidence-deep")
        roots: list[str] = []
        raw_lines = [f"alias:: {_alias(page_index)}\n", "\n"]
        for block_index in range(24):
            content = f"block-{page_index:04d}-{block_index:02d}"
            if block_index == 0:
                content += f" #runtime-evidence [[{target}]]"
            identity = _expected_uuid(title, block_index + 3, None, content)
            nodes.append(_expected_node(
                title, content, block_index + 3, 0, (block_index + 1,), identity, None,
                roots[-1] if roots else None, (identity,), (),
                (target,) if block_index == 0 else (), ("runtime-evidence",) if block_index == 0 else (),
            ))
            roots.append(identity)
            raw_lines.append("- " + content + "\n")
        first_ordinary.append(roots[0])
        pages.append(PageRow(
            title, f"pages/{title}.md", sha256("".join(raw_lines).encode("utf-8")).hexdigest(),
            (("alias", (_alias(page_index),)),), ("alias",),
            (target, "runtime-evidence", _alias(page_index)), (), tuple(roots), None, None, 2,
        ))
    index = [(page.title, page.title) for page in pages]
    index.extend((_alias(i), f"runtime-evidence-page-{i:04d}") for i in range(1, 96))
    backlinks: dict[str, tuple[str, ...]] = {"runtime-evidence": tuple(first_ordinary)}
    for i in range(1, 95):
        backlinks[f"runtime-evidence-page-{i + 1:04d}"] = (first_ordinary[i - 1],)
        backlinks[_alias(i + 1)] = (first_ordinary[i - 1],)
    backlinks["runtime-evidence-deep"] = (first_ordinary[-1],)
    return SmallGraphProjection(
        tuple(pages), tuple(nodes), tuple(sorted(index)),
        tuple((page.logical_source, page.title) for page in pages),
        tuple((page.title.lower(), page.title) for page in pages),
        tuple(node.uuid for node in nodes), tuple(sorted(backlinks.items())),
    )


def _structure_fail() -> NoReturn:
    raise AssertionError("small workload structure mismatch") from None


def _need(condition: bool) -> None:
    if not condition:
        _structure_fail()


def _text(value: object, maximum: int, *, exact: bool = False) -> str:
    if type(value) is not str:
        _structure_fail()
    _need(len(value) == maximum if exact else len(value) <= maximum)
    return value


def _integer(value: object, minimum: int, maximum: int) -> int:
    if type(value) is not int:
        _structure_fail()
    _need(minimum <= value <= maximum)
    return value


def _strings(value: object, count: int, length: int, *, exact_length: bool = False) -> tuple[str, ...]:
    if type(value) is not list:
        _structure_fail()
    _need(len(value) <= count)
    return tuple(_text(item, length, exact=exact_length) for item in value)


def _optional_uuid(value: object) -> str | None:
    return None if value is None else _text(value, 36, exact=True)


def _owned_root(root: Path) -> str:
    _need(type(root) is type(Path()))
    _need(root.is_absolute() and ".." not in root.parts)
    return _text(str(root), 4096)


def _page_observation(
    page: LogseqPage, *, graph_root: Path, logical_source: str, node_limit: int,
) -> tuple[PageRow, tuple[NodeRow, ...], tuple[LogseqNode, ...]]:
    from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage

    _need(type(page) is LogseqPage)
    _need(type(node_limit) is int and node_limit in (24, 1024))
    root = _owned_root(graph_root)
    title = _text(page.title, 26)
    _need(title in _titles())
    logical = _text(logical_source, 35)
    _need(logical == f"pages/{title}.md")
    physical = str(graph_root / "pages" / (title + ".md"))
    _need(_text(page.source_path, len(physical)) == physical)
    _need(_text(page.graph_root, len(root)) == root)
    deep = title == "runtime-evidence-deep"
    raw = _text(page.raw_content, 1062912 if deep else 470)
    _need(type(page.properties) is dict)
    if deep:
        _need(len(page.properties) == 0)
        properties: PropertyRows = ()
    else:
        _need(len(page.properties) == 1)
        key = next(iter(page.properties))
        _need(type(key) is str and key == "alias")
        properties = (("alias", (_text(page.properties["alias"], 27),)),)
    order = _strings(page.properties_order, 1, 5)
    refs = _strings(page.refs, 3, 27)
    namespace = _strings(page.namespace_chain, 0, 26)
    tab_size = _integer(page.tab_size, 1, 16)
    for value in (page.created_at, page.updated_at):
        _need(value is None or (type(value) is int and value >= 0))
    _need(type(page.root_nodes) is list and 1 <= len(page.root_nodes) <= (1 if deep else 24))
    for node in page.root_nodes:
        _need(type(node) is LogseqNode)
    # Each pending entry holds a bounded flat path, never a recursive projection.
    pending: list[tuple[LogseqNode, str | None, str | None, tuple[str, ...], tuple[int, ...]]] = [
        (node, None, page.root_nodes[i - 1].uuid if i else None, (), (i + 1,))
        for i, node in reversed(list(enumerate(page.root_nodes)))
    ]
    seen_objects: set[int] = set()
    seen_uuids: set[str] = set()
    rows: list[NodeRow] = []
    attached: list[LogseqNode] = []
    while pending:
        _need(len(pending) <= node_limit and len(rows) < node_limit)
        node, parent, left, ancestors, outline = pending.pop()
        _need(type(node) is LogseqNode and id(node) not in seen_objects)
        seen_objects.add(id(node))
        identity = _text(node.uuid, 36, exact=True)
        _need(identity not in seen_uuids)
        seen_uuids.add(identity)
        _need(type(node.children) is list and len(node.children) <= (1 if deep else 0))
        child_ids: list[str] = []
        for child in node.children:
            _need(type(child) is LogseqNode)
            child_ids.append(_text(child.uuid, 36, exact=True))
        ancestry = _strings(node.path, 1024, 36, exact_length=True)
        _need(type(node.outline_path) is list and len(node.outline_path) <= 1024)
        actual_outline = tuple(_integer(item, 1, 24) for item in node.outline_path)
        _need(1 <= len(outline) <= 1024 and ancestry == (*ancestors, identity)
              and actual_outline == outline)
        parent_id, left_id = _optional_uuid(node.parent_id), _optional_uuid(node.left_id)
        _need(parent_id == parent and left_id == left)
        _need(_text(node.source_path, len(physical)) == physical)
        _need(type(node.properties) is dict and len(node.properties) == 0)
        node_order = _strings(node.properties_order, 0, 5)
        content, clean = _text(node.content, 62), _text(node.clean_text, 62)
        indent = _integer(node.indent_level, 0, 1023)
        _need(indent == (len(outline) - 1 if deep else 0))
        first, last = _integer(node.line_start, 1, 1024), _integer(node.line_end, 1, 1024)
        _need(first <= last)
        links, tags = _strings(node.wikilinks, 1, 27), _strings(node.tags, 1, 27)
        assets, block_refs = _strings(node.assets, 0, 1), _strings(node.block_refs, 0, 36)
        node_refs = _strings(node.refs, 2, 27)
        _need(type(node.synthetic_id) is bool)
        source_uuid = _optional_uuid(node.source_uuid)
        _need(all(value is None for value in (
            node.task_status, node.task_priority, node.repeater, node.scheduled_at,
            node.deadline_at, node.created_at, node.updated_at,
        )))
        rows.append(NodeRow(
            (title, actual_outline), logical, identity, source_uuid, node.synthetic_id,
            content, clean, indent, first, last, (), node_order, links, tags, assets,
            block_refs, node_refs, None, None, None, None, None, None, None,
            parent_id, left_id, ancestry, actual_outline, tuple(child_ids),
        ))
        attached.append(node)
        for i, child in reversed(list(enumerate(node.children))):
            pending.append((child, identity, child_ids[i - 1] if i else None,
                            ancestry, (*outline, i + 1)))
    return (
        PageRow(title, logical, sha256(raw.encode("utf-8")).hexdigest(), properties, order,
                refs, namespace, tuple(_text(node.uuid, 36, exact=True) for node in page.root_nodes),
                None, None, tab_size),
        tuple(rows), tuple(attached),
    )


def _observe_page_fields(
    page: LogseqPage, *, graph_root: Path, logical_source: str, node_limit: int,
) -> tuple[PageRow, tuple[NodeRow, ...]]:
    """Bounded per-page seam; a small controlled subtree is not full-graph admission."""
    try:
        row, nodes, _ = _page_observation(
            page, graph_root=graph_root, logical_source=logical_source, node_limit=node_limit,
        )
        return row, nodes
    except (AssertionError, AttributeError, KeyError, TypeError, ValueError, OverflowError):
        _structure_fail()


def _graph_observation(graph: LogseqGraph, *, graph_root: Path) -> SmallGraphProjection:
    from logseq_matryca_parser.graph import LogseqGraph
    from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage

    root = _owned_root(graph_root)
    _need(type(graph) is LogseqGraph and type(graph.graph_path) is type(graph_root))
    _need(graph.graph_path == graph_root)
    _need(type(graph.pages) is dict and len(graph.pages) == 191)
    _need(type(graph._source_pages) is dict and len(graph._source_pages) == 96)
    _need(type(graph._lower_title_map) is dict and len(graph._lower_title_map) == 96)
    _need(type(graph._node_registry) is dict and len(graph._node_registry) == 3304)
    _need(type(graph._backlink_registry) is dict and len(graph._backlink_registry) <= 190)
    _need(type(graph._index_diagnostics) is tuple and len(graph._index_diagnostics) == 0)
    for key, page in graph.pages.items():
        _text(key, 27)
        _need(type(page) is LogseqPage)
    for key, page in graph._source_pages.items():
        _text(key, len(root) + 36)
        _need(type(page) is LogseqPage)
    for key, value in graph._lower_title_map.items():
        _text(key, 26)
        _text(value, 26)
    for key, node in graph._node_registry.items():
        _text(key, 36, exact=True)
        _need(type(node) is LogseqNode)
    for key, values in graph._backlink_registry.items():
        _text(key, 27)
        _strings(values, 95, 36, exact_length=True)
    titles = _titles()
    physical = {str(graph_root / "pages" / (title + ".md")): title for title in titles}
    _need(set(graph._source_pages) == set(physical))
    expected_page_keys = {*titles, *(_alias(i) for i in range(1, 96))}
    _need(set(graph.pages) == expected_page_keys)
    pages: list[PageRow] = []
    rows: list[NodeRow] = []
    attached: dict[str, LogseqNode] = {}
    page_objects: set[int] = set()
    object_ids: set[int] = set()
    for source, title in physical.items():
        page = graph._source_pages[source]
        _need(_text(page.title, 26) == title and id(page) not in page_objects)
        page_objects.add(id(page))
        _need(graph.pages[title] is page)
        page_index = len(pages)
        if page_index:
            _need(graph.pages[_alias(page_index)] is page)
        row, page_rows, native_nodes = _page_observation(
            page, graph_root=graph_root, logical_source=f"pages/{title}.md",
            node_limit=1024 if page_index == 0 else 24,
        )
        _need(len(page_rows) == (1024 if page_index == 0 else 24))
        pages.append(row)
        rows.extend(page_rows)
        _need(len(rows) <= 3304)
        for node in native_nodes:
            _need(id(node) not in object_ids and node.uuid not in attached)
            object_ids.add(id(node))
            attached[node.uuid] = node
    _need(len(rows) == 3304 and len(page_objects) == 96)
    identities = tuple(node.uuid for node in rows)
    _need(tuple(graph._node_registry) == identities)
    _need(all(graph._node_registry[key] is attached[key] for key in identities))
    for title in titles:
        _need(graph.get_page(title.upper()) is graph.pages[title])
    for i in range(1, 96):
        _need(graph.get_page(_alias(i)) is graph.pages[f"runtime-evidence-page-{i:04d}"])
    # No legacy tree helper is invoked until every graph member is fully prevalidated.
    from tests.parser_assurance.invariants import assert_tree_invariants

    for source in physical:
        assert_tree_invariants(graph._source_pages[source])
    return SmallGraphProjection(
        tuple(pages), tuple(rows),
        tuple((key, graph.pages[key].title) for key in sorted(graph.pages)),
        tuple((f"pages/{title}.md", title) for title in titles),
        tuple(sorted(graph._lower_title_map.items())), identities,
        tuple((key, tuple(graph._backlink_registry[key])) for key in sorted(graph._backlink_registry)),
    )


def observe_small_graph(graph: LogseqGraph, *, graph_root: Path) -> SmallGraphProjection:
    """Observe only exact native, owned small graphs without recursive dumping."""
    try:
        return _graph_observation(graph, graph_root=graph_root)
    except (AssertionError, AttributeError, KeyError, TypeError, ValueError, OverflowError):
        _structure_fail()


def assert_small_graph_semantics(graph: LogseqGraph, *, graph_root: Path) -> None:
    """Reject a bounded structure or any difference from independent expectations."""
    observed = observe_small_graph(graph, graph_root=graph_root)
    if observed != expected_small_graph():
        raise AssertionError("small workload semantic mismatch") from None
