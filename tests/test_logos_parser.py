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


@pytest.mark.parametrize(
    "content",
    [
        "- Root\n      - Impossible jump to level 3",
        "- Root\n   - Misaligned indentation",
    ],
)
def test_indentation_impossibilities_raise(
    parser: StackMachineParser, content: str
) -> None:
    """Parser rejects impossible or malformed indentation transitions."""
    with pytest.raises(LogseqIndentationError):
        parser.parse(content, page_title="invalid-indentation")


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