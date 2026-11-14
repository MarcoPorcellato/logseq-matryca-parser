"""Descriptor-validated agent writes under caller-trusted, stable parent paths.

Existing files are updated in place, not replaced. Writes are not crash-atomic
or serialized across processes; alias state remains an unauthenticated cache.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path


class _AgentFileWriteError(OSError):
    """A controlled agent-file failure whose message contains no source path."""


def _require_regular_single_link(info: os.stat_result) -> None:
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise _AgentFileWriteError("Agent file target is not a singly linked regular file.")


def _write_agent_file(path: Path, text: str, *, append: bool = False) -> None:
    """Validate before rewriting/appending; preserve an existing file's inode.

    New POSIX permissions are at most 0600, subject to umask. New Windows files
    inherit the parent's DACL; POSIX mode bits are not a Windows privacy claim.
    Failure after truncation or writing may leave changed or incomplete bytes.
    """
    fd: int | None = None
    pending: BaseException | None = None
    try:
        # Match the former UTF-8 text writes, including native newline translation.
        payload = text.replace("\n", os.linesep).encode("utf-8")
        try:
            previous = os.lstat(path)
        except FileNotFoundError:
            previous = None
        if previous is not None:
            _require_regular_single_link(previous)

        flags = os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
        flags |= getattr(os, "O_NONBLOCK", 0)
        if append:
            flags |= os.O_APPEND
        if previous is None:
            flags |= os.O_CREAT | os.O_EXCL
        fd = os.open(path, flags, 0o600)
        opened = os.fstat(fd)
        _require_regular_single_link(opened)
        current = os.lstat(path)
        _require_regular_single_link(current)
        identity = (opened.st_dev, opened.st_ino)
        if identity != (current.st_dev, current.st_ino) or (
            previous is not None and identity != (previous.st_dev, previous.st_ino)
        ):
            raise _AgentFileWriteError("Agent file target changed before writing.")

        if not append:
            os.ftruncate(fd, 0)
        remaining = memoryview(payload)
        while remaining:
            written = os.write(fd, remaining)
            if written <= 0:
                raise _AgentFileWriteError("Agent file write made no progress.")
            remaining = remaining[written:]
        os.fsync(fd)
    except (OSError, UnicodeError):
        pending = _AgentFileWriteError("Agent file could not be written safely.")
        raise pending from None
    except BaseException as exc:
        pending = exc
        raise
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                if pending is not None:
                    pending.add_note("Agent file descriptor cleanup failed.")
                else:
                    raise _AgentFileWriteError("Agent file descriptor could not be closed.") from None
