"""Descriptor-relative, same-filesystem Org source reader for macOS and Linux."""

from __future__ import annotations

import ctypes
import errno
import os
import stat
import sys
from contextlib import suppress
from typing import Literal

from ._org_source_contract import _MAX_SOURCE_BYTES, OrgSourceCode, OrgSourceFailure


class _DarwinStatFS(ctypes.Structure):
    """The 64-bit ``struct statfs`` selected by current arm64 macOS headers."""

    _fields_ = [
        ("f_bsize", ctypes.c_uint32),
        ("f_iosize", ctypes.c_int32),
        ("f_blocks", ctypes.c_uint64),
        ("f_bfree", ctypes.c_uint64),
        ("f_bavail", ctypes.c_uint64),
        ("f_files", ctypes.c_uint64),
        ("f_ffree", ctypes.c_uint64),
        ("f_fsid", ctypes.c_int32 * 2),
        ("f_owner", ctypes.c_uint32),
        ("f_type", ctypes.c_uint32),
        ("f_flags", ctypes.c_uint32),
        ("f_fssubtype", ctypes.c_uint32),
        ("f_fstypename", ctypes.c_char * 16),
        ("f_mntonname", ctypes.c_char * 1024),
        ("f_mntfromname", ctypes.c_char * 1024),
        ("f_flags_ext", ctypes.c_uint32),
        ("f_reserved", ctypes.c_uint32 * 7),
    ]


class _LinuxStatFS(ctypes.Structure):
    """The glibc x86_64 ``struct statfs`` layout used by ubuntu-24.04."""

    _fields_ = [
        ("f_type", ctypes.c_int64),
        ("f_bsize", ctypes.c_int64),
        ("f_blocks", ctypes.c_uint64),
        ("f_bfree", ctypes.c_uint64),
        ("f_bavail", ctypes.c_uint64),
        ("f_files", ctypes.c_uint64),
        ("f_ffree", ctypes.c_uint64),
        ("f_fsid", ctypes.c_int * 2),
        ("f_namelen", ctypes.c_uint64),
        ("f_frsize", ctypes.c_uint64),
        ("f_flags", ctypes.c_uint64),
        ("f_spare", ctypes.c_uint64 * 4),
    ]


def _layout_matches(structure, *, size: int, offsets: dict[str, int]) -> bool:
    try:
        return ctypes.sizeof(structure) == size and all(
            getattr(structure, field).offset == offset for field, offset in offsets.items()
        )
    except (AttributeError, TypeError):
        return False


def _statfs_for_fd(descriptor: int, platform: Literal["darwin", "linux"] | None = None):
    selected = platform or sys.platform
    structure: type[_DarwinStatFS] | type[_LinuxStatFS]
    if selected == "darwin":
        structure = _DarwinStatFS
        if not _layout_matches(
            structure,
            size=2168,
            offsets={"f_fstypename": 72, "f_mntonname": 88, "f_mntfromname": 1112},
        ):
            raise NotImplementedError
        if sys.platform != "darwin" or os.uname().machine != "arm64":
            raise NotImplementedError
    elif selected == "linux":
        structure = _LinuxStatFS
        if not _layout_matches(
            structure,
            size=120,
            offsets={"f_type": 0, "f_bsize": 8, "f_blocks": 16, "f_fsid": 56, "f_namelen": 64, "f_spare": 88},
        ):
            raise NotImplementedError
        if ctypes.sizeof(ctypes.c_void_p) != 8 or ctypes.sizeof(ctypes.c_long) != 8:
            raise NotImplementedError
        if sys.platform != "linux" or os.uname().machine != "x86_64":
            raise NotImplementedError
    else:
        raise NotImplementedError
    library = ctypes.CDLL(None, use_errno=True)
    call = getattr(library, "fstatfs", None)
    if call is None:
        raise NotImplementedError
    call.argtypes = [ctypes.c_int, ctypes.POINTER(structure)]
    call.restype = ctypes.c_int
    result = structure()
    if call(descriptor, ctypes.byref(result)) != 0:
        error = ctypes.get_errno()
        raise OSError(error, "fstatfs failed")
    return result


def _is_allowed_filesystem(descriptor: int, platform: Literal["darwin", "linux"]) -> bool:
    details = _statfs_for_fd(descriptor, platform)
    if platform == "darwin":
        return details.f_fstypename.split(b"\0", 1)[0].lower() == b"apfs"
    return ctypes.c_uint(details.f_type).value == 0xEF53


def _rejected() -> OrgSourceFailure:
    return OrgSourceFailure(OrgSourceCode.SOURCE_REJECTED)


def _read_failed() -> OrgSourceFailure:
    return OrgSourceFailure(OrgSourceCode.READ_FAILED)


def read_posix_source(components: list[str], *, platform: Literal["darwin", "linux"]) -> bytes | OrgSourceFailure:
    """Walk from root using held directory descriptors; never reopen by full path."""
    required_flags = ("O_RDONLY", "O_DIRECTORY", "O_CLOEXEC", "O_NOFOLLOW", "O_NONBLOCK", "O_NOCTTY")
    if any(not hasattr(os, name) for name in required_flags) or os.open not in getattr(os, "supports_dir_fd", set()):
        return OrgSourceFailure(OrgSourceCode.SOURCE_UNSUPPORTED)
    if platform == "darwin":
        if sys.platform != "darwin" or os.uname().machine != "arm64":
            return OrgSourceFailure(OrgSourceCode.SOURCE_UNSUPPORTED)
        parent_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
        leaf_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_NOCTTY
    elif platform == "linux":
        if sys.platform != "linux" or os.uname().machine != "x86_64" or not hasattr(os, "O_PATH"):
            return OrgSourceFailure(OrgSourceCode.SOURCE_UNSUPPORTED)
        parent_flags = os.O_PATH | os.O_CLOEXEC | os.O_NOFOLLOW
        leaf_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_NOCTTY
    else:
        return OrgSourceFailure(OrgSourceCode.SOURCE_UNSUPPORTED)

    descriptors: list[int] = []
    try:
        try:
            root = os.open("/", parent_flags)
            descriptors.append(root)
            root_stat = os.fstat(root)
            if not stat.S_ISDIR(root_stat.st_mode):
                return _rejected()
            if not _is_allowed_filesystem(root, platform):
                return _rejected()
            device = root_stat.st_dev

            parent = root
            for component in components[:-1]:
                child = os.open(component, parent_flags, dir_fd=parent)
                descriptors.append(child)
                child_stat = os.fstat(child)
                if not stat.S_ISDIR(child_stat.st_mode) or (platform == "linux" and child_stat.st_dev != device):
                    return _rejected()
                if not _is_allowed_filesystem(child, platform):
                    return _rejected()
                parent = child

            leaf = os.open(components[-1], leaf_flags, dir_fd=parent)
            descriptors.append(leaf)
            leaf_stat = os.fstat(leaf)
            if not stat.S_ISREG(leaf_stat.st_mode) or (platform == "linux" and leaf_stat.st_dev != device):
                return _rejected()
            if not _is_allowed_filesystem(leaf, platform):
                return _rejected()
            if leaf_stat.st_size > _MAX_SOURCE_BYTES:
                return OrgSourceFailure(OrgSourceCode.SOURCE_TOO_LARGE)

            content = bytearray()
            while True:
                remaining = _MAX_SOURCE_BYTES + 1 - len(content)
                block = os.read(leaf, min(65_536, remaining))
                if not block:
                    return bytes(content)
                content.extend(block)
                if len(content) > _MAX_SOURCE_BYTES:
                    return OrgSourceFailure(OrgSourceCode.SOURCE_TOO_LARGE)
        except NotImplementedError:
            return OrgSourceFailure(OrgSourceCode.SOURCE_UNSUPPORTED)
        except UnicodeError:
            return _read_failed()
        except OSError as error:
            if error.errno in {errno.ELOOP, errno.ENOTDIR}:
                return _rejected()
            return _read_failed()
        except (AttributeError, TypeError, ValueError, OverflowError):
            return OrgSourceFailure(OrgSourceCode.SOURCE_UNSUPPORTED)
    finally:
        for descriptor in reversed(descriptors):
            with suppress(OSError):
                os.close(descriptor)
