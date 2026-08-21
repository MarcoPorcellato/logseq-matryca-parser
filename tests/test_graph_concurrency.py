"""Deterministic one-process concurrency regressions for ``LogseqGraph``."""

from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

import pytest

import logseq_matryca_parser.graph as graph_module
from logseq_matryca_parser.graph import LogseqGraph
from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage


def _walk(nodes: list[LogseqNode]) -> Iterator[LogseqNode]:
    """Yield an outline in deterministic depth-first order without recursion."""
    pending = list(reversed(nodes))
    while pending:
        node = pending.pop()
        yield node
        pending.extend(reversed(node.children))


def _public_graph_projection(
    graph: LogseqGraph,
    targets: tuple[str, ...],
) -> dict[str, object]:
    """Capture public graph behavior without deriving expectations from internals."""
    pages = tuple(
        (page.title, tuple(node.uuid for node in _walk(page.root_nodes)))
        for page in graph.iter_canonical_pages()
    )
    casefold_pages: list[tuple[str, str | None]] = []
    for target in targets:
        page = graph.get_page(target.casefold())
        casefold_pages.append((target, page.title if page is not None else None))
    return {
        "pages": pages,
        "nodes": tuple(
            (node_uuid, graph.get_node_by_uuid(node_uuid) is not None)
            for _title, node_uuids in pages
            for node_uuid in node_uuids
        ),
        "backlinks": tuple(
            (target, tuple(node.uuid for node in graph.get_backlinks(target)))
            for target in targets
        ),
        "casefold_pages": tuple(casefold_pages),
        "diagnostics": graph.index_diagnostics,
    }


def _graph_with_reload_target(tmp_path: Path) -> tuple[LogseqGraph, Path]:
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "Target.md").write_text("- Target anchor\n", encoding="utf-8")
    reload_path = pages / "Refresh.md"
    reload_path.write_text("- Original source [[Target]]\n", encoding="utf-8")
    return LogseqGraph.load_directory(graph_root), reload_path


def test_failed_refresh_preserves_complete_prior_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A parse failure must not remove prior nodes or backlinks before publication."""
    graph, reload_path = _graph_with_reload_target(tmp_path)
    targets = ("Refresh", "Target")
    before = _public_graph_projection(graph, targets)
    reload_path.write_text("- Replacement source [[Target]]\n", encoding="utf-8")

    def raise_parse(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("synthetic parse failure")

    monkeypatch.setattr(
        graph_module.StackMachineParser,
        "parse_page_file",
        raise_parse,
    )

    with pytest.raises(RuntimeError, match="synthetic parse failure"):
        graph.invalidate_and_reload_page(reload_path)

    assert _public_graph_projection(graph, targets) == before


def test_effective_properties_never_mix_page_and_node_versions_during_reload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One composite reader must not join an old node with new page properties."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    reload_path = pages / "Refresh.md"
    reload_path.write_text(
        "phase:: old\n\n- Original\n  state:: old-node\n",
        encoding="utf-8",
    )
    graph = LogseqGraph.load_directory(graph_root)
    old_uuid = graph.pages["Refresh"].root_nodes[0].uuid
    old_properties = graph.get_effective_properties(old_uuid)
    reload_path.write_text(
        "phase:: new\n\n- Replacement\n  state:: new-node\n",
        encoding="utf-8",
    )

    build_entered = Event()
    allow_build_to_continue = Event()
    reader_started = Event()
    reader_finished = Event()
    page_lookup_reached = Event()
    allow_page_lookup_to_continue = Event()
    original_build_lower_title_map = graph_module._build_lower_title_map
    original_page_for_node = LogseqGraph._page_for_node

    def pause_candidate_build(pages: dict[str, LogseqPage]) -> dict[str, str]:
        build_entered.set()
        assert allow_build_to_continue.wait(timeout=5), "reload did not resume"
        return original_build_lower_title_map(pages)

    monkeypatch.setattr(graph_module, "_build_lower_title_map", pause_candidate_build)

    def pause_page_lookup(self: LogseqGraph, node: LogseqNode) -> LogseqPage | None:
        page = original_page_for_node(self, node)
        page_lookup_reached.set()
        assert allow_page_lookup_to_continue.wait(timeout=5), "reader did not resume"
        return page

    monkeypatch.setattr(LogseqGraph, "_page_for_node", pause_page_lookup)

    def read_effective_properties() -> dict[str, object]:
        reader_started.set()
        try:
            return graph.get_effective_properties(old_uuid)
        finally:
            reader_finished.set()

    with ThreadPoolExecutor(max_workers=2) as pool:
        reload_future = pool.submit(graph.invalidate_and_reload_page, reload_path)
        assert build_entered.wait(timeout=3), "reload did not reach candidate build"
        reader_future = pool.submit(read_effective_properties)
        assert reader_started.wait(timeout=3), "reader did not start"
        try:
            assert not page_lookup_reached.wait(timeout=1), (
                "reader reached page lookup while candidate publication was incomplete"
            )
            assert not reader_finished.is_set(), (
                "reader finished before the candidate snapshot was published"
            )
        finally:
            allow_build_to_continue.set()
            allow_page_lookup_to_continue.set()
        reload_future.result(timeout=3)
        observed_properties = reader_future.result(timeout=3)

    new_properties = graph.get_effective_properties(old_uuid)
    assert observed_properties in (old_properties, new_properties)
