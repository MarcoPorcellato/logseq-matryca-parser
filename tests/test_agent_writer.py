from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from logseq_matryca_parser.agent_writer import (
    LogseqConfigReader,
    append_child_to_node,
    logseq_agent_write,
)
from logseq_matryca_parser.graph import LogseqGraph


@pytest.mark.parametrize(
    ("day", "expected_suffix"),
    [
        (1, "st"),
        (2, "nd"),
        (3, "rd"),
        (4, "th"),
        (11, "th"),
        (12, "th"),
        (13, "th"),
        (21, "st"),
        (22, "nd"),
        (23, "rd"),
        (31, "st"),
    ],
)
def test_get_day_ordinal(day: int, expected_suffix: str) -> None:
    assert LogseqConfigReader.get_day_ordinal(day) == expected_suffix


def test_logseq_agent_write_append_only(tmp_path: Path) -> None:
    pages_dir = tmp_path / "pages"
    config_path = tmp_path / "config.edn"
    config_path.write_text(
        ':journal/page-title-format "yyyy-MM-dd"\n',
        encoding="utf-8",
    )
    fixed_now = datetime(2026, 5, 10, 12, 0, 0)
    expected_file = pages_dir / "2026-W19-agent.md"

    tags = ["agent/hermes", "#review"]

    with patch("logseq_matryca_parser.agent_writer.datetime") as mock_datetime:
        mock_datetime.now.return_value = fixed_now

        result_first = logseq_agent_write(
            "First insight line.",
            str(config_path),
            str(pages_dir),
            context_tags=tags,
        )
        result_second = logseq_agent_write(
            "Second block body.",
            str(config_path),
            str(pages_dir),
            context_tags=tags,
        )

    assert result_first == {"status": "success", "path": str(expected_file)}
    assert result_second == {"status": "success", "path": str(expected_file)}
    assert expected_file.is_file()

    written = expected_file.read_text(encoding="utf-8")
    header = "- [[2026-05-10]] [[agent/hermes]] [[#review]]"
    assert header in written
    assert "First insight line." in written
    assert "Second block body." in written
    assert written.index("First insight line.") < written.index("Second block body.")


def test_append_child_to_node_inserts_indented_bullet(tmp_path: Path) -> None:
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    page_path = pages / "Splice.md"
    page_path.write_text(
        "- Parent block\n"
        "  id:: 11111111-1111-1111-1111-111111111111\n"
        "  - Existing child\n",
        encoding="utf-8",
    )

    graph = LogseqGraph.load_directory(graph_root)
    parent = graph.pages["Splice"].root_nodes[0]

    append_child_to_node(graph, parent.uuid, "Appended by headless writer")

    updated = page_path.read_text(encoding="utf-8")
    lines = updated.splitlines()
    assert lines == [
        "- Parent block",
        "  id:: 11111111-1111-1111-1111-111111111111",
        "  - Existing child",
        "  - Appended by headless writer",
    ]


def test_append_child_to_node_refreshes_in_memory_graph(tmp_path: Path) -> None:
    """After splice, ``LogseqGraph`` must reflect the new child (BUG-016)."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    page_path = pages / "Splice.md"
    page_path.write_text("- Parent block\n", encoding="utf-8")

    graph = LogseqGraph.load_directory(graph_root)
    parent = graph.pages["Splice"].root_nodes[0]
    assert parent.children == []

    append_child_to_node(graph, parent.uuid, "new child")

    refreshed_parent = graph.pages["Splice"].root_nodes[0]
    assert len(refreshed_parent.children) == 1
    assert refreshed_parent.children[0].clean_text == "new child"


def test_append_child_to_node_respects_four_space_tab_size(tmp_path: Path) -> None:
    """Four-space vaults receive child bullets indented with the detected tab width."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    page_path = pages / "Wide.md"
    page_path.write_text("- Parent block\n    - Existing four-space child\n", encoding="utf-8")

    graph = LogseqGraph.load_directory(graph_root)
    parent = graph.pages["Wide"].root_nodes[0]

    append_child_to_node(graph, parent.uuid, "Appended with four spaces")

    updated = page_path.read_text(encoding="utf-8")
    assert "    - Appended with four spaces" in updated


# ── LogseqConfigReader / format_timestamp (issue #48) ──────────────────


def test_format_timestamp_produces_logseq_journal_format(tmp_path: Path):
    config = tmp_path / "config.edn"
    config.write_text(':journal/page-title-format "yyyy_MM_dd"')
    reader = LogseqConfigReader(str(config))
    ts = reader.format_timestamp(datetime(2026, 5, 10))
    assert ts == "2026_05_10"


def test_format_timestamp_with_ordinal_day(tmp_path: Path):
    config = tmp_path / "config.edn"
    config.write_text(':journal/page-title-format "MMM do, yyyy"')
    reader = LogseqConfigReader(str(config))
    ts = reader.format_timestamp(datetime(2026, 5, 1))
    assert "1st" in ts or "May" in ts


def test_config_reader_loads_format(tmp_path: Path):
    config = tmp_path / "config.edn"
    config.write_text(':journal/page-title-format "yyyy-MM-dd"')
    reader = LogseqConfigReader(str(config))
    assert reader.load_journal_format() == "yyyy-MM-dd"
