from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

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
from tests.parser_assurance.invariants import assert_tree_invariants
from tests.parser_assurance.projection import IdentityPolicy, project_page


@pytest.mark.parametrize("tab_size", [2, 4])
@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_scalar_metadata_survives_multiline_roundtrip(tab_size: int, newline: str) -> None:
    child_indent = " " * tab_size
    child_text_indent = child_indent + "  "
    source = newline.join(
        [
            "- root",
            "  literal-key:: kept",
            "  root continuation",
            "  lateproperty:: literal",
            f"{child_indent}- child",
            f"{child_text_indent}id:: 11111111-1111-1111-1111-111111111111",
            f"{child_text_indent}literal-key:: child-value",
            f"{child_text_indent}child continuation",
            "",
        ]
    )
    parser = StackMachineParser(tab_size=tab_size)
    original = parser.parse(source, page_title="scalar-roundtrip")
    assert len(original.root_nodes) == 1
    root = original.root_nodes[0]
    assert len(root.children) == 1
    assert root.properties == {"literal-key": "kept"}
    assert root.children[0].properties == {
        "id": "11111111-1111-1111-1111-111111111111",
        "literal-key": "child-value",
    }

    rendered = serialize_logseq_page(original)
    reparsed = parser.parse(rendered, page_title=original.title)
    assert len(reparsed.root_nodes) == 1
    assert len(reparsed.root_nodes[0].children) == 1
    for page in (original, reparsed):
        assert_tree_invariants(page)
        current_root = page.root_nodes[0]
        child = current_root.children[0]
        assert current_root.properties == {"literal-key": "kept"}
        assert child.properties == {
            "id": "11111111-1111-1111-1111-111111111111",
            "literal-key": "child-value",
        }
        assert "lateproperty" not in current_root.properties
        assert "lateproperty:: literal" in current_root.content
        assert child.source_uuid == "11111111-1111-1111-1111-111111111111"
        assert child.synthetic_id is False
    assert reparsed.root_nodes[0].content == root.content
    assert reparsed.root_nodes[0].children[0].content == root.children[0].content
    assert rendered.index("  literal-key:: kept\n") < rendered.index("  root continuation\n")
    assert rendered.index(f"{child_text_indent}id::") < rendered.index(
        f"{child_text_indent}child continuation\n"
    )
    assert "\r" not in rendered
    policy: IdentityPolicy = {
        "synthetic_uuid": "recomputed",
        "source_uuid": "preserve",
        "relations": "outline_paths",
    }
    assert project_page(
        reparsed, profile="semantic_roundtrip_v1", identity_policy=policy
    ) == project_page(original, profile="semantic_roundtrip_v1", identity_policy=policy)


@pytest.mark.parametrize(
    ("value", "property_lines"),
    [
        ("", ["  status:: "]),
        ("   ", ["  status::    "]),
        ('""', ['  status:: ""']),
        ("''", ["  status:: ''"]),
        ('" "', ['  status:: " "']),
        ("one\ntwo", ["  status:: one\ntwo"]),
        ("one\rtwo", ["  status:: one\rtwo"]),
        (["one"], ["  status::", "    - one"]),
        (("one",), ["  status::", "    - one"]),
        ({"one"}, ["  status::", "    - one"]),
        ([], ["  status::"]),
        ({"nested": "value"}, ["  status:: {'nested': 'value'}"]),
        (None, ["  status:: None"]),
    ],
)
def test_excluded_property_values_keep_legacy_output(value: Any, property_lines: list[str]) -> None:
    node = LogseqNode(
        uuid="root",
        content="Root\nContinuation",
        properties={"status": value, "other": "kept"},
        indent_level=0,
    )
    assert _serialize_logseq_node_lines(node, tab_size=2) == [
        "- Root",
        "  Continuation",
        *property_lines,
        "  other:: kept",
    ]


@pytest.mark.parametrize(
    ("content", "content_lines"),
    [
        ("Root", ["- Root"]),
        ("Root\n", ["- Root"]),
        ("Root\n\n", ["- Root", "  "]),
        ("Root\n```python\nprint(1)\n```", ["- Root", "  ```python", "  print(1)", "  ```"]),
        ("Root\n~~~\ncode\n~~~", ["- Root", "  ~~~", "  code", "  ~~~"]),
        ("```python\ncode\n```", ["- ```python", "  code", "  ```"]),
        ("Root\n{{query (task TODO)}}", ["- Root", "  {{query (task TODO)}}"]),
        ("Root\n:LOGBOOK:\n:END:", ["- Root", "  :LOGBOOK:", "  :END:"]),
        ("Root\n> quotation", ["- Root", "  > quotation"]),
        ("Root\n- list item", ["- Root", "  - list item"]),
        ("Root\n    indented code", ["- Root", "    indented code"]),
    ],
)
def test_complex_content_keeps_legacy_metadata_order(
    content: str, content_lines: list[str]
) -> None:
    node = LogseqNode(uuid="root", content=content, properties={"status": "kept"}, indent_level=0)
    assert _serialize_logseq_node_lines(node, tab_size=2) == [*content_lines, "  status:: kept"]


def test_mixed_drawer_list_scalar_keeps_exact_legacy_output() -> None:
    node = LogseqNode(
        uuid="root",
        content="Root\nContinuation",
        properties={"status": "kept", "tags": ["topic"], "logbook": ["CLOCK: fixed"]},
        indent_level=0,
    )
    assert _serialize_logseq_node_lines(node, tab_size=2) == [
        "- Root",
        "  Continuation",
        "  :LOGBOOK:",
        "  CLOCK: fixed",
        "  :END:",
        "  status:: kept",
        "  tags::",
        "    - topic",
    ]


def test_scalar_metadata_order_ignores_non_emitted_derived_values() -> None:
    node = LogseqNode(
        uuid="root",
        content="Root\nContinuation",
        properties={"scheduled": {"derived": True}, "status": "kept"},
        properties_order=["scheduled", "status"],
        indent_level=0,
    )
    assert _serialize_logseq_node_lines(node, tab_size=2) == [
        "- Root",
        "  status:: kept",
        "  Continuation",
    ]


@pytest.mark.parametrize(
    ("value", "rendered"), [("kept", "kept"), (True, "True"), (7, "7"), (1.5, "1.5")]
)
def test_builtin_scalar_metadata_uses_existing_format_before_prose(value: Any, rendered: str) -> None:
    node = LogseqNode(
        uuid="root", content="Root\nContinuation", properties={"status": value}, indent_level=0
    )
    assert _serialize_logseq_node_lines(node, tab_size=2) == [
        "- Root", f"  status:: {rendered}", "  Continuation"
    ]


def test_arbitrary_scalar_looking_object_keeps_legacy_order() -> None:
    class ScalarLooking:
        def __str__(self) -> str:
            return "kept"

    node = LogseqNode(
        uuid="root", content="Root\nContinuation", properties={"status": ScalarLooking()}, indent_level=0
    )
    assert _serialize_logseq_node_lines(node, tab_size=2) == [
        "- Root", "  Continuation", "  status:: kept"
    ]


def test_derived_only_metadata_does_not_change_prose_output() -> None:
    node = LogseqNode(
        uuid="root", content="Root\nContinuation", properties={"scheduled": "derived"}, indent_level=0
    )
    assert _serialize_logseq_node_lines(node, tab_size=2) == ["- Root", "  Continuation"]


def test_invalid_property_key_keeps_legacy_order() -> None:
    node = LogseqNode(
        uuid="root", content="Root\nContinuation", properties={"not a key": "kept"}, indent_level=0
    )
    assert _serialize_logseq_node_lines(node, tab_size=2) == [
        "- Root", "  Continuation", "  not a key:: kept"
    ]


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
        "    id:: 22222222-2222-2222-2222-222222222222",
        "    Second line",
        "    Third line",
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
