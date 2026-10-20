"""Regressions for non-empty pages that contain metadata but no blocks."""

from __future__ import annotations

from pathlib import Path

import pytest

from logseq_matryca_parser.logos_parser import StackMachineParser


@pytest.mark.parametrize("line_ending", ["\n", "\r\n"], ids=["LF", "CRLF"])
def test_metadata_only_text_page_preserves_page_metadata(line_ending: str) -> None:
    lines = [
        "TiTlE:: Sprint Plan",
        "aLIas:: Sprint Board",
        "ReLaTeD:: [[Alpha]] and [Beta label]([[Beta]])",
    ]
    content = line_ending.join(lines) + line_ending

    page = StackMachineParser().parse(content, page_title="input-title")

    assert page.title == "Sprint Plan"
    assert page.properties == {
        "title": "Sprint Plan",
        "alias": "Sprint Board",
        "related": "[[Alpha]] and [Beta label]([[Beta]])",
    }
    assert page.properties_order == ["title", "alias", "related"]
    assert page.raw_content == content
    assert page.refs == ["Sprint Board", "Alpha", "Beta"]
    assert page.root_nodes == []


def test_metadata_only_file_page_and_compatibility_reader(tmp_path: Path) -> None:
    content = (
        "TiTlE:: Sprint Plan\n"
        "aLIas:: Sprint Board\n"
        "ReLaTeD:: [[Alpha]] and [Beta label]([[Beta]])\n"
    )
    source_path = tmp_path / "metadata-only.md"
    source_path.write_text(content, encoding="utf-8")
    parser = StackMachineParser()

    page = parser.parse_page_file(source_path)

    assert page.title == "Sprint Plan"
    assert page.properties == {
        "title": "Sprint Plan",
        "alias": "Sprint Board",
        "related": "[[Alpha]] and [Beta label]([[Beta]])",
    }
    assert page.properties_order == ["title", "alias", "related"]
    assert page.raw_content == content
    assert page.refs == ["Sprint Board", "Alpha", "Beta"]
    assert page.root_nodes == []
    assert parser.parse_file(source_path) == []
