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


def test_concurrent_watcher_callbacks_follow_publication_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Concurrent watcher routes cannot enqueue callbacks out of publication order."""
    pytest.importorskip("watchdog")
    from unittest.mock import MagicMock, patch

    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    first_path = pages / "First.md"
    second_path = pages / "Second.md"
    first_path.write_text("- first v1\n", encoding="utf-8")
    second_path.write_text("- second v1\n", encoding="utf-8")
    graph = LogseqGraph.load_directory(graph_root)

    first_submit_entered = Event()
    second_submitted = Event()
    simultaneous_submissions = Event()
    callbacks_delivered = Event()
    delivered: list[Path] = []
    original_submit = graph_module._OrderedCallbackDispatcher.submit

    def coordinate_submission(
        dispatcher: graph_module._OrderedCallbackDispatcher,
        path: Path,
    ) -> None:
        resolved = path.resolve()
        if resolved == first_path.resolve():
            first_submit_entered.set()
            if second_submitted.wait(timeout=3):
                simultaneous_submissions.set()
        original_submit(dispatcher, path)
        if resolved == second_path.resolve():
            second_submitted.set()

    monkeypatch.setattr(
        graph_module._OrderedCallbackDispatcher,
        "submit",
        coordinate_submission,
    )

    def callback(path: Path) -> None:
        delivered.append(path.resolve())
        if len(delivered) == 2:
            callbacks_delivered.set()

    mock_observer = MagicMock()
    mock_observer.is_alive.return_value = False
    with patch("watchdog.observers.Observer", return_value=mock_observer):
        watcher = graph.start_watching(callback=callback, debounce_seconds=0)
        handler = mock_observer.schedule.call_args[0][0]

    class _Event:
        is_directory = False

        def __init__(self, path: Path) -> None:
            self.src_path = str(path)

    first_path.write_text("- first v2\n", encoding="utf-8")
    second_path.write_text("- second v2\n", encoding="utf-8")
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first_future = pool.submit(handler.on_modified, _Event(first_path))
            assert first_submit_entered.wait(timeout=3), "first callback submit did not begin"
            second_future = pool.submit(handler.on_modified, _Event(second_path))
            first_future.result(timeout=5)
            second_future.result(timeout=5)
        assert callbacks_delivered.wait(timeout=3), "watcher callbacks were not delivered"
    finally:
        watcher.stop()

    assert not simultaneous_submissions.is_set(), (
        "a later publication reached callback submission before the earlier publication enqueued"
    )
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


def test_callback_dispatcher_start_failure_restores_restartable_watcher_state(
    tmp_path: Path,
) -> None:
    """A callback worker startup failure cannot leave the watcher permanently starting."""
    pytest.importorskip("watchdog")
    from unittest.mock import MagicMock, patch

    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "Live.md").write_text("- live\n", encoding="utf-8")
    graph = LogseqGraph.load_directory(graph_root)
    watcher = LogseqGraphWatcher(graph, callback=lambda _path: None, debounce_seconds=0)

    with patch.object(
        graph_module._OrderedCallbackDispatcher,
        "start",
        side_effect=RuntimeError("synthetic dispatcher start failure"),
    ):
        with pytest.raises(RuntimeError, match="synthetic dispatcher start failure"):
            watcher.start()

    assert watcher._observer is None
    assert watcher._debouncer is None
    assert watcher._callback_dispatcher is None
    assert not watcher._starting

    observer = MagicMock()
    observer.is_alive.return_value = False
    with patch("watchdog.observers.Observer", return_value=observer):
        watcher.start()
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


def test_watcher_rejects_start_while_stop_is_in_progress(tmp_path: Path) -> None:
    """A concurrent start cannot race a watcher teardown transition."""
    pytest.importorskip("watchdog")
    from unittest.mock import MagicMock, patch

    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "Live.md").write_text("- live\n", encoding="utf-8")
    graph = LogseqGraph.load_directory(graph_root)
    watcher = LogseqGraphWatcher(graph, debounce_seconds=0)
    observer = MagicMock()
    observer.is_alive.return_value = False
    stop_entered = Event()
    allow_stop_to_finish = Event()

    def block_observer_stop() -> None:
        stop_entered.set()
        assert allow_stop_to_finish.wait(timeout=5), "observer stop did not resume"

    observer.stop.side_effect = block_observer_stop
    with patch("watchdog.observers.Observer", return_value=observer):
        watcher.start()
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                stop_future = pool.submit(watcher.stop)
                assert stop_entered.wait(timeout=3), "observer stop did not begin"
                with pytest.raises(RuntimeError, match="still stopping"):
                    watcher.start()
                allow_stop_to_finish.set()
                stop_future.result(timeout=3)
        finally:
            allow_stop_to_finish.set()
            watcher.stop()


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


def test_renamed_stable_uuid_resorts_shared_backlink_key(tmp_path: Path) -> None:
    """A renamed source with stable IDs keeps cold-load backlink order."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "Target.md").write_text("- target\n", encoding="utf-8")
    contributor_uuid = "11111111-1111-1111-1111-111111111111"
    renamed_uuid = "22222222-2222-2222-2222-222222222222"
    (pages / "Middle.md").write_text(
        f"- contributor [[Target]]\n  id:: {contributor_uuid}\n",
        encoding="utf-8",
    )
    source = pages / "Zulu.md"
    source.write_text(
        f"- renamed [[Target]]\n  id:: {renamed_uuid}\n",
        encoding="utf-8",
    )
    old_graph = LogseqGraph.load_directory(graph_root)

    destination = pages / "Alpha.md"
    source.rename(destination)
    cold_graph = LogseqGraph.load_directory(graph_root)
    old_contributor = old_graph.pages["Middle"].root_nodes[0].model_copy(
        update={"uuid": contributor_uuid}
    )
    old_renamed = old_graph.pages["Zulu"].root_nodes[0].model_copy(
        update={"uuid": renamed_uuid}
    )
    candidate_contributor = cold_graph.pages["Middle"].root_nodes[0].model_copy(
        update={"uuid": contributor_uuid}
    )
    candidate_renamed = cold_graph.pages["Alpha"].root_nodes[0].model_copy(
        update={"uuid": renamed_uuid}
    )

    repaired = graph_module._repair_changed_backlink_contributions(
        old_pages=old_graph.pages,
        old_nodes={contributor_uuid: old_contributor, renamed_uuid: old_renamed},
        old_backlinks={"target": [contributor_uuid, renamed_uuid]},
        candidate_pages=cold_graph.pages,
        candidate_nodes={
            contributor_uuid: candidate_contributor,
            renamed_uuid: candidate_renamed,
        },
    )

    assert repaired["target"] == [renamed_uuid, contributor_uuid]


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


@pytest.mark.parametrize("operation", ["create", "edit", "delete", "rename"])
def test_incremental_lifecycle_operations_match_a_cold_graph(
    tmp_path: Path, operation: str
) -> None:
    """Each supported incremental lifecycle operation converges to its cold graph."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    anchor_path = pages / "Anchor.md"
    anchor_path.write_text("- anchor\n", encoding="utf-8")
    subject_path = pages / "Subject.md"

    if operation != "create":
        subject_path.write_text(
            "alias:: Old Alias\n\n- subject [[Anchor]]\n",
            encoding="utf-8",
        )
    incremental = LogseqGraph.load_directory(graph_root)

    if operation == "create":
        subject_path.write_text(
            "alias:: Created Alias\n\n- created [[Anchor]]\n",
            encoding="utf-8",
        )
        incremental.invalidate_and_reload_page(subject_path)
    elif operation == "edit":
        subject_path.write_text(
            "alias:: Edited Alias\n\n- edited [[Anchor]]\n",
            encoding="utf-8",
        )
        incremental.invalidate_and_reload_page(subject_path)
    elif operation == "delete":
        subject_path.unlink()
        incremental.invalidate_and_reload_page(subject_path)
    else:
        renamed_path = pages / "Renamed.md"
        subject_path.write_text(
            "title:: Renamed\nalias:: New Alias\n\n- renamed [[Anchor]]\n",
            encoding="utf-8",
        )
        subject_path.rename(renamed_path)
        incremental.invalidate_and_reload_page(subject_path)
        incremental.invalidate_and_reload_page(renamed_path)

    cold_graph = LogseqGraph.load_directory(graph_root)
    targets = ("Anchor", "Subject", "Renamed", "Old Alias", "New Alias", "Created Alias")
    assert _public_graph_projection(incremental, targets) == _public_graph_projection(
        cold_graph,
        targets,
    )


@pytest.mark.parametrize("collision_kind", ["canonical", "alias"])
@pytest.mark.parametrize("operation", ["edit", "delete", "rename"])
def test_collision_transition_incremental_reload_matches_a_cold_graph(
    tmp_path: Path, collision_kind: str, operation: str
) -> None:
    """Changing a collision winner restores every retained physical-page participant."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    journals = graph_root / "journals"
    pages.mkdir(parents=True)
    journals.mkdir()

    if collision_kind == "canonical":
        (journals / "Shared.md").write_text(
            "- journal contender [[Anchor]]\n",
            encoding="utf-8",
        )
        winner_path = pages / "Shared.md"
        winner_path.write_text("- page winner [[Anchor]]\n", encoding="utf-8")
        collision_title = "Shared"
        if operation == "edit":
            post_operation_title = "Updated"
        elif operation == "rename":
            post_operation_title = "Renamed"
        else:
            post_operation_title = "Shared"
    else:
        (pages / "A-Canonical.md").write_text(
            "title:: Claimed\n\n- canonical contender [[Anchor]]\n",
            encoding="utf-8",
        )
        winner_path = pages / "Z-Alias.md"
        winner_path.write_text(
            "alias:: Claimed\n\n- alias winner [[Anchor]]\n",
            encoding="utf-8",
        )
        collision_title = "Claimed"
        if operation == "edit":
            post_operation_title = "Replacement"
        elif operation == "rename":
            post_operation_title = "Z-Renamed"
        else:
            post_operation_title = "Claimed"

    incremental = LogseqGraph.load_directory(graph_root)

    if operation == "edit":
        if collision_kind == "canonical":
            winner_path.write_text(
                "title:: Updated\n\n- updated winner [[Anchor]]\n",
                encoding="utf-8",
            )
        else:
            winner_path.write_text(
                "alias:: Replacement\n\n- updated winner [[Anchor]]\n",
                encoding="utf-8",
            )
        incremental.invalidate_and_reload_page(winner_path)
    elif operation == "delete":
        winner_path.unlink()
        incremental.invalidate_and_reload_page(winner_path)
    else:
        renamed_path = winner_path.with_name(f"{post_operation_title}.md")
        winner_path.rename(renamed_path)
        incremental.invalidate_and_reload_page(winner_path)
        incremental.invalidate_and_reload_page(renamed_path)

    cold_graph = LogseqGraph.load_directory(graph_root)
    targets = (collision_title, post_operation_title, "Anchor")
    assert _public_graph_projection(incremental, targets) == _public_graph_projection(
        cold_graph,
        targets,
    )


def test_unrelated_graph_instances_do_not_share_mutation_coordination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One vault's paused reload cannot delay another graph instance's reload."""
    first_root = tmp_path / "first-vault"
    second_root = tmp_path / "second-vault"
    first_path = first_root / "pages" / "First.md"
    second_path = second_root / "pages" / "Second.md"
    first_path.parent.mkdir(parents=True)
    second_path.parent.mkdir(parents=True)
    first_path.write_text("- first v1\n", encoding="utf-8")
    second_path.write_text("- second v1\n", encoding="utf-8")
    first_graph = LogseqGraph.load_directory(first_root)
    second_graph = LogseqGraph.load_directory(second_root)
    assert first_graph._coordination_lock is not second_graph._coordination_lock

    first_path.write_text("- first v2\n", encoding="utf-8")
    second_path.write_text("- second v2\n", encoding="utf-8")
    first_build_entered = Event()
    allow_first_build_to_finish = Event()
    original_build_lower_title_map = graph_module._build_lower_title_map

    def pause_first_graph_build(pages: dict[str, LogseqPage]) -> dict[str, str]:
        if any(
            page.source_path
            and Path(page.source_path).resolve().is_relative_to(first_root.resolve())
            for page in pages.values()
        ):
            first_build_entered.set()
            assert allow_first_build_to_finish.wait(timeout=5), "first reload did not resume"
        return original_build_lower_title_map(pages)

    monkeypatch.setattr(graph_module, "_build_lower_title_map", pause_first_graph_build)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first_future = pool.submit(first_graph.invalidate_and_reload_page, first_path)
        assert first_build_entered.wait(timeout=3), "first reload did not reach candidate build"
        second_future = pool.submit(second_graph.invalidate_and_reload_page, second_path)
        try:
            second_future.result(timeout=1)
        finally:
            allow_first_build_to_finish.set()
        first_future.result(timeout=3)

    assert "first v2" in first_graph.pages["First"].root_nodes[0].clean_text
    assert "second v2" in second_graph.pages["Second"].root_nodes[0].clean_text
