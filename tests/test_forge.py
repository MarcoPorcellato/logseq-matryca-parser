import json
import re

import pytest

from logseq_matryca_parser.forge import (
    FlatListForgeVisitor,
    ForgeExporter,
    JSONForgeVisitor,
    MarkdownForgeVisitor,
)
from logseq_matryca_parser.logos_core import LogseqNode


@pytest.fixture
def sample_ast() -> list[LogseqNode]:
    child = LogseqNode(
        uuid="456",
        content="Figlio",
        indent_level=1,
        properties={"custom": "valore"},
        parent_id="123",
    )
    root = LogseqNode(uuid="123", content="Radice", indent_level=0, children=[child])
    return [root]


def test_forge_clean_markdown(sample_ast: list[LogseqNode]) -> None:
    md_output = ForgeExporter.to_clean_markdown(sample_ast)
    assert "- Radice" in md_output
    assert "  - Figlio" in md_output
    assert "[:custom valore]" in md_output


def test_forge_flat_list(sample_ast: list[LogseqNode]) -> None:
    flat = ForgeExporter.to_flat_list(sample_ast)
    assert len(flat) == 2
    assert flat[1]["parent_id"] == "123"


def test_forge_json_nested_structure(sample_ast: list[LogseqNode]) -> None:
    json_payload = json.loads(ForgeExporter.to_json(sample_ast))
    assert len(json_payload) == 1
    assert json_payload[0]["uuid"] == "123"
    assert len(json_payload[0]["children"]) == 1
    assert json_payload[0]["children"][0]["uuid"] == "456"


def test_forge_obsidian_markdown_translation() -> None:
    block_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    child = LogseqNode(
        uuid="22222222-2222-2222-2222-222222222222",
        content="Target block",
        clean_text="Target block",
        indent_level=1,
        parent_id="11111111-1111-1111-1111-111111111111",
        source_uuid=block_id,
        synthetic_id=True,
        properties={"id": block_id},
    )
    root = LogseqNode(
        uuid="11111111-1111-1111-1111-111111111111",
        content=f"Ref (({block_id})) and [[Wiki Page]]",
        clean_text=f"Ref (({block_id})) and [[Wiki Page]]",
        indent_level=0,
        block_refs=[block_id],
        children=[child],
    )
    page_props = {"title": "MyPage", "type": "project"}
    md = ForgeExporter.to_obsidian_markdown([root], page_props)
    assert md.startswith("---\n")
    assert "type: project" in md
    assert "title: MyPage" in md
    assert "id::" not in md
    assert "[[Wiki Page]]" in md
    assert re.search(r"\[\[MyPage#\^[0-9a-f]+\]\]", md)
    assert not re.search(r"\(\([a-f0-9-]{36}\)\)", md)
    assert "Target block ^" in md


@pytest.mark.parametrize(
    ("visitor_cls", "method_name"),
    [
        (JSONForgeVisitor, "get_json"),
        (FlatListForgeVisitor, "get_data"),
        (MarkdownForgeVisitor, "get_markdown"),
    ],
)
def test_forge_visitors_are_ast_compatible(visitor_cls: type[object], method_name: str) -> None:
    visitor = visitor_cls()  # type: ignore[call-arg]
    assert hasattr(visitor, "visit_node")
    assert hasattr(visitor, "depart_node")
    assert hasattr(visitor, method_name)