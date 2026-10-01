"""Tests for the private, read-only Org source acquisition boundary."""

from __future__ import annotations

import os
import platform
import sys
from pathlib import Path

import pytest

from logseq_matryca_parser._org_source import OrgSourceCode, OrgSourceFailure, read_org_source


def _org_file(directory: Path, name: str = "page.org", data: bytes = b"* page\n") -> Path:
    path = directory / name
    path.write_bytes(data)
    return path


@pytest.mark.parametrize("spelling", [b"/tmp/page.org", "relative.org", "./page.org", "../page.org", "/tmp//page.org", "/tmp/page.org/", "/tmp/page.ORG", "/tmp/a\x00.org"])
def test_rejects_invalid_path_spellings(spelling: str | bytes) -> None:
    result = read_org_source(spelling)  # type: ignore[arg-type]
    assert isinstance(result, OrgSourceFailure)
    assert result.code is OrgSourceCode.PATH_INVALID


def test_path_object_normalization_is_validated_as_exposed() -> None:
    # pathlib removes dot components before os.fspath exposes the spelling.
    path = Path("/tmp") / "folder" / ".." / "page.org"
    result = read_org_source(path)
    assert isinstance(result, OrgSourceFailure)
    assert result.code is OrgSourceCode.PATH_INVALID


def test_rejects_arbitrary_pathlike_without_calling_fspath() -> None:
    class CustomPathLike:
        called = False

        def __fspath__(self) -> str:
            self.called = True
            return "/tmp/page.org"

    custom_path = CustomPathLike()
    result = read_org_source(custom_path)  # type: ignore[arg-type]
    assert isinstance(result, OrgSourceFailure)
    assert result.code is OrgSourceCode.PATH_INVALID
    assert custom_path.called is False


def test_reads_raw_bytes_from_one_regular_org_file(tmp_path: Path) -> None:
    expected = b"* page\n\xff"
    path = _org_file(tmp_path, data=expected)
    assert read_org_source(path) == expected


def test_rejects_leaf_symlink_without_exposing_path(tmp_path: Path) -> None:
    target = _org_file(tmp_path, "target.org")
    link = tmp_path / "page.org"
    link.symlink_to(target)
    result = read_org_source(link)
    assert isinstance(result, OrgSourceFailure)
    assert result.code is OrgSourceCode.SOURCE_REJECTED
    assert repr(result) == "OrgSourceFailure(code=<OrgSourceCode.SOURCE_REJECTED: 'ORG_FILE_SOURCE_REJECTED'>)"
    assert str(target) not in repr(result)


def test_rejects_parent_symlink(tmp_path: Path) -> None:
    real_parent = tmp_path / "real"
    real_parent.mkdir()
    _org_file(real_parent)
    link_parent = tmp_path / "link"
    link_parent.symlink_to(real_parent, target_is_directory=True)
    result = read_org_source(link_parent / "page.org")
    assert isinstance(result, OrgSourceFailure)
    assert result.code is OrgSourceCode.SOURCE_REJECTED


def test_rejects_directory_and_non_org_leaf(tmp_path: Path) -> None:
    directory = tmp_path / "folder.org"
    directory.mkdir()
    result = read_org_source(directory)
    assert isinstance(result, OrgSourceFailure)
    assert result.code is OrgSourceCode.SOURCE_REJECTED


def test_source_byte_cap_and_exact_cap(tmp_path: Path) -> None:
    cap = 8_388_608
    exact = _org_file(tmp_path, "exact.org", b"x" * cap)
    assert read_org_source(exact) == b"x" * cap
    too_large = _org_file(tmp_path, "large.org", b"x" * (cap + 1))
    result = read_org_source(too_large)
    assert isinstance(result, OrgSourceFailure)
    assert result.code is OrgSourceCode.SOURCE_TOO_LARGE


def test_rejects_path_over_unicode_codepoint_cap_before_open(monkeypatch: pytest.MonkeyPatch) -> None:
    from logseq_matryca_parser import _org_source_posix as posix

    monkeypatch.setattr(posix.os, "open", lambda *args, **kwargs: pytest.fail("must not open invalid path"))
    result = read_org_source("/" + "a" * 32_767)
    assert isinstance(result, OrgSourceFailure)
    assert result.code is OrgSourceCode.PATH_INVALID


def test_short_reads_are_accumulated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from logseq_matryca_parser import _org_source_posix as posix

    expected = b"short reads stay complete"
    path = _org_file(tmp_path, data=expected)
    original_read = os.read
    monkeypatch.setattr(posix.os, "read", lambda descriptor, size: original_read(descriptor, min(size, 3)))
    assert read_org_source(path) == expected


def test_growing_source_over_cap_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from logseq_matryca_parser import _org_source_posix as posix

    path = _org_file(tmp_path, data=b"")
    monkeypatch.setattr(posix.os, "read", lambda descriptor, size: b"x" * size)
    result = read_org_source(path)
    assert isinstance(result, OrgSourceFailure)
    assert result.code is OrgSourceCode.SOURCE_TOO_LARGE


def test_filesystem_rejection_closes_every_acquired_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from logseq_matryca_parser import _org_source_posix as posix

    path = _org_file(tmp_path)
    opened: list[int] = []
    closed: list[int] = []
    real_open, real_close = os.open, os.close

    def tracked_open(*args, **kwargs):
        descriptor = real_open(*args, **kwargs)
        opened.append(descriptor)
        return descriptor

    def tracked_close(descriptor):
        closed.append(descriptor)
        return real_close(descriptor)

    monkeypatch.setattr(posix.os, "open", tracked_open)
    monkeypatch.setattr(posix.os, "supports_dir_fd", os.supports_dir_fd | {tracked_open})
    monkeypatch.setattr(posix.os, "close", tracked_close)
    monkeypatch.setattr(posix, "_is_allowed_filesystem", lambda *args: False)
    result = read_org_source(path)
    assert isinstance(result, OrgSourceFailure)
    assert result.code is OrgSourceCode.SOURCE_REJECTED
    assert sorted(opened) == sorted(closed)


@pytest.mark.skipif(
    not (sys.platform == "darwin" or (sys.platform == "linux" and platform.machine() == "x86_64")),
    reason="native allowlisted POSIX filesystem traversal qualification",
)
def test_each_held_component_is_checked_before_the_next_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from logseq_matryca_parser import _org_source_posix as posix

    nested = tmp_path / "one" / "two"
    nested.mkdir(parents=True)
    path = _org_file(nested)
    path_components = [part for part in os.fspath(path).split("/") if part]
    expected_handles = 1 + len(path_components)  # root, each parent, and leaf
    selected_platform = "darwin" if sys.platform == "darwin" else "linux"
    real_open, real_close = os.open, os.close
    real_filesystem_check = posix._is_allowed_filesystem

    for rejected_index in range(expected_handles):
        opened: list[int] = []
        checked: list[int] = []
        closed: list[int] = []

        def tracked_open(
            name, flags, *args, _open=real_open, _opened=opened, **kwargs
        ):
            descriptor = _open(name, flags, *args, **kwargs)
            _opened.append(descriptor)
            return descriptor

        def tracked_close(
            descriptor: int, *, _closed=closed, _close=real_close
        ) -> None:
            _closed.append(descriptor)
            _close(descriptor)

        def reject_selected_component(
            descriptor: int,
            selected: str,
            *,
            _checked=checked,
            _selected_platform=selected_platform,
            _rejected_index=rejected_index,
            _filesystem_check=real_filesystem_check,
        ) -> bool:
            _checked.append(descriptor)
            assert selected == _selected_platform
            if len(_checked) - 1 == _rejected_index:
                return False
            return _filesystem_check(descriptor, selected)  # type: ignore[arg-type]

        with monkeypatch.context() as patcher:
            patcher.setattr(posix.os, "open", tracked_open)
            patcher.setattr(posix.os, "supports_dir_fd", os.supports_dir_fd | {tracked_open})
            patcher.setattr(posix.os, "close", tracked_close)
            patcher.setattr(posix, "_is_allowed_filesystem", reject_selected_component)
            result = read_org_source(path)

        assert isinstance(result, OrgSourceFailure)
        assert result.code is OrgSourceCode.SOURCE_REJECTED
        assert checked == opened
        assert len(opened) == rejected_index + 1
        assert sorted(opened) == sorted(closed)


def test_invalid_utf8_is_returned_unchanged_for_parser_handoff(tmp_path: Path) -> None:
    raw = b"* page\n\xff\xfe"
    assert read_org_source(_org_file(tmp_path, data=raw)) == raw


def test_missing_file_maps_to_fixed_read_failure(tmp_path: Path) -> None:
    result = read_org_source(tmp_path / "missing.org")
    assert isinstance(result, OrgSourceFailure)
    assert result.code is OrgSourceCode.READ_FAILED
    assert str(tmp_path) not in repr(result)


def test_unrepresentable_native_path_is_fixed_read_failure(tmp_path: Path) -> None:
    result = read_org_source(f"{tmp_path}/\ud800.org")
    assert isinstance(result, OrgSourceFailure)
    assert result.code is OrgSourceCode.READ_FAILED


@pytest.mark.skipif(sys.platform != "darwin", reason="native macOS fstatfs ABI assertion")
def test_native_macos_statfs_layout_and_filesystem_type(tmp_path: Path) -> None:
    import ctypes

    from logseq_matryca_parser import _org_source_posix as posix

    assert ctypes.sizeof(posix._DarwinStatFS) == 2168
    assert posix._DarwinStatFS.f_fstypename.offset == 72
    assert posix._DarwinStatFS.f_mntonname.offset == 88
    assert posix._DarwinStatFS.f_mntfromname.offset == 1112
    descriptor = os.open(tmp_path, os.O_RDONLY)
    try:
        fs = posix._statfs_for_fd(descriptor)
    finally:
        os.close(descriptor)
    assert fs.f_fstypename.split(b"\0", 1)[0].lower() == b"apfs"


def test_linux_statfs_x64_layout_declaration() -> None:
    import ctypes

    from logseq_matryca_parser import _org_source_posix as posix

    assert ctypes.sizeof(posix._LinuxStatFS) == 120
    assert posix._LinuxStatFS.f_type.offset == 0
    assert posix._LinuxStatFS.f_bsize.offset == 8
    assert posix._LinuxStatFS.f_blocks.offset == 16
    assert posix._LinuxStatFS.f_fsid.offset == 56
    assert posix._LinuxStatFS.f_namelen.offset == 64
    assert posix._LinuxStatFS.f_spare.offset == 88


def test_linux_statfs_target_layout_is_independent_of_host_long_width() -> None:
    import ctypes
    import importlib

    from logseq_matryca_parser import _org_source_posix as posix

    original_c_long, original_c_ulong = ctypes.c_long, ctypes.c_ulong
    try:
        ctypes.c_long = ctypes.c_int32  # type: ignore[assignment, misc]
        ctypes.c_ulong = ctypes.c_uint32  # type: ignore[assignment, misc]
        importlib.reload(posix)
        assert ctypes.sizeof(posix._LinuxStatFS) == 120
        assert posix._LinuxStatFS.f_type.offset == 0
        assert posix._LinuxStatFS.f_bsize.offset == 8
        assert posix._LinuxStatFS.f_blocks.offset == 16
        assert posix._LinuxStatFS.f_fsid.offset == 56
        assert posix._LinuxStatFS.f_namelen.offset == 64
        assert posix._LinuxStatFS.f_spare.offset == 88
    finally:
        ctypes.c_long = original_c_long  # type: ignore[assignment, misc]
        ctypes.c_ulong = original_c_ulong  # type: ignore[assignment, misc]
        importlib.reload(posix)


@pytest.mark.skipif(sys.platform != "linux" or platform.machine() != "x86_64", reason="native Linux x64 fstatfs ABI assertion")
def test_native_linux_fstatfs_abi_and_filesystem_magic(tmp_path: Path) -> None:
    import ctypes

    from logseq_matryca_parser import _org_source_posix as posix

    descriptor = os.open(tmp_path, os.O_RDONLY)
    try:
        fs = posix._statfs_for_fd(descriptor, "linux")
        allowed = posix._is_allowed_filesystem(descriptor, "linux")
    finally:
        os.close(descriptor)
    assert ctypes.sizeof(fs) == 120
    assert fs.f_type != 0
    assert allowed is (ctypes.c_ulong(fs.f_type).value == 0xEF53)


def test_linux_statfs_abi_mismatch_fails_before_calling_native_function(monkeypatch: pytest.MonkeyPatch) -> None:
    import ctypes
    from types import SimpleNamespace

    from logseq_matryca_parser import _org_source_posix as posix

    class WrongStatFS(ctypes.Structure):
        _fields_ = [("f_type", ctypes.c_long)]

    class FakeFunction:
        calls = 0

        def __call__(self, *_args):
            self.calls += 1
            return 0

    native_call = FakeFunction()
    library_loads: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def fake_cdll(*args, **kwargs):
        library_loads.append((args, kwargs))
        return SimpleNamespace(fstatfs=native_call)

    monkeypatch.setattr(posix, "_LinuxStatFS", WrongStatFS)
    monkeypatch.setattr(posix.ctypes, "CDLL", fake_cdll)
    with pytest.raises(NotImplementedError):
        posix._statfs_for_fd(7, "linux")
    assert library_loads == []
    assert native_call.calls == 0
