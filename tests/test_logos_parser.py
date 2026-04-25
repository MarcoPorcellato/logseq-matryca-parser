"""Hardening tests for the LOGOS stack-machine parser."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from logseq_matryca_parser.exceptions import BlockReferenceError, LogseqIndentationError
from logseq_matryca_parser.logos_parser import LogosParser, StackMachineParser, is_system_block


@pytest.fixture
def parser() -> StackMachineParser:
    """Create a parser configured with 2-space indentation."""
    return LogosParser(tab_size=2)


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        (":LOGBOOK:", True),
        ("  :logbook:", True),
        ("CLOCK: [2026-04-25 Sat 10:12]--[2026-04-25 Sat 10:30]", True),
        ("collapsed:: true", True),
        ("  END:", True),
        ("- user content", False),
        ("id:: 01234567-89ab-cdef-0123-456789abcdef", False),
        ("custom:: value", False),
    ],
)
def test_is_system_block_detection(line: str, expected: bool) -> None:
    """System metadata lines are identified and regular content is preserved."""
    assert is_system_block(line) is expected


def test_zero_to_four_space_fracture_binds_to_root(parser: StackMachineParser) -> None:
    """A direct 0->4 space jump is legal and binds to root."""
    content = "- Root\n    - Four space child"
    page = parser.parse(content, page_title="space-fracture")

    assert len(page.root_nodes) == 1
    assert len(page.root_nodes[0].children) == 1
    assert page.root_nodes[0].children[0].content == "Four space child"


def test_misaligned_indentation_still_raises(parser: StackMachineParser) -> None:
    """Non-tab-size aligned indentation remains invalid."""
    with pytest.raises(LogseqIndentationError):
        parser.parse("- Root\n   - Misaligned indentation", page_title="invalid-indentation")


@pytest.mark.parametrize(
    "missing_uuid",
    [
        "01234567-89ab-cdef-0123-456789abcdef",
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    ],
)
def test_unresolved_block_reference_raises(
    parser: StackMachineParser, missing_uuid: str
) -> None:
    """Unresolved ((uuid)) references trigger BlockReferenceError."""
    content = f"- Root with missing ref (({missing_uuid}))"
    with pytest.raises(BlockReferenceError):
        parser.parse(content, page_title="missing-ref")


def test_resolved_block_reference_does_not_raise(parser: StackMachineParser) -> None:
    """References to registered local block UUIDs must remain valid."""
    existing_uuid = "11111111-1111-1111-1111-111111111111"
    content = (
        "- Root\n"
        f"  id:: {existing_uuid}\n"
        f"  - Child referencing parent (({existing_uuid}))"
    )

    page = parser.parse(content, page_title="resolved-ref")
    assert len(page.root_nodes) == 1
    assert page.root_nodes[0].uuid == existing_uuid
    assert page.root_nodes[0].children[0].block_refs == [existing_uuid]


@pytest.mark.parametrize(
    "noise_line",
    [
        ":LOGBOOK:",
        "CLOCK: [2026-04-25 Sat 10:12]--[2026-04-25 Sat 10:30] =>  0:18:00",
        "collapsed:: true",
    ],
)
def test_system_noise_is_dropped_from_ast(
    parser: StackMachineParser, noise_line: str
) -> None:
    """System lines are ignored and never pollute content or clean_text."""
    content = f"- Root\n{noise_line}\n  - Child"
    page = parser.parse(content, page_title="noise-filter")

    assert len(page.root_nodes) == 1
    root = page.root_nodes[0]
    assert root.content == "Root"
    assert root.clean_text == "Root"
    assert len(root.children) == 1
    assert root.children[0].content == "Child"
    assert noise_line not in root.content
    assert noise_line not in root.clean_text


def test_parse_file_empty_returns_no_nodes(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Empty files return no nodes and emit a warning message."""
    file_path = tmp_path / "empty.md"
    file_path.write_text("   \n\n  ", encoding="utf-8")

    with caplog.at_level(logging.WARNING):
        roots = LogosParser().parse_file(file_path)

    assert roots == []
    assert "vuoto" in caplog.text


@pytest.mark.parametrize(
    ("content", "expected_properties"),
    [
        (
            "title:: Resilient Page\ntags:: parser,logseq\n- Root block",
            {"title": "Resilient Page", "tags": "parser,logseq"},
        ),
        (
            "  title:: Indented Frontmatter\n\n- Root block",
            {"title": "Indented Frontmatter"},
        ),
    ],
)
def test_frontmatter_properties_are_stored_at_page_level(
    parser: StackMachineParser, content: str, expected_properties: dict[str, str]
) -> None:
    """Leading key::value metadata is parsed as page properties, not block nodes."""
    page = parser.parse(content, page_title="frontmatter")
    assert page.properties == expected_properties
    assert len(page.root_nodes) == 1
    assert page.root_nodes[0].content == "Root block"


def test_multiline_clean_text_strips_property_lines_only(parser: StackMachineParser) -> None:
    """Shift+Enter style multiline content drops property lines but keeps text newlines."""
    content = "- First line\n  body:: hidden metadata\n  Third line"
    page = parser.parse(content, page_title="multiline")
    root = page.root_nodes[0]

    assert root.properties["body"] == "hidden metadata"
    assert root.clean_text == "First line\nThird line"


@pytest.mark.parametrize(
    "content",
    [
        "- Root\n  tags::\n    - Alpha\n    - Beta",
        "- Root\n  aliases::\n    - One",
    ],
)
def test_list_properties_do_not_crash_and_keep_children(
    parser: StackMachineParser, content: str
) -> None:
    """Property keys followed by bullet lists remain parseable and keep child blocks."""
    page = parser.parse(content, page_title="list-property")
    root = page.root_nodes[0]

    assert len(root.children) >= 1


@pytest.mark.parametrize(
    "content",
    [
        "- Code sample\n  ```python\n  id:: 11111111-1111-1111-1111-111111111111\n  CLOCK: [2026-04-25 Sat 10:12]\n  print('hi')\n  ```",
        "- Query\n  ```sql\n  collapsed:: true\n  SELECT * FROM table;\n  ```",
    ],
)
def test_code_block_immunity_preserves_literal_lines(
    parser: StackMachineParser, content: str
) -> None:
    """Lines inside fenced code blocks remain literal parser-immune content."""
    page = parser.parse(content, page_title="code-fence")
    root = page.root_nodes[0]

    assert "```" in root.content
    assert "id::" in root.content or "collapsed::" in root.content
    assert "CLOCK:" in root.content or "SELECT * FROM table;" in root.content
    assert root.properties == {}


@pytest.mark.parametrize(
    ("raw_block", "expected_status", "expected_clean"),
    [
        ("TODO Write parser", "TODO", "Write parser"),
        ("DOING Mid task", "DOING", "Mid task"),
        ("DONE Finish docs", "DONE", "Finish docs"),
        ("LATER revisit", "LATER", "revisit"),
        ("NOW ship", "NOW", "ship"),
        ("WAITING review", "WAITING", "review"),
        ("CANCELED old idea", "CANCELED", "old idea"),
    ],
)
def test_task_marker_extraction(
    parser: StackMachineParser, raw_block: str, expected_status: str, expected_clean: str
) -> None:
    """Known task markers are extracted and removed from clean text."""
    page = parser.parse(f"- {raw_block}", page_title="tasks")
    root = page.root_nodes[0]

    assert root.task_status == expected_status
    assert root.clean_text == expected_clean


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (
            "- TODO Plan launch SCHEDULED: <2026-04-30 Thu>\n  Details",
            {"scheduled": "<2026-04-30 Thu>"},
        ),
        (
            "- DONE Finish draft DEADLINE: <2026-05-01 Fri>",
            {"deadline": "<2026-05-01 Fri>"},
        ),
    ],
)
def test_time_topology_is_extracted_and_stripped(
    parser: StackMachineParser, content: str, expected: dict[str, str]
) -> None:
    """SCHEDULED/DEADLINE tokens are moved to properties and removed from clean_text."""
    page = parser.parse(content, page_title="timeline")
    root = page.root_nodes[0]

    for key, value in expected.items():
        assert root.properties[key] == value
    assert "SCHEDULED:" not in root.clean_text
    assert "DEADLINE:" not in root.clean_text


@pytest.mark.parametrize(
    "content",
    [
        "- Root\n  - {{cloze hidden answer}}",
        "- Root\n  - {{embed ((22222222-2222-2222-2222-222222222222))}}",
    ],
)
def test_macros_are_handled_as_content_without_crash(
    parser: StackMachineParser, content: str
) -> None:
    """Macros remain valid block content and do not break AST building."""
    page = parser.parse(content, page_title="macro")
    root = page.root_nodes[0]
    child = root.children[0]

    assert "{{" in child.content and "}}" in child.content


def test_absolute_indentation_overrides_heading_semantics(parser: StackMachineParser) -> None:
    """Indented headings become children by whitespace, not heading depth."""
    content = "- Parent\n  - ### Child Heading"
    page = parser.parse(content, page_title="heading-indent")

    parent = page.root_nodes[0]
    child = parent.children[0]
    assert child.content == "### Child Heading"
    assert child.properties["heading_level"] == 3


def test_empty_logbook_drawer_tolerance(parser: StackMachineParser) -> None:
    """An empty :LOGBOOK: drawer does not swallow following blocks."""
    content = "- Root\n  :LOGBOOK:\n  :END:\n  - Child after drawer"
    page = parser.parse(content, page_title="drawer")

    root = page.root_nodes[0]
    assert root.properties["logbook"] == []
    assert len(root.children) == 1
    assert root.children[0].content == "Child after drawer"


@pytest.mark.parametrize(
    ("content", "expected_tags", "expected_ref"),
    [
        (
            "- Root #[[Complex Tag]]",
            ["Complex Tag"],
            None,
        ),
        (
            "- Root [My Alias](((12345678-1234-1234-1234-1234567890ab)))\n"
            "  - Target\n"
            "    id:: 12345678-1234-1234-1234-1234567890ab",
            [],
            "12345678-1234-1234-1234-1234567890ab",
        ),
    ],
)
def test_complex_tag_aliasing_patterns(
    parser: StackMachineParser,
    content: str,
    expected_tags: list[str],
    expected_ref: str | None,
) -> None:
    """Complex tags and aliased block refs are parsed with official patterns."""
    page = parser.parse(content, page_title="complex-alias")
    root = page.root_nodes[0]

    assert root.tags == expected_tags
    if expected_ref is not None:
        assert expected_ref in root.block_refs