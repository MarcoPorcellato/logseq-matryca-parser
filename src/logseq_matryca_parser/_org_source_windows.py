"""Handle-relative NT source reader for the supported Windows x64 profile."""

from __future__ import annotations

import ctypes
import os
import sys
from ctypes import wintypes
from typing import Any, cast

from ._org_source_contract import (
    _MAX_SOURCE_BYTES,
    OrgSourceCode,
    OrgSourceFailure,
    _utf16_code_units,
)


class _UNICODE_STRING(ctypes.Structure):
    _fields_ = [
        ("Length", ctypes.c_uint16),
        ("MaximumLength", ctypes.c_uint16),
        ("Buffer", ctypes.POINTER(ctypes.c_uint16)),
    ]


class _OBJECT_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("Length", ctypes.c_uint32),
        ("RootDirectory", wintypes.HANDLE),
        ("ObjectName", ctypes.POINTER(_UNICODE_STRING)),
        ("Attributes", ctypes.c_uint32),
        ("SecurityDescriptor", wintypes.LPVOID),
        ("SecurityQualityOfService", wintypes.LPVOID),
    ]


class _IO_STATUS_BLOCK_UNION(ctypes.Union):
    _fields_ = [("Status", ctypes.c_int32), ("Pointer", wintypes.LPVOID)]


class _IO_STATUS_BLOCK(ctypes.Structure):
    _anonymous_ = ("_value",)
    _fields_ = [("_value", _IO_STATUS_BLOCK_UNION), ("Information", ctypes.c_size_t)]


class _FILE_STANDARD_INFO(ctypes.Structure):
    _fields_ = [
        ("AllocationSize", ctypes.c_int64),
        ("EndOfFile", ctypes.c_int64),
        ("NumberOfLinks", ctypes.c_uint32),
        ("DeletePending", ctypes.c_uint8),
        ("Directory", ctypes.c_uint8),
    ]


class _FILE_ATTRIBUTE_TAG_INFO(ctypes.Structure):
    _fields_ = [("FileAttributes", ctypes.c_uint32), ("ReparseTag", ctypes.c_uint32)]


_HANDLE = ctypes.c_void_p
_NTSTATUS = ctypes.c_int32
_OBJ_CASE_INSENSITIVE = 0x40
_FILE_OPEN = 1
_FILE_READ_DATA = 0x0001
_FILE_READ_ATTRIBUTES = 0x0080
_FILE_TRAVERSE = 0x0020
_SYNCHRONIZE = 0x00100000
_FILE_SHARE_ALL = 0x00000001 | 0x00000002 | 0x00000004
_FILE_OPEN_REPARSE_POINT = 0x00200000
_FILE_SYNCHRONOUS_IO_NONALERT = 0x00000020
_FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
_FILE_STANDARD_INFORMATION = 5
_FILE_ATTRIBUTE_TAG_INFORMATION = 35
_FILE_TYPE_DISK = 0x0001
_INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


def _unicode_string(
    value: str, code_units: tuple[int, ...] | None = None
) -> tuple[_UNICODE_STRING, ctypes.Array[ctypes.c_uint16]]:
    units = code_units if code_units is not None else _utf16_code_units(value, max_units=32_767)
    if units is None:
        raise ValueError("invalid UTF-16 name")
    encoded_length = len(units) * ctypes.sizeof(ctypes.c_uint16)
    maximum_length = encoded_length + ctypes.sizeof(ctypes.c_uint16)
    if maximum_length > 0xFFFF:
        raise ValueError("UTF-16 name exceeds UNICODE_STRING limits")
    backing = (ctypes.c_uint16 * (len(units) + 1))(*units, 0)
    descriptor = _UNICODE_STRING(
        encoded_length,
        maximum_length,
        ctypes.cast(backing, ctypes.POINTER(ctypes.c_uint16)),
    )
    return descriptor, backing


def _nt_create_file(ntdll, name: str, root, access: int, code_units: tuple[int, ...] | None = None):
    descriptor, backing = _unicode_string(name, code_units)
    attributes = _OBJECT_ATTRIBUTES(
        ctypes.sizeof(_OBJECT_ATTRIBUTES),
        root,
        ctypes.pointer(descriptor),
        _OBJ_CASE_INSENSITIVE,
        None,
        None,
    )
    status_block = _IO_STATUS_BLOCK()
    handle = _HANDLE()
    status = ntdll.NtCreateFile(
        ctypes.byref(handle),
        access,
        ctypes.byref(attributes),
        ctypes.byref(status_block),
        None,
        0,
        _FILE_SHARE_ALL,
        _FILE_OPEN,
        _FILE_OPEN_REPARSE_POINT | _FILE_SYNCHRONOUS_IO_NONALERT,
        None,
        0,
    )
    del backing
    handle_value = ctypes.cast(handle, ctypes.c_void_p).value
    if int(status) < 0 or status_block.Status < 0:
        if handle_value not in (None, _INVALID_HANDLE_VALUE):
            _close_failed_handle(handle)
        return None
    if handle_value in (None, _INVALID_HANDLE_VALUE):
        return None
    return handle


def _close_failed_handle(handle) -> None:
    """Release an output handle returned alongside a failed create status."""
    cast(Any, ctypes).WinDLL("kernel32", use_last_error=True).CloseHandle(handle)


def _query_handle(ntdll, handle, information_class: int, structure):
    result = structure()
    status_block = _IO_STATUS_BLOCK()
    status = ntdll.NtQueryInformationFile(
        handle,
        ctypes.byref(status_block),
        ctypes.byref(result),
        ctypes.sizeof(result),
        information_class,
    )
    if int(status) < 0 or status_block.Status < 0:
        raise OSError("handle information unavailable")
    return result


def _ntfs_volume(kernel32, handle) -> tuple[bool, int, int]:
    volume_name = ctypes.create_unicode_buffer(32768)
    filesystem_name = ctypes.create_unicode_buffer(256)
    serial = wintypes.DWORD()
    max_component = wintypes.DWORD()
    flags = wintypes.DWORD()
    if not kernel32.GetVolumeInformationByHandleW(
        handle,
        volume_name,
        len(volume_name),
        ctypes.byref(serial),
        ctypes.byref(max_component),
        ctypes.byref(flags),
        filesystem_name,
        len(filesystem_name),
    ):
        raise OSError("volume information unavailable")
    return filesystem_name.value.upper() == "NTFS", max_component.value, serial.value


def _close(kernel32, handles: list[_HANDLE]) -> None:
    for handle in reversed(handles):
        if handle and ctypes.cast(handle, ctypes.c_void_p).value not in (None, _INVALID_HANDLE_VALUE):
            kernel32.CloseHandle(handle)


def read_windows_source(
    drive: str, components: list[tuple[str, tuple[int, ...]]]
) -> bytes | OrgSourceFailure:
    if sys.platform != "win32" or os.name != "nt" or ctypes.sizeof(ctypes.c_void_p) != 8:
        return OrgSourceFailure(OrgSourceCode.SOURCE_UNSUPPORTED)
    if (
        ctypes.sizeof(_UNICODE_STRING) != 16
        or _UNICODE_STRING.Buffer.offset != 8
        or ctypes.sizeof(_OBJECT_ATTRIBUTES) != 48
        or _OBJECT_ATTRIBUTES.RootDirectory.offset != 8
        or _OBJECT_ATTRIBUTES.ObjectName.offset != 16
        or _OBJECT_ATTRIBUTES.Attributes.offset != 24
        or _OBJECT_ATTRIBUTES.SecurityDescriptor.offset != 32
        or _OBJECT_ATTRIBUTES.SecurityQualityOfService.offset != 40
        or ctypes.sizeof(_IO_STATUS_BLOCK) != 16
        or _IO_STATUS_BLOCK.Information.offset != 8
        or ctypes.sizeof(_NTSTATUS) != 4
    ):
        return OrgSourceFailure(OrgSourceCode.SOURCE_UNSUPPORTED)
    try:
        ntdll = ctypes.WinDLL("ntdll", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        for name in ("NtCreateFile", "NtQueryInformationFile"):
            if not hasattr(ntdll, name):
                return OrgSourceFailure(OrgSourceCode.SOURCE_UNSUPPORTED)
        for name in ("GetVolumeInformationByHandleW", "GetFileType", "ReadFile", "CloseHandle"):
            if not hasattr(kernel32, name):
                return OrgSourceFailure(OrgSourceCode.SOURCE_UNSUPPORTED)
    except (AttributeError, OSError):
        return OrgSourceFailure(OrgSourceCode.SOURCE_UNSUPPORTED)

    handles: list[_HANDLE] = []
    try:
        root = _nt_create_file(
            ntdll,
            "\\??\\" + drive + ":\\",
            None,
            _FILE_READ_ATTRIBUTES | _FILE_TRAVERSE | _SYNCHRONIZE,
        )
        if root is None:
            return OrgSourceFailure(OrgSourceCode.READ_FAILED)
        handles.append(root)
        root_standard = _query_handle(ntdll, root, _FILE_STANDARD_INFORMATION, _FILE_STANDARD_INFO)
        root_attributes = _query_handle(ntdll, root, _FILE_ATTRIBUTE_TAG_INFORMATION, _FILE_ATTRIBUTE_TAG_INFO)
        allowed_fs, max_component, volume_serial = _ntfs_volume(kernel32, root)
        if not bool(root_standard.Directory) or root_attributes.FileAttributes & _FILE_ATTRIBUTE_REPARSE_POINT or not allowed_fs:
            return OrgSourceFailure(OrgSourceCode.SOURCE_REJECTED)

        parent = root
        leaf = None
        for index, (component, code_units) in enumerate(components):
            if len(code_units) > 255 or len(code_units) > max_component:
                return OrgSourceFailure(OrgSourceCode.PATH_INVALID)
            is_leaf = index == len(components) - 1
            access = _SYNCHRONIZE | _FILE_READ_ATTRIBUTES
            if not is_leaf:
                access |= _FILE_TRAVERSE
            else:
                access |= _FILE_READ_DATA
            child = _nt_create_file(ntdll, component, parent, access, code_units)
            if child is None:
                return OrgSourceFailure(OrgSourceCode.READ_FAILED)
            handles.append(child)
            standard = _query_handle(ntdll, child, _FILE_STANDARD_INFORMATION, _FILE_STANDARD_INFO)
            attributes = _query_handle(ntdll, child, _FILE_ATTRIBUTE_TAG_INFORMATION, _FILE_ATTRIBUTE_TAG_INFO)
            allowed_fs, max_component, child_volume_serial = _ntfs_volume(kernel32, child)
            if attributes.FileAttributes & _FILE_ATTRIBUTE_REPARSE_POINT or not allowed_fs or child_volume_serial != volume_serial:
                return OrgSourceFailure(OrgSourceCode.SOURCE_REJECTED)
            if bool(standard.Directory) != (not is_leaf):
                return OrgSourceFailure(OrgSourceCode.SOURCE_REJECTED)
            if is_leaf:
                leaf = child
                if kernel32.GetFileType(leaf) != _FILE_TYPE_DISK:
                    return OrgSourceFailure(OrgSourceCode.SOURCE_REJECTED)
                if standard.EndOfFile < 0 or standard.EndOfFile > _MAX_SOURCE_BYTES:
                    return OrgSourceFailure(OrgSourceCode.SOURCE_TOO_LARGE)
            else:
                parent = child

        if leaf is None:
            return OrgSourceFailure(OrgSourceCode.READ_FAILED)
        output = bytearray()
        while True:
            capacity = min(65_536, _MAX_SOURCE_BYTES + 1 - len(output))
            buffer = ctypes.create_string_buffer(capacity)
            read = wintypes.DWORD()
            if not kernel32.ReadFile(leaf, buffer, capacity, ctypes.byref(read), None):
                return OrgSourceFailure(OrgSourceCode.READ_FAILED)
            if read.value == 0:
                return bytes(output)
            output.extend(buffer.raw[: read.value])
            if len(output) > _MAX_SOURCE_BYTES:
                return OrgSourceFailure(OrgSourceCode.SOURCE_TOO_LARGE)
    except (OSError, OverflowError, TypeError, ValueError, UnicodeError):
        return OrgSourceFailure(OrgSourceCode.READ_FAILED)
    finally:
        _close(kernel32, handles)
