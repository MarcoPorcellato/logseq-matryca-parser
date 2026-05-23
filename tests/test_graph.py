"""Tests for the in-memory ``LogseqGraph`` orchestrator."""

from __future__ import annotations

from pathlib import Path

import pytest

from logseq_matryca_parser.graph import GraphQuery, LogseqGraph


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


def test_graph_backlink_resolution_cross_page(tmp_path: Path) -> None:
    """Backlinks resolve for page wikilinks and native block UUIDs referenced across pages."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    block_uuid = "64c752b0-d33b-4448-a261-e4dc2bbe12d3"
    (pages / "Page B.md").write_text(
        f"- Target block\n  id:: {block_uuid}\n",
        encoding="utf-8",
    )
    (pages / "Page A.md").write_text(
        f"- Linking block references [[Page B]] and (({block_uuid}))\n",
        encoding="utf-8",
    )

    graph = LogseqGraph.load_directory(graph_root)
    page_a = graph.pages["Page A"]
    linker = page_a.root_nodes[0]

    by_page = graph.get_backlinks("Page B")
    by_uuid = graph.get_backlinks(block_uuid)

    assert linker in by_page
    assert linker in by_uuid
    assert graph.get_backlinks("page b") == by_page


def test_property_inheritance_overrides(tmp_path: Path) -> None:
    """Page frontmatter flows down the outline; a descendant ``status`` overrides an inherited one."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "Scope.md").write_text(
        "project:: Matryca\n"
        "status:: WIP\n"
        "- Root\n"
        "  - Middle\n"
        "    status:: DONE\n"
        "    - Inner leaf\n",
        encoding="utf-8",
    )

    graph = LogseqGraph.load_directory(graph_root)
    scope = graph.pages["Scope"]
    root = scope.root_nodes[0]
    middle = root.children[0]
    leaf = middle.children[0]

    effective = graph.get_effective_properties(leaf.uuid)

    assert effective.get("project") == "Matryca"
    assert effective.get("status") == "DONE"
    assert effective.get("status") != "WIP"


def test_namespace_hierarchy_and_relative_resolution(tmp_path: Path) -> None:
    """Namespace-aware link resolution and direct child listing match Logseq-style scoping."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "Progetti" / "AI").mkdir(parents=True)
    (pages / "Progetti" / "AI" / "Matryca.md").write_text("- hub\n", encoding="utf-8")
    (pages / "Progetti" / "AI" / "Parser.md").write_text("- tool\n", encoding="utf-8")
    (pages / "Progetti" / "AI" / "Team").mkdir(parents=True)
    (pages / "Progetti" / "AI" / "Team" / "Lead.md").write_text("- nested\n", encoding="utf-8")
    (pages / "Progetti" / "AI" / "Sviluppo.md").write_text("- contextual sviluppo\n", encoding="utf-8")
    (pages / "Progetti" / "Sviluppo.md").write_text("- sibling namespace\n", encoding="utf-8")
    (pages / "Sviluppo.md").write_text("- global sviluppo\n", encoding="utf-8")

    graph = LogseqGraph.load_directory(graph_root)

    assert graph.resolve_relative_page_link("Progetti/AI/Matryca", "Sviluppo") == "Progetti/AI/Sviluppo"
    assert graph.resolve_relative_page_link("Progetti/AI/Matryca", "Parser") == "Progetti/AI/Parser"
    assert graph.resolve_relative_page_link("Progetti/AI/Matryca", "Unknown") is None
    assert graph.resolve_relative_page_link("Progetti/AI/Matryca", "Matryca") == "Progetti/AI/Matryca"

    children = graph.get_namespace_children("Progetti/AI")
    titles = {p.title for p in children}
    assert titles == {"Progetti/AI/Matryca", "Progetti/AI/Parser", "Progetti/AI/Sviluppo"}
    assert "Progetti/AI/Team/Lead" not in titles


def test_fluent_graph_query_pipeline(tmp_path: Path) -> None:
    """Chained ``GraphQuery`` filters combine with strict ancestry and task metadata."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "FluentQuery.md").write_text(
        "- Branch alpha #pipeline\n"
        "  - Middle #pipeline\n"
        "    - TODO [#A] Deep hit #pipeline\n"
        "- Branch beta #pipeline\n"
        "  - TODO [#A] Shallow hit #pipeline\n",
        encoding="utf-8",
    )

    graph = LogseqGraph.load_directory(graph_root)
    demo = graph.pages["FluentQuery"]
    alpha = demo.root_nodes[0]
    middle = alpha.children[0]
    deep = middle.children[0]

    q = graph.query()
    assert isinstance(q, GraphQuery)

    hits = (
        graph.query()
        .has_tag("pipeline")
        .with_priority("A")
        .is_task_state("TODO")
        .under_parent(middle.uuid)
        .execute()
    )

    assert hits == [deep]

    beta = demo.root_nodes[1]
    shallow = beta.children[0]
    branch_beta_hits = (
        graph.query()
        .has_tag("pipeline")
        .with_priority("A")
        .is_task_state("TODO")
        .under_parent(beta.uuid)
        .execute()
    )
    assert branch_beta_hits == [shallow]


def test_graph_incremental_page_invalidation(tmp_path: Path) -> None:
    """Single-file invalidation purges stale UUIDs and backlinks without a full directory reload."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "Target.md").write_text("- Anchor\n", encoding="utf-8")
    (pages / "Other.md").write_text("- Still [[Target]]\n", encoding="utf-8")
    path_bridge = pages / "Bridge.md"
    path_bridge.write_text("- Bridge to [[Target]]\n", encoding="utf-8")

    graph = LogseqGraph.load_directory(graph_root)
    bridge_page = graph.pages["Bridge"]
    bridge_node = bridge_page.root_nodes[0]
    stale_uuid = bridge_node.uuid

    assert graph.get_node_by_uuid(stale_uuid) is bridge_node
    assert bridge_node in graph.get_backlinks("Target")

    path_bridge.write_text("- Isolated after edit\n", encoding="utf-8")
    graph.invalidate_and_reload_page(path_bridge)

    assert graph.get_node_by_uuid(stale_uuid) is None
    assert "Isolated" in graph.pages["Bridge"].root_nodes[0].clean_text
    remaining = graph.get_backlinks("Target")
    assert len(remaining) == 1
    assert remaining[0].source_path == str((pages / "Other.md").resolve())


def test_graph_watcher_filesystem_events(tmp_path: Path) -> None:
    """Watchdog handler routes ``on_modified`` / ``on_created`` into incremental invalidation."""
    pytest.importorskip("watchdog")
    from unittest.mock import MagicMock, patch

    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    path_doc = pages / "Live.md"
    path_doc.write_text("- v1\n", encoding="utf-8")
    graph = LogseqGraph.load_directory(graph_root)
    old_uuid = graph.pages["Live"].root_nodes[0].uuid

    callback_paths: list[Path] = []

    def cb(p: Path) -> None:
        callback_paths.append(p.resolve())

    mock_observer = MagicMock()
    with patch("watchdog.observers.Observer", return_value=mock_observer):
        watcher = graph.start_watching(callback=cb)
        handler = mock_observer.schedule.call_args[0][0]
        mock_observer.start.assert_called_once()

    path_doc.write_text("- v2 breakthrough\n", encoding="utf-8")

    class _Ev:
        is_directory = False
        src_path = str(path_doc)

    handler.on_modified(_Ev())
    assert old_uuid != graph.pages["Live"].root_nodes[0].uuid
    assert "v2" in graph.pages["Live"].root_nodes[0].clean_text
    assert callback_paths == [path_doc.resolve()]

    callback_paths.clear()
    handler.on_created(_Ev())
    assert callback_paths == [path_doc.resolve()]

    callback_paths.clear()
    class _DirEv:
        is_directory = True
        src_path = str(pages)

    handler.on_modified(_DirEv())
    assert callback_paths == []

    watcher.stop()
    mock_observer.stop.assert_called_once()


def test_get_broken_references_flags_missing_uuid(tmp_path: Path) -> None:
    """Nodes referencing unknown block UUIDs are returned by the AST linter."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    fake_uuid = "00000000-0000-0000-0000-000000000099"
    (pages / "Broken.md").write_text(
        f"- Linker references (({fake_uuid}))\n",
        encoding="utf-8",
    )

    graph = LogseqGraph.load_directory(graph_root)
    linker = graph.pages["Broken"].root_nodes[0]

    broken = graph.get_broken_references()

    assert linker in broken
    assert fake_uuid in linker.block_refs
