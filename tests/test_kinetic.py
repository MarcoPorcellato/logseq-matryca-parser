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


def test_export_command_json_preserves_duplicate_block_identity(
    tmp_path: Path,
) -> None:
    graph_root = tmp_path / "graph"
    pages_dir = graph_root / "pages"
    journals_dir = graph_root / "journals"
    pages_dir.mkdir(parents=True, exist_ok=True)
    journals_dir.mkdir(parents=True, exist_ok=True)
    (pages_dir / "identity.md").write_text("- repeated\n- repeated\n", encoding="utf-8")
    output_dir = tmp_path / "out-json"

    result = runner.invoke(app, ["export", str(graph_root), str(output_dir), "--format", "json"])

    assert result.exit_code == 0
    payload = json.loads((output_dir / "graph.json").read_text(encoding="utf-8"))
    ast = payload[0]["ast"]
    first, second = ast
    assert first["content"] == "repeated"
    assert second["content"] == "repeated"
    assert first["uuid"] != second["uuid"]
    assert first["path"] == [first["uuid"]]
    assert second["path"] == [second["uuid"]]
    assert second["left_id"] == first["uuid"]


def test_export_command_json_preserves_source_uuid_separately(
    tmp_path: Path,
) -> None:
    graph_root = tmp_path / "graph"
    pages_dir = graph_root / "pages"
    journals_dir = graph_root / "journals"
    pages_dir.mkdir(parents=True, exist_ok=True)
    journals_dir.mkdir(parents=True, exist_ok=True)
    source_uuid = "11111111-1111-1111-1111-111111111111"
    (pages_dir / "identity.md").write_text(
        f"- Root\n  id:: {source_uuid}\n  - Child\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "out-json"

    result = runner.invoke(app, ["export", str(graph_root), str(output_dir), "--format", "json"])

    assert result.exit_code == 0
    payload = json.loads((output_dir / "graph.json").read_text(encoding="utf-8"))
    root = payload[0]["ast"][0]
    child = root["children"][0]
    assert root["uuid"] != source_uuid
    assert root["source_uuid"] == source_uuid
    assert root["synthetic_id"] is False
    assert root["source_path"] == str((pages_dir / "identity.md").resolve())
    assert root["line_start"] == 1
    assert root["line_end"] == 2
    assert root["outline_path"] == [1]
    assert child["parent_id"] == root["uuid"]
    assert child["path"] == [root["uuid"], child["uuid"]]


def test_export_command_obsidian_writes_namespace_markdown(tmp_path: Path) -> None:
    graph_root = tmp_path / "graph"
    pages_dir = graph_root / "pages"
    journals_dir = graph_root / "journals"
    pages_dir.mkdir(parents=True, exist_ok=True)
    journals_dir.mkdir(parents=True, exist_ok=True)
    block_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    ns = pages_dir / "Projects" / "AI"
    ns.mkdir(parents=True)
    (ns / "Demo.md").write_text(
        "scope:: demo\n\n"
        f"- Pointer (({block_id}))\n",
        encoding="utf-8",
    )
    (pages_dir / "Target.md").write_text(
        f"- Claim line\n  id:: {block_id}\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "out-obsidian"

    result = runner.invoke(
        app, ["export", str(graph_root), str(output_dir), "--format", "obsidian"]
    )

    assert result.exit_code == 0
    assert "Obsidian vault export completed" in result.output
    demo_md = output_dir / "Projects" / "AI" / "Demo.md"
    target_md = output_dir / "Target.md"
    assert demo_md.is_file()
    assert target_md.is_file()
    demo_body = demo_md.read_text(encoding="utf-8")
    assert demo_body.startswith("---\n")
    assert "scope: demo" in demo_body
    assert "[[Target#" in demo_body
    target_body = target_md.read_text(encoding="utf-8")
    assert "id::" not in target_body
    assert "^" in target_body


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
    assert "- Build parser #kinetic" in body


def test_export_command_langchain_enriched_writes_hydrated_file(tmp_path: Path) -> None:
    graph_root = tmp_path / "graph"
    pages_dir = graph_root / "pages"
    journals_dir = graph_root / "journals"
    pages_dir.mkdir(parents=True, exist_ok=True)
    journals_dir.mkdir(parents=True, exist_ok=True)
    (pages_dir / "Alpha.md").write_text(
        "type:: spec\n"
        "\n"
        "- Parent block\n"
        "  - Nested insight\n",
        encoding="utf-8",
    )
    (journals_dir / "2026_05_18.md").write_text(
        "- Journal note #daily\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "out-langchain-enriched"

    with patch("logseq_matryca_parser.synapse.Document", FakeDocument):
        result = runner.invoke(
            app,
            ["export", str(graph_root), str(output_dir), "--format", "langchain-enriched"],
        )

    assert result.exit_code == 0
    assert "contextual chunks" in result.output
    out_file = output_dir / "langchain_enriched.json"
    assert out_file.exists()
    payload = json.loads(out_file.read_text(encoding="utf-8"))
    assert len(payload) >= 3
    nested = next(p for p in payload if p["metadata"].get("clean_text") == "Nested insight")
    assert "Parent block" in nested["page_content"]
    assert "Alpha" in nested["page_content"]
    assert nested["page_content"].startswith("[")
    eff = nested["metadata"].get("effective_properties")
    assert isinstance(eff, dict)
    assert eff.get("type") == "spec"


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

    with patch("logseq_matryca_parser.lens.GraphVisualizer.export_html") as export_html_mock:
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


def test_demo_command_builds_showcase_without_disk_graph(tmp_path: Path) -> None:
    out = tmp_path / "showcase.html"

    with patch("logseq_matryca_parser.lens.GraphVisualizer.export_html") as export_html_mock:
        result = runner.invoke(app, ["demo", str(out)])

    assert result.exit_code == 0
    assert "Showcase example written" in result.output
    export_html_mock.assert_called_once()
    call_path = export_html_mock.call_args[0][0]
    assert call_path == out.resolve()


def test_append_command_success_prints_path(tmp_path: Path) -> None:
    config = tmp_path / "config.edn"
    pages = tmp_path / "pages"
    config.write_text("", encoding="utf-8")
    pages.mkdir()
    written = pages / "2026-W01-agent.md"
    with patch("logseq_matryca_parser.kinetic.logseq_agent_write") as write_mock:
        write_mock.return_value = {"status": "success", "path": str(written)}
        result = runner.invoke(
            app,
            [
                "append",
                "Line one",
                "--config",
                str(config.resolve()),
                "--pages",
                str(pages.resolve()),
                "--tags",
                "alpha",
                "--tags",
                "beta",
            ],
        )

    assert result.exit_code == 0
    assert "Appended to agent page:" in result.output
    assert str(written) in result.output
    write_mock.assert_called_once_with(
        "Line one",
        str(config.resolve()),
        str(pages.resolve()),
        context_tags=["alpha", "beta"],
    )


def test_append_command_success_without_tags_passes_none(tmp_path: Path) -> None:
    config = tmp_path / "config.edn"
    pages = tmp_path / "pages"
    config.touch()
    pages.mkdir()
    with patch("logseq_matryca_parser.kinetic.logseq_agent_write") as write_mock:
        write_mock.return_value = {"status": "success", "path": "/abs/agent.md"}
        result = runner.invoke(
            app,
            [
                "append",
                "Note body",
                "--config",
                str(config.resolve()),
                "--pages",
                str(pages.resolve()),
            ],
        )

    assert result.exit_code == 0
    write_mock.assert_called_once_with(
        "Note body",
        str(config.resolve()),
        str(pages.resolve()),
        context_tags=None,
    )


def test_append_command_failure_exits_with_error(tmp_path: Path) -> None:
    config = tmp_path / "config.edn"
    pages = tmp_path / "pages"
    config.touch()
    pages.mkdir()
    with patch("logseq_matryca_parser.kinetic.logseq_agent_write") as write_mock:
        write_mock.return_value = {"status": "error", "message": "disk full"}
        result = runner.invoke(
            app,
            [
                "append",
                "x",
                "--config",
                str(config.resolve()),
                "--pages",
                str(pages.resolve()),
            ],
        )

    assert result.exit_code == 1
    assert "Append failed:" in result.output
    assert "disk full" in result.output


def test_append_command_rejects_relative_config_path(tmp_path: Path) -> None:
    pages = tmp_path / "pages"
    pages.mkdir(parents=True)
    result = runner.invoke(
        app,
        [
            "append",
            "x",
            "--config",
            "relative/config.edn",
            "--pages",
            str(pages.resolve()),
        ],
    )

    assert result.exit_code == 1
    assert "must be an absolute path" in result.output
