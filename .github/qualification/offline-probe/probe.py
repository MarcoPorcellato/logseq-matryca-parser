"""Private, bounded offline diagnostic probe; invocation remains separately gated."""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.metadata
import importlib.util
import json
import multiprocessing
import os
import re
import select
import selectors
import signal
import stat
import struct
import subprocess
import sys
import time
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

MAX_CHILD_OUTPUT = 4096
MAX_SUMMARY_BYTES = 512 * 1024
MAX_CHILD_SECONDS = 3.0
RUN_SECONDS = 120.0
FINAL_RESERVE_SECONDS = 10.0
MAX_STAGE_SECONDS = 3.0
STAGE_CLEANUP_SECONDS = 0.25
MAX_STAGE_FRAME_BYTES = 2 * 1024 * 1024
MAX_STAGE_PAYLOAD_BYTES = 64 * 1024 * 1024
MAX_STAGE_PAYLOAD_FRAME_BYTES = 90 * 1024 * 1024
STAGE_FRAME_METADATA_BYTES = 64 * 1024
EXPECTED_HEAD = "bda44e60a36cfa73d086159fa7dabea8f29dd519"
EXPECTED_MANIFEST_SHA256 = "6146667f162a6824887862885acd51fda94ccd597e638493a6824b1d14455fe3"
EXPECTED_SOURCE_COMMIT = "08f855f24d66e4509b7ea808554c13b4649e6ee1"
EXPECTED_SOURCE_TREE = "3309b25a2a603036a1a56b51d6e38d206c8106a6"
REPO_ROOT = Path(os.path.abspath(__file__)).parents[3]
EXPECTED_OBSERVER_SHA256 = "aa8a043b0c6a3335bca794756a5ed4ecd181105ade6518724f194a4a84206aa4"
EXPECTED_OBSERVER_DESTINATION = str(
    REPO_ROOT
    / ".superpowers/sdd/corpora/logseq-docs-08f855f24d66e4509b7ea808554c13b4649e6ee1/attempt-2"
)
EXPECTED_COUNT = 313
OBSERVER_RELATIVE_PATH = (
    ".superpowers/sdd/official-corpus-copy-plan/acquisition-attempt-2-observer.json"
)
OUTCOME_CLASSES = {
    "parsed_invariants_pass",
    "expected_domain_rejection",
    "unexpected_exception",
    "raw_content_mismatch",
    "tree_invariants",
}
_SHA256_HEX = frozenset("0123456789abcdef")


class ProbeStop(Exception):
    """Sanitized fail-closed stop; message contains no source content."""


class StageFailure(ProbeStop):
    """Bounded stage failure with observer-confirmed cleanup state."""

    def __init__(self, reason: str, *, cleanup_confirmed: bool) -> None:
        self.cleanup_confirmed = cleanup_confirmed
        super().__init__(reason)


@dataclass
class OwnedOutput:
    path: Path
    parent_fd: int
    directory_fd: int
    name: str
    device: int
    inode: int
    summary_fd: int | None = None

    def close(self) -> None:
        for descriptor in (self.summary_fd, self.directory_fd, self.parent_fd):
            if descriptor is None:
                continue
            with suppress(OSError):
                os.close(descriptor)
        self.summary_fd = None


def _deadline_check(deadline: float, *, cutoff: float | None = None) -> float:
    now = time.monotonic()
    boundary = min(deadline, cutoff) if cutoff is not None else deadline
    if now >= boundary:
        raise ProbeStop("lifecycle_deadline")
    return boundary - now


def _phase_deadline_check(deadline: float, phase_cutoff: float | None = None) -> float:
    cutoff = (
        deadline - FINAL_RESERVE_SECONDS if phase_cutoff is None else min(deadline, phase_cutoff)
    )
    return _deadline_check(deadline, cutoff=cutoff)


def open_directory(
    path: Path, *, deadline: float | None = None, phase_cutoff: float | None = None
) -> int:
    """Open absolute directory through no-follow descriptors, never path-resolve it."""
    if os.name != "posix" or not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise ProbeStop("descriptor_filesystem_unsupported")
    absolute = Path(os.path.abspath(path))
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = os.open(absolute.anchor, flags)
    try:
        for part in absolute.parts[1:]:
            if deadline is not None:
                _phase_deadline_check(deadline, phase_cutoff)
            child = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _safe_relative_file(relative: str) -> tuple[str, ...]:
    path = PurePosixPath(relative)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("unsafe relative path")
    return path.parts


def _open_directory_at(
    root_fd: int,
    relative: str,
    *,
    deadline: float | None = None,
    phase_cutoff: float | None = None,
) -> int:
    current = os.dup(root_fd)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        for part in _safe_relative_file(relative):
            if deadline is not None:
                _phase_deadline_check(deadline, phase_cutoff)
            child = os.open(part, flags, dir_fd=current)
            os.close(current)
            current = child
        return current
    except BaseException:
        os.close(current)
        raise


def _open_parent_at(
    root_fd: int,
    relative: str,
    *,
    deadline: float | None = None,
    phase_cutoff: float | None = None,
) -> tuple[int, str]:
    parts = _safe_relative_file(relative)
    current = os.dup(root_fd)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        for part in parts[:-1]:
            if deadline is not None:
                _phase_deadline_check(deadline, phase_cutoff)
            child = os.open(part, flags, dir_fd=current)
            os.close(current)
            current = child
        return current, parts[-1]
    except BaseException:
        os.close(current)
        raise


def read_regular_at(
    root_fd: int,
    relative: str,
    *,
    expected_size: int | None = None,
    max_bytes: int | None = None,
    deadline: float | None = None,
    phase_cutoff: float | None = None,
) -> bytes:
    parent_fd, leaf = _open_parent_at(
        root_fd, relative, deadline=deadline, phase_cutoff=phase_cutoff
    )
    try:
        fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
        try:
            info = os.fstat(fd)
            if (
                not stat.S_ISREG(info.st_mode)
                or (expected_size is not None and info.st_size != expected_size)
                or (max_bytes is not None and info.st_size > max_bytes)
            ):
                raise ValueError("selected input type or size mismatch")
            size_bound = info.st_size if expected_size is None else expected_size
            chunks: list[bytes] = []
            remaining = size_bound + 1
            while remaining:
                if deadline is not None:
                    _phase_deadline_check(deadline, phase_cutoff)
                chunk = os.read(fd, min(65536, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            data = b"".join(chunks)
            if len(data) != size_bound:
                raise ValueError("selected input changed while reading")
            return data
        finally:
            os.close(fd)
    finally:
        os.close(parent_fd)


def _inventory_at(
    root_fd: int, deadline: float | None = None, *, phase_cutoff: float | None = None
) -> set[str]:
    found: set[str] = set()

    def visit(fd: int, prefix: str) -> None:
        for name in sorted(os.listdir(fd)):
            if deadline is not None:
                _phase_deadline_check(deadline, phase_cutoff)
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            relative = f"{prefix}/{name}" if prefix else name
            _safe_relative_file(relative)
            if stat.S_ISDIR(info.st_mode):
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                try:
                    visit(child, relative)
                finally:
                    os.close(child)
            elif stat.S_ISREG(info.st_mode):
                found.add(relative)
            elif stat.S_ISLNK(info.st_mode):
                raise ValueError("symlink corpus inventory entry")
            else:
                raise ValueError("special corpus inventory entry")

    visit(root_fd, "")
    return found


def validate_destination(destination: str) -> PurePosixPath:
    path = PurePosixPath(destination)
    if (
        path.is_absolute()
        or len(path.parts) < 2
        or path.parts[0] != "corpus"
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.suffix != ".md"
    ):
        raise ValueError("invalid manifest destination")
    return path


def _ensure_no_symlink_ancestors(path: Path) -> None:
    absolute = Path(os.path.abspath(path))
    for candidate in (absolute, *absolute.parents):
        try:
            mode = candidate.lstat().st_mode
        except OSError as exc:
            raise ValueError("source ancestor unavailable") from exc
        if stat.S_ISLNK(mode):
            raise ValueError("symlinked source ancestor")


def _git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def load_verified_inputs(
    root: Path | int,
    entries: list[dict[str, Any]],
    *,
    expected_count: int,
    deadline: float | None = None,
    phase_cutoff: float | None = None,
) -> list[dict[str, Any]]:
    """Read each selected Markdown file once and return those exact checked bytes."""
    if isinstance(root, Path):
        owned_fd = True
        root_fd = open_directory(root, deadline=deadline, phase_cutoff=phase_cutoff)
    else:
        owned_fd = False
        root_fd = root
    if len(entries) != expected_count:
        if owned_fd:
            os.close(root_fd)
        raise ValueError("manifest selection count mismatch")
    try:
        destinations: set[str] = set()
        for entry in entries:
            if deadline is not None:
                _phase_deadline_check(deadline, phase_cutoff)
            destination = str(entry.get("destination", ""))
            destination_path = validate_destination(destination)
            source_path = PurePosixPath(str(entry.get("source_path", "")))
            if (
                source_path.is_absolute()
                or source_path.suffix != ".md"
                or any(part in {"", ".", ".."} for part in source_path.parts)
                or source_path.parts != destination_path.parts[1:]
            ):
                raise ValueError("invalid source identity")
            if destination in destinations:
                raise ValueError("duplicate manifest destination")
            destinations.add(destination_path.relative_to("corpus").as_posix())
        if _inventory_at(root_fd, deadline) != destinations:
            raise ValueError("corpus inventory mismatch")

        records: list[dict[str, Any]] = []
        for entry in entries:
            if deadline is not None:
                _phase_deadline_check(deadline, phase_cutoff)
            relative = (
                validate_destination(str(entry["destination"])).relative_to("corpus").as_posix()
            )
            payload = read_regular_at(
                root_fd,
                relative,
                expected_size=int(entry["size"]),
                deadline=deadline,
                phase_cutoff=phase_cutoff,
            )
            if hashlib.sha256(payload).hexdigest() != entry.get("sha256"):
                raise ValueError("selected input sha256 mismatch")
            if _git_blob(payload) != entry.get("git_blob"):
                raise ValueError("selected input Git blob mismatch")
            try:
                payload.decode("utf-8", errors="strict")
            except UnicodeDecodeError as exc:
                raise ValueError("selected input is not strict UTF-8") from exc
            records.append(
                {
                    "source_path": str(entry["source_path"]),
                    "destination": str(entry["destination"]),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "payload": payload,
                }
            )
        return records
    finally:
        if owned_fd:
            os.close(root_fd)


def _packet_result(packet: bytes) -> dict[str, Any]:
    value = json.loads(packet.decode("utf-8", errors="strict"))
    if not isinstance(value, dict) or value.get("classification") not in OUTCOME_CLASSES | {
        "binding_failure"
    }:
        raise ValueError("invalid worker result")
    classification = value["classification"]
    expected_fields = {
        "binding_failure": {"classification"},
        "expected_domain_rejection": {"classification", "exception_type"},
        "unexpected_exception": {"classification", "exception_type"},
        "raw_content_mismatch": {"classification"},
        "tree_invariants": {"classification"},
        "parsed_invariants_pass": {
            "classification",
            "root_count",
            "node_count",
            "invariant_result",
        },
    }[classification]
    if set(value) != expected_fields:
        raise ValueError("worker result shape mismatch")
    if classification in {"expected_domain_rejection", "unexpected_exception"} and (
        not isinstance(value["exception_type"], str)
        or not value["exception_type"]
        or len(value["exception_type"]) > 100
    ):
        raise ValueError("invalid exception classification")
    if classification == "parsed_invariants_pass":
        for key in ("root_count", "node_count"):
            if not isinstance(value[key], int) or isinstance(value[key], bool) or value[key] < 0:
                raise ValueError("invalid node count")
        if value["invariant_result"] != "pass":
            raise ValueError("incomplete worker result")
    return value


def decode_worker_packet(raw: bytes) -> dict[str, Any]:
    """Validate exact child input framing before any import, decode, or parse."""
    try:
        packet = json.loads(raw.decode("utf-8", errors="strict"))
        if not isinstance(packet, dict) or set(packet) != {"payload", "sha256", "page_title"}:
            raise ValueError("packet keys")
        encoded, digest, title = packet["payload"], packet["sha256"], packet["page_title"]
        if (
            not isinstance(encoded, str)
            or not isinstance(digest, str)
            or len(digest) != 64
            or not set(digest) <= _SHA256_HEX
            or not isinstance(title, str)
            or not title
        ):
            raise ValueError("packet field types")
        payload = base64.b64decode(encoded, validate=True)
        if hashlib.sha256(payload).hexdigest() != digest:
            raise ValueError("packet hash")
        text = payload.decode("utf-8", errors="strict")
        return {"classification": "verified", "payload": payload, "text": text, "page_title": title}
    except (UnicodeError, json.JSONDecodeError, ValueError, TypeError, KeyError):
        return {"classification": "binding_failure"}


def classify_worker_setup_error(error: BaseException) -> dict[str, Any]:
    del error
    return {"classification": "binding_failure"}


def classify_parse(
    payload: bytes,
    page_title: str,
    parser_type: type[Any],
    domain_error: type[BaseException],
    check_invariants: Any,
) -> dict[str, Any]:
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return {"classification": "binding_failure"}
    try:
        page = parser_type(tab_size=2, strict_refs=False).parse(text, page_title=page_title)
    except domain_error as exc:
        return _exception_result(exc, domain=True)
    except Exception as exc:
        return _exception_result(exc)
    if page.raw_content != text:
        return {"classification": "raw_content_mismatch"}
    try:
        check_invariants(page)
    except AssertionError:
        return {"classification": "tree_invariants"}
    except Exception as exc:
        return _exception_result(exc)
    pending = list(reversed(page.root_nodes))
    node_count = 0
    while pending:
        node = pending.pop()
        node_count += 1
        pending.extend(reversed(node.children))
    return {
        "classification": "parsed_invariants_pass",
        "root_count": len(page.root_nodes),
        "node_count": node_count,
        "invariant_result": "pass",
    }


def classify_worker_result(packet: bytes, returncode: int) -> dict[str, Any]:
    try:
        result = _packet_result(packet)
    except (UnicodeError, json.JSONDecodeError, ValueError, TypeError):
        return {"classification": "invalid_child_result"}
    if returncode != 0:
        return {"classification": "invalid_child_result"}
    return result


def _process_group_exists(process_group: int) -> bool:
    try:
        os.killpg(process_group, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _signal_group(process_group: int, signum: int) -> None:
    with suppress(ProcessLookupError):
        os.killpg(process_group, signum)


def _stage_pack(value: Any, *, max_payload_bytes: int | None = None) -> Any:
    if isinstance(value, bytes):
        byte_limit = MAX_STAGE_FRAME_BYTES if max_payload_bytes is None else max_payload_bytes
        if len(value) > byte_limit:
            raise ProbeStop("stage_result_too_large")
        return {"__probe_stage_bytes__": base64.b64encode(value).decode("ascii")}
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("stage result keys must be text")
        return {
            key: _stage_pack(item, max_payload_bytes=max_payload_bytes)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_stage_pack(item, max_payload_bytes=max_payload_bytes) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError("unsupported stage result")


def _stage_unpack(value: Any) -> Any:
    if isinstance(value, dict):
        if set(value) == {"__probe_stage_bytes__"}:
            encoded = value["__probe_stage_bytes__"]
            if not isinstance(encoded, str):
                raise ValueError("invalid staged bytes")
            return base64.b64decode(encoded, validate=True)
        return {key: _stage_unpack(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_stage_unpack(item) for item in value]
    return value


def _write_stage_frame(write_fd: int, envelope: dict[str, Any], frame_limit: int) -> None:
    payload = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if not payload or len(payload) > frame_limit:
        payload = b'{"error":"stage_result_too_large","ok":false}'
    pending = memoryview(struct.pack(">I", len(payload)) + payload)
    while pending:
        written = os.write(write_fd, pending[:65536])
        if written <= 0:
            raise OSError("stage IPC closed")
        pending = pending[written:]


def _stage_process_entry(
    result_read_fd: int,
    result_write_fd: int,
    output_read_fd: int,
    output_write_fd: int,
    operation: Any,
    frame_limit: int,
    max_payload_bytes: int | None,
) -> None:
    for descriptor in (result_read_fd, output_read_fd):
        with suppress(OSError):
            os.close(descriptor)
    try:
        os.setsid()
        os.dup2(output_write_fd, 1)
        os.dup2(output_write_fd, 2)
        if output_write_fd not in (1, 2):
            os.close(output_write_fd)
        # Python-level streams may be redirected by pytest or another caller;
        # bind them to the supervised descriptors before invoking the stage.
        sys.stdout = os.fdopen(os.dup(1), "w", buffering=1, encoding="utf-8", errors="replace")
        sys.stderr = os.fdopen(os.dup(2), "w", buffering=1, encoding="utf-8", errors="replace")
        try:
            envelope = {
                "ok": True,
                "value": _stage_pack(operation(), max_payload_bytes=max_payload_bytes),
            }
        except ProbeStop as exc:
            code = str(exc)
            envelope = {
                "ok": False,
                "error": code
                if re.fullmatch(r"[a-z0-9_]{1,80}", code)
                else "stage_operation_failed",
            }
        except BaseException:
            envelope = {"ok": False, "error": "stage_operation_failed"}
        finally:
            for stream in (sys.stdout, sys.stderr):
                with suppress(BaseException):
                    stream.flush()
                    stream.close()
        _write_stage_frame(result_write_fd, envelope, frame_limit)
    except BaseException:
        with suppress(BaseException):
            _write_stage_frame(
                result_write_fd, {"ok": False, "error": "stage_worker_failed"}, frame_limit
            )
    finally:
        with suppress(OSError):
            os.close(result_write_fd)


def _cleanup_stage_process(process: Any, deadline: float) -> bool:
    process_group = process.pid
    try:
        if process.is_alive() or _process_group_exists(process_group):
            _signal_group(process_group, signal.SIGTERM)
            with suppress(OSError, ProcessLookupError):
                process.terminate()
        grace = min(deadline, time.monotonic() + 0.1)
        process.join(max(0.0, grace - time.monotonic()))
        if process.is_alive() or _process_group_exists(process_group):
            _signal_group(process_group, signal.SIGKILL)
            with suppress(OSError, ProcessLookupError):
                process.kill()
        process.join(max(0.0, deadline - time.monotonic()))
        while _process_group_exists(process_group) and time.monotonic() < deadline:
            _signal_group(process_group, signal.SIGKILL)
            time.sleep(min(0.01, max(0.0, deadline - time.monotonic())))
        return process.exitcode is not None and not _process_group_exists(process_group)
    except BaseException:
        with suppress(BaseException):
            _signal_group(process_group, signal.SIGKILL)
        with suppress(BaseException):
            process.kill()
            process.join(max(0.0, deadline - time.monotonic()))
        return False


def _bounded_stage(
    name: str,
    operation: Any,
    *,
    deadline: float,
    reserve_final: bool = True,
    max_payload_bytes: int | None = None,
) -> Any:
    """Run one blocking stage in an observer-owned process and framed pipe."""
    cutoff = deadline - FINAL_RESERVE_SECONDS if reserve_final else deadline
    started = time.monotonic()
    stage_deadline = min(started + MAX_STAGE_SECONDS, cutoff)
    work_deadline = stage_deadline - STAGE_CLEANUP_SECONDS
    if max_payload_bytes is not None and not 0 <= max_payload_bytes <= MAX_STAGE_PAYLOAD_BYTES:
        raise StageFailure("stage_payload_limit_invalid", cleanup_confirmed=True)
    frame_limit = MAX_STAGE_FRAME_BYTES
    if max_payload_bytes is not None:
        base64_bound = 4 * ((max_payload_bytes + 2) // 3)
        frame_limit = min(MAX_STAGE_PAYLOAD_FRAME_BYTES, base64_bound + STAGE_FRAME_METADATA_BYTES)
    if work_deadline <= started:
        raise StageFailure(f"{name}_budget_unavailable", cleanup_confirmed=True)
    if os.name != "posix":
        raise StageFailure("stage_platform_unsupported", cleanup_confirmed=True)
    result_read_fd = result_write_fd = -1
    output_read_fd = output_write_fd = -1
    process: Any | None = None
    start_entered = False
    try:
        result_read_fd, result_write_fd = os.pipe()
        output_read_fd, output_write_fd = os.pipe()
        os.set_blocking(result_read_fd, False)
        os.set_blocking(output_read_fd, False)
        process = multiprocessing.get_context("fork").Process(
            target=_stage_process_entry,
            args=(
                result_read_fd,
                result_write_fd,
                output_read_fd,
                output_write_fd,
                operation,
                frame_limit,
                max_payload_bytes,
            ),
            name=f"offline-probe-{name}",
            daemon=True,
        )
        start_entered = True
        process.start()
    except BaseException as exc:
        for descriptor in (result_read_fd, result_write_fd, output_read_fd, output_write_fd):
            if descriptor >= 0:
                with suppress(OSError):
                    os.close(descriptor)
        cleanup_confirmed = not start_entered
        if process is not None:
            try:
                if process.pid is not None:
                    cleanup_confirmed = _cleanup_stage_process(process, stage_deadline)
                elif start_entered:
                    cleanup_confirmed = False
                if process.exitcode is not None or (process.pid is None and not start_entered):
                    process.close()
            except BaseException:
                cleanup_confirmed = False
        if isinstance(exc, KeyboardInterrupt):
            raise StageFailure(f"{name}_interrupted", cleanup_confirmed=cleanup_confirmed) from None
        raise StageFailure("stage_start_failure", cleanup_confirmed=cleanup_confirmed) from None
    for descriptor in (result_write_fd, output_write_fd):
        with suppress(OSError):
            os.close(descriptor)
    frame = bytearray()
    frame_size: int | None = None
    result_eof = False
    output_eof = False
    output_count = 0
    failure = "stage_timeout"
    envelope: dict[str, Any] | None = None
    try:
        while time.monotonic() < work_deadline and not (result_eof and output_eof):
            try:
                ready, _, _ = select.select(
                    [result_read_fd, output_read_fd],
                    [],
                    [],
                    min(0.05, max(0.0, work_deadline - time.monotonic())),
                )
            except (OSError, ValueError):
                failure = "stage_channel_failure"
                break
            if not ready:
                continue
            for descriptor in ready:
                while True:
                    try:
                        if descriptor == output_read_fd:
                            chunk = os.read(
                                output_read_fd,
                                min(65536, MAX_CHILD_OUTPUT + 1 - output_count),
                            )
                        else:
                            chunk = os.read(
                                result_read_fd,
                                min(65536, frame_limit + 5 - len(frame)),
                            )
                    except BlockingIOError:
                        break
                    except OSError:
                        failure = "stage_channel_failure"
                        break
                    if not chunk:
                        if descriptor == output_read_fd:
                            output_eof = True
                        else:
                            result_eof = True
                        break
                    if descriptor == output_read_fd:
                        output_count += len(chunk)
                        if output_count > MAX_CHILD_OUTPUT:
                            failure = "stage_output_overflow"
                            break
                        continue
                    frame.extend(chunk)
                    if len(frame) >= 4 and frame_size is None:
                        frame_size = struct.unpack(">I", frame[:4])[0]
                        if frame_size <= 0 or frame_size > frame_limit:
                            failure = "stage_frame_invalid"
                            break
                    if frame_size is not None and len(frame) > 4 + frame_size:
                        failure = "stage_frame_invalid"
                        break
                if failure != "stage_timeout":
                    break
            if failure != "stage_timeout":
                break
        if result_eof and output_eof:
            if failure == "stage_timeout":
                if frame_size is None or len(frame) != 4 + frame_size:
                    failure = "stage_frame_invalid"
                else:
                    try:
                        decoded = json.loads(bytes(frame[4:]).decode("utf-8", errors="strict"))
                    except (UnicodeError, json.JSONDecodeError):
                        failure = "stage_frame_invalid"
                    else:
                        if not isinstance(decoded, dict) or set(decoded) not in (
                            {"ok", "value"},
                            {"ok", "error"},
                        ):
                            failure = "stage_frame_invalid"
                        elif decoded.get("ok") is True and set(decoded) == {"ok", "value"}:
                            envelope = decoded
                        elif decoded.get("ok") is False and set(decoded) == {"ok", "error"}:
                            error = decoded["error"]
                            failure = (
                                error
                                if isinstance(error, str)
                                and re.fullmatch(r"[a-z0-9_]{1,80}", error)
                                else "stage_frame_invalid"
                            )
            process.join(max(0.0, stage_deadline - time.monotonic()))
            if process.exitcode != 0:
                failure = "stage_worker_failed"
    except KeyboardInterrupt:
        failure = f"{name}_interrupted"
    except BaseException:
        failure = "stage_observer_failed"
    finally:
        cleanup = _cleanup_stage_process(process, stage_deadline)
        for descriptor in (result_read_fd, output_read_fd):
            with suppress(OSError):
                os.close(descriptor)
        if process.exitcode is not None:
            process.close()
    if not cleanup:
        raise StageFailure("stage_cleanup_unconfirmed", cleanup_confirmed=False)
    if time.monotonic() >= cutoff:
        raise StageFailure("lifecycle_deadline", cleanup_confirmed=True)
    if time.monotonic() >= stage_deadline:
        raise StageFailure(f"{name}_timeout", cleanup_confirmed=True)
    if failure != "stage_timeout":
        raise StageFailure(failure, cleanup_confirmed=True)
    if envelope is None:
        raise StageFailure(f"{name}_timeout", cleanup_confirmed=True)
    value = _stage_unpack(envelope["value"])
    completed = time.monotonic()
    if completed >= cutoff:
        raise StageFailure("lifecycle_deadline", cleanup_confirmed=True)
    if completed >= stage_deadline:
        raise StageFailure(f"{name}_timeout", cleanup_confirmed=True)
    return value


def _cleanup_process_group(process: subprocess.Popen[bytes], deadline: float) -> bool:
    pgid = process.pid
    try:
        if process.poll() is None or _process_group_exists(pgid):
            _signal_group(pgid, signal.SIGTERM)
            grace = min(deadline, time.monotonic() + 0.1)
            while process.poll() is None and time.monotonic() < grace:
                time.sleep(min(0.01, max(0, grace - time.monotonic())))
            if process.poll() is None or _process_group_exists(pgid):
                _signal_group(pgid, signal.SIGKILL)
        remaining = max(0, deadline - time.monotonic())
        try:
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            _signal_group(pgid, signal.SIGKILL)
            return False
        while _process_group_exists(pgid) and time.monotonic() < deadline:
            _signal_group(pgid, signal.SIGKILL)
            time.sleep(min(0.01, max(0, deadline - time.monotonic())))
        return not _process_group_exists(pgid) and process.returncode is not None
    except BaseException:
        with suppress(BaseException):
            _signal_group(pgid, signal.SIGKILL)
        return False


def run_worker(
    payload: bytes,
    expected_sha256: str,
    page_title: str,
    *,
    timeout: float,
    command: list[str] | None = None,
    deadline: float | None = None,
) -> dict[str, Any]:
    """Run one child; include process-group cleanup in its absolute wall bound."""
    if not __debug__:
        return {"classification": "runner_rejected_optimized_python", "cleanup_confirmed": True}
    if os.name != "posix":
        return {"classification": "runner_platform_unsupported", "cleanup_confirmed": True}
    now = time.monotonic()
    shared_deadline = deadline if deadline is not None else now + timeout
    child_deadline = min(
        now + timeout,
        shared_deadline - FINAL_RESERVE_SECONDS if deadline is not None else shared_deadline,
    )
    if child_deadline <= now:
        return {"classification": "timeout", "cleanup_confirmed": True}
    cleanup_reserve = min(0.25, max(0.01, (child_deadline - now) / 5))
    work_cutoff = child_deadline - cleanup_reserve
    packet = json.dumps(
        {
            "payload": base64.b64encode(payload).decode("ascii"),
            "sha256": expected_sha256,
            "page_title": page_title,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    env = dict(os.environ)
    script_path = Path(os.path.abspath(__file__))
    env["PYTHONPATH"] = os.pathsep.join(
        (str(script_path.parent), str(REPO_ROOT / "src"), str(REPO_ROOT))
    )
    argv = command or [sys.executable, str(script_path), "--worker"]
    try:
        process = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            start_new_session=True,
        )
    except OSError:
        return {"classification": "worker_start_failure", "cleanup_confirmed": True}
    if process.stdin is None or process.stdout is None:
        cleanup = _cleanup_process_group(process, child_deadline)
        return {"classification": "worker_io_failure", "cleanup_confirmed": cleanup}
    selector: selectors.BaseSelector | None = None
    stdout_bytes = bytearray()
    stderr_bytes = bytearray()
    pending = memoryview(packet)
    overflow = False
    io_failure = False
    interrupted = False
    completed_by_cutoff = False
    descendant_seen = False
    result: dict[str, Any] | None = None
    cleanup = False
    try:
        selector = selectors.DefaultSelector()
        for stream, label in ((process.stdout, "stdout"),):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, label)
        os.set_blocking(process.stdin.fileno(), False)
        selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")
        while time.monotonic() < work_cutoff:
            if process.poll() is not None and not selector.get_map():
                completed_by_cutoff = True
                break
            if not selector.get_map() and process.poll() is None:
                time.sleep(min(0.01, max(0, work_cutoff - time.monotonic())))
                continue
            for key, _ in selector.select(min(0.05, max(0, work_cutoff - time.monotonic()))):
                if key.data == "stdin":
                    try:
                        sent = os.write(key.fd, pending[:65536])
                    except BlockingIOError:
                        continue
                    except (BrokenPipeError, OSError):
                        io_failure = True
                        pending = memoryview(b"")
                        selector.unregister(key.fileobj)
                        process.stdin.close()
                        break
                    pending = pending[sent:]
                    if not pending:
                        selector.unregister(key.fileobj)
                        process.stdin.close()
                    continue
                target = stdout_bytes if key.data == "stdout" else stderr_bytes
                combined = len(stdout_bytes) + len(stderr_bytes)
                try:
                    chunk = os.read(key.fd, min(4096, MAX_CHILD_OUTPUT + 1 - combined))
                except BlockingIOError:
                    continue
                except OSError:
                    io_failure = True
                    break
                if not chunk:
                    selector.unregister(key.fileobj)
                    if process.stdout is not None:
                        process.stdout.close()
                    continue
                target.extend(chunk)
                if len(stdout_bytes) + len(stderr_bytes) > MAX_CHILD_OUTPUT:
                    overflow = True
                    break
            if overflow or io_failure:
                break
        completed_by_cutoff = completed_by_cutoff or (
            process.poll() is not None and not selector.get_map() and time.monotonic() < work_cutoff
        )
        leader_exited_before_cutoff = process.poll() is not None and time.monotonic() < work_cutoff
        if process.poll() is not None:
            process.wait(timeout=0)
        descendant_seen = leader_exited_before_cutoff and _process_group_exists(process.pid)
        if descendant_seen:
            _signal_group(process.pid, signal.SIGTERM)
        cleanup = _cleanup_process_group(process, child_deadline)
        if overflow:
            result = {"classification": "output_overflow"}
        elif io_failure:
            result = {"classification": "worker_io_failure"}
        elif not completed_by_cutoff:
            result = {"classification": "timeout"}
        elif descendant_seen:
            result = {"classification": "worker_descendant_detected"}
        else:
            result = classify_worker_result(bytes(stdout_bytes), process.returncode or 0)
    except KeyboardInterrupt:
        interrupted = True
        cleanup = _cleanup_process_group(process, child_deadline)
        result = {"classification": "worker_interrupted"}
    except BaseException as exc:
        io_failure = True
        cleanup = _cleanup_process_group(process, child_deadline)
        result = {"classification": "worker_io_failure", "exception_type": type(exc).__name__}
    finally:
        if selector is not None:
            with suppress(BaseException):
                selector.close()
        for stream in (process.stdin, process.stdout):
            with suppress(BaseException):
                stream.close()
        if not cleanup:
            cleanup = _cleanup_process_group(process, child_deadline)
    if result is None:
        result = {"classification": "worker_interrupted" if interrupted else "worker_io_failure"}
    if not cleanup:
        result["classification"] = "cleanup_unconfirmed"
    elif time.monotonic() >= child_deadline:
        result["classification"] = "timeout"
    result["cleanup_confirmed"] = cleanup
    result["return_code"] = process.returncode
    return result


def _exception_result(exc: BaseException, *, domain: bool = False) -> dict[str, Any]:
    return {
        "classification": "expected_domain_rejection" if domain else "unexpected_exception",
        "exception_type": type(exc).__name__,
    }


def worker_main() -> None:
    """Child entry point; consumes checked packet, never prints document data."""
    if not __debug__:
        _worker_emit({"classification": "binding_failure"})
        return
    try:
        decoded = decode_worker_packet(sys.stdin.buffer.read())
        if decoded["classification"] != "verified":
            _worker_emit({"classification": "binding_failure"})
            return
        expected_origin = (REPO_ROOT / "src" / "logseq_matryca_parser").resolve()
        spec = importlib.util.find_spec("logseq_matryca_parser")
        if (
            spec is None
            or spec.origin is None
            or Path(spec.origin).resolve().parent != expected_origin
        ):
            _worker_emit({"classification": "binding_failure"})
            return
        try:
            from logseq_matryca_parser import LogseqParserError
            from logseq_matryca_parser.logos_parser import StackMachineParser
            from tests.parser_assurance.invariants import assert_tree_invariants
        except Exception as exc:
            _worker_emit(classify_worker_setup_error(exc))
            return
        result = classify_parse(
            decoded["payload"],
            decoded["page_title"],
            StackMachineParser,
            LogseqParserError,
            assert_tree_invariants,
        )
        _worker_emit(result)
    except BaseException:
        _worker_emit({"classification": "binding_failure"})


def _worker_emit(value: dict[str, Any]) -> None:
    data = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def create_output_directory_at(
    parent_fd: int,
    name: str,
    display_path: Path,
    *,
    deadline: float | None = None,
) -> OwnedOutput:
    if name in {"", ".", ".."} or "/" in name:
        raise ValueError("output must be a single path component")
    if deadline is not None:
        _deadline_check(deadline, cutoff=deadline - FINAL_RESERVE_SECONDS)
    os.mkdir(name, mode=0o700, dir_fd=parent_fd)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    directory_fd = os.open(name, flags, dir_fd=parent_fd)
    os.fchmod(directory_fd, 0o700)
    info = os.fstat(directory_fd)
    return OwnedOutput(
        display_path, os.dup(parent_fd), directory_fd, name, info.st_dev, info.st_ino
    )


def create_output_directory(path: Path) -> OwnedOutput:
    parent_fd = open_directory(path.parent)
    try:
        return create_output_directory_at(parent_fd, path.name, path)
    finally:
        os.close(parent_fd)


def write_private_at(
    output: OwnedOutput,
    name: str,
    data: bytes,
    *,
    deadline: float | None = None,
) -> None:
    if name != "summary.json" or len(data) > MAX_SUMMARY_BYTES:
        raise ValueError("private summary name or size rejected")
    if output.summary_fd is not None:
        raise FileExistsError("summary already created")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    descriptor = os.open(name, flags, 0o600, dir_fd=output.directory_fd)
    output.summary_fd = descriptor
    try:
        os.fchmod(descriptor, 0o600)
        view = memoryview(data)
        while view:
            if deadline is not None:
                _deadline_check(deadline)
            count = os.write(descriptor, view[:65536])
            if count <= 0:
                raise OSError("summary write made no progress")
            view = view[count:]
        os.fsync(descriptor)
        if deadline is not None:
            _deadline_check(deadline)
        info = os.stat(output.name, dir_fd=output.parent_fd, follow_symlinks=False)
        if not stat.S_ISDIR(info.st_mode) or (info.st_dev, info.st_ino) != (
            output.device,
            output.inode,
        ):
            raise ProbeStop("output_identity_changed")
        os.fsync(output.directory_fd)
    except BaseException:
        os.close(descriptor)
        output.summary_fd = None
        raise


def _file_binding(
    deadline: float | None = None, *, phase_cutoff: float | None = None
) -> dict[str, str]:
    repo_fd = open_directory(REPO_ROOT, deadline=deadline, phase_cutoff=phase_cutoff)
    try:
        package_fd = _open_directory_at(
            repo_fd,
            "src/logseq_matryca_parser",
            deadline=deadline,
            phase_cutoff=phase_cutoff,
        )
        try:
            package_paths = _inventory_at(package_fd, deadline, phase_cutoff=phase_cutoff)
        finally:
            os.close(package_fd)
        paths = {
            f"src/logseq_matryca_parser/{relative}"
            for relative in package_paths
            if relative.endswith(".py")
        }
        paths.update(
            {
                "tests/parser_assurance/invariants.py",
                ".superpowers/sdd/official-corpus-offline-probe/probe.py",
                ".superpowers/sdd/official-corpus-offline-probe/test_probe.py",
                "pyproject.toml",
                "uv.lock",
            }
        )
        result: dict[str, str] = {}
        for relative in sorted(paths):
            if deadline is not None:
                _phase_deadline_check(deadline, phase_cutoff)
            payload = read_regular_at(
                repo_fd,
                relative,
                max_bytes=64 * 1024 * 1024,
                deadline=deadline,
                phase_cutoff=phase_cutoff,
            )
            result[relative] = hashlib.sha256(payload).hexdigest()
        return result
    finally:
        os.close(repo_fd)


def _bindings_changed(before: dict[str, str], after: dict[str, str]) -> bool:
    return before != after


def aggregate_file_binding(bindings: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for path, file_hash in sorted(bindings.items()):
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _runtime_binding(
    deadline: float | None = None, *, phase_cutoff: float | None = None
) -> dict[str, Any]:
    if deadline is not None:
        _phase_deadline_check(deadline, phase_cutoff)
    executable = Path(sys.executable).resolve(strict=True)
    executable_parent_fd = open_directory(
        executable.parent, deadline=deadline, phase_cutoff=phase_cutoff
    )
    try:
        executable_bytes = read_regular_at(
            executable_parent_fd,
            executable.name,
            deadline=deadline,
            phase_cutoff=phase_cutoff,
        )
    finally:
        os.close(executable_parent_fd)
    versions: dict[str, str] = {}
    for distribution in importlib.metadata.distributions():
        if deadline is not None:
            _phase_deadline_check(deadline, phase_cutoff)
        versions[distribution.metadata.get("Name") or "unknown"] = distribution.version
    return {
        "python_path": str(executable),
        "python_sha256": hashlib.sha256(executable_bytes).hexdigest(),
        "python_version": sys.version,
        "optimization": sys.flags.optimize,
        "installed_distributions": dict(
            sorted(versions.items(), key=lambda item: item[0].casefold())
        ),
    }


def _git(*args: str, deadline: float | None = None) -> str:
    command_deadline = deadline if deadline is not None else time.monotonic() + MAX_STAGE_SECONDS
    _deadline_check(
        command_deadline,
        cutoff=command_deadline - FINAL_RESERVE_SECONDS
        if deadline is not None
        else command_deadline,
    )
    process: subprocess.Popen[bytes] | None = None
    selector: selectors.BaseSelector | None = None
    output = bytearray()
    try:
        process = subprocess.Popen(
            ["git", *args],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if process.stdout is None:
            raise ProbeStop("git_output_unavailable")
        os.set_blocking(process.stdout.fileno(), False)
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        eof = False
        while not eof:
            _deadline_check(
                command_deadline,
                cutoff=command_deadline - FINAL_RESERVE_SECONDS
                if deadline is not None
                else command_deadline,
            )
            ready = selector.select(min(0.05, max(0.0, command_deadline - time.monotonic())))
            if not ready:
                continue
            try:
                chunk = os.read(process.stdout.fileno(), MAX_CHILD_OUTPUT + 1 - len(output))
            except BlockingIOError:
                continue
            if not chunk:
                eof = True
                continue
            output.extend(chunk)
            if len(output) > MAX_CHILD_OUTPUT:
                raise ProbeStop("stage_output_overflow")
        remaining = max(0.0, command_deadline - time.monotonic())
        try:
            return_code = process.wait(timeout=remaining)
        except subprocess.TimeoutExpired as exc:
            raise ProbeStop("lifecycle_deadline") from exc
        if return_code != 0:
            raise ProbeStop("git_command_failed")
        return bytes(output).decode("utf-8", errors="strict").strip()
    except (OSError, UnicodeError) as exc:
        raise ProbeStop("git_command_failed") from exc
    finally:
        if selector is not None:
            selector.close()
        if process is not None:
            if process.poll() is None:
                with suppress(OSError):
                    process.kill()
                with suppress(subprocess.TimeoutExpired):
                    process.wait(timeout=max(0.0, command_deadline - time.monotonic()))
            if process.stdout is not None:
                process.stdout.close()


def _manifest_inputs(
    attempt_fd: int, deadline: float | None = None
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        data = read_regular_at(
            attempt_fd, "manifest.json", max_bytes=1024 * 1024, deadline=deadline
        )
    except (OSError, ValueError) as exc:
        raise ProbeStop("manifest_not_regular") from exc
    if hashlib.sha256(data).hexdigest() != EXPECTED_MANIFEST_SHA256:
        raise ProbeStop("manifest_hash_mismatch")
    manifest = json.loads(data.decode("utf-8", errors="strict"))
    if (
        manifest.get("source", {}).get("commit") != EXPECTED_SOURCE_COMMIT
        or manifest.get("source", {}).get("tree") != EXPECTED_SOURCE_TREE
    ):
        raise ProbeStop("manifest_source_mismatch")
    entries = [
        entry
        for entry in manifest.get("files", [])
        if str(entry.get("destination", "")).startswith("corpus/")
        and str(entry.get("destination", "")).endswith(".md")
    ]
    return manifest, entries


def _preflight(deadline: float) -> dict[str, str]:
    head = _git("rev-parse", "HEAD", deadline=deadline)
    if head != EXPECTED_HEAD:
        raise ProbeStop("repository_head_mismatch")
    return {
        "repository_head": head,
        "git_status": _git("status", "--short", "--branch", deadline=deadline),
    }


def _manifest_stage(deadline: float) -> dict[str, Any]:
    repo_fd = open_directory(REPO_ROOT, deadline=deadline)
    try:
        attempt_fd = _open_directory_at(
            repo_fd,
            ".superpowers/sdd/corpora/logseq-docs-08f855f24d66e4509b7ea808554c13b4649e6ee1/attempt-2",
            deadline=deadline,
        )
        try:
            _manifest, entries = _manifest_inputs(attempt_fd, deadline)
            if len(entries) != EXPECTED_COUNT:
                raise ProbeStop("manifest_binding_mismatch")
            return {"manifest_sha256": EXPECTED_MANIFEST_SHA256, "entries": entries}
        finally:
            os.close(attempt_fd)
    finally:
        os.close(repo_fd)


def _observer_stage(deadline: float) -> str:
    repo_fd = open_directory(REPO_ROOT, deadline=deadline)
    try:
        raw = _observer_bytes(repo_fd, deadline)
        return verify_observer(raw, expected_sha256=EXPECTED_OBSERVER_SHA256)
    finally:
        os.close(repo_fd)


def _create_output_identity(path: Path, *, deadline: float) -> dict[str, list[int]]:
    parent_fd = open_directory(path.parent, deadline=deadline)
    try:
        output = create_output_directory_at(parent_fd, path.name, path, deadline=deadline)
        try:
            parent = os.fstat(output.parent_fd)
            attempt = os.fstat(output.directory_fd)
            return {
                "parent": [parent.st_dev, parent.st_ino],
                "attempt": [attempt.st_dev, attempt.st_ino],
            }
        finally:
            output.close()
    finally:
        os.close(parent_fd)


def _validate_corpus_inventory(entries: list[dict[str, Any]], *, deadline: float) -> dict[str, int]:
    repo_fd = open_directory(REPO_ROOT, deadline=deadline)
    try:
        attempt_fd = _open_directory_at(
            repo_fd,
            ".superpowers/sdd/corpora/logseq-docs-08f855f24d66e4509b7ea808554c13b4649e6ee1/attempt-2",
            deadline=deadline,
        )
        try:
            corpus_fd = _open_directory_at(attempt_fd, "corpus", deadline=deadline)
            try:
                selected: set[str] = set()
                for entry in entries:
                    if deadline is not None:
                        _deadline_check(deadline, cutoff=deadline - FINAL_RESERVE_SECONDS)
                    destination = str(entry.get("destination", ""))
                    destination_path = validate_destination(destination)
                    source_path = PurePosixPath(str(entry.get("source_path", "")))
                    if (
                        source_path.is_absolute()
                        or source_path.suffix != ".md"
                        or any(part in {"", ".", ".."} for part in source_path.parts)
                        or source_path.parts != destination_path.parts[1:]
                        or destination in selected
                    ):
                        raise ProbeStop("manifest_selection_invalid")
                    selected.add(destination_path.relative_to("corpus").as_posix())
                if len(entries) != EXPECTED_COUNT or _inventory_at(corpus_fd, deadline) != selected:
                    raise ProbeStop("corpus_inventory_mismatch")
                return {"selected_count": len(selected), "inventory_count": len(selected)}
            finally:
                os.close(corpus_fd)
        finally:
            os.close(attempt_fd)
    finally:
        os.close(repo_fd)


def _read_verified_entry(entry: dict[str, Any], *, deadline: float) -> dict[str, Any]:
    source_path = str(entry.get("source_path", ""))
    destination = validate_destination(str(entry.get("destination", "")))
    parsed_source = PurePosixPath(source_path)
    if (
        parsed_source.is_absolute()
        or parsed_source.suffix != ".md"
        or any(part in {"", ".", ".."} for part in parsed_source.parts)
        or parsed_source.parts != destination.parts[1:]
    ):
        raise ProbeStop("manifest_selection_invalid")
    repo_fd = open_directory(REPO_ROOT, deadline=deadline)
    try:
        attempt_fd = _open_directory_at(
            repo_fd,
            ".superpowers/sdd/corpora/logseq-docs-08f855f24d66e4509b7ea808554c13b4649e6ee1/attempt-2",
            deadline=deadline,
        )
        try:
            corpus_fd = _open_directory_at(attempt_fd, "corpus", deadline=deadline)
            try:
                payload = read_regular_at(
                    corpus_fd,
                    destination.relative_to("corpus").as_posix(),
                    expected_size=int(entry["size"]),
                    deadline=deadline,
                )
            finally:
                os.close(corpus_fd)
        finally:
            os.close(attempt_fd)
    finally:
        os.close(repo_fd)
    payload_sha = hashlib.sha256(payload).hexdigest()
    if payload_sha != entry.get("sha256") or _git_blob(payload) != entry.get("git_blob"):
        raise ProbeStop("selected_input_binding_mismatch")
    try:
        payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ProbeStop("selected_input_invalid_utf8") from exc
    return {
        "source_path": source_path,
        "destination": str(entry["destination"]),
        "sha256": payload_sha,
        "payload": payload,
    }


def _observer_bytes(repo_fd: int, deadline: float | None = None) -> bytes:
    return read_regular_at(repo_fd, OBSERVER_RELATIVE_PATH, max_bytes=64 * 1024, deadline=deadline)


def verify_observer(raw: bytes, *, expected_sha256: str) -> str:
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ProbeStop("observer_sha256_mismatch")
    try:
        observer = json.loads(raw.decode("utf-8", errors="strict"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ProbeStop("observer_invalid") from exc
    if not isinstance(observer, dict):
        raise ProbeStop("observer_invalid")
    if (
        observer.get("artifacts", {}).get("manifest_sha256") != EXPECTED_MANIFEST_SHA256
        or observer.get("authorization_id") != "official-logseq-docs-text-copy-v2"
        or observer.get("destination", {}).get("path") != EXPECTED_OBSERVER_DESTINATION
        or observer.get("outcome") != "deadline_qualified"
        or observer.get("owned_children_reaped") is not True
        or observer.get("repository_head") != EXPECTED_HEAD
        or observer.get("run_id") != "logseq-docs-08f855f-attempt-2-2026-10-05"
        or observer.get("source", {}).get("commit") != EXPECTED_SOURCE_COMMIT
        or observer.get("source", {}).get("tree") != EXPECTED_SOURCE_TREE
        or observer.get("worker_complete") is not True
    ):
        raise ProbeStop("observer_binding_mismatch")
    return expected_sha256


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _attempt_identity(path: Path) -> dict[str, list[int]]:
    parent_fd = open_directory(path.parent)
    try:
        parent_info = os.fstat(parent_fd)
        attempt_fd = os.open(
            path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd
        )
        try:
            attempt_info = os.fstat(attempt_fd)
            os.fchmod(attempt_fd, 0o700)
            return {
                "parent": [parent_info.st_dev, parent_info.st_ino],
                "attempt": [attempt_info.st_dev, attempt_info.st_ino],
            }
        finally:
            os.close(attempt_fd)
    finally:
        os.close(parent_fd)


def _open_bound_attempt(
    path: Path,
    identity: dict[str, list[int]],
    *,
    deadline: float,
    phase_cutoff: float,
) -> tuple[int, int]:
    _phase_deadline_check(deadline, phase_cutoff)
    parent_fd = open_directory(path.parent, deadline=deadline, phase_cutoff=phase_cutoff)
    parent_info = os.fstat(parent_fd)
    if [parent_info.st_dev, parent_info.st_ino] != identity.get("parent"):
        os.close(parent_fd)
        raise ProbeStop("output_parent_identity_changed")
    try:
        attempt_fd = os.open(
            path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd
        )
    except BaseException:
        os.close(parent_fd)
        raise
    info = os.fstat(attempt_fd)
    if (
        [info.st_dev, info.st_ino] != identity.get("attempt")
        or not stat.S_ISDIR(info.st_mode)
        or stat.S_IMODE(info.st_mode) != 0o700
    ):
        os.close(attempt_fd)
        os.close(parent_fd)
        raise ProbeStop("output_attempt_identity_changed")
    _phase_deadline_check(deadline, phase_cutoff)
    return parent_fd, attempt_fd


def _write_provisional_file(
    path: Path, identity: dict[str, list[int]], data: bytes, *, deadline: float
) -> dict[str, Any]:
    if len(data) > MAX_SUMMARY_BYTES:
        raise ProbeStop("summary_size_limit")
    parent_fd, attempt_fd = _open_bound_attempt(
        path, identity, deadline=deadline, phase_cutoff=deadline
    )
    try:
        descriptor = os.open(
            "summary.json",
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=attempt_fd,
        )
        try:
            os.fchmod(descriptor, 0o600)
            pending = memoryview(data)
            while pending:
                _deadline_check(deadline)
                written = os.write(descriptor, pending[:65536])
                if written <= 0:
                    raise OSError("summary writer made no progress")
                pending = pending[written:]
            os.fsync(descriptor)
            os.fsync(attempt_fd)
        finally:
            os.close(descriptor)
        return {"summary_sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}
    finally:
        os.close(attempt_fd)
        os.close(parent_fd)


def _verify_provisional_file(
    path: Path,
    identity: dict[str, list[int]],
    expected_bytes: bytes,
    *,
    expected_summary_sha256: str,
    before_files: dict[str, str],
    after_files: dict[str, str],
    before_runtime: dict[str, Any],
    after_runtime: dict[str, Any],
    records: list[dict[str, Any]],
    selection_count: int,
    deadline: float,
) -> dict[str, Any]:
    _deadline_check(deadline)
    if before_files != after_files or before_runtime != after_runtime:
        raise ProbeStop("post_binding_mismatch")
    if len(records) != selection_count or any(
        row.get("classification") != "parsed_invariants_pass"
        or row.get("invariant_result") != "pass"
        or row.get("cleanup_confirmed") is not True
        for row in records
    ):
        raise ProbeStop("complete_selection_mismatch")
    parent_fd, attempt_fd = _open_bound_attempt(
        path, identity, deadline=deadline, phase_cutoff=deadline
    )
    try:
        descriptor = os.open("summary.json", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=attempt_fd)
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600:
                raise ProbeStop("summary_file_mode_mismatch")
            if info.st_size != len(expected_bytes) or info.st_size > MAX_SUMMARY_BYTES:
                raise ProbeStop("summary_size_mismatch")
            chunks: list[bytes] = []
            remaining = len(expected_bytes) + 1
            while remaining:
                _deadline_check(deadline)
                chunk = os.read(descriptor, min(65536, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            actual = b"".join(chunks)
            actual_sha256 = hashlib.sha256(actual).hexdigest()
            if (
                actual != expected_bytes
                or actual_sha256 != expected_summary_sha256
                or actual_sha256 != hashlib.sha256(expected_bytes).hexdigest()
            ):
                raise ProbeStop("summary_bytes_mismatch")
        finally:
            os.close(descriptor)
        _deadline_check(deadline)
        summary = json.loads(actual.decode("utf-8", errors="strict"))
        if (
            not isinstance(summary, dict)
            or summary.get("status") != "provisional"
            or summary.get("diagnostic_outcome") != "complete"
            or summary.get("completed_count") != selection_count
            or summary.get("selection_count") != selection_count
            or summary.get("source_file_sha256_before") != before_files
            or summary.get("source_file_sha256_after") != after_files
            or summary.get("runtime") != before_runtime
        ):
            raise ProbeStop("summary_content_mismatch")
        return {
            "summary_sha256": actual_sha256,
            "size": len(actual),
            "attempt_identity": identity["attempt"],
            "source_aggregate_sha256": aggregate_file_binding(after_files),
            "runtime_sha256": _canonical_sha256(after_runtime),
            "completed_count": len(records),
            "selection_count": selection_count,
        }
    finally:
        os.close(attempt_fd)
        os.close(parent_fd)


def _completion_witness(
    verification: dict[str, Any], *, started: float, deadline: float
) -> dict[str, Any]:
    completed = time.monotonic()
    if completed >= deadline:
        raise ProbeStop("lifecycle_deadline")
    witness = {
        "schema": 1,
        "outcome": "diagnostic_complete",
        "summary_sha256": verification["summary_sha256"],
        "source_aggregate_sha256": verification["source_aggregate_sha256"],
        "runtime_sha256": verification["runtime_sha256"],
        "completed_count": verification["completed_count"],
        "selection_count": verification["selection_count"],
        "started_monotonic": started,
        "completed_monotonic": completed,
        "deadline_monotonic": deadline,
    }
    if (
        len(json.dumps(witness, sort_keys=True, separators=(",", ":")).encode("utf-8")) + 1
        > MAX_CHILD_OUTPUT
    ):
        raise ProbeStop("completion_witness_too_large")
    return witness


def _finalize_summary(
    summary: dict[str, Any], *, deadline: float, started: float
) -> tuple[dict[str, Any], bytes, int]:
    value = dict(summary)
    requested_status = value.get("status")
    diagnostic_outcome = (
        "complete"
        if requested_status == "pass_diagnostic_only"
        else requested_status
        if requested_status in {"fail", "incomplete", "complete"}
        else "incomplete"
    )
    value["status"] = "provisional"
    value["diagnostic_outcome"] = diagnostic_outcome
    records = value.get("results", [])
    if not isinstance(records, list):
        records = []
    value["completed_count"] = int(value.get("completed_count", len(records)))
    value["recorded_result_count"] = len(records)
    if time.monotonic() >= deadline:
        value["diagnostic_outcome"], value["reason"] = "incomplete", "lifecycle_deadline"
    value["elapsed_seconds"] = max(0.0, time.monotonic() - started)
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
    if len(encoded) > MAX_SUMMARY_BYTES:
        keep = {
            key: value[key]
            for key in (
                "schema",
                "candidate",
                "repository_head",
                "git_status",
                "manifest_sha256",
                "observer_sha256",
                "source_commit",
                "source_tree",
                "selection_count",
                "completed_count",
                "started_monotonic",
                "elapsed_seconds",
                "runtime",
                "source_file_sha256_before",
                "source_file_sha256_after",
                "source_aggregate_sha256_before",
                "source_aggregate_sha256_after",
            )
            if key in value
        }
        value = {
            **keep,
            "status": "provisional",
            "diagnostic_outcome": "incomplete",
            "reason": "summary_size_limit",
            "recorded_result_count": 0,
            "results": [],
        }
        value["elapsed_seconds"] = max(0.0, time.monotonic() - started)
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
    if len(encoded) > MAX_SUMMARY_BYTES:
        value = {
            "schema": 1,
            "candidate": "candidate_unadmitted",
            "status": "provisional",
            "diagnostic_outcome": "incomplete",
            "reason": "summary_metadata_size_limit",
            "completed_count": int(summary.get("completed_count", len(records))),
            "recorded_result_count": 0,
            "results": [],
            "elapsed_seconds": max(0.0, time.monotonic() - started),
        }
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
    complete_allowed = (
        value.get("diagnostic_outcome") == "complete"
        and value.get("completed_count") == value.get("selection_count")
        and value.get("recorded_result_count") == value.get("completed_count")
        and time.monotonic() < deadline
    )
    if not complete_allowed and value.get("diagnostic_outcome") == "complete":
        value["diagnostic_outcome"], value["reason"] = (
            "incomplete",
            "lifecycle_deadline_or_count_mismatch",
        )
        value["elapsed_seconds"] = max(0.0, time.monotonic() - started)
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
    return value, encoded, 0 if complete_allowed and len(encoded) <= MAX_SUMMARY_BYTES else 1


def run_probe() -> tuple[int, dict[str, Any] | None]:
    started = time.monotonic()
    deadline = started + RUN_SECONDS
    if not __debug__ or sys.flags.optimize != 0:
        return 1, None
    output_path = REPO_ROOT / ".superpowers/sdd/official-corpus-offline-probe/attempt-1"
    records: list[dict[str, Any]] = []
    try:
        preflight = _bounded_stage("preflight", lambda: _preflight(deadline), deadline=deadline)
        before_files = _bounded_stage(
            "source_before", lambda: _file_binding(deadline), deadline=deadline
        )
        before_runtime = _bounded_stage(
            "runtime_before", lambda: _runtime_binding(deadline), deadline=deadline
        )
        manifest_result = _bounded_stage(
            "manifest", lambda: _manifest_stage(deadline), deadline=deadline
        )
        entries = manifest_result["entries"]
        manifest_sha = manifest_result["manifest_sha256"]
        observer_sha = _bounded_stage(
            "observer", lambda: _observer_stage(deadline), deadline=deadline
        )
        identity = _bounded_stage(
            "output_create",
            lambda: _create_output_identity(output_path, deadline=deadline),
            deadline=deadline,
        )
        inventory = _bounded_stage(
            "input_inventory",
            lambda: _validate_corpus_inventory(entries, deadline=deadline),
            deadline=deadline,
        )
        if inventory["selected_count"] != len(entries) or inventory["inventory_count"] != len(
            entries
        ):
            raise StageFailure("corpus_inventory_mismatch", cleanup_confirmed=True)

        status = "pass_diagnostic_only"
        reason = "single_traversal_complete"
        for entry in entries:
            if time.monotonic() >= deadline - FINAL_RESERVE_SECONDS:
                raise StageFailure("lifecycle_deadline", cleanup_confirmed=True)
            size = int(entry["size"])
            item = _bounded_stage(
                "input_read",
                lambda entry=entry: _read_verified_entry(entry, deadline=deadline),
                deadline=deadline,
                max_payload_bytes=size,
            )
            title = PurePosixPath(item["source_path"]).stem
            child = run_worker(
                item["payload"],
                item["sha256"],
                title,
                timeout=MAX_CHILD_SECONDS,
                deadline=deadline,
            )
            classification = str(child.get("classification", "invalid_child_result"))
            cleanup_confirmed = child.get("cleanup_confirmed") is True
            row = {
                "source_path": item["source_path"],
                "input_sha256": item["sha256"],
                "classification": classification,
                "root_count": child.get("root_count"),
                "node_count": child.get("node_count"),
                "invariant_result": child.get("invariant_result"),
                "exception_type": child.get("exception_type"),
                "cleanup_confirmed": cleanup_confirmed,
            }
            records.append(row)
            if not cleanup_confirmed:
                raise StageFailure("worker_cleanup_unconfirmed", cleanup_confirmed=False)
            if classification != "parsed_invariants_pass":
                status = (
                    "fail"
                    if classification
                    in {
                        "expected_domain_rejection",
                        "unexpected_exception",
                        "raw_content_mismatch",
                        "tree_invariants",
                    }
                    else "incomplete"
                )
                reason = classification
                break
        after_files = _bounded_stage(
            "source_after",
            lambda: _file_binding(deadline, phase_cutoff=deadline),
            deadline=deadline,
            reserve_final=False,
        )
        after_runtime = _bounded_stage(
            "runtime_after",
            lambda: _runtime_binding(deadline, phase_cutoff=deadline),
            deadline=deadline,
            reserve_final=False,
        )
        if before_files != after_files or before_runtime != after_runtime:
            status, reason = "incomplete", "post_binding_mismatch"
        summary = {
            "schema": 1,
            "candidate": "candidate_unadmitted",
            "status": status,
            "reason": reason,
            "repository_head": preflight["repository_head"],
            "git_status": preflight["git_status"],
            "manifest_sha256": manifest_sha,
            "observer_sha256": observer_sha,
            "source_commit": EXPECTED_SOURCE_COMMIT,
            "source_tree": EXPECTED_SOURCE_TREE,
            "selection_count": len(entries),
            "completed_count": len(records),
            "started_monotonic": started,
            "elapsed_seconds": time.monotonic() - started,
            "runtime": before_runtime,
            "source_file_sha256_before": before_files,
            "source_file_sha256_after": after_files,
            "source_aggregate_sha256_before": aggregate_file_binding(before_files),
            "source_aggregate_sha256_after": aggregate_file_binding(after_files),
            "results": records,
        }
        summary_value, summary_bytes, exit_code = _finalize_summary(
            summary, deadline=deadline, started=started
        )
        write_result = _bounded_stage(
            "summary_write",
            lambda: _write_provisional_file(
                output_path, identity, summary_bytes, deadline=deadline
            ),
            deadline=deadline,
            reserve_final=False,
        )
        summary_sha256 = hashlib.sha256(summary_bytes).hexdigest()
        if write_result != {"summary_sha256": summary_sha256, "size": len(summary_bytes)}:
            raise StageFailure("summary_write_result_mismatch", cleanup_confirmed=True)
        if exit_code != 0:
            return 1, None
        verification = _bounded_stage(
            "summary_verify",
            lambda: _verify_provisional_file(
                output_path,
                identity,
                summary_bytes,
                expected_summary_sha256=summary_sha256,
                before_files=before_files,
                after_files=after_files,
                before_runtime=before_runtime,
                after_runtime=after_runtime,
                records=records,
                selection_count=len(entries),
                deadline=deadline,
            ),
            deadline=deadline,
            reserve_final=False,
        )
        witness = _completion_witness(verification, started=started, deadline=deadline)
        return 0, witness
    except (StageFailure, ProbeStop):
        return 1, None
    except BaseException:
        return 1, None


def _publish_live_witness(witness: dict[str, Any]) -> None:
    deadline = witness.get("deadline_monotonic")
    if not isinstance(deadline, (int, float)) or isinstance(deadline, bool):
        raise ProbeStop("witness_deadline_invalid")
    try:
        encoded = (
            json.dumps(witness, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
                "utf-8"
            )
            + b"\n"
        )
        if len(encoded) > MAX_CHILD_OUTPUT:
            raise ProbeStop("completion_witness_too_large")
        descriptor = sys.stdout.fileno()
        info = os.fstat(descriptor)
        if not (
            stat.S_ISFIFO(info.st_mode) or (stat.S_ISCHR(info.st_mode) and os.isatty(descriptor))
        ):
            raise ProbeStop("witness_output_unsupported")
        was_blocking = os.get_blocking(descriptor)
        changed = False
        restore_failed = False
        try:
            if was_blocking:
                os.set_blocking(descriptor, False)
                changed = True
            offset = 0
            while offset < len(encoded):
                remaining = _deadline_check(deadline)
                try:
                    _, writable, exceptional = select.select(
                        [], [descriptor], [descriptor], min(0.05, remaining)
                    )
                except (OSError, ValueError) as exc:
                    raise ProbeStop("witness_output_unavailable") from exc
                if exceptional:
                    raise ProbeStop("witness_output_unavailable")
                if not writable:
                    continue
                try:
                    written = os.write(descriptor, encoded[offset:])
                except BlockingIOError:
                    continue
                if written <= 0:
                    raise ProbeStop("witness_output_incomplete")
                offset += written
                _deadline_check(deadline)
        finally:
            if changed:
                try:
                    os.set_blocking(descriptor, was_blocking)
                except OSError:
                    restore_failed = True
        if restore_failed:
            raise ProbeStop("witness_output_state_restore_failed")
        _deadline_check(deadline)
    except ProbeStop:
        raise
    except (AttributeError, OSError, TypeError, ValueError) as exc:
        raise ProbeStop("witness_output_unsupported") from exc


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--worker":
        worker_main()
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run", action="store_true", help="opt in to one bounded, offline diagnostic pass"
    )
    args = parser.parse_args()
    if not args.run:
        parser.error("explicit --run required; this probe is not executed by default")
    exit_code, witness = run_probe()
    if witness is None:
        return exit_code
    if exit_code != 0:
        return 1
    try:
        _publish_live_witness(witness)
    except ProbeStop:
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProbeStop as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from None
    except Exception as exc:
        print(type(exc).__name__, file=sys.stderr)
        raise SystemExit(2) from None
