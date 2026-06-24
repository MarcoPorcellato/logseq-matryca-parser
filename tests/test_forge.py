import json
import re

import pytest

from logseq_matryca_parser.forge import (
    FlatListForgeVisitor,
    ForgeExporter,
    JSONForgeVisitor,
    MarkdownForgeVisitor,
    ObsidianForgeVisitor,
    _build_local_embed_index,
    _page_properties_to_yaml_frontmatter,
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
        synthetic_id=False,
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


# ── direct ObsidianForgeVisitor tests (issue #30) ────────────────────────


class TestObsidianForgeVisitorDirect:
    """Unit tests for ObsidianForgeVisitor constructed directly (not via ForgeExporter)."""

    def test_yaml_frontmatter_from_page_properties(self):
        """_page_properties_to_yaml_frontmatter emits --- delimited YAML."""
        props = {"title": "MyPage", "type": "project", "tags": "a, b"}
        header = _page_properties_to_yaml_frontmatter(props)
        assert header.startswith("---\n")
        assert "title: MyPage" in header
        assert "type: project" in header
        assert header.endswith("---\n\n")

    def test_yaml_frontmatter_empty_properties_returns_empty(self):
        assert _page_properties_to_yaml_frontmatter({}) == ""

    def test_local_embed_index_maps_uuids(self):
        """_build_local_embed_index maps a flat node list by uuid."""
        flat = [
            LogseqNode(uuid="aaa", content="A", indent_level=0),
            LogseqNode(uuid="bbb", content="B", indent_level=0),
        ]
        index = _build_local_embed_index(flat)
        assert "aaa" in index
        assert "bbb" in index
        assert index["aaa"].content == "A"

    def test_visitor_constructs_with_minimal_params(self, sample_ast):
        visitor = ObsidianForgeVisitor(
            page_title="TestPage",
            suffix_map={},
            needs_suffix=set(),
            local_index={},
            embed_resolver=None,
            header="---\n---\n\n",
        )
        sample_ast[0].accept(visitor)
        output = visitor.get_markdown()
        assert "- Radice" in output
        assert output.startswith("---\n")

    def test_visitor_appends_trailing_block_anchor(self):
        """A node needing a suffix gets ^anchor appended to its line."""
        node = LogseqNode(
            uuid="target-uuid-12345678",
            content="Target block",
            clean_text="Target block",
            indent_level=0,
        )
        suffix_map = {"target-uuid-12345678": "myanchor"}
        visitor = ObsidianForgeVisitor(
            page_title="P",
            suffix_map=suffix_map,
            needs_suffix={"target-uuid-12345678"},
            local_index={},
            embed_resolver=None,
            header="",
        )
        node.accept(visitor)
        output = visitor.get_markdown()
        assert "Target block ^myanchor" in output

    def test_visitor_node_without_suffix_no_anchor(self):
        """A node NOT in needs_suffix gets no ^anchor."""
        node = LogseqNode(
            uuid="plain-node",
            content="Plain block",
            clean_text="Plain block",
            indent_level=0,
        )
        visitor = ObsidianForgeVisitor(
            page_title="P",
            suffix_map={},
            needs_suffix=set(),
            local_index={},
            embed_resolver=None,
            header="",
        )
        node.accept(visitor)
        output = visitor.get_markdown()
        assert output.strip() == "- Plain block"

    def test_uuid_to_anchor_with_mock_resolver(self):
        """A mock embed_resolver transforms ((uuid)) → [[Other#^anchor]]."""
        block_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        node = LogseqNode(
            uuid="ref-node",
            content=f"Ref (({block_id}))",
            clean_text=f"Ref (({block_id}))",
            indent_level=0,
            block_refs=[block_id],
        )

        def mock_resolver(uid: str) -> tuple[str, str] | None:
            if uid == block_id:
                return ("OtherPage", "other-anchor")
            return None

        visitor = ObsidianForgeVisitor(
            page_title="CurrentPage",
            suffix_map={},
            needs_suffix=set(),
            local_index={},
            embed_resolver=mock_resolver,
            header="",
        )
        node.accept(visitor)
        output = visitor.get_markdown()
        assert "[[OtherPage#^other-anchor]]" in output
        assert "((" not in output

    def test_visitor_preserves_wikilinks(self):
        """Wikilinks [[Page]] pass through unchanged."""
        node = LogseqNode(
            uuid="wiki-node",
            content="See [[Target Page]]",
            clean_text="See [[Target Page]]",
            indent_level=0,
        )
        visitor = ObsidianForgeVisitor(
            page_title="P",
            suffix_map={},
            needs_suffix=set(),
            local_index={},
            embed_resolver=None,
            header="",
        )
        node.accept(visitor)
        output = visitor.get_markdown()
        assert "[[Target Page]]" in output

    def test_visitor_strips_inline_id_property(self):
        """Inline id:: UUID is stripped from output."""
        node = LogseqNode(
            uuid="with-id",
            content="Text id:: aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee more",
            clean_text="Text id:: aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee more",
            indent_level=0,
        )
        visitor = ObsidianForgeVisitor(
            page_title="P",
            suffix_map={},
            needs_suffix=set(),
            local_index={},
            embed_resolver=None,
            header="",
        )
        node.accept(visitor)
        output = visitor.get_markdown()
        assert "id::" not in output