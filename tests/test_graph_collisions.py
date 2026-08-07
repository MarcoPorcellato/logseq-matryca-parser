from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from logseq_matryca_parser import (
    Diagnostic,
    DiagnosticCode,
    LogseqGraph,
    PageTitleCollisionError,
    collect_graph_diagnostics,
)
from logseq_matryca_parser.kinetic import app

runner = CliRunner()


def _collision_diagnostics(graph: LogseqGraph) -> list[Diagnostic]:
    return [
        item
        for item in collect_graph_diagnostics(graph)
        if item.code == DiagnosticCode.GRAPH_PAGE_TITLE_COLLISION
    ]


def test_pages_journals_collision_preserves_winner_and_reports_paths(tmp_path: Path) -> None:
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    journals = graph_root / "journals"
    pages.mkdir(parents=True)
    journals.mkdir(parents=True)
    (pages / "Daily.md").write_text("- pages winner\n", encoding="utf-8")
    (journals / "Daily.md").write_text("- journals loser\n", encoding="utf-8")

    graph = LogseqGraph.load_directory(graph_root)
    diagnostics = _collision_diagnostics(graph)

    assert graph.pages["Daily"].source_path == str((pages / "Daily.md").resolve())
    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.context == {
        "loser_path": "journals/Daily.md",
        "reason": "derived_title",
        "title": "Daily",
        "winner_path": "pages/Daily.md",
    }
    assert graph.search_content("journals loser") == []
    assert len(graph.search_content("pages winner")) == 1


def test_frontmatter_collision_reports_reason_and_has_no_ghost_nodes(tmp_path: Path) -> None:
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "A.md").write_text("title:: Shared\n\n- loser-A\n", encoding="utf-8")
    (pages / "B.md").write_text("title:: Shared\n\n- winner-B\n", encoding="utf-8")

    graph = LogseqGraph.load_directory(graph_root)
    diagnostic = _collision_diagnostics(graph)[0]

    assert diagnostic.context["reason"] == "frontmatter_title"
    assert diagnostic.context["winner_path"] == "pages/B.md"
    assert diagnostic.context["loser_path"] == "pages/A.md"
    assert graph.search_content("loser-A") == []
    assert len(graph.search_content("winner-B")) == 1
    assert all(graph.page_for_node(node) is not None for node in graph.iter_attached_nodes())


def test_alias_collision_preserves_existing_remap_policy_and_reports_it(tmp_path: Path) -> None:
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "A.md").write_text("alias:: B\n\n- alias winner\n", encoding="utf-8")
    (pages / "B.md").write_text("- canonical loser\n", encoding="utf-8")

    graph = LogseqGraph.load_directory(graph_root)
    diagnostic = _collision_diagnostics(graph)[0]

    assert graph.pages["B"].source_path == str((pages / "A.md").resolve())
    assert diagnostic.context["reason"] == "alias"
    assert diagnostic.context["winner_path"] == "pages/A.md"
    assert diagnostic.context["loser_path"] == "pages/B.md"
    assert graph.search_content("canonical loser") == []


def test_strict_title_collision_raises_typed_error_with_relative_paths(tmp_path: Path) -> None:
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    journals = graph_root / "journals"
    pages.mkdir(parents=True)
    journals.mkdir(parents=True)
    (pages / "Daily.md").write_text("- pages\n", encoding="utf-8")
    (journals / "Daily.md").write_text("- journals\n", encoding="utf-8")

    with pytest.raises(PageTitleCollisionError) as raised:
        LogseqGraph.load_directory(graph_root, strict_title_collisions=True)

    assert raised.value.diagnostics[0].code == DiagnosticCode.GRAPH_PAGE_TITLE_COLLISION
    assert "pages/Daily.md" in str(raised.value)
    assert "journals/Daily.md" in str(raised.value)
    assert str(tmp_path) not in str(raised.value)


def test_collision_diagnostics_render_as_json_and_human_table(tmp_path: Path) -> None:
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    journals = graph_root / "journals"
    pages.mkdir(parents=True)
    journals.mkdir(parents=True)
    (pages / "Daily.md").write_text("- pages\n", encoding="utf-8")
    (journals / "Daily.md").write_text("- journals\n", encoding="utf-8")

    json_result = runner.invoke(app, ["scan", str(graph_root), "--diagnostics-json"])
    human_result = runner.invoke(app, ["scan", str(graph_root), "--diagnostics"])
    broken_refs_result = runner.invoke(app, ["scan", str(graph_root), "--broken-refs"])

    assert json_result.exit_code == 1
    payload = json.loads(json_result.output)
    assert payload[0]["code"] == "graph.page_title_collision"
    assert str(tmp_path) not in json_result.output
    assert human_result.exit_code == 1
    assert "Graph Diagnostics" in human_result.output
    assert "graph.page_title_collision" in human_result.output
    assert broken_refs_result.exit_code == 0
    assert "No unresolved block references" in broken_refs_result.output
