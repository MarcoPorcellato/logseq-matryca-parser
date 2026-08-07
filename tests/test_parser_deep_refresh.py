"""Regression coverage for immutable parser refreshes at arbitrary depth."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from logseq_matryca_parser.logos_core import LogseqNode
from logseq_matryca_parser.logos_parser import StackMachineParser
from logseq_matryca_parser.logseq_markdown import serialize_logseq_page


def _nested_source(depth: int, tail: list[tuple[int, str]]) -> str:
    lines = [f"{'  ' * level}- node-{level + 1}" for level in range(depth)]
    lines.extend(f"{'  ' * (depth + extra_indent)}{text}" for extra_indent, text in tail)
    return "\n".join(lines)


def _branch(root: LogseqNode) -> list[LogseqNode]:
    branch = [root]
    while branch[-1].children:
        assert len(branch[-1].children) == 1
        branch.append(branch[-1].children[0])
    return branch


def _walk(node: LogseqNode) -> Iterator[LogseqNode]:
    yield node
    for child in node.children:
        yield from _walk(child)


def _semantic_snapshot(node: LogseqNode) -> tuple[object, ...]:
    return (
        node.uuid,
        node.content,
        node.clean_text,
        node.properties,
        node.properties_order,
        node.wikilinks,
        node.tags,
        node.block_refs,
        node.parent_id,
        node.left_id,
        tuple(_semantic_snapshot(child) for child in node.children),
    )


@pytest.mark.parametrize("depth", [1, 2, 3, 4, 8, 32])
def test_soft_break_refresh_propagates_to_root_at_any_depth(depth: int) -> None:
    source = _nested_source(depth, [(0, "continuation-at-leaf")])
    first = StackMachineParser().parse(source, page_title="deep-soft-break")
    second = StackMachineParser().parse(source, page_title="deep-soft-break")
    branch = _branch(first.root_nodes[0])

    assert len(branch) == depth
    assert branch[-1].content.endswith("continuation-at-leaf")
    assert branch[-1].line_end == depth + 1
    assert [node.uuid for node in branch] == [node.uuid for node in _branch(second.root_nodes[0])]

    for parent, child in zip(branch, branch[1:], strict=False):
        assert child.parent_id == parent.uuid
        assert child.left_id is None


def test_deep_refresh_preserves_sibling_order_and_left_pointer() -> None:
    source = "\n".join(
        [f"{'  ' * level}- node-{level + 1}" for level in range(7)]
        + [
            f"{'  ' * 7}- first-leaf",
            f"{'  ' * 7}- second-leaf",
            f"{'  ' * 8}second-continuation",
        ]
    )
    page = StackMachineParser().parse(source, page_title="deep-siblings")
    parent = page.root_nodes[0]
    for _ in range(6):
        parent = parent.children[0]
    first, second = parent.children

    assert [first.clean_text, second.clean_text] == [
        "first-leaf",
        "second-leaf\nsecond-continuation",
    ]
    assert second.left_id == first.uuid
    assert second.parent_id == parent.uuid
    assert second.line_end == 10


@pytest.mark.parametrize(
    ("tail", "assertion"),
    [
        ([(0, "status:: active")], "block-property"),
        ([(0, "```python"), (0, "value = 42"), (0, "```")], "fenced-code"),
        (
            [(0, "#+BEGIN_QUERY"), (0, '[?p :block/name "[[Ghost]]"]'), (0, "#+END_QUERY")],
            "query",
        ),
        ([(0, "tags::"), (1, "- [[AI]]")], "list-property"),
    ],
)
def test_deep_refresh_families_survive_roundtrip(
    tail: list[tuple[int, str]],
    assertion: str,
) -> None:
    source = _nested_source(8, tail)
    parser = StackMachineParser()
    page = parser.parse(source, page_title=f"deep-{assertion}")
    leaf = _branch(page.root_nodes[0])[-1]

    if assertion == "block-property":
        assert leaf.properties["status"] == "active"
    elif assertion == "fenced-code":
        assert "value = 42" in leaf.content
    elif assertion == "query":
        assert "+BEGIN_QUERY" in leaf.content
        assert "Ghost" not in leaf.wikilinks
    else:
        assert leaf.properties["tags"] == ["[[AI]]"]
        assert "AI" in leaf.wikilinks

    rendered = serialize_logseq_page(page)
    reparsed = parser.parse(rendered, page_title=f"deep-{assertion}")

    if assertion == "list-property":
        reparsed_leaf = _branch(reparsed.root_nodes[0])[-1]
        assert reparsed_leaf.properties["tags"] == ["AI"]
        assert reparsed_leaf.tags == ["AI"]
        assert [node.uuid for node in _branch(reparsed.root_nodes[0])] == [
            node.uuid for node in _branch(page.root_nodes[0])
        ]
    else:
        assert _semantic_snapshot(reparsed.root_nodes[0]) == _semantic_snapshot(page.root_nodes[0])
    assert len(list(_walk(reparsed.root_nodes[0]))) == 8
