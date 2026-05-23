from __future__ import annotations

from pathlib import Path

from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage
from logseq_matryca_parser.logos_parser import StackMachineParser
from logseq_matryca_parser.logseq_markdown import (
    _serialize_logseq_node_lines,
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
    rendered = serialize_logseq_page(page)

    assert rendered == (
        "- Checklist item\n"
        "  Second soft-break line\n"
        "  id:: 33333333-3333-3333-3333-333333333333\n"
    )

    reparsed = parser.parse(rendered, page_title="multiline-roundtrip")
    root = reparsed.root_nodes[0]

    assert "Checklist item" in root.content
    assert "Second soft-break line" in root.content
    assert root.properties["id"] == "33333333-3333-3333-3333-333333333333"


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
