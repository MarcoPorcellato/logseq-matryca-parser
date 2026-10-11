"""Handwritten, bounded semantic facts; no parser or serializer oracle."""

from __future__ import annotations

from dataclasses import dataclass

from logseq_matryca_parser.logos_core import LogseqPage
from tests.parser_assurance.invariants import assert_tree_invariants, walk_nodes


@dataclass(frozen=True)
class ExpectedNode:
    outline_path: tuple[int, ...]
    content: str
    line_span: tuple[int, int]
    properties: tuple[tuple[str, object], ...]
    properties_order: tuple[str, ...]
    source_uuid: str | None
    synthetic_id: bool
    wikilinks: tuple[str, ...]
    tags: tuple[str, ...]
    refs: tuple[str, ...]
    task_status: str | None
    task_priority: str | None
    child_count: int


@dataclass(frozen=True)
class Anchor:
    case_id: str
    source: str
    input_title: str
    expected_title: str
    page_properties: tuple[tuple[str, object], ...]
    page_properties_order: tuple[str, ...]
    page_refs: tuple[str, ...]
    nodes: tuple[ExpectedNode, ...]
    roundtrip: bool


ANCHORS: tuple[Anchor, ...] = (
    Anchor(
        case_id="nested-native-property-order-crlf",
        source=(
            "- TODO [#A] root [[Body]]\r\n"
            "  zeta:: kept\r\n"
            "  alpha:: [[Property]]\r\n"
            "  id:: 11111111-1111-1111-1111-111111111111\r\n"
            "  continuation 東京\r\n"
            "  - TODO [#B] child\r\n"
            "    beta:: child-value"
        ),
        input_title="s1-nested-crlf",
        expected_title="s1-nested-crlf",
        page_properties=(),
        page_properties_order=(),
        page_refs=("Body", "Property", "A", "B"),
        nodes=(
            ExpectedNode(
                outline_path=(1,),
                content="TODO [#A] root [[Body]]\n  continuation 東京",
                line_span=(1, 5),
                properties=(
                    ("zeta", "kept"),
                    ("alpha", "[[Property]]"),
                    ("id", "11111111-1111-1111-1111-111111111111"),
                ),
                properties_order=("zeta", "alpha", "id"),
                source_uuid="11111111-1111-1111-1111-111111111111",
                synthetic_id=False,
                wikilinks=("Body", "Property"),
                tags=("A",),
                refs=("Body", "Property", "A"),
                task_status="TODO",
                task_priority="A",
                child_count=1,
            ),
            ExpectedNode(
                outline_path=(1, 1),
                content="TODO [#B] child",
                line_span=(6, 7),
                properties=(("beta", "child-value"),),
                properties_order=("beta",),
                source_uuid=None,
                synthetic_id=True,
                wikilinks=(),
                tags=("B",),
                refs=("B",),
                task_status="TODO",
                task_priority="B",
                child_count=0,
            ),
        ),
        roundtrip=True,
    ),
    Anchor(
        case_id="equal-content-distinct-native-order",
        source=(
            "- TODO repeated [[Shared]]\n"
            "  id:: 11111111-1111-1111-1111-111111111111\n"
            "  zeta:: kept\n"
            "- TODO repeated [[Shared]]\n"
            "  zeta:: kept\n"
            "  id:: 22222222-2222-2222-2222-222222222222\n"
        ),
        input_title="s1-equal-content",
        expected_title="s1-equal-content",
        page_properties=(),
        page_properties_order=(),
        page_refs=("Shared",),
        nodes=(
            ExpectedNode(
                outline_path=(1,),
                content="TODO repeated [[Shared]]",
                line_span=(1, 3),
                properties=(
                    ("id", "11111111-1111-1111-1111-111111111111"),
                    ("zeta", "kept"),
                ),
                properties_order=("id", "zeta"),
                source_uuid="11111111-1111-1111-1111-111111111111",
                synthetic_id=False,
                wikilinks=("Shared",),
                tags=(),
                refs=("Shared",),
                task_status="TODO",
                task_priority=None,
                child_count=0,
            ),
            ExpectedNode(
                outline_path=(2,),
                content="TODO repeated [[Shared]]",
                line_span=(4, 6),
                properties=(
                    ("zeta", "kept"),
                    ("id", "22222222-2222-2222-2222-222222222222"),
                ),
                properties_order=("zeta", "id"),
                source_uuid="22222222-2222-2222-2222-222222222222",
                synthetic_id=False,
                wikilinks=("Shared",),
                tags=(),
                refs=("Shared",),
                task_status="TODO",
                task_priority=None,
                child_count=0,
            ),
        ),
        roundtrip=True,
    ),
    Anchor(
        case_id="fenced-fake-id-does-not-rebind",
        source=(
            "- TODO [[Visible]]\n"
            "  id:: 11111111-1111-1111-1111-111111111111\n"
            "  zeta:: kept\n"
            "  alpha:: plain\n"
            "  ```\n"
            "  id:: 22222222-2222-2222-2222-222222222222\n"
            "  zeta:: [[Hidden]] #hidden\n"
            "  ```\n"
            "  [[Visible]]\n"
        ),
        input_title="s1-fenced-native",
        expected_title="s1-fenced-native",
        page_properties=(),
        page_properties_order=(),
        page_refs=("Visible",),
        nodes=(
            ExpectedNode(
                outline_path=(1,),
                content=(
                    "TODO [[Visible]]\n"
                    "  ```\n"
                    "  id:: 22222222-2222-2222-2222-222222222222\n"
                    "  zeta:: [[Hidden]] #hidden\n"
                    "  ```\n"
                    "  [[Visible]]"
                ),
                line_span=(1, 9),
                properties=(
                    ("id", "11111111-1111-1111-1111-111111111111"),
                    ("zeta", "kept"),
                    ("alpha", "plain"),
                ),
                properties_order=("id", "zeta", "alpha"),
                source_uuid="11111111-1111-1111-1111-111111111111",
                synthetic_id=False,
                wikilinks=("Visible", "Visible"),
                tags=(),
                refs=("Visible",),
                task_status="TODO",
                task_priority=None,
                child_count=0,
            ),
        ),
        roundtrip=False,
    ),
    Anchor(
        case_id="metadata-only-crlf-no-final-newline",
        source=(
            "title:: S1 metadata\r\n"
            "alias:: Board\r\n"
            "related:: [[Alpha]] and [[Beta]]"
        ),
        input_title="s1-metadata-input",
        expected_title="S1 metadata",
        page_properties=(
            ("title", "S1 metadata"),
            ("alias", "Board"),
            ("related", "[[Alpha]] and [[Beta]]"),
        ),
        page_properties_order=("title", "alias", "related"),
        page_refs=("Board", "Alpha", "Beta"),
        nodes=(),
        roundtrip=False,
    ),
)


def _validate_properties(
    properties: tuple[tuple[str, object], ...], order: tuple[str, ...]
) -> None:
    keys = [key for key, _ in properties]
    assert len(keys) <= 3, "anchor.bounds.properties"
    assert len(set(keys)) == len(keys), "anchor.bounds.property_keys"
    assert all(key and isinstance(value, str) for key, value in properties), "anchor.bounds.property_values"
    assert len(order) == len(keys) and set(order) == set(keys), "anchor.bounds.property_order"


def validate_anchor(anchor: Anchor) -> None:
    """Check the declared finite domain without inferring source semantics."""
    assert anchor.case_id, "anchor.bounds.case_id"
    assert 0 < len(anchor.source.encode("utf-8")) <= 2048, "anchor.bounds.source_bytes"
    assert len(anchor.nodes) <= 16, "anchor.bounds.nodes"
    assert "\t" not in anchor.source, "anchor.bounds.indentation"
    assert "\r" not in anchor.source.replace("\r\n", ""), "anchor.bounds.newlines"
    lines = anchor.source.splitlines()
    fence_count = 0
    for line in lines:
        assert (len(line) - len(line.lstrip(" "))) % 2 == 0, "anchor.bounds.indentation"
        stripped = line.strip()
        assert not stripped.startswith("~~~"), "anchor.bounds.fences"
        if stripped.startswith("```"):
            assert stripped == "```", "anchor.bounds.fences"
            fence_count += 1
    assert fence_count % 2 == 0, "anchor.bounds.closed_fences"
    _validate_properties(anchor.page_properties, anchor.page_properties_order)
    paths = [node.outline_path for node in anchor.nodes]
    assert paths == sorted(paths) and len(set(paths)) == len(paths), "anchor.bounds.preorder"
    seen: set[tuple[int, ...]] = set()
    sibling_counts: dict[tuple[int, ...], int] = {}
    for node in anchor.nodes:
        path = node.outline_path
        assert 1 <= len(path) <= 4 and all(type(index) is int and index > 0 for index in path), "anchor.bounds.depth"
        parent = path[:-1]
        assert not parent or parent in seen, "anchor.bounds.parent"
        expected_index = sibling_counts.get(parent, 0) + 1
        assert path[-1] == expected_index, "anchor.bounds.sibling_index"
        sibling_counts[parent] = expected_index
        seen.add(path)
        assert node.child_count == sum(other[:-1] == path for other in paths), "anchor.bounds.child_count"
        assert 1 <= node.line_span[0] <= node.line_span[1] <= len(lines), "anchor.bounds.line_span"
        _validate_properties(node.properties, node.properties_order)
    native_ids = [node.source_uuid for node in anchor.nodes if node.source_uuid is not None]
    assert len(set(native_ids)) == len(native_ids), "anchor.bounds.native_ids"


def assert_anchor(page: LogseqPage, anchor: Anchor) -> None:
    """Check literal fields first, then reuse structural invariants."""
    assert page.raw_content == anchor.source, "anchor.page.raw_content"
    assert page.title == anchor.expected_title, "anchor.page.title"
    assert page.tab_size == 2, "anchor.page.tab_size"
    assert page.properties == dict(anchor.page_properties), "anchor.page.properties"
    assert tuple(page.properties_order) == anchor.page_properties_order, "anchor.page.properties_order"
    assert tuple(page.refs) == anchor.page_refs, "anchor.page.refs"
    nodes = list(walk_nodes(page.root_nodes))
    assert len(nodes) == len(anchor.nodes), "anchor.nodes.count"
    assert tuple(tuple(node.outline_path) for node in nodes) == tuple(
        expected.outline_path for expected in anchor.nodes
    ), "anchor.nodes.outline_paths"
    for node, expected in zip(nodes, anchor.nodes, strict=True):
        assert node.content == expected.content, "anchor.node.content"
        assert (node.line_start, node.line_end) == expected.line_span, "anchor.node.line_span"
        assert node.properties == dict(expected.properties), "anchor.node.properties"
        assert tuple(node.properties_order) == expected.properties_order, "anchor.node.properties_order"
        assert node.source_uuid == expected.source_uuid, "anchor.node.source_uuid"
        assert node.synthetic_id is expected.synthetic_id, "anchor.node.synthetic_id"
        assert tuple(node.wikilinks) == expected.wikilinks, "anchor.node.wikilinks"
        assert tuple(node.tags) == expected.tags, "anchor.node.tags"
        assert tuple(node.refs) == expected.refs, "anchor.node.refs"
        assert node.task_status == expected.task_status, "anchor.node.task_status"
        assert node.task_priority == expected.task_priority, "anchor.node.task_priority"
        assert len(node.children) == expected.child_count, "anchor.node.child_count"
        assert node.indent_level == len(expected.outline_path) - 1, "anchor.node.indent_level"
        assert not node.block_refs, "anchor.node.block_refs"
        assert node.uuid, "anchor.node.parser_uuid"
        assert node.uuid != node.source_uuid, "anchor.node.native_uuid_separation"
    assert_tree_invariants(page)
