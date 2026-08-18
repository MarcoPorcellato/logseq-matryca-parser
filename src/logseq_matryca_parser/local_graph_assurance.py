"""Bounded, privacy-safe local graph assurance for the KINETIC CLI.

The worker parses only regular Markdown files below ``pages/`` and ``journals/``.
It denies ordinary socket entry points and returns aggregate JSON only: never
paths, page titles, UUIDs, Markdown, snippets, exception text, or host names.
"""

from __future__ import annotations

import json
import multiprocessing
import os
import platform
import queue
import socket
import stat
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from logseq_matryca_parser.logos_core import LogseqNode
from logseq_matryca_parser.logos_parser import StackMachineParser

REPORT_SCHEMA_VERSION = 1

_LIMIT_KEYS = frozenset({"max_files", "max_total_bytes", "max_file_bytes", "timeout_seconds"})
_OBSERVED_KEYS = frozenset(
    {
        "markdown_files",
        "total_bytes",
        "parsed_pages",
        "parsed_nodes",
        "root_nodes",
        "block_references",
    }
)
_RUNTIME_KEYS = frozenset({"python", "platform"})
_FINDING_CODES = frozenset(
    {
        "graph.duplicate_source_identity",
        "graph.duplicate_synthetic_identity",
        "graph.page_title_collision",
        "graph.structure_invariant_violation",
        "graph.unresolved_block_reference",
        "parse.invalid_utf8",
        "parse.unclassified_failure",
        "runner.invalid_report",
        "runner.no_report",
        "runner.timeout",
        "runner.unexpected_failure",
        "vault.directory_read_error",
        "vault.entry_stat_error",
        "vault.file_changed_or_unreadable",
        "vault.invalid_root",
        "vault.max_file_bytes_exceeded",
        "vault.max_files_exceeded",
        "vault.max_total_bytes_exceeded",
        "vault.root_directory_rejected",
        "vault.symlink_rejected",
    }
)


@dataclass(frozen=True)
class AssuranceLimits:
    """Explicit bounds for one assurance run."""

    max_files: int = 10_000
    max_total_bytes: int = 128 * 1024 * 1024
    max_file_bytes: int = 8 * 1024 * 1024
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if min(self.max_files, self.max_total_bytes, self.max_file_bytes) < 1:
            raise ValueError("file and byte limits must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")


def _report(limits: AssuranceLimits, status: str = "passed") -> dict[str, object]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "status": status,
        "limits": asdict(limits),
        "observed": {
            "markdown_files": 0,
            "total_bytes": 0,
            "parsed_pages": 0,
            "parsed_nodes": 0,
            "root_nodes": 0,
            "block_references": 0,
        },
        "findings": [],
        "runtime": {
            "python": f"{sys.version_info.major}.{sys.version_info.minor}",
            "platform": platform.system().lower(),
        },
    }


def _finding(report: dict[str, object], code: str, count: int = 1) -> None:
    findings = report["findings"]
    assert isinstance(findings, list)
    for finding in findings:
        if isinstance(finding, dict) and finding.get("code") == code:
            finding["count"] = int(finding["count"]) + count
            return
    findings.append({"code": code, "count": count})


def _failed(limits: AssuranceLimits, status: str, code: str) -> dict[str, object]:
    report = _report(limits, status)
    _finding(report, code)
    return report


def _walk_markdown(root: Path, limits: AssuranceLimits, report: dict[str, object]) -> list[Path]:
    files: list[Path] = []
    total_bytes = 0

    def visit(directory: Path) -> bool:
        nonlocal total_bytes
        try:
            entries = sorted(directory.iterdir(), key=lambda item: item.name)
        except OSError:
            report.update(_failed(limits, "error", "vault.directory_read_error"))
            return False
        for entry in entries:
            try:
                entry_stat = entry.lstat()
            except OSError:
                report.update(_failed(limits, "error", "vault.entry_stat_error"))
                return False
            if stat.S_ISLNK(entry_stat.st_mode):
                report.update(_failed(limits, "findings", "vault.symlink_rejected"))
                return False
            if stat.S_ISDIR(entry_stat.st_mode):
                if entry.name in {".git", ".recycle", "logseq"}:
                    continue
                if not visit(entry):
                    return False
                continue
            if not stat.S_ISREG(entry_stat.st_mode) or entry.suffix.lower() != ".md":
                continue
            if len(files) >= limits.max_files:
                report.update(_failed(limits, "limit_exceeded", "vault.max_files_exceeded"))
                return False
            if entry_stat.st_size > limits.max_file_bytes:
                report.update(_failed(limits, "limit_exceeded", "vault.max_file_bytes_exceeded"))
                return False
            total_bytes += entry_stat.st_size
            if total_bytes > limits.max_total_bytes:
                report.update(_failed(limits, "limit_exceeded", "vault.max_total_bytes_exceeded"))
                return False
            files.append(entry)
        return True

    for name in ("pages", "journals"):
        folder = root / name
        if not folder.exists():
            continue
        if folder.is_symlink() or not folder.is_dir():
            report.update(_failed(limits, "findings", "vault.root_directory_rejected"))
            return []
        if not visit(folder):
            return []
    observed = report["observed"]
    assert isinstance(observed, dict)
    observed["markdown_files"] = len(files)
    observed["total_bytes"] = total_bytes
    return files


def _read_regular_file(root: Path, path: Path, max_bytes: int) -> bytes | None:
    try:
        path_stat = path.lstat()
        if stat.S_ISLNK(path_stat.st_mode) or not stat.S_ISREG(path_stat.st_mode):
            return None
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
        before = resolved.stat()
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(resolved, flags)
    except (OSError, RuntimeError, ValueError):
        return None
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (
            before.st_dev,
            before.st_ino,
        ):
            return None
        chunks: list[bytes] = []
        remaining = max_bytes + 1
        while remaining:
            chunk = os.read(descriptor, min(64 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        after = os.fstat(descriptor)
        if (
            len(data) != before.st_size
            or before.st_size > max_bytes
            or (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino)
        ):
            return None
        return data
    finally:
        os.close(descriptor)


def _walk_nodes(
    nodes: list[LogseqNode],
) -> Iterator[tuple[LogseqNode, str | None, str | None, tuple[str, ...]]]:
    def visit(
        siblings: list[LogseqNode], parent: str | None, path: tuple[str, ...]
    ) -> Iterator[tuple[LogseqNode, str | None, str | None, tuple[str, ...]]]:
        left: str | None = None
        for node in siblings:
            expected_path = (*path, node.uuid)
            yield node, parent, left, expected_path
            yield from visit(node.children, node.uuid, expected_path)
            left = node.uuid

    yield from visit(nodes, None, ())


def _assure(root_text: str, limits: AssuranceLimits) -> dict[str, object]:
    root = Path(root_text)
    report = _report(limits)
    try:
        root = root.resolve(strict=True)
    except (OSError, RuntimeError):
        return _failed(limits, "error", "vault.invalid_root")
    if not root.is_dir():
        return _failed(limits, "error", "vault.invalid_root")
    paths = _walk_markdown(root, limits, report)
    if report["status"] != "passed":
        return report

    seen_titles: set[str] = set()
    seen_source_ids: set[str] = set()
    all_ids: set[str] = set()
    references: list[str] = []
    bytes_read = 0
    for index, path in enumerate(paths):
        raw = _read_regular_file(root, path, limits.max_file_bytes)
        if raw is None:
            return _failed(limits, "error", "vault.file_changed_or_unreadable")
        bytes_read += len(raw)
        if bytes_read > limits.max_total_bytes:
            return _failed(limits, "limit_exceeded", "vault.max_total_bytes_exceeded")
        try:
            page = StackMachineParser().parse(raw.decode("utf-8-sig"), page_title=f"m5-{index}")
        except UnicodeDecodeError:
            report["status"] = "findings"
            _finding(report, "parse.invalid_utf8")
            continue
        except Exception:
            report["status"] = "findings"
            _finding(report, "parse.unclassified_failure")
            continue
        observed = report["observed"]
        assert isinstance(observed, dict)
        observed["parsed_pages"] = int(observed["parsed_pages"]) + 1
        observed["root_nodes"] = int(observed["root_nodes"]) + len(page.root_nodes)
        if page.title in seen_titles:
            report["status"] = "findings"
            _finding(report, "graph.page_title_collision")
        seen_titles.add(page.title)
        for node, parent, left, expected_path in _walk_nodes(page.root_nodes):
            observed["parsed_nodes"] = int(observed["parsed_nodes"]) + 1
            if (
                node.parent_id != parent
                or node.left_id != left
                or tuple(node.path) != expected_path
            ):
                report["status"] = "findings"
                _finding(report, "graph.structure_invariant_violation")
            if node.uuid in all_ids:
                report["status"] = "findings"
                _finding(report, "graph.duplicate_synthetic_identity")
            all_ids.add(node.uuid)
            source_ids = {
                value
                for value in (node.source_uuid, node.properties.get("id"))
                if isinstance(value, str) and value
            }
            for source_id in source_ids:
                if source_id in seen_source_ids:
                    report["status"] = "findings"
                    _finding(report, "graph.duplicate_source_identity")
                seen_source_ids.add(source_id)
                all_ids.add(source_id)
            references.extend(node.block_refs)
    observed = report["observed"]
    assert isinstance(observed, dict)
    observed["block_references"] = len(references)
    missing = sum(reference not in all_ids for reference in references)
    if missing:
        report["status"] = "findings"
        _finding(report, "graph.unresolved_block_reference", missing)
    return report


@contextmanager
def _network_denied() -> Iterator[None]:
    def denied(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("network disabled")

    originals = socket.socket, socket.create_connection, socket.getaddrinfo
    socket.socket = denied  # type: ignore[assignment, misc]
    socket.create_connection = denied  # type: ignore[assignment, misc]
    socket.getaddrinfo = denied  # type: ignore[assignment, misc]
    try:
        yield
    finally:
        socket.socket = originals[0]  # type: ignore[assignment, misc]
        socket.create_connection = originals[1]  # type: ignore[assignment, misc]
        socket.getaddrinfo = originals[2]  # type: ignore[assignment, misc]


def _worker(root: str, limits: AssuranceLimits, result_queue: Any) -> None:
    try:
        with _network_denied():
            result_queue.put(_assure(root, limits))
    except BaseException:
        result_queue.put(_failed(limits, "error", "runner.unexpected_failure"))


def _safe_report(value: object) -> bool:
    if not isinstance(value, dict) or set(value) != {
        "schema_version",
        "status",
        "limits",
        "observed",
        "findings",
        "runtime",
    }:
        return False
    if value.get("schema_version") != REPORT_SCHEMA_VERSION or value.get("status") not in {
        "passed",
        "findings",
        "limit_exceeded",
        "error",
        "timeout",
    }:
        return False
    limits = value.get("limits")
    if not isinstance(limits, dict) or set(limits) != _LIMIT_KEYS:
        return False
    for key in ("max_files", "max_total_bytes", "max_file_bytes"):
        if not isinstance(limits[key], int) or isinstance(limits[key], bool) or limits[key] < 1:
            return False
    timeout = limits["timeout_seconds"]
    if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or timeout <= 0:
        return False

    observed = value.get("observed")
    if not isinstance(observed, dict) or set(observed) != _OBSERVED_KEYS:
        return False
    if any(
        not isinstance(count, int) or isinstance(count, bool) or count < 0
        for count in observed.values()
    ):
        return False

    runtime = value.get("runtime")
    if (
        not isinstance(runtime, dict)
        or set(runtime) != _RUNTIME_KEYS
        or not all(isinstance(part, str) for part in runtime.values())
    ):
        return False

    findings = value.get("findings")
    if not isinstance(findings, list):
        return False
    return all(
        isinstance(item, dict)
        and set(item) == {"code", "count"}
        and isinstance(item["code"], str)
        and item["code"] in _FINDING_CODES
        and isinstance(item["count"], int)
        and not isinstance(item["count"], bool)
        and item["count"] > 0
        for item in findings
    ) and _json_safe(value)


def _json_safe(value: object) -> bool:
    try:
        json.dumps(value, sort_keys=True)
    except (TypeError, ValueError):
        return False
    return True


def run_local_graph_assurance(
    graph_path: Path, limits: AssuranceLimits | None = None
) -> dict[str, object]:
    """Run assurance in a fresh local worker and return the safe report only."""
    selected = limits or AssuranceLimits()
    context = multiprocessing.get_context("spawn")
    result_queue: Any = context.Queue(maxsize=1)
    process = context.Process(
        target=_worker, args=(str(graph_path.expanduser().resolve()), selected, result_queue)
    )
    process.start()
    process.join(selected.timeout_seconds)
    if process.is_alive():
        process.terminate()
        process.join()
        return _failed(selected, "timeout", "runner.timeout")
    try:
        result = result_queue.get(timeout=0.5)
    except queue.Empty:
        result = _failed(selected, "error", "runner.no_report")
    finally:
        result_queue.close()
        result_queue.join_thread()
    return result if _safe_report(result) else _failed(selected, "error", "runner.invalid_report")


def run_local_graph_assurance_self_test(limits: AssuranceLimits | None = None) -> dict[str, object]:
    """Exercise the same child-worker path against a temporary synthetic vault."""
    with tempfile.TemporaryDirectory(prefix="matryca-assurance-") as temporary:
        root = Path(temporary)
        (root / "pages").mkdir()
        (root / "journals").mkdir()
        (root / "pages" / "Alpha.md").write_text(
            "- Parent\n  id:: 11111111-1111-1111-1111-111111111111\n", encoding="utf-8"
        )
        (root / "journals" / "2026_08_18.md").write_text(
            "- ((11111111-1111-1111-1111-111111111111))\n", encoding="utf-8"
        )
        return run_local_graph_assurance(root, limits)
