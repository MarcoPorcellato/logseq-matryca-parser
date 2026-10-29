from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from datetime import datetime, tzinfo
from pathlib import Path

import pytest
from typer.testing import CliRunner

import logseq_matryca_parser.agent_writer as agent_writer_module
from logseq_matryca_parser._agent_file_io import _write_agent_file
from logseq_matryca_parser.agent_press import SessionAliasRegistry
from logseq_matryca_parser.agent_writer import logseq_agent_write
from logseq_matryca_parser.kinetic import app
from logseq_matryca_parser.logos_core import LogseqNode

BLOCK_UUID = "11111111-1111-1111-1111-111111111111"


class _FixedDatetime(datetime):
    @classmethod
    def now(cls, tz: tzinfo | None = None) -> _FixedDatetime:
        return cls(2026, 10, 28, 12, 0, tzinfo=tz)


@pytest.fixture(autouse=True)
def _fixed_week(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_writer_module, "datetime", _FixedDatetime)


def _registry() -> SessionAliasRegistry:
    registry = SessionAliasRegistry()
    registry.generate_aliases(
        [LogseqNode(uuid=BLOCK_UUID, content="example", indent_level=0)]
    )
    return registry


def _weekly_paths(tmp_path: Path) -> tuple[Path, Path, Path]:
    config = tmp_path / "config.edn"
    config.write_text(':journal/page-title-format "yyyy-MM-dd"\n', encoding="utf-8")
    pages = tmp_path / "pages"
    pages.mkdir()
    return config, pages, pages / "2026-W44-agent.md"


def _assert_sanitized(message: str, path: Path) -> None:
    assert str(path) not in message
    assert str(path.parent) not in message


@pytest.mark.parametrize("inside", [False, True])
def test_state_rejects_leaf_symlink_without_changing_target(
    tmp_path: Path, inside: bool
) -> None:
    graph = tmp_path / "graph"
    graph.mkdir()
    target = (graph if inside else tmp_path) / "sentinel.json"
    target.write_bytes(b"private sentinel")
    state = graph / ".matryca_xray_state.json"
    state.symlink_to(target)

    with pytest.raises(OSError) as raised:
        _registry().save_to_disk(state)

    assert target.read_bytes() == b"private sentinel"
    assert state.is_symlink()
    _assert_sanitized(str(raised.value), state)


def test_state_dangling_symlink_does_not_create_target(tmp_path: Path) -> None:
    target = tmp_path / "must-not-exist.json"
    state = tmp_path / "state.json"
    state.symlink_to(target)

    with pytest.raises(OSError):
        _registry().save_to_disk(state)

    assert not target.exists()
    assert state.is_symlink()


def test_state_rejects_hardlink_without_truncating_shared_inode(tmp_path: Path) -> None:
    target = tmp_path / "sentinel.json"
    target.write_bytes(b"private sentinel")
    state = tmp_path / "state.json"
    os.link(target, state)

    with pytest.raises(OSError):
        _registry().save_to_disk(state)

    assert target.read_bytes() == state.read_bytes() == b"private sentinel"


def test_state_rewrite_keeps_inode_mode_and_json_contract(tmp_path: Path) -> None:
    state = tmp_path / "state.json"
    state.write_text("old bytes must not survive the rewrite", encoding="utf-8")
    state.chmod(0o640)
    before = state.stat()

    _registry().save_to_disk(state)

    after = state.stat()
    assert (after.st_dev, after.st_ino) == (before.st_dev, before.st_ino)
    if os.name != "nt":
        assert stat.S_IMODE(after.st_mode) == 0o640
        assert (after.st_uid, after.st_gid) == (before.st_uid, before.st_gid)
    assert json.loads(state.read_text(encoding="utf-8")) == {"0": BLOCK_UUID}
    assert SessionAliasRegistry.load_from_disk(state).resolve_alias(0) == BLOCK_UUID


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode bits do not describe a Windows DACL")
def test_new_state_has_no_group_or_other_permissions(tmp_path: Path) -> None:
    state = tmp_path / "state.json"

    _registry().save_to_disk(state)

    assert stat.S_IMODE(state.stat().st_mode) & 0o177 == 0
    assert json.loads(state.read_text(encoding="utf-8")) == {"0": BLOCK_UUID}


@pytest.mark.parametrize("link_kind", ["symlink", "hardlink"])
def test_weekly_append_refuses_linked_leaf_without_changing_target(
    tmp_path: Path, link_kind: str
) -> None:
    config, pages, weekly = _weekly_paths(tmp_path)
    target = tmp_path / "sentinel.md"
    target.write_bytes(b"private sentinel\n")
    if link_kind == "symlink":
        weekly.symlink_to(target)
    else:
        os.link(target, weekly)

    result = logseq_agent_write("must not append", str(config), str(pages))

    assert result["status"] == "error"
    assert target.read_bytes() == b"private sentinel\n"
    _assert_sanitized(result["message"], weekly)


def test_weekly_append_keeps_inode_and_existing_content(tmp_path: Path) -> None:
    config, pages, weekly = _weekly_paths(tmp_path)
    weekly.write_text("Existing header\n", encoding="utf-8")
    before = weekly.stat()

    result = logseq_agent_write(
        "New block.", str(config), str(pages), context_tags=["agent/security"]
    )

    assert result == {"status": "success", "path": str(weekly)}
    after = weekly.stat()
    assert (after.st_dev, after.st_ino) == (before.st_dev, before.st_ino)
    assert weekly.read_text(encoding="utf-8") == (
        "Existing header\n- [[2026-10-28]] [[agent/security]]\nNew block.\n"
    )


@pytest.mark.parametrize("no_matches", [False, True])
def test_xray_save_refusal_exits_one_before_any_stdout(
    tmp_path: Path, no_matches: bool
) -> None:
    graph = tmp_path / "graph"
    pages = graph / "pages"
    pages.mkdir(parents=True)
    (pages / "Page.md").write_text("- visible block\n", encoding="utf-8")
    target = tmp_path / "sentinel.json"
    target.write_bytes(b"private sentinel")
    (graph / ".matryca_xray_state.json").symlink_to(target)
    args = ["agent-read", str(graph)]
    if no_matches:
        args.extend(["--query", "does-not-match"])

    result = CliRunner().invoke(app, args)

    assert result.exit_code == 1
    assert result.stdout == ""
    assert result.stderr
    assert target.read_bytes() == b"private sentinel"
    _assert_sanitized(result.stderr, graph / ".matryca_xray_state.json")


@pytest.mark.parametrize("operation", ["state", "weekly"])
def test_directory_leaf_refusal_has_no_path_in_error(
    tmp_path: Path, operation: str
) -> None:
    config, pages, weekly = _weekly_paths(tmp_path)
    target = weekly if operation == "weekly" else tmp_path / "state.json"
    target.mkdir()
    sentinel = target / "keep.txt"
    sentinel.write_bytes(b"unchanged")

    if operation == "state":
        with pytest.raises(OSError) as raised:
            _registry().save_to_disk(target)
        message = str(raised.value)
    else:
        result = logseq_agent_write("blocked", str(config), str(pages))
        assert result["status"] == "error"
        message = result["message"]

    _assert_sanitized(message, target)
    assert sentinel.read_bytes() == b"unchanged"


@pytest.mark.parametrize("after_open", [False, True])
@pytest.mark.parametrize("replacement_kind", ["regular", "symlink"])
def test_changed_leaf_is_rejected_before_mutation_even_without_no_follow_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    after_open: bool,
    replacement_kind: str,
) -> None:
    state = tmp_path / "state.json"
    backup = tmp_path / "original.json"
    other = tmp_path / "other.json"
    state.write_bytes(b"original")
    other.write_bytes(b"replacement")
    real_open = os.open
    opened: list[int] = []

    def swap() -> None:
        state.rename(backup)
        if replacement_kind == "symlink":
            state.symlink_to(other)
        else:
            other.rename(state)

    def swapping_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if path != state:
            return real_open(path, flags, mode, dir_fd=dir_fd)
        assert not flags & os.O_TRUNC
        if not after_open:
            swap()
        fd = real_open(path, flags, mode, dir_fd=dir_fd)
        opened.append(fd)
        if after_open:
            swap()
        return fd

    monkeypatch.delattr(os, "O_NOFOLLOW", raising=False)
    monkeypatch.setattr(os, "open", swapping_open)

    with pytest.raises(OSError) as raised:
        _registry().save_to_disk(state)

    assert backup.read_bytes() == b"original"
    assert (other if replacement_kind == "symlink" else state).read_bytes() == b"replacement"
    _assert_sanitized(str(raised.value), state)
    for fd in opened:
        with pytest.raises(OSError):
            os.fstat(fd)


def test_new_state_does_not_overwrite_a_concurrent_creator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = tmp_path / "state.json"
    real_open = os.open

    def competing_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if path == state:
            state.write_bytes(b"concurrent owner")
            assert flags & os.O_CREAT
            assert flags & os.O_EXCL
            assert not flags & os.O_TRUNC
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", competing_open)

    with pytest.raises(OSError):
        _registry().save_to_disk(state)

    assert state.read_bytes() == b"concurrent owner"


def test_hardlink_added_during_open_is_refused_before_truncation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = tmp_path / "state.json"
    state.write_bytes(b"original")
    linked = tmp_path / "other-name.json"
    real_open = os.open

    def linking_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        fd = real_open(path, flags, mode, dir_fd=dir_fd)
        if path == state:
            os.link(state, linked)
        return fd

    monkeypatch.setattr(os, "open", linking_open)

    with pytest.raises(OSError):
        _registry().save_to_disk(state)

    assert state.read_bytes() == linked.read_bytes() == b"original"


@pytest.mark.parametrize("stage", ["ftruncate", "write", "fsync"])
def test_io_failure_is_sanitized_and_closes_the_opened_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    state = tmp_path / "state.json"
    state.write_bytes(b"original")
    opened: list[int] = []
    real_open = os.open

    def tracking_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        fd = real_open(path, flags, mode, dir_fd=dir_fd)
        if path == state:
            opened.append(fd)
        return fd

    def fail(*args: object) -> int:
        raise OSError(f"sensitive I/O failure at {state}")

    monkeypatch.setattr(os, "open", tracking_open)
    monkeypatch.setattr(os, stage, fail)

    with pytest.raises(OSError) as raised:
        _registry().save_to_disk(state)

    _assert_sanitized(str(raised.value), state)
    assert len(opened) == 1
    with pytest.raises(OSError):
        os.fstat(opened[0])
    if stage == "ftruncate":
        assert state.read_bytes() == b"original"


def test_short_writes_produce_complete_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state = tmp_path / "state.json"
    real_write = os.write

    def short_write(fd: int, data: bytes | memoryview) -> int:
        return real_write(fd, data[:3])

    monkeypatch.setattr(os, "write", short_write)

    _registry().save_to_disk(state)

    assert json.loads(state.read_text(encoding="utf-8")) == {"0": BLOCK_UUID}


def test_zero_progress_is_an_error_not_an_unbounded_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = tmp_path / "state.json"
    calls = 0

    def no_progress(fd: int, data: bytes | memoryview) -> int:
        nonlocal calls
        calls += 1
        if calls > 1:
            raise AssertionError("zero-progress write was retried")
        return 0

    monkeypatch.setattr(os, "write", no_progress)

    with pytest.raises(OSError):
        _registry().save_to_disk(state)

    assert calls == 1


@pytest.mark.skipif(os.name == "nt", reason="POSIX FIFOs are not a Windows file type")
def test_fifo_refusal_does_not_wait_for_a_reader(tmp_path: Path) -> None:
    fifo = tmp_path / "state.fifo"
    os.mkfifo(fifo)
    program = (
        "import sys\n"
        "from pathlib import Path\n"
        "from logseq_matryca_parser.agent_press import SessionAliasRegistry\n"
        "try:\n"
        "    SessionAliasRegistry().save_to_disk(Path(sys.argv[1]))\n"
        "except OSError:\n"
        "    sys.exit(73)\n"
    )
    try:
        result = subprocess.run(
            [sys.executable, "-c", program, str(fifo)],
            capture_output=True,
            timeout=3,
            check=False,
        )
    except subprocess.TimeoutExpired:
        pytest.fail("state write waited for a FIFO reader instead of refusing the leaf")

    assert result.returncode == 73


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode bits do not describe a Windows DACL")
def test_new_state_respects_a_more_restrictive_umask(tmp_path: Path) -> None:
    state = tmp_path / "state.json"
    previous = os.umask(0o777)
    try:
        _registry().save_to_disk(state)
        mode = stat.S_IMODE(state.stat().st_mode)
    finally:
        os.umask(previous)
        if state.exists():
            state.chmod(0o600)

    assert mode == 0


def test_successive_state_saves_keep_subclass_and_latest_mapping(tmp_path: Path) -> None:
    class ConsumerRegistry(SessionAliasRegistry):
        pass

    state = tmp_path / "state.json"
    _registry().save_to_disk(state)
    ConsumerRegistry().save_to_disk(state)

    restored = ConsumerRegistry.load_from_disk(state)
    assert isinstance(restored, ConsumerRegistry)
    assert restored.resolve_alias(0) is None
    assert json.loads(state.read_text(encoding="utf-8")) == {}


@pytest.mark.skipif(os.name != "nt", reason="Windows junctions require the native Windows runner")
@pytest.mark.parametrize("operation", ["state", "weekly"])
def test_windows_junction_leaf_is_refused_without_skip_on_creation_failure(
    tmp_path: Path, operation: str
) -> None:
    config, pages, weekly = _weekly_paths(tmp_path)
    destination = tmp_path / "junction-target"
    destination.mkdir()
    sentinel = destination / "keep.txt"
    sentinel.write_bytes(b"unchanged")
    leaf = weekly if operation == "weekly" else tmp_path / "state.json"
    created = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(leaf), str(destination)],
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert created.returncode == 0, "required Windows junction fixture could not be created"
    try:
        if operation == "state":
            with pytest.raises(OSError):
                _registry().save_to_disk(leaf)
        else:
            result = logseq_agent_write("must not append", str(config), str(pages))
            assert result["status"] == "error"
        assert sentinel.read_bytes() == b"unchanged"
    finally:
        os.rmdir(leaf)


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode bits do not describe a Windows DACL")
def test_new_weekly_page_has_no_group_or_other_permissions(tmp_path: Path) -> None:
    config, pages, weekly = _weekly_paths(tmp_path)

    result = logseq_agent_write("new", str(config), str(pages))

    assert result["status"] == "success"
    assert stat.S_IMODE(weekly.stat().st_mode) & 0o177 == 0


@pytest.mark.skipif(not hasattr(os, "setxattr"), reason="OS does not expose POSIX xattr APIs")
@pytest.mark.parametrize("append", [False, True])
def test_existing_extended_attribute_survives_inplace_write(tmp_path: Path, append: bool) -> None:
    target = tmp_path / "metadata.txt"
    target.write_bytes(b"old")
    setxattr = getattr(os, "setxattr", None)
    getxattr = getattr(os, "getxattr", None)
    assert setxattr is not None and getxattr is not None
    setxattr(target, "user.matryca_security_test", b"preserved")

    _write_agent_file(target, "new", append=append)

    assert getxattr(target, "user.matryca_security_test") == b"preserved"
    assert target.read_bytes() == (b"oldnew" if append else b"new")


@pytest.mark.parametrize("operation", ["state", "weekly"])
def test_readonly_existing_file_refusal_preserves_content(
    tmp_path: Path, operation: str
) -> None:
    if os.name != "nt" and os.geteuid() == 0:
        pytest.skip("root bypasses ordinary POSIX write permission checks")
    config, pages, weekly = _weekly_paths(tmp_path)
    target = weekly if operation == "weekly" else tmp_path / "state.json"
    target.write_bytes(b"unchanged")
    target.chmod(0o400)
    try:
        if operation == "state":
            with pytest.raises(OSError) as raised:
                _registry().save_to_disk(target)
            _assert_sanitized(str(raised.value), target)
        else:
            result = logseq_agent_write("must not append", str(config), str(pages))
            assert result["status"] == "error"
            _assert_sanitized(result["message"], target)
        assert target.read_bytes() == b"unchanged"
    finally:
        target.chmod(0o600)


@pytest.mark.parametrize("append", [False, True])
def test_utf8_and_native_text_newlines_match_previous_text_mode(
    tmp_path: Path, append: bool
) -> None:
    expected = tmp_path / "expected.txt"
    target = tmp_path / "actual.txt"
    text = "café\nline\r\nlast\rno-newline"
    if append:
        expected.write_bytes(b"prefix\n")
        target.write_bytes(b"prefix\n")
    with expected.open("a" if append else "w", encoding="utf-8") as stream:
        stream.write(text)

    _write_agent_file(target, text, append=append)

    assert target.read_bytes() == expected.read_bytes()


def test_short_append_writes_keep_header_and_full_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "append.txt"
    target.write_bytes(b"header\n")
    real_write = os.write

    def short_write(fd: int, data: bytes | memoryview) -> int:
        return real_write(fd, data[:2])

    monkeypatch.setattr(os, "write", short_write)

    _write_agent_file(target, "body\n", append=True)

    assert target.read_bytes() == b"header\n" + "body\n".replace("\n", os.linesep).encode()


def test_cancellation_closes_owned_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "state.json"
    interrupted: list[int] = []

    def interrupt(fd: int, data: bytes | memoryview) -> int:
        interrupted.append(fd)
        raise KeyboardInterrupt

    monkeypatch.setattr(os, "write", interrupt)

    with pytest.raises(KeyboardInterrupt):
        _registry().save_to_disk(target)

    assert len(interrupted) == 1
    with pytest.raises(OSError):
        os.fstat(interrupted[0])


@pytest.mark.parametrize("write_fails", [False, True])
def test_close_failure_is_reported_without_retry_or_masking_primary_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, write_fails: bool
) -> None:
    target = tmp_path / "state.json"
    closed: list[int] = []
    real_close = os.close

    def close_then_fail(fd: int) -> None:
        closed.append(fd)
        real_close(fd)
        raise OSError(f"sensitive close failure at {target}")

    def fail_write(fd: int, data: bytes | memoryview) -> int:
        raise OSError(f"sensitive write failure at {target}")

    with monkeypatch.context() as injected:
        injected.setattr(os, "close", close_then_fail)
        if write_fails:
            injected.setattr(os, "write", fail_write)
        with pytest.raises(OSError) as raised:
            _registry().save_to_disk(target)

    assert len(closed) == 1
    _assert_sanitized(str(raised.value), target)
    if write_fails:
        assert "Agent file descriptor cleanup failed." in raised.value.__notes__
    else:
        assert "closed" in str(raised.value)
        assert SessionAliasRegistry.load_from_disk(target).resolve_alias(0) == BLOCK_UUID
    with pytest.raises(OSError):
        os.fstat(closed[0])


def test_interrupted_state_rewrite_makes_later_alias_write_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    graph = tmp_path / "graph"
    pages = graph / "pages"
    pages.mkdir(parents=True)
    source = pages / "Page.md"
    original = f"- parent\n  id:: {BLOCK_UUID}\n".encode()
    source.write_bytes(original)
    state = graph / ".matryca_xray_state.json"
    _registry().save_to_disk(state)

    def fail_write(fd: int, data: bytes | memoryview) -> int:
        raise OSError("injected state-write failure")

    with monkeypatch.context() as injected:
        injected.setattr(os, "write", fail_write)
        with pytest.raises(OSError):
            _registry().save_to_disk(state)
    assert state.read_bytes() == b""

    result = CliRunner().invoke(
        app, ["agent-write", str(graph), "--alias", "0", "--content", "must not write"]
    )

    assert result.exit_code == 1
    assert result.stdout == ""
    assert source.read_bytes() == original
