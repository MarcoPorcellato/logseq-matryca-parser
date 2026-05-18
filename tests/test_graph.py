"""Tests for the in-memory ``LogseqGraph`` orchestrator."""

from __future__ import annotations

from pathlib import Path

from logseq_matryca_parser.graph import LogseqGraph


def test_load_directory_empty_graph(tmp_path: Path) -> None:
    """A vault with no markdown yields an empty graph."""
    graph_root = tmp_path / "vault"
    graph_root.mkdir()
    (graph_root / "pages").mkdir()

    graph = LogseqGraph.load_directory(graph_root)

    assert graph.graph_path == graph_root.resolve()
    assert graph.pages == {}
    assert graph.get_node_by_uuid("nonexistent") is None


def test_load_directory_bulk_parse_and_uuid_lookup(tmp_path: Path) -> None:
    """Multiple pages are indexed and nodes are reachable by synthetic UUID."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "Alpha.md").write_text("- Root alpha\n  - Nested #shared\n", encoding="utf-8")
    (pages / "Beta.md").write_text("- Root beta with needle\n", encoding="utf-8")

    graph = LogseqGraph.load_directory(graph_root)

    assert set(graph.pages.keys()) == {"Alpha", "Beta"}
    alpha_page = graph.pages["Alpha"]
    root = alpha_page.root_nodes[0]
    child = root.children[0]

    assert graph.get_node_by_uuid(root.uuid) == root
    assert graph.get_node_by_uuid(child.uuid) == child
    assert graph.get_node_by_uuid("00000000-0000-0000-0000-000000000000") is None


def test_get_nodes_by_tag_cross_page(tmp_path: Path) -> None:
    """Tag query returns nodes from every loaded page."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "One.md").write_text("- Block one #project-x\n", encoding="utf-8")
    (pages / "Two.md").write_text("- Block two #project-x\n", encoding="utf-8")

    graph = LogseqGraph.load_directory(graph_root)
    tagged = graph.get_nodes_by_tag("project-x")

    assert len(tagged) == 2
    assert {n.clean_text for n in tagged} == {"Block one #project-x", "Block two #project-x"}


def test_search_content_linear_scan(tmp_path: Path) -> None:
    """``search_content`` matches substrings on ``clean_text``."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "Doc.md").write_text("- First line about quantum\n- Second unrelated\n", encoding="utf-8")

    graph = LogseqGraph.load_directory(graph_root)
    hits = graph.search_content("quantum")

    assert len(hits) == 1
    assert "quantum" in hits[0].clean_text


def test_search_content_empty_query_returns_empty(tmp_path: Path) -> None:
    """An empty query short-circuits to an empty result list."""
    graph_root = tmp_path / "vault"
    (graph_root / "pages").mkdir(parents=True)
    (graph_root / "pages" / "X.md").write_text("- hi\n", encoding="utf-8")

    graph = LogseqGraph.load_directory(graph_root)
    assert graph.search_content("") == []


def test_journals_directory_is_discovered(tmp_path: Path) -> None:
    """Markdown under ``journals/`` is included in the graph."""
    graph_root = tmp_path / "vault"
    journals = graph_root / "journals"
    journals.mkdir(parents=True)
    (journals / "2026_05_18.md").write_text("- Journal entry #daily\n", encoding="utf-8")

    graph = LogseqGraph.load_directory(graph_root)

    assert "2026_05_18" in graph.pages
    assert len(graph.get_nodes_by_tag("daily")) == 1
