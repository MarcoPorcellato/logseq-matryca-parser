from __future__ import annotations

from pathlib import Path

from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage
from logseq_matryca_parser.logos_parser import StackMachineParser
from logseq_matryca_parser.logseq_markdown import (
    _serialize_logseq_node_lines,
    detect_tab_size_from_markdown,
    format_logseq_block_property_lines,
    format_logseq_page_properties,
    serialize_logseq_page,
    write_logseq_page,
)


def test_page_properties_serialize_python_lists_as_comma_separated_values() -> None:
    rendered = format_logseq_page_properties(
        {
            "tags": ["#AI", "[[Agent]]", "parser"],
            "alias": ["[[Demo Page]]", "#Alt"],
            "status": ["WIP", "Review"],
        }
    )
    assert rendered == (
        "tags:: AI, Agent, parser\n"
        "alias:: Demo Page, Alt\n"
        "status:: WIP, Review\n"
        "\n"
    )


def test_page_properties_append_runtime_keys_missing_from_properties_order() -> None:
    rendered = format_logseq_page_properties(
        {
            "alias": "Demo",
            "tags": "parser,logseq",
            "matryca-badge": "true",
        },
        properties_order=["alias", "tags"],
    )
    assert rendered == (
        "alias:: Demo\n"
        "tags:: parser,logseq\n"
        "matryca-badge:: true\n"
        "\n"
    )


def test_serialize_logseq_page_formats_list_tags_and_preserves_missing_page_keys() -> None:
    page = LogseqPage(
        title="Runtime Page",
        raw_content="",
        properties={
            "alias": ["[[Demo Page]]", "#Alt"],
            "tags": ["#AI", "parser"],
            "matryca-badge": "true",
        },
        properties_order=["alias", "tags"],
        root_nodes=[
            LogseqNode(
                uuid="root",
                content="Root block",
                indent_level=0,
            )
        ],
    )
    rendered = serialize_logseq_page(page)
    assert rendered == (
        "alias:: Demo Page, Alt\n"
        "tags:: AI, parser\n"
        "matryca-badge:: true\n"
        "\n"
        "- Root block\n"
    )


def test_page_properties_are_raw_frontmatter_not_bullets() -> None:
    rendered = format_logseq_page_properties({"alias": "Demo", "tags": "parser,logseq"})
    assert rendered == "alias:: Demo\ntags:: parser,logseq\n\n"
    assert not rendered.lstrip().startswith("-")


def test_block_properties_use_parent_plus_two_spaces_before_children() -> None:
    node = LogseqNode(
        uuid="root",
        content="Parent block",
        indent_level=1,
        properties={"id": "11111111-1111-1111-1111-111111111111", "status": "WIP"},
        properties_order=["id", "status"],
        children=[
            LogseqNode(
                uuid="child",
                content="Child block",
                indent_level=2,
                parent_id="root",
            )
        ],
    )
    lines = format_logseq_block_property_lines(node, "  ")
    assert lines == [
        "    id:: 11111111-1111-1111-1111-111111111111",
        "    status:: WIP",
    ]


def test_block_properties_append_runtime_keys_missing_from_properties_order() -> None:
    node = LogseqNode(
        uuid="root",
        content="Parent block",
        indent_level=1,
        properties={
            "id": "11111111-1111-1111-1111-111111111111",
            "matryca-badge": "true",
        },
        properties_order=["id"],
    )
    lines = format_logseq_block_property_lines(node, "  ")
    assert lines == [
        "    id:: 11111111-1111-1111-1111-111111111111",
        "    matryca-badge:: true",
    ]


def test_multiline_block_continuation_lines_use_bullet_text_alignment() -> None:
    node = LogseqNode(
        uuid="root",
        content="First line\nSecond line\nThird line",
        indent_level=1,
        properties={"id": "22222222-2222-2222-2222-222222222222"},
        properties_order=["id"],
    )
    lines = _serialize_logseq_node_lines(node, tab_size=2)
    assert lines == [
        "  - First line",
        "    Second line",
        "    Third line",
        "    id:: 22222222-2222-2222-2222-222222222222",
    ]


def test_multiline_block_roundtrip_preserves_soft_breaks() -> None:
    source = (
        "- Checklist item\n"
        "Second soft-break line\n"
        "  id:: 33333333-3333-3333-3333-333333333333\n"
    )
    parser = StackMachineParser()
    page = parser.parse(source, page_title="multiline-roundtrip")
    root = page.root_nodes[0]

    assert "Checklist item" in root.content
    assert "Second soft-break line" in root.content
    assert "id:: 33333333-3333-3333-3333-333333333333" in root.content
    assert "id" not in root.properties

    rendered = serialize_logseq_page(page)
    reparsed = parser.parse(rendered, page_title="multiline-roundtrip")
    roundtrip_root = reparsed.root_nodes[0]

    assert "Checklist item" in roundtrip_root.content
    assert "Second soft-break line" in roundtrip_root.content
    assert "id" not in roundtrip_root.properties


def test_serialize_logseq_page_roundtrip_matches_logseq_layout() -> None:
    source = (
        "alias:: Resilient Page\n"
        "tags:: parser,logseq\n"
        "\n"
        "- Root block\n"
        "  id:: 22222222-2222-2222-2222-222222222222\n"
        "  - Child block\n"
    )
    parser = StackMachineParser()
    page = parser.parse(source, page_title="Resilient Page")
    rendered = serialize_logseq_page(page)

    assert rendered.startswith("alias:: Resilient Page\n")
    assert "tags:: parser,logseq\n\n" in rendered
    assert "- Root block\n" in rendered
    assert "  id:: 22222222-2222-2222-2222-222222222222\n" in rendered
    assert rendered.index("  id::") < rendered.index("  - Child block")


def test_serialize_logseq_page_preserves_four_space_indent(tmp_path: Path) -> None:
    """Detected ``tab_size`` round-trips four-space outline indentation."""
    from logseq_matryca_parser.logos_parser import StackMachineParser

    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    path = pages / "four.md"
    source = "- root\n    - child\n"
    path.write_text(source, encoding="utf-8")

    page = StackMachineParser().parse_page_file(path)
    assert page.tab_size == 4
    rendered = serialize_logseq_page(page)
    assert rendered == source


def test_write_logseq_page_uses_utf8(tmp_path: Path) -> None:
    page = LogseqPage(
        title="Emoji 🚀",
        raw_content="",
        properties={"tags": "emoji"},
        root_nodes=[
            LogseqNode(
                uuid="root",
                content="Block with café",
                indent_level=0,
            )
        ],
    )
    destination = tmp_path / "emoji.md"
    write_logseq_page(page, destination)
    body = destination.read_text(encoding="utf-8")
    assert body.startswith("tags:: emoji\n\n")
    assert "café" in body
    assert "🚀" not in body


# ── detect_tab_size_from_markdown tests (issue #43) ──────────────────────


class TestDetectTabSize:
    """Unit tests for ``detect_tab_size_from_markdown()`` indent inference."""

    def test_two_space_indent_returns_2(self):
        assert detect_tab_size_from_markdown("- a\n  - b\n    - c\n") == 2

    def test_four_space_indent_returns_4(self):
        assert detect_tab_size_from_markdown("- a\n    - b\n        - c\n") == 4

    def test_single_bullet_returns_default(self):
        assert detect_tab_size_from_markdown("- only one\n") == 2
        assert detect_tab_size_from_markdown("- only one\n", default=4) == 4

    def test_empty_or_whitespace_returns_default(self):
        assert detect_tab_size_from_markdown("") == 2
        assert detect_tab_size_from_markdown("   \n\n") == 2
        assert detect_tab_size_from_markdown("no bullets here\n") == 2

    def test_mixed_two_and_four_uses_gcd(self):
        """When both 2 and 4-space indents appear, gcd is 2."""
        text = "- a\n  - two space\n    - four space\n"
        assert detect_tab_size_from_markdown(text) == 2

    def test_tab_characters_replaced_by_default_width(self):
        text = "- a\n\t- tab child\n"
        result = detect_tab_size_from_markdown(text)
        assert result in (1, 2)  # tab=2 spaces, so indent=2, gcd=2

    def test_only_tabs(self):
        text = "- root\n\t- child\n\t\t- grandchild\n"
        result = detect_tab_size_from_markdown(text, default=2)
        assert isinstance(result, int)
        assert result >= 1
