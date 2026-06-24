"""Tests for the in-memory ``LogseqGraph`` orchestrator."""

from __future__ import annotations

from pathlib import Path

import pytest

from logseq_matryca_parser.exceptions import BlockReferenceError
from logseq_matryca_parser.graph import GraphQuery, LogseqGraph, _normalize_relative_link_target


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


def test_page_title_override_in_graph_index(tmp_path: Path) -> None:
    """``title::`` frontmatter re-keys the page in ``graph.pages`` and updates ``page.title``."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "file_name.md").write_text(
        "title:: Custom Title\n\n- Root block\n",
        encoding="utf-8",
    )

    graph = LogseqGraph.load_directory(graph_root)
    page = graph.pages["Custom Title"]

    assert "file_name" not in graph.pages
    assert page.title == "Custom Title"
    assert page.root_nodes[0].content == "Root block"


def test_case_insensitive_property_keys(tmp_path: Path) -> None:
    """``TITLE::`` frontmatter normalizes to ``title`` and overrides the graph page key."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "file_name.md").write_text(
        "TITLE:: Custom Page\n\n- Root block\n",
        encoding="utf-8",
    )

    graph = LogseqGraph.load_directory(graph_root)
    page = graph.pages["Custom Page"]

    assert page.title == "Custom Page"
    assert page.properties.get("title") == "Custom Page"
    assert "file_name" not in graph.pages


def test_case_insensitive_graph_routing(tmp_path: Path) -> None:
    """Lowercase wikilink titles resolve to the canonical-cased page object."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "JavaScript.md").write_text("- Language notes\n", encoding="utf-8")

    graph = LogseqGraph.load_directory(graph_root)
    page = graph.get_page("javascript")

    assert page is not None
    assert page.title == "JavaScript"
    assert graph.pages["JavaScript"] is page


def test_page_aliases_and_backlink_resolution(tmp_path: Path) -> None:
    """``alias::`` keys resolve to the canonical page and receive incoming wikilink backlinks."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "Development.md").write_text(
        "alias:: Dev, Coding\n\n- Hub block\n",
        encoding="utf-8",
    )
    (pages / "Linker.md").write_text(
        "- Links [[Dev]] and [[Coding]]\n",
        encoding="utf-8",
    )

    graph = LogseqGraph.load_directory(graph_root)
    development = graph.pages["Development"]
    linker = graph.pages["Linker"].root_nodes[0]

    assert graph.pages["Dev"] is development
    assert graph.pages["Coding"] is development
    assert linker in graph.get_backlinks("Dev")
    assert linker in graph.get_backlinks("Coding")
    assert linker in graph.get_backlinks("Development")
    assert graph.get_backlinks("dev") == graph.get_backlinks("Dev")


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
        watcher = graph.start_watching(callback=cb, debounce_seconds=0)
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


def test_watcher_ignores_temp_and_swap_files(tmp_path: Path) -> None:
    """Swap/temp filenames must not enqueue incremental reloads."""
    pytest.importorskip("watchdog")
    from unittest.mock import MagicMock, patch

    from logseq_matryca_parser.graph import _is_ignored_watcher_path

    assert _is_ignored_watcher_path(Path("notes.swp")) is True
    assert _is_ignored_watcher_path(Path("draft~")) is True
    assert _is_ignored_watcher_path(Path("cache.tmp")) is True
    assert _is_ignored_watcher_path(Path(".DS_Store")) is True
    assert _is_ignored_watcher_path(Path("Real.md")) is False

    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    path_doc = pages / "Live.md"
    path_doc.write_text("- v1\n", encoding="utf-8")
    graph = LogseqGraph.load_directory(graph_root)

    routed: list[Path] = []

    mock_observer = MagicMock()
    with patch("watchdog.observers.Observer", return_value=mock_observer):
        watcher = graph.start_watching(
            callback=lambda p: routed.append(p.resolve()),
            debounce_seconds=0,
        )
        handler = mock_observer.schedule.call_args[0][0]

    class _Ev:
        is_directory = False

    for temp_name in ("Ghost.swp", "Ghost~", "Ghost.tmp", ".DS_Store"):

        class _TempEv:
            is_directory = False
            src_path = str(pages / temp_name)

        handler.on_modified(_TempEv())

    assert routed == []
    watcher.stop()


def test_debounced_graph_event_router_coalesces_rapid_events(tmp_path: Path) -> None:
    """Multiple schedules for the same path should invoke the route callback once."""
    import time

    from logseq_matryca_parser.graph import _DebouncedGraphEventRouter

    target = tmp_path / "pages" / "Live.md"
    target.parent.mkdir(parents=True)
    hits: list[Path] = []
    router = _DebouncedGraphEventRouter(hits.append, debounce_seconds=0.05)

    router.schedule(target)
    router.schedule(target)
    time.sleep(0.12)

    assert hits == [target.resolve()]
    router.cancel_all()


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


def test_invalidate_and_reload_purges_deleted_page(tmp_path: Path) -> None:
    """Deleting a page file must purge registry entries without raising (BUG-005)."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    gone_path = pages / "Gone.md"
    gone_path.write_text("- orphan content\n", encoding="utf-8")

    graph = LogseqGraph.load_directory(graph_root)
    stale_uuid = graph.pages["Gone"].root_nodes[0].uuid
    assert graph.get_node_by_uuid(stale_uuid) is not None

    gone_path.unlink()
    graph.invalidate_and_reload_page(gone_path)

    assert graph.get_page("Gone") is None
    assert graph.get_node_by_uuid(stale_uuid) is None


def test_title_collision_pages_journals_no_ghost_registry(tmp_path: Path) -> None:
    """``pages/`` and ``journals/`` with the same title must not leave loser nodes in the registry."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    journals = graph_root / "journals"
    pages.mkdir(parents=True)
    journals.mkdir(parents=True)
    (pages / "Daily.md").write_text("- from pages folder\n", encoding="utf-8")
    (journals / "Daily.md").write_text("- from journals folder\n", encoding="utf-8")

    graph = LogseqGraph.load_directory(graph_root)
    winner = graph.pages["Daily"]

    assert winner.source_path == str((pages / "Daily.md").resolve())
    assert len(list(graph.iter_canonical_pages())) == 1
    assert all(graph._page_for_node(n) is not None for n in graph._node_registry.values())
    hits = graph.search_content("from journals folder")
    assert hits == []
    hits_pages = graph.search_content("from pages folder")
    assert len(hits_pages) == 1


def test_duplicate_title_override_no_ghost_registry(tmp_path: Path) -> None:
    """Two files with the same ``title::`` must index only the path-sorted winner's nodes."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "A.md").write_text("title:: Shared\n\n- from-A\n", encoding="utf-8")
    (pages / "B.md").write_text("title:: Shared\n\n- from-B\n", encoding="utf-8")

    graph = LogseqGraph.load_directory(graph_root)
    winner = graph.pages["Shared"]

    assert winner.source_path == str((pages / "B.md").resolve())
    assert graph.search_content("from-A") == []
    assert len(graph.search_content("from-B")) == 1
    assert len(list(graph.iter_canonical_pages())) == 1


def test_get_namespace_children_case_insensitive_prefix(tmp_path: Path) -> None:
    """Namespace child listing matches ``get_page`` case-insensitive routing."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "Progetti" / "AI").mkdir(parents=True)
    (pages / "Progetti" / "AI" / "Matryca.md").write_text("- hub\n", encoding="utf-8")

    graph = LogseqGraph.load_directory(graph_root)
    children = graph.get_namespace_children("progetti/ai")

    assert {p.title for p in children} == {"Progetti/AI/Matryca"}


def test_get_node_by_embed_ref_uuid_case_insensitive(tmp_path: Path) -> None:
    """Block UUID lookup is case-insensitive for ``source_uuid`` and ``id::`` properties."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    block_uuid = "64c752b0-d33b-4448-a261-e4dc2bbe12d3"
    upper_uuid = block_uuid.upper()
    (pages / "Target.md").write_text(
        f"- Block\n  id:: {block_uuid}\n",
        encoding="utf-8",
    )

    graph = LogseqGraph.load_directory(graph_root)
    node = graph.get_node_by_embed_ref(upper_uuid)

    assert node is not None
    assert node.properties.get("id") == block_uuid


def test_watcher_on_deleted_purges_page(tmp_path: Path) -> None:
    """``on_deleted`` routes into incremental invalidation (BUG-014)."""
    pytest.importorskip("watchdog")
    from unittest.mock import MagicMock, patch

    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    path_doc = pages / "Ephemeral.md"
    path_doc.write_text("- live\n", encoding="utf-8")
    graph = LogseqGraph.load_directory(graph_root)
    stale_uuid = graph.pages["Ephemeral"].root_nodes[0].uuid

    mock_observer = MagicMock()
    with patch("watchdog.observers.Observer", return_value=mock_observer):
        watcher = graph.start_watching(debounce_seconds=0)
        handler = mock_observer.schedule.call_args[0][0]

    path_doc.unlink()

    class _DelEv:
        is_directory = False
        src_path = str(path_doc)

    handler.on_deleted(_DelEv())
    assert graph.get_page("Ephemeral") is None
    assert graph.get_node_by_uuid(stale_uuid) is None
    watcher.stop()


def test_search_content_is_case_insensitive(tmp_path: Path) -> None:
    """``search_content`` matches case-insensitively (aligned with ``get_page``)."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "Doc.md").write_text("- Hello World note\n", encoding="utf-8")

    graph = LogseqGraph.load_directory(graph_root)
    assert len(graph.search_content("hello")) == 1
    assert len(graph.search_content("HELLO")) == 1


def test_get_nodes_by_tag_accepts_hash_prefix_and_case(tmp_path: Path) -> None:
    """Tag queries accept ``#`` prefix and case-insensitive matching."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "Tagged.md").write_text("- Block with #MyTag\n", encoding="utf-8")

    graph = LogseqGraph.load_directory(graph_root)
    assert len(graph.get_nodes_by_tag("mytag")) == 1
    assert len(graph.get_nodes_by_tag("#MyTag")) == 1
    hits = graph.query().has_tag("#mytag").execute()
    assert len(hits) == 1


def test_resolve_relative_page_link_supports_parent_segments(tmp_path: Path) -> None:
    """``../`` and ``./`` segments resolve before namespace shadowing."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "Global.md").write_text("- global\n", encoding="utf-8")
    (pages / "NS").mkdir(parents=True)
    (pages / "NS" / "Child.md").write_text("- child\n", encoding="utf-8")
    (pages / "NS" / "Sibling.md").write_text("- sibling\n", encoding="utf-8")

    graph = LogseqGraph.load_directory(graph_root)
    assert graph.resolve_relative_page_link("NS/Child", "../Sibling") == "NS/Sibling"
    assert graph.resolve_relative_page_link("NS/Child", "./Child") == "NS/Child"
    assert graph.resolve_relative_page_link("NS/Child", "Global") == "Global"


def test_get_namespace_children_dedupes_alias_keys(tmp_path: Path) -> None:
    """Namespace listing must not duplicate pages reachable via ``alias::`` keys (BUG-007)."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "NS").mkdir(parents=True)
    (pages / "NS" / "Leaf.md").write_text(
        "alias:: NS/AliasLeaf\n\n- body\n",
        encoding="utf-8",
    )

    graph = LogseqGraph.load_directory(graph_root)
    children = graph.get_namespace_children("NS")

    assert len(children) == 1
    assert children[0].title == "NS/Leaf"


def test_load_directory_strict_refs_validates_cross_page(tmp_path: Path) -> None:
    """``strict_refs=True`` accepts cross-page block refs but rejects vault-wide orphans."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    block_uuid = "64c752b0-d33b-4448-a261-e4dc2bbe12d3"
    (pages / "Target.md").write_text(f"- anchor\n  id:: {block_uuid}\n", encoding="utf-8")
    (pages / "Linker.md").write_text(f"- see (({block_uuid}))\n", encoding="utf-8")

    graph = LogseqGraph.load_directory(graph_root, strict_refs=True)
    assert len(graph.pages) == 2

    (pages / "Broken.md").write_text(
        "- missing ((00000000-0000-0000-0000-000000000099))\n",
        encoding="utf-8",
    )
    with pytest.raises(BlockReferenceError):
        LogseqGraph.load_directory(graph_root, strict_refs=True)


# ── _normalize_relative_link_target tests (issue #45) ────────────────────


class TestNormalizeRelativeLinkTarget:
    """Unit tests for ``_normalize_relative_link_target()`` path resolver."""

    def test_no_relative_prefix_returns_unchanged(self):
        assert _normalize_relative_link_target("A/B", "C") == "C"
        assert _normalize_relative_link_target("A", "B/C") == "B/C"

    def test_dot_slash_current_dir(self):
        assert _normalize_relative_link_target("A/B/C", "./D") == "A/B/D"
        assert _normalize_relative_link_target("A", "./B") == "B"

    def test_dot_slash_only_returns_current(self):
        assert _normalize_relative_link_target("A/B/C", "./") == "A/B/C"
        assert _normalize_relative_link_target("Page", "./") == "Page"

    def test_dot_dot_parent(self):
        assert _normalize_relative_link_target("A/B/C", "../D") == "A/B/D"
        assert _normalize_relative_link_target("A/B/C", "../../E") == "A/E"

    def test_dot_dot_beyond_root(self):
        assert _normalize_relative_link_target("A", "../../B") == "B"
        assert _normalize_relative_link_target("Page", "../Other") == "Other"

    def test_lone_dot_and_double_dot(self):
        assert _normalize_relative_link_target("A/B", ".") == "A/B"
        assert _normalize_relative_link_target("A/B/C", "..") == "A/B"

    def test_mixed_segments(self):
        # ./ strips from current and prepends; ../.. goes up two levels
        assert _normalize_relative_link_target("X/Y/Z", "../a/./b") == "X/Y/a/b"
        assert _normalize_relative_link_target("A/B/C", "../../D/E") == "A/D/E"
