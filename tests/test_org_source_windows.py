"""Windows-only path and native ABI contract tests for the Org source reader."""

from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from logseq_matryca_parser import _org_source_windows as windows
from logseq_matryca_parser._org_source import (
    OrgSourceCode,
    OrgSourceFailure,
    _windows_components,
    read_org_source,
)


def test_windows_x64_nt_abi_layout() -> None:
    assert ctypes.sizeof(ctypes.c_void_p) == 8
    assert ctypes.sizeof(windows._UNICODE_STRING) == 16
    assert windows._UNICODE_STRING.Buffer.offset == 8
    assert ctypes.sizeof(windows._OBJECT_ATTRIBUTES) == 48
    assert windows._OBJECT_ATTRIBUTES.RootDirectory.offset == 8
    assert windows._OBJECT_ATTRIBUTES.ObjectName.offset == 16
    assert windows._OBJECT_ATTRIBUTES.Attributes.offset == 24
    assert windows._OBJECT_ATTRIBUTES.SecurityDescriptor.offset == 32
    assert windows._OBJECT_ATTRIBUTES.SecurityQualityOfService.offset == 40
    assert ctypes.sizeof(windows._IO_STATUS_BLOCK) == 16
    assert windows._IO_STATUS_BLOCK.Status.offset == 0
    assert windows._IO_STATUS_BLOCK.Information.offset == 8
    status_block = windows._IO_STATUS_BLOCK()
    status_block.Status = windows._NTSTATUS(-1).value
    assert status_block.Status == -1
    assert ctypes.sizeof(windows._FILE_STANDARD_INFO) == 24
    assert ctypes.sizeof(windows._FILE_ATTRIBUTE_TAG_INFO) == 8
    assert windows._NTSTATUS(-1).value == -1
    assert ctypes.sizeof(windows._HANDLE) == 8


def test_windows_file_information_class_values_match_nt_query_contract() -> None:
    assert windows._FILE_STANDARD_INFORMATION == 5
    assert windows._FILE_ATTRIBUTE_TAG_INFORMATION == 35


def test_windows_open_contract_uses_exact_flags_and_access_masks() -> None:
    assert windows._OBJ_CASE_INSENSITIVE == 0x40
    assert windows._FILE_OPEN == 1
    assert windows._FILE_SHARE_ALL == 0x7
    assert windows._FILE_OPEN_REPARSE_POINT == 0x00200000
    assert windows._FILE_SYNCHRONOUS_IO_NONALERT == 0x20
    assert windows._FILE_READ_DATA == 0x1
    assert windows._FILE_READ_ATTRIBUTES == 0x80
    assert windows._FILE_TRAVERSE == 0x20
    assert windows._SYNCHRONIZE == 0x00100000
    assert not hasattr(windows, "_FILE_DIRECTORY_FILE")
    assert not hasattr(windows, "_FILE_NON_DIRECTORY_FILE")


def test_windows_utf16_name_uses_byte_length_not_codepoint_count() -> None:
    value, backing = windows._unicode_string("é.org")
    raw = ctypes.string_at(ctypes.addressof(backing), ctypes.sizeof(backing))
    assert value.Length == 10
    assert value.MaximumLength == 12
    assert value.Buffer is not None
    assert raw[:10] == "é.org".encode("utf-16-le")
    assert raw[10:12] == b"\0\0"


def test_windows_unicode_string_maximum_includes_utf16_nul_terminator() -> None:
    value, backing = windows._unicode_string("x" * 255)
    raw = ctypes.string_at(ctypes.addressof(backing), ctypes.sizeof(backing))
    assert value.Length == 510
    assert value.MaximumLength == 512
    assert raw[510:512] == b"\0\0"


@pytest.mark.parametrize("ntstatus, iosb_status", [(0, -1), (-1, 0)])
def test_nt_create_file_rejects_either_failure_status_and_closes_output_handle_once(
    monkeypatch: pytest.MonkeyPatch, ntstatus: int, iosb_status: int
) -> None:
    output_value = 0x1234
    closed: list[int] = []

    def create_file(output_handle, _access, _attributes, iosb, *_rest):
        ctypes.cast(output_handle, ctypes.POINTER(ctypes.c_void_p)).contents.value = output_value
        ctypes.cast(iosb, ctypes.POINTER(windows._IO_STATUS_BLOCK)).contents.Status = iosb_status
        return ntstatus

    monkeypatch.setattr(
        windows,
        "_close_failed_handle",
        lambda handle: closed.append(cast(int, ctypes.cast(handle, ctypes.c_void_p).value)),
        raising=False,
    )
    result = windows._nt_create_file(SimpleNamespace(NtCreateFile=create_file), "page.org", None, 0)
    assert result is None
    assert closed == [output_value]


@pytest.mark.parametrize("ntstatus, iosb_status", [(0, -1), (-1, 0)])
def test_nt_query_information_rejects_either_failure_status(ntstatus: int, iosb_status: int) -> None:
    def query(_handle, iosb, _output, _length, _class):
        ctypes.cast(iosb, ctypes.POINTER(windows._IO_STATUS_BLOCK)).contents.Status = iosb_status
        return ntstatus

    with pytest.raises(OSError):
        windows._query_handle(SimpleNamespace(NtQueryInformationFile=query), ctypes.c_void_p(0x1234), 1, ctypes.c_int32)


@pytest.mark.parametrize("spelling", [r"C:\folder/name.org", "C:\\COM¹.org", "C:\\\ud800.org"])
def test_windows_rejects_win32_invalid_and_reserved_names(spelling: str) -> None:
    result = read_org_source(spelling)
    assert isinstance(result, OrgSourceFailure)
    assert result.code is OrgSourceCode.PATH_INVALID


def test_windows_path_validation_counts_supplementary_codepoint_as_two_utf16_units() -> None:
    parsed = _windows_components("C:\\😀.org")
    assert parsed == ("C", [("😀.org", (0xD83D, 0xDE00, 0x2E, 0x6F, 0x72, 0x67))])


def test_windows_path_validation_rejects_lone_surrogate() -> None:
    parsed = _windows_components("C:\\\ud800.org")
    assert isinstance(parsed, OrgSourceFailure)
    assert parsed.code is OrgSourceCode.PATH_INVALID


@pytest.mark.parametrize(
    "spelling",
    [
        r"relative\page.org",
        r"C:page.org",
        r"\\server\share\page.org",
        r"\??\C:\page.org",
        r"C:/page.org",
        r"C:\folder\..\page.org",
        r"C:\folder\\page.org",
        r"C:\folder\page.ORG",
        r"C:\folder\page.org:stream",
        r"C:\CON.org",
        r"C:\folder.\page.org",
    ],
)
def test_windows_rejects_invalid_path_grammar(spelling: str) -> None:
    result = read_org_source(spelling)
    assert isinstance(result, OrgSourceFailure)
    assert result.code is OrgSourceCode.PATH_INVALID


def test_windows_rejects_posix_absolute_spelling_as_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")

    result = read_org_source("/tmp/page.org")

    assert isinstance(result, OrgSourceFailure)
    assert result.code is OrgSourceCode.PATH_INVALID


@pytest.mark.skipif(sys.platform == "win32", reason="native Windows qualification is a separate matrix")
def test_non_windows_platform_fails_closed_for_windows_path() -> None:
    result = read_org_source(r"C:\folder\page.org")
    assert isinstance(result, OrgSourceFailure)
    assert result.code is OrgSourceCode.SOURCE_UNSUPPORTED


@pytest.mark.skipif(sys.platform != "win32", reason="native Windows x64 handle qualification")
def test_native_windows_regular_file_passes_ntfs_leaf_predicates(tmp_path: Path) -> None:
    assert ctypes.sizeof(ctypes.c_void_p) == 8
    path = tmp_path / "page.org"
    expected = b"* native Windows source\n"
    path.write_bytes(expected)

    assert read_org_source(path) == expected


@pytest.mark.skipif(sys.platform != "win32", reason="native Windows x64 leaf qualification")
def test_native_windows_rejects_directory_as_org_leaf(tmp_path: Path) -> None:
    assert ctypes.sizeof(ctypes.c_void_p) == 8
    path = tmp_path / "directory.org"
    path.mkdir()

    result = read_org_source(path)

    assert isinstance(result, OrgSourceFailure)
    assert result.code is OrgSourceCode.SOURCE_REJECTED


@pytest.mark.skipif(sys.platform != "win32", reason="native Windows x64 reparse-point qualification")
def test_native_windows_rejects_parent_reparse_point(tmp_path: Path) -> None:
    assert ctypes.sizeof(ctypes.c_void_p) == 8
    real_parent = tmp_path / "real"
    real_parent.mkdir()
    (real_parent / "page.org").write_bytes(b"* page\n")
    link_parent = tmp_path / "linked"
    try:
        os.symlink(real_parent, link_parent, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"directory symlink creation is unavailable: {error}")

    result = read_org_source(link_parent / "page.org")

    assert isinstance(result, OrgSourceFailure)
    assert result.code is OrgSourceCode.SOURCE_REJECTED


@pytest.mark.skipif(sys.platform != "win32", reason="native Windows x64 reparse-point qualification")
def test_native_windows_rejects_leaf_reparse_point(tmp_path: Path) -> None:
    assert ctypes.sizeof(ctypes.c_void_p) == 8
    target = tmp_path / "target.org"
    target.write_bytes(b"* page\n")
    link = tmp_path / "page.org"
    try:
        os.symlink(target, link)
    except OSError as error:
        pytest.skip(f"file symlink creation is unavailable: {error}")

    result = read_org_source(link)

    assert isinstance(result, OrgSourceFailure)
    assert result.code is OrgSourceCode.SOURCE_REJECTED
