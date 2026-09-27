"""Bounded generated assurance for valid Logseq outline parsing."""

from __future__ import annotations

from dataclasses import dataclass
from string import ascii_lowercase, digits

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage
from logseq_matryca_parser.logos_parser import StackMachineParser
from logseq_matryca_parser.logseq_markdown import serialize_logseq_page
from tests.parser_assurance.invariants import assert_tree_invariants
from tests.parser_assurance.projection import IdentityPolicy, project_page

_MAX_DEPTH = 5
_MAX_NODES = 16
_MAX_SOURCE_BYTES = 16 * 1024
_ROUNDTRIP_IDENTITY_POLICY = IdentityPolicy(
    synthetic_uuid="recomputed",
    source_uuid="absent",
    relations="outline_paths",
)


@dataclass(frozen=True)
class Outline:
    """Independent, immutable model of one block and its ordered children."""

    content: str
    children: tuple[Outline, ...] = ()


def _block_text_strategy() -> SearchStrategy[str]:
    # Alphanumeric-only text is a safe single line: no block, property, task,
    # reference, macro, asset, or continuation syntax is generated.
    return st.text(alphabet=ascii_lowercase + digits, min_size=1, max_size=24)


def _outline_strategy(depth: int = 0, budget: int = _MAX_NODES) -> SearchStrategy[Outline]:
    @st.composite
    def build(draw: st.DrawFn) -> Outline:
        content = draw(_block_text_strategy())
        if depth >= _MAX_DEPTH or budget == 1:
            return Outline(content)

        child_count = draw(st.integers(min_value=0, max_value=min(3, budget - 1)))
        remaining_budget = budget - 1
        children: list[Outline] = []
        for index in range(child_count):
            later_children = child_count - index - 1
            child_budget = draw(
                st.integers(min_value=1, max_value=remaining_budget - later_children)
            )
            remaining_budget -= child_budget
            children.append(draw(_outline_strategy(depth + 1, child_budget)))
        return Outline(content, tuple(children))

    return build()


def _render_outline(outline: Outline) -> str:
    lines: list[str] = []

    def append(node: Outline, depth: int) -> None:
        lines.append(f"{'  ' * depth}- {node.content}")
        for child in node.children:
            append(child, depth + 1)

    append(outline, 0)
    return "\n".join(lines) + "\n"


def _roundtrip_fixture_strategy() -> SearchStrategy[tuple[Outline, str, str]]:
    safe_value = st.text(alphabet=ascii_lowercase + digits, min_size=1, max_size=12)
    return st.tuples(_outline_strategy(), safe_value, safe_value)


def _render_roundtrip_fixture(outline: Outline, property_value: str, target: str) -> str:
    linked_outline = Outline(f"{outline.content} [[{target}]]", outline.children)
    lines = [f"- {linked_outline.content}", f"  status:: {property_value}"]

    def append_children(node: Outline, depth: int) -> None:
        for child in node.children:
            lines.append(f"{'  ' * depth}- {child.content}")
            append_children(child, depth + 1)

    append_children(linked_outline, 1)
    return "\n".join(lines) + "\n"


def _assert_model_bounds(outline: Outline) -> None:
    pending = [(outline, 0)]
    node_count = 0
    while pending:
        node, depth = pending.pop()
        node_count += 1
        assert depth <= _MAX_DEPTH
        assert len(node.children) <= 3
        pending.extend((child, depth + 1) for child in node.children)
    assert node_count <= _MAX_NODES


def _parsed_outline(nodes: list[LogseqNode]) -> tuple[Outline, ...]:
    return tuple(Outline(node.content, _parsed_outline(node.children)) for node in nodes)


def _assert_matches_model(page: LogseqPage, expected: Outline) -> None:
    assert _parsed_outline(page.root_nodes) == (expected,)


@settings(
    max_examples=40,
    derandomize=True,
    deadline=None,
    database=None,
    print_blob=True,
)
@given(model=_outline_strategy())
def test_valid_generated_outlines_match_independent_recursive_model(model: Outline) -> None:
    _assert_model_bounds(model)
    source = _render_outline(model)
    assert source.endswith("\n")
    assert len(source.encode("utf-8")) <= _MAX_SOURCE_BYTES

    page = StackMachineParser().parse(source, page_title="generated-outline")

    _assert_matches_model(page, model)
    assert_tree_invariants(page)


@settings(
    max_examples=40,
    derandomize=True,
    deadline=None,
    database=None,
    print_blob=True,
)
@given(fixture=_roundtrip_fixture_strategy())
def test_generated_simple_properties_and_wikilinks_survive_semantic_roundtrip(
    fixture: tuple[Outline, str, str],
) -> None:
    outline, property_value, target = fixture
    _assert_model_bounds(outline)
    source = _render_roundtrip_fixture(outline, property_value, target)
    assert source.endswith("\n")
    assert len(source.encode("utf-8")) <= _MAX_SOURCE_BYTES

    parser = StackMachineParser()
    first = parser.parse(source, page_title="generated-semantic-roundtrip")
    expected_outline = Outline(f"{outline.content} [[{target}]]", outline.children)
    _assert_matches_model(first, expected_outline)
    generated_root = first.root_nodes[0]
    assert generated_root.properties["status"] == property_value
    assert generated_root.wikilinks == [target]
    assert generated_root.refs == [target]
    assert_tree_invariants(first)

    serialized = serialize_logseq_page(first)
    second = parser.parse(serialized, page_title="generated-semantic-roundtrip")
    assert_tree_invariants(second)

    assert project_page(
        first,
        profile="semantic_roundtrip_v1",
        identity_policy=_ROUNDTRIP_IDENTITY_POLICY,
    ) == project_page(
        second,
        profile="semantic_roundtrip_v1",
        identity_policy=_ROUNDTRIP_IDENTITY_POLICY,
    )


def test_semantic_projection_rejects_changed_block_content() -> None:
    page = StackMachineParser().parse(
        "- original\n  status:: active\n", page_title="projection-negative-control"
    )
    node = page.root_nodes[0]
    changed_node = node.model_copy(update={"content": "changed"})
    changed_page = page.model_copy(update={"root_nodes": [changed_node]})

    assert project_page(
        page,
        profile="semantic_roundtrip_v1",
        identity_policy=_ROUNDTRIP_IDENTITY_POLICY,
    ) != project_page(
        changed_page,
        profile="semantic_roundtrip_v1",
        identity_policy=_ROUNDTRIP_IDENTITY_POLICY,
    )


def test_recursive_model_oracle_rejects_reparenting_with_same_preorder() -> None:
    expected = Outline("root", (Outline("child", (Outline("grandchild"),)),))
    page = StackMachineParser().parse(
        "- root\n  - child\n    - grandchild\n", page_title="oracle-sensitivity"
    )
    root = page.root_nodes[0]
    child = root.children[0]
    grandchild = child.children[0]

    promoted_grandchild = grandchild.model_copy(
        update={
            "parent_id": root.uuid,
            "left_id": child.uuid,
            "path": [*root.path, grandchild.uuid],
            "outline_path": [*root.outline_path, 2],
        }
    )
    promoted_child = child.model_copy(update={"children": []})
    mutated_root = root.model_copy(update={"children": [promoted_child, promoted_grandchild]})
    mutated_page = page.model_copy(update={"root_nodes": [mutated_root]})

    assert [node.uuid for node in _preorder(mutated_page.root_nodes)] == [
        node.uuid for node in _preorder(page.root_nodes)
    ]
    assert_tree_invariants(mutated_page)
    with pytest.raises(AssertionError):
        _assert_matches_model(mutated_page, expected)


def test_tree_invariants_reject_wrong_parent_pointer() -> None:
    page = StackMachineParser().parse("- root\n  - child\n", page_title="parent-control")
    root = page.root_nodes[0]
    child = root.children[0].model_copy(update={"parent_id": "not-the-root"})
    corrupted_root = root.model_copy(update={"children": [child]})
    corrupted_page = page.model_copy(update={"root_nodes": [corrupted_root]})

    with pytest.raises(AssertionError):
        assert_tree_invariants(corrupted_page)


def test_tree_invariants_reject_wrong_left_pointer() -> None:
    page = StackMachineParser().parse(
        "- root\n  - first\n  - second\n", page_title="left-control"
    )
    root = page.root_nodes[0]
    second = root.children[1].model_copy(update={"left_id": None})
    corrupted_root = root.model_copy(
        update={"children": [root.children[0], second]}
    )
    corrupted_page = page.model_copy(update={"root_nodes": [corrupted_root]})

    with pytest.raises(AssertionError):
        assert_tree_invariants(corrupted_page)


def _preorder(nodes: list[LogseqNode]) -> list[LogseqNode]:
    ordered: list[LogseqNode] = []
    for node in nodes:
        ordered.append(node)
        ordered.extend(_preorder(node.children))
    return ordered
