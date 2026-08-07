from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path
from typing import Any, cast

import pytest
from typer.testing import CliRunner

from logseq_matryca_parser import DiagnosticCode, LogseqGraph, VaultWriteError
from logseq_matryca_parser.agent_writer import append_child_to_node
from logseq_matryca_parser.kinetic import app

runner = CliRunner()


def _single_node_graph(tmp_path: Path) -> tuple[LogseqGraph, Path, str]:
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    page_path = pages / "Write.md"
    page_path.write_text("- Parent\n", encoding="utf-8")
    graph = LogseqGraph.load_directory(graph_root)
    return graph, page_path, graph.pages["Write"].root_nodes[0].uuid


def test_dry_run_returns_patch_without_mutation_or_reload(tmp_path: Path) -> None:
    graph, page_path, target_uuid = _single_node_graph(tmp_path)
    before = page_path.read_bytes()

    proposal = append_child_to_node(graph, target_uuid, "preview", dry_run=True)

    assert proposal.applied is False
    assert proposal.path == page_path.resolve()
    assert "--- a/pages/Write.md" in proposal.unified_diff
    assert "+++ b/pages/Write.md" in proposal.unified_diff
    assert "+  - preview" in proposal.unified_diff
    assert page_path.read_bytes() == before
    assert graph.pages["Write"].root_nodes[0].children == []


def test_external_symlink_target_is_rejected_without_mutation(tmp_path: Path) -> None:
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    outside = tmp_path / "outside.md"
    outside.write_text("- Outside\n", encoding="utf-8")
    (pages / "Escape.md").symlink_to(outside)
    graph = LogseqGraph.load_directory(graph_root)
    target_uuid = next(graph.iter_canonical_pages()).root_nodes[0].uuid

    with pytest.raises(VaultWriteError) as raised:
        append_child_to_node(graph, target_uuid, "must not escape")

    assert raised.value.diagnostic.code == DiagnosticCode.WRITER_VAULT_ESCAPE
    assert raised.value.diagnostic.source_path is None
    assert outside.read_text(encoding="utf-8") == "- Outside\n"


def test_symlink_swap_before_replace_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    graph, page_path, target_uuid = _single_node_graph(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("outside\n", encoding="utf-8")
    real_mkstemp = tempfile.mkstemp

    def swapping_mkstemp(
        suffix: str | None = None,
        prefix: str | None = None,
        dir: str | os.PathLike[str] | None = None,
        text: bool = False,
    ) -> tuple[int, str]:
        fd, temp_path = real_mkstemp(suffix=suffix, prefix=prefix, dir=dir, text=text)
        page_path.unlink()
        page_path.symlink_to(outside)
        return fd, temp_path

    monkeypatch.setattr("logseq_matryca_parser.agent_writer.tempfile.mkstemp", swapping_mkstemp)

    with pytest.raises(VaultWriteError) as raised:
        append_child_to_node(graph, target_uuid, "blocked")

    assert raised.value.diagnostic.code == DiagnosticCode.WRITER_VAULT_ESCAPE
    assert outside.read_text(encoding="utf-8") == "outside\n"


def test_regular_target_swap_before_replace_is_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    graph, page_path, target_uuid = _single_node_graph(tmp_path)
    replacement = page_path.parent / "replacement.md"
    replacement.write_text("- replacement\n", encoding="utf-8")
    real_mkstemp = tempfile.mkstemp

    def swapping_mkstemp(
        suffix: str | None = None,
        prefix: str | None = None,
        dir: str | os.PathLike[str] | None = None,
        text: bool = False,
    ) -> tuple[int, str]:
        fd, temp_path = real_mkstemp(suffix=suffix, prefix=prefix, dir=dir, text=text)
        replacement.replace(page_path)
        return fd, temp_path

    monkeypatch.setattr("logseq_matryca_parser.agent_writer.tempfile.mkstemp", swapping_mkstemp)

    with pytest.raises(VaultWriteError) as raised:
        append_child_to_node(graph, target_uuid, "blocked")

    assert raised.value.diagnostic.code == DiagnosticCode.WRITER_TARGET_CHANGED
    assert page_path.read_text(encoding="utf-8") == "- replacement\n"


def test_atomic_replace_preserves_permission_bits(tmp_path: Path) -> None:
    graph, page_path, target_uuid = _single_node_graph(tmp_path)
    page_path.chmod(0o640)
    original_owner = (page_path.stat().st_uid, page_path.stat().st_gid)

    proposal = append_child_to_node(graph, target_uuid, "written")

    assert proposal.applied is True
    assert stat.S_IMODE(page_path.stat().st_mode) == 0o640
    assert (page_path.stat().st_uid, page_path.stat().st_gid) == original_owner


@pytest.mark.parametrize(
    ("kwargs", "error_type"),
    [
        ({"max_source_bytes": 1}, VaultWriteError),
        ({"max_content_bytes": 1}, VaultWriteError),
        ({"max_target_depth": 0}, ValueError),
    ],
)
def test_writer_limits_fail_before_mutation(
    tmp_path: Path,
    kwargs: dict[str, int],
    error_type: type[Exception],
) -> None:
    graph, page_path, target_uuid = _single_node_graph(tmp_path)
    before = page_path.read_bytes()

    with pytest.raises(error_type):
        append_child_to_node(graph, target_uuid, "too large", **cast(Any, kwargs))

    assert page_path.read_bytes() == before


def test_agent_write_cli_dry_run_prints_patch_only(tmp_path: Path) -> None:
    graph, page_path, target_uuid = _single_node_graph(tmp_path)
    before = page_path.read_bytes()

    result = runner.invoke(
        app,
        [
            "agent-write",
            str(graph.graph_path),
            "--target-uuid",
            target_uuid,
            "--content",
            "preview",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "--- a/pages/Write.md" in result.output
    assert "+  - preview" in result.output
    assert page_path.read_bytes() == before


def test_file_uri_asset_must_remain_inside_graph(tmp_path: Path) -> None:
    graph, _page_path, _target_uuid = _single_node_graph(tmp_path)
    inside = graph.graph_path / "assets" / "inside.txt"
    inside.parent.mkdir()
    inside.write_text("inside", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    page = graph.pages["Write"]

    assert page.resolve_asset_path(inside.as_uri()) == str(inside.resolve())
    assert page.resolve_asset_path(outside.as_uri()) is None


def test_asset_symlink_escape_is_rejected(tmp_path: Path) -> None:
    graph, _page_path, _target_uuid = _single_node_graph(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    link = graph.graph_path / "assets" / "escape.txt"
    link.parent.mkdir()
    link.symlink_to(outside)

    assert graph.pages["Write"].resolve_asset_path("../assets/escape.txt") is None


def test_symlink_loops_fail_closed(tmp_path: Path) -> None:
    graph, page_path, target_uuid = _single_node_graph(tmp_path)
    page = graph.pages["Write"]
    loop = graph.graph_path / "assets" / "loop"
    loop.parent.mkdir()
    loop.symlink_to(loop)

    page_path.unlink()
    page_path.symlink_to(page_path)

    with pytest.raises(VaultWriteError) as raised:
        append_child_to_node(graph, target_uuid, "blocked")

    assert raised.value.diagnostic.code == DiagnosticCode.WRITER_VAULT_ESCAPE
    assert page.resolve_asset_path("../assets/loop") is None
