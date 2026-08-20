"""Test-only structural invariants shared by parser assurance suites."""

from __future__ import annotations

from collections.abc import Iterator

from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage


def walk_nodes(nodes: list[LogseqNode]) -> Iterator[LogseqNode]:
    """Yield nodes in deterministic pre-order."""
    pending = list(reversed(nodes))
    while pending:
        node = pending.pop()
        yield node
        pending.extend(reversed(node.children))


def assert_tree_invariants(page: LogseqPage) -> None:
    """Assert the structural contract shared by parsed and reparsed pages."""
    nodes = list(walk_nodes(page.root_nodes))
    assert len({node.uuid for node in nodes}) == len(nodes)

    pending: list[tuple[list[LogseqNode], LogseqNode | None]] = [(page.root_nodes, None)]
    while pending:
        siblings, parent = pending.pop()
        for index, node in enumerate(siblings):
            assert node.parent_id == (parent.uuid if parent is not None else None)
            assert node.left_id == (siblings[index - 1].uuid if index else None)
            expected_path = [node.uuid] if parent is None else [*parent.path, node.uuid]
            assert node.path == expected_path
            expected_outline = [index + 1] if parent is None else [*parent.outline_path, index + 1]
            assert node.outline_path == expected_outline
        pending.extend((node.children, node) for node in reversed(siblings) if node.children)
