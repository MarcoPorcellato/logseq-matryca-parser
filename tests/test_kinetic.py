from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from logseq_matryca_parser.kinetic import app

runner = CliRunner()


class FakeDocument:
    def __init__(self, page_content: str, metadata: dict[str, object]) -> None:
        self.page_content = page_content
        self.metadata = metadata


def _create_graph(tmp_path: Path) -> Path:
    graph_root = tmp_path / "graph"
    pages_dir = graph_root / "pages"
    journals_dir = graph_root / "journals"
    pages_dir.mkdir(parents=True, exist_ok=True)
    journals_dir.mkdir(parents=True, exist_ok=True)

    (pages_dir / "project.md").write_text(
        "- TODO Build parser #kinetic\n"
        "  - Child block #nested\n",
        encoding="utf-8",
    )
    (journals_dir / "2026_04_25.md").write_text(
        "- DONE Journal task #daily\n",
        encoding="utf-8",
    )
    return graph_root


def test_scan_command_prints_graph_statistics(tmp_path: Path) -> None:
    graph_root = _create_graph(tmp_path)

    result = runner.invoke(app, ["scan", str(graph_root)])

    assert result.exit_code == 0
    assert "Graph Scan Statistics" in result.output
    assert "Total Pages" in result.output
    assert "2" in result.output
    assert "Total Tasks found" in result.output


def test_export_command_json_writes_output_file(tmp_path: Path) -> None:
    graph_root = _create_graph(tmp_path)
    output_dir = tmp_path / "out-json"

    result = runner.invoke(app, ["export", str(graph_root), str(output_dir), "--format", "json"])

    assert result.exit_code == 0
    output_file = output_dir / "graph.json"
    assert output_file.exists()
    payload = json.loads(output_file.read_text(encoding="utf-8"))
    assert len(payload) == 2
    assert payload[0]["ast"]


def test_export_command_markdown_writes_output_file(tmp_path: Path) -> None:
    graph_root = _create_graph(tmp_path)
    output_dir = tmp_path / "out-markdown"

    result = runner.invoke(
        app, ["export", str(graph_root), str(output_dir), "--format", "markdown"]
    )

    assert result.exit_code == 0
    output_file = output_dir / "graph.md"
    assert output_file.exists()
    body = output_file.read_text(encoding="utf-8")
    assert "# project" in body
    assert "- TODO Build parser #kinetic" in body


def test_export_command_langchain_writes_output_file(tmp_path: Path) -> None:
    graph_root = _create_graph(tmp_path)
    output_dir = tmp_path / "out-langchain"

    with patch("logseq_matryca_parser.synapse.Document", FakeDocument):
        result = runner.invoke(
            app, ["export", str(graph_root), str(output_dir), "--format", "langchain"]
        )

    assert result.exit_code == 0
    output_file = output_dir / "langchain.json"
    assert output_file.exists()
    payload = json.loads(output_file.read_text(encoding="utf-8"))
    assert len(payload) >= 2
    assert "page_content" in payload[0]
    assert "metadata" in payload[0]


def test_visualize_command_prints_deep_stats_and_success_message(tmp_path: Path) -> None:
    graph_root = _create_graph(tmp_path)
    output_html = tmp_path / "lens.html"

    with patch("logseq_matryca_parser.kinetic.GraphVisualizer.export_html") as export_html_mock:
        result = runner.invoke(app, ["visualize", str(graph_root), str(output_html)])

    assert result.exit_code == 0
    assert "LENS Deep Statistics" in result.output
    assert "Top 10 Most Connected Nodes" in result.output
    assert "Top 5 Largest Pages" in result.output
    assert "Visualization HTML written:" in result.output
    export_html_mock.assert_called_once_with(output_html)


def test_visualize_command_invalid_graph_path_exits_with_error(tmp_path: Path) -> None:
    missing_graph_path = tmp_path / "does_not_exist"
    output_html = tmp_path / "lens.html"

    result = runner.invoke(app, ["visualize", str(missing_graph_path), str(output_html)])

    assert result.exit_code == 1
    assert "Invalid graph path" in result.output
