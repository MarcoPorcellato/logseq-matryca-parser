"""Deterministic one-process concurrency regressions for ``LogseqGraph``."""

from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

import pytest

import logseq_matryca_parser.graph as graph_module
from logseq_matryca_parser.agent_writer import append_child_to_node
from logseq_matryca_parser.graph import LogseqGraph, LogseqGraphWatcher
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


def test_watcher_callbacks_are_nonblocking_ordered_and_isolated(tmp_path: Path) -> None:
    """A blocked or failing callback cannot block reloads or later callback delivery."""
    pytest.importorskip("watchdog")
    from unittest.mock import MagicMock, patch

    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    first_path = pages / "First.md"
    second_path = pages / "Second.md"
    first_path.write_text("- first\n", encoding="utf-8")
    second_path.write_text("- second\n", encoding="utf-8")
    graph = LogseqGraph.load_directory(graph_root)

    callback_started = Event()
    allow_first_callback_to_finish = Event()
    second_callback_delivered = Event()
    first_handler_returned = Event()
    delivered: list[Path] = []

    def callback(path: Path) -> None:
        delivered.append(path.resolve())
        if path.resolve() == first_path.resolve():
            callback_started.set()
            assert allow_first_callback_to_finish.wait(timeout=5), "callback did not resume"
            raise RuntimeError("synthetic callback failure")
        second_callback_delivered.set()

    mock_observer = MagicMock()
    mock_observer.is_alive.return_value = False
    with patch("watchdog.observers.Observer", return_value=mock_observer):
        watcher = graph.start_watching(callback=callback, debounce_seconds=0)
        handler = mock_observer.schedule.call_args[0][0]

    class _Event:
        is_directory = False

        def __init__(self, path: Path) -> None:
            self.src_path = str(path)

    def route_first_event() -> None:
        handler.on_modified(_Event(first_path))
        first_handler_returned.set()

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            first_future = pool.submit(route_first_event)
            assert callback_started.wait(timeout=3), "first callback did not start"
            assert first_handler_returned.wait(timeout=1), (
                "watcher handler waited for a blocked user callback"
            )
            handler.on_modified(_Event(second_path))
            allow_first_callback_to_finish.set()
            assert second_callback_delivered.wait(timeout=3), "second callback was not delivered"
            first_future.result(timeout=3)
    finally:
        allow_first_callback_to_finish.set()
        watcher.stop()

    assert delivered == [first_path.resolve(), second_path.resolve()]


def test_watcher_start_failure_cleans_dispatcher_and_rejects_reentry(tmp_path: Path) -> None:
    """Watcher startup cannot leak a callback worker or create a second observer."""
    pytest.importorskip("watchdog")
    from unittest.mock import MagicMock, patch

    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "Live.md").write_text("- live\n", encoding="utf-8")
    graph = LogseqGraph.load_directory(graph_root)
    watcher = LogseqGraphWatcher(graph, callback=lambda _path: None, debounce_seconds=0)

    failed_observer = MagicMock()
    failed_observer.is_alive.return_value = False
    failed_observer.start.side_effect = RuntimeError("synthetic observer failure")
    with patch("watchdog.observers.Observer", return_value=failed_observer):
        with pytest.raises(RuntimeError, match="synthetic observer failure"):
            watcher.start()

    assert watcher._observer is None
    assert watcher._debouncer is None
    assert watcher._callback_dispatcher is None

    start_entered = Event()
    allow_start_to_finish = Event()
    running_observer = MagicMock()
    running_observer.is_alive.return_value = False

    def block_observer_start() -> None:
        start_entered.set()
        assert allow_start_to_finish.wait(timeout=5), "observer start did not resume"

    running_observer.start.side_effect = block_observer_start
    with patch("watchdog.observers.Observer", return_value=running_observer):
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                start_future = pool.submit(watcher.start)
                assert start_entered.wait(timeout=3), "observer start did not begin"
                with pytest.raises(RuntimeError, match="already started"):
                    watcher.start()
                allow_start_to_finish.set()
                start_future.result(timeout=3)
        finally:
            allow_start_to_finish.set()
            watcher.stop()


def test_callback_dispatcher_reports_a_callback_that_outlives_bounded_close(
    tmp_path: Path,
) -> None:
    """A bounded close reports an admitted callback that still needs a later join."""
    callback_started = Event()
    release_callback = Event()

    def callback(_path: Path) -> None:
        callback_started.set()
        assert release_callback.wait(timeout=5), "callback did not resume"

    dispatcher = graph_module._OrderedCallbackDispatcher(callback).start()
    dispatcher.submit(tmp_path / "pages" / "Live.md")
    assert callback_started.wait(timeout=3), "callback did not start"
    try:
        assert not dispatcher.close(timeout=0.1)
    finally:
        release_callback.set()
    assert dispatcher.close(timeout=3)


def test_watcher_stop_retains_an_observer_that_outlives_its_bounded_join(
    tmp_path: Path,
) -> None:
    """A timed-out observer stop retains lifecycle ownership and blocks restart."""
    pytest.importorskip("watchdog")
    from unittest.mock import MagicMock, patch

    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "Live.md").write_text("- live\n", encoding="utf-8")
    graph = LogseqGraph.load_directory(graph_root)
    watcher = LogseqGraphWatcher(graph, debounce_seconds=0)
    observer = MagicMock()
    observer.is_alive.return_value = True

    with patch("watchdog.observers.Observer", return_value=observer):
        watcher.start()
        watcher.stop()
        assert watcher._observer is observer
        assert watcher._debouncer is not None
        with pytest.raises(RuntimeError, match="still stopping"):
            watcher.start()
        observer.is_alive.return_value = False
        watcher.stop()

    assert watcher._observer is None
    assert watcher._debouncer is None


@pytest.mark.parametrize("destination_first", [False, True])
def test_watcher_rename_orders_converge_to_a_cold_graph(
    tmp_path: Path, destination_first: bool
) -> None:
    """Source-first and destination-first rename events converge to one snapshot."""
    pytest.importorskip("watchdog")
    from unittest.mock import MagicMock, patch

    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "Target.md").write_text("- target\n", encoding="utf-8")
    source_path = pages / "Source.md"
    destination_path = pages / "Renamed.md"
    source_path.write_text("- source [[Target]]\n", encoding="utf-8")
    graph = LogseqGraph.load_directory(graph_root)

    mock_observer = MagicMock()
    mock_observer.is_alive.return_value = False
    with patch("watchdog.observers.Observer", return_value=mock_observer):
        watcher = graph.start_watching(debounce_seconds=0)
        handler = mock_observer.schedule.call_args[0][0]

    class _PathEvent:
        is_directory = False

        def __init__(self, path: Path) -> None:
            self.src_path = str(path)

    class _MovedEvent(_PathEvent):
        def __init__(self, source: Path, destination: Path) -> None:
            super().__init__(source)
            self.dest_path = str(destination)

    source_path.rename(destination_path)
    try:
        if destination_first:
            handler.on_created(_PathEvent(destination_path))
            handler.on_deleted(_PathEvent(source_path))
        else:
            handler.on_moved(_MovedEvent(source_path, destination_path))
    finally:
        watcher.stop()

    cold_graph = LogseqGraph.load_directory(graph_root)
    targets = ("Source", "Renamed", "Target")
    assert _public_graph_projection(graph, targets) == _public_graph_projection(
        cold_graph,
        targets,
    )


def test_watcher_replay_after_writer_append_converges_to_a_cold_graph(tmp_path: Path) -> None:
    """A watcher replay after a serialized append leaves the same graph as cold load."""
    pytest.importorskip("watchdog")
    from unittest.mock import MagicMock, patch

    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    page_path = pages / "Splice.md"
    page_path.write_text("- parent\n", encoding="utf-8")
    graph = LogseqGraph.load_directory(graph_root)
    parent_uuid = graph.pages["Splice"].root_nodes[0].uuid

    mock_observer = MagicMock()
    mock_observer.is_alive.return_value = False
    with patch("watchdog.observers.Observer", return_value=mock_observer):
        watcher = graph.start_watching(debounce_seconds=0)
        handler = mock_observer.schedule.call_args[0][0]

    class _Event:
        is_directory = False
        src_path = str(page_path)

    try:
        append_child_to_node(graph, parent_uuid, "writer child")
        handler.on_modified(_Event())
    finally:
        watcher.stop()

    cold_graph = LogseqGraph.load_directory(graph_root)
    assert _public_graph_projection(graph, ("Splice",)) == _public_graph_projection(
        cold_graph,
        ("Splice",),
    )
