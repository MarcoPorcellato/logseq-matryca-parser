"""Public graph construction from already-captured Markdown snapshots."""

from __future__ import annotations

import builtins
import os
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any, overload

import pytest

import logseq_matryca_parser.graph as graph_module
from logseq_matryca_parser import (
    BlockReferenceError,
    LogseqGraph,
    PageTitleCollisionError,
    SnapshotPage,
)


class _OversizedSnapshotMapping(Mapping[str, str]):
    """Fail if the factory touches entries after seeing an over-limit cardinality."""

    def __getitem__(self, _key: str) -> str:
        raise AssertionError("oversized mapping entries must not be read")

    def __iter__(self) -> Iterator[str]:
        raise AssertionError("oversized mapping must not be iterated")

    def __len__(self) -> int:
        return graph_module._MAX_SNAPSHOT_PAGE_COUNT + 1


class _UnderreportedSnapshotSequence(Sequence[SnapshotPage]):
    """Exercise the iteration-time bound when an untrusted sequence lies about length."""

    @overload
    def __getitem__(self, index: int) -> SnapshotPage: ...

    @overload
    def __getitem__(self, index: slice) -> Sequence[SnapshotPage]: ...

    def __getitem__(self, index: int | slice) -> SnapshotPage | Sequence[SnapshotPage]:
        snapshots = (
            SnapshotPage(logical_path="pages/Alpha.md", text="- alpha\n"),
            SnapshotPage(logical_path="pages/Beta.md", text="- beta\n"),
        )
        return snapshots[index]

    def __len__(self) -> int:
        return 0


def test_from_snapshot_pages_mapping_and_sequence_match_disk_graph(tmp_path: Path) -> None:
    """Snapshot construction reuses Parser graph semantics without source reopening."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    block_uuid = "64c752b0-d33b-4448-a261-e4dc2bbe12d3"
    alpha = f"- Anchor\n  id:: {block_uuid}\n"
    beta = f"alias:: Bee\n\n- Links [[Alpha]] and (({block_uuid}))\n"
    (pages / "Alpha.md").write_text(alpha, encoding="utf-8")
    (pages / "Beta.md").write_text(beta, encoding="utf-8")

    disk_graph = LogseqGraph.load_directory(graph_root, strict_refs=True)
    snapshot_graph = LogseqGraph.from_snapshot_pages(
        graph_root,
        [
            SnapshotPage(logical_path="pages/Beta.md", text=beta),
            SnapshotPage(logical_path="pages/Alpha.md", text=alpha),
        ],
        strict_refs=True,
    )
    mapping_graph = LogseqGraph.from_snapshot_pages(
        graph_root,
        {"pages/Alpha.md": alpha, "pages/Beta.md": beta},
        strict_refs=True,
    )

    assert set(snapshot_graph.pages) == set(disk_graph.pages) == set(mapping_graph.pages)
    for title in disk_graph.pages:
        disk_page = disk_graph.pages[title]
        snapshot_page = snapshot_graph.pages[title]
        mapping_page = mapping_graph.pages[title]
        assert snapshot_page.title == disk_page.title == mapping_page.title
        assert snapshot_page.root_nodes == disk_page.root_nodes == mapping_page.root_nodes
        assert snapshot_page.refs == disk_page.refs == mapping_page.refs
        assert snapshot_page.properties == disk_page.properties == mapping_page.properties
    assert [page.title for page in snapshot_graph.iter_canonical_pages()] == [
        page.title for page in disk_graph.iter_canonical_pages()
    ]
    assert snapshot_graph.get_backlinks("Alpha") == disk_graph.get_backlinks("Alpha")
    assert snapshot_graph.get_backlinks(block_uuid) == disk_graph.get_backlinks(block_uuid)


def test_from_snapshot_pages_never_discovers_or_reopens_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Logical source paths are metadata, never filesystem-read authority."""
    graph_root = tmp_path / "unopened-vault"

    def reject_filesystem_access(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("snapshot factory must not access the filesystem")

    monkeypatch.setattr(graph_module, "discover_graph_files", reject_filesystem_access)
    monkeypatch.setattr(
        graph_module.StackMachineParser,
        "parse_page_file",
        reject_filesystem_access,
    )

    graph = LogseqGraph.from_snapshot_pages(
        graph_root,
        [SnapshotPage(logical_path="pages/Alpha.md", text="- Snapshot only\n")],
    )

    assert graph.graph_path == graph_root.resolve()
    assert graph.pages["Alpha"].source_path == str((graph_root / "pages" / "Alpha.md").resolve())
    assert graph.pages["Alpha"].root_nodes[0].content == "Snapshot only"


def test_from_snapshot_pages_uses_lexical_graph_path_without_filesystem_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Snapshot graph roots normalize lexically without resolve, stat, or open calls."""
    graph_root = Path("snapshot-root/../vault")
    normalized_root = Path(os.path.abspath(graph_root))
    original_resolve: Any = graph_module.Path.resolve
    original_stat: Any = graph_module.Path.stat
    original_open: Any = graph_module.Path.open
    original_builtin_open: Any = builtins.open

    def is_snapshot_path(path: Path) -> bool:
        return (
            path in (graph_root, normalized_root)
            or graph_root in path.parents
            or normalized_root in path.parents
        )

    def guarded_resolve(path: Path, *args: Any, **kwargs: Any) -> Any:
        if is_snapshot_path(path):
            raise AssertionError("snapshot graph path must not resolve")
        return original_resolve(path, *args, **kwargs)

    def guarded_stat(path: Path, *args: Any, **kwargs: Any) -> Any:
        if is_snapshot_path(path):
            raise AssertionError("snapshot graph path must not stat")
        return original_stat(path, *args, **kwargs)

    def guarded_path_open(path: Path, *args: Any, **kwargs: Any) -> Any:
        if is_snapshot_path(path):
            raise AssertionError("snapshot graph path must not open")
        return original_open(path, *args, **kwargs)

    def guarded_builtin_open(file: Any, *args: Any, **kwargs: Any) -> Any:
        if isinstance(file, (str, os.PathLike)) and is_snapshot_path(Path(file)):
            raise AssertionError("snapshot graph path must not open")
        return original_builtin_open(file, *args, **kwargs)

    monkeypatch.setattr(graph_module.Path, "resolve", guarded_resolve)
    monkeypatch.setattr(graph_module.Path, "stat", guarded_stat)
    monkeypatch.setattr(graph_module.Path, "open", guarded_path_open)
    monkeypatch.setattr(builtins, "open", guarded_builtin_open)

    graph = LogseqGraph.from_snapshot_pages(
        graph_root,
        {
            "pages/Alpha.md": "- Snapshot only\n",
            "pages/Beta.md": "- [[alpha]]\n",
        },
    )

    assert graph.graph_path == normalized_root
    assert graph.pages["Alpha"].source_path == str(normalized_root / "pages" / "Alpha.md")
    assert [node.content for node in graph.get_backlinks("Alpha")] == ["[[alpha]]"]


def test_from_snapshot_pages_does_not_follow_existing_logical_symlinks(tmp_path: Path) -> None:
    """A logical path stays metadata even when a same-named source symlink exists."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    outside = tmp_path / "Outside.md"
    outside.write_text("- outside\n", encoding="utf-8")
    logical_source = pages / "Alpha.md"
    try:
        logical_source.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation unavailable on this platform")

    graph = LogseqGraph.from_snapshot_pages(
        graph_root,
        {"pages/Alpha.md": "- Snapshot only\n"},
    )

    assert graph.pages["Alpha"].source_path == str(logical_source)
    assert graph.pages["Alpha"].root_nodes[0].content == "Snapshot only"


@pytest.mark.parametrize(
    "snapshots",
    [
        [SnapshotPage(logical_path="../outside.md", text="- unsafe\n")],
        [SnapshotPage(logical_path="pages/Alpha.txt", text="- malformed\n")],
        [
            SnapshotPage(logical_path="pages/Alpha.md", text="- first\n"),
            SnapshotPage(logical_path="pages/./Alpha.md", text="- second\n"),
        ],
    ],
)
def test_from_snapshot_pages_rejects_unsafe_or_duplicate_logical_paths(
    tmp_path: Path, snapshots: list[SnapshotPage]
) -> None:
    """Only unique POSIX Markdown paths under pages or journals are admissible."""
    with pytest.raises(ValueError):
        LogseqGraph.from_snapshot_pages(tmp_path / "vault", snapshots)


def test_from_snapshot_pages_enforces_page_and_aggregate_byte_bounds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bounded callers cannot force unbounded page or text aggregation."""
    monkeypatch.setattr(graph_module, "_MAX_SNAPSHOT_PAGE_COUNT", 1)
    with pytest.raises(ValueError, match="page limit"):
        LogseqGraph.from_snapshot_pages(
            tmp_path / "vault",
            {
                "pages/Alpha.md": "- alpha\n",
                "pages/Beta.md": "- beta\n",
            },
        )

    monkeypatch.setattr(graph_module, "_MAX_SNAPSHOT_TOTAL_BYTES", 4)
    with pytest.raises(ValueError, match="byte limit"):
        LogseqGraph.from_snapshot_pages(
            tmp_path / "vault",
            {"pages/Alpha.md": "- alpha\n"},
        )


def test_from_snapshot_pages_rejects_oversized_mapping_before_iteration(tmp_path: Path) -> None:
    """The page ceiling applies before any caller-controlled mapping is materialized."""
    with pytest.raises(ValueError, match="page limit"):
        LogseqGraph.from_snapshot_pages(tmp_path / "vault", _OversizedSnapshotMapping())


def test_from_snapshot_pages_enforces_bound_while_iterating_untrusted_sequence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A false sequence length cannot bypass the page ceiling during normalization."""
    monkeypatch.setattr(graph_module, "_MAX_SNAPSHOT_PAGE_COUNT", 1)

    with pytest.raises(ValueError, match="page limit"):
        LogseqGraph.from_snapshot_pages(tmp_path / "vault", _UnderreportedSnapshotSequence())


def test_from_snapshot_pages_preserves_strict_reference_and_collision_modes(tmp_path: Path) -> None:
    """Snapshot graphs use the same strict validation and diagnostics builders as disk loads."""
    graph_root = tmp_path / "vault"

    with pytest.raises(BlockReferenceError):
        LogseqGraph.from_snapshot_pages(
            graph_root,
            {"pages/Broken.md": "- missing ((00000000-0000-0000-0000-000000000099))\n"},
            strict_refs=True,
        )

    with pytest.raises(PageTitleCollisionError):
        LogseqGraph.from_snapshot_pages(
            graph_root,
            {
                "pages/A.md": "title:: Shared\n\n- first\n",
                "pages/B.md": "title:: Shared\n\n- second\n",
            },
            strict_title_collisions=True,
        )
