"""Agent write helpers: weekly append-only logging and headless AST markdown splicing."""

from __future__ import annotations

import logging
import os
import re
import stat
import tempfile
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from difflib import unified_diff
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn, NotRequired, TypedDict

if TYPE_CHECKING:
    from logseq_matryca_parser.graph import LogseqGraph

from logseq_matryca_parser.diagnostics import Diagnostic, DiagnosticCode, DiagnosticSeverity
from logseq_matryca_parser.exceptions import VaultWriteError
from logseq_matryca_parser.logos_core import LogseqNode

logger = logging.getLogger(__name__)

DEFAULT_MAX_SOURCE_BYTES = 8 * 1024 * 1024
DEFAULT_MAX_CONTENT_BYTES = 1024 * 1024
DEFAULT_MAX_TARGET_DEPTH = 128


@dataclass(frozen=True)
class WriteProposal:
    """Immutable preview/result for one vault-contained markdown splice."""

    path: Path
    unified_diff: str
    applied: bool


def _raise_writer_error(
    code: DiagnosticCode,
    message: str,
    *,
    graph: LogseqGraph,
    source_path: Path | None,
    context: dict[str, str],
) -> NoReturn:
    relative_path: str | None = None
    if source_path is not None:
        with suppress(OSError, RuntimeError, ValueError):
            relative_path = source_path.resolve().relative_to(graph.graph_path.resolve()).as_posix()
    raise VaultWriteError(
        Diagnostic(
            code=code,
            severity=DiagnosticSeverity.ERROR,
            source_path=relative_path,
            message=message,
            context=context,
        )
    )


def _validate_write_target(
    graph: LogseqGraph,
    source_path: Path,
    *,
    target_uuid: str,
) -> tuple[Path, os.stat_result]:
    try:
        root = graph.graph_path.resolve(strict=True)
        resolved = source_path.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        _raise_writer_error(
            DiagnosticCode.WRITER_VAULT_ESCAPE,
            "Writer target is outside the selected vault",
            graph=graph,
            source_path=source_path,
            context={"operation": "append_child", "target_uuid": target_uuid},
        )
    if not graph.is_tracked_markdown_path(resolved):
        _raise_writer_error(
            DiagnosticCode.WRITER_VAULT_ESCAPE,
            "Writer target is not a tracked vault Markdown file",
            graph=graph,
            source_path=resolved,
            context={"operation": "append_child", "target_uuid": target_uuid},
        )
    target_stat = os.stat(resolved, follow_symlinks=False)
    if not stat.S_ISREG(target_stat.st_mode):
        _raise_writer_error(
            DiagnosticCode.WRITER_VAULT_ESCAPE,
            "Writer target is not a regular file",
            graph=graph,
            source_path=resolved,
            context={"operation": "append_child", "target_uuid": target_uuid},
        )
    return resolved, target_stat


def _identity(target_stat: os.stat_result) -> tuple[int, int, int, int]:
    return (
        target_stat.st_dev,
        target_stat.st_ino,
        target_stat.st_size,
        target_stat.st_mtime_ns,
    )


def _read_validated_target(
    graph: LogseqGraph,
    source_path: Path,
    expected_stat: os.stat_result,
    *,
    target_uuid: str,
) -> tuple[str, os.stat_result]:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(source_path, flags)
    except OSError:
        _raise_writer_error(
            DiagnosticCode.WRITER_TARGET_CHANGED,
            "Writer target changed before it could be read",
            graph=graph,
            source_path=source_path,
            context={"operation": "append_child", "target_uuid": target_uuid},
        )
    with os.fdopen(fd, encoding="utf-8-sig") as handle:
        opened_stat = os.fstat(handle.fileno())
        if _identity(opened_stat) != _identity(expected_stat):
            _raise_writer_error(
                DiagnosticCode.WRITER_TARGET_CHANGED,
                "Writer target changed before it could be read",
                graph=graph,
                source_path=source_path,
                context={"operation": "append_child", "target_uuid": target_uuid},
            )
        return handle.read(), opened_stat


class AgentWriteResult(TypedDict):
    """Structured result from :func:`logseq_agent_write`."""

    status: str
    path: NotRequired[str]
    entry: NotRequired[str]
    message: NotRequired[str]

_DEFAULT_JOURNAL_FORMAT = "%Y-%m-%d"
_JOURNAL_PAGE_TITLE_FORMAT_RE = re.compile(
    r':journal/page-title-format\s+"([^"]*)"',
)

_ENGLISH_MONTH_ABBR: tuple[str, ...] = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)
_ENGLISH_MONTH_FULL: tuple[str, ...] = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


class LogseqConfigReader:
    """Load ``config.edn`` and translate Clojure/Java-style date tokens to Python ``strftime``."""

    # Longest tokens first to avoid partial replacements (e.g. ``yyyy`` before ``yy``).
    TOKEN_MAP: dict[str, str] = {
        "yyyy": "%Y",
        "yy": "%y",
        "MMMM": "%B",
        "MMM": "%b",
        "MM": "%m",
        "dd": "%d",
        "HH": "%H",
        "mm": "%M",
        "ss": "%S",
        "do": "{day_ordinal}",
    }

    def __init__(self, config_path: str) -> None:
        self.config_path = config_path

    def load_journal_format(self) -> str:
        """Return ``:journal/page-title-format`` from ``config.edn``."""
        try:
            with open(self.config_path, encoding="utf-8") as f:
                content = f.read()
        except OSError as exc:
            logger.warning("Could not read Logseq config at %s: %s", self.config_path, exc)
            return _DEFAULT_JOURNAL_FORMAT

        match = _JOURNAL_PAGE_TITLE_FORMAT_RE.search(content)
        if match:
            return match.group(1)
        return _DEFAULT_JOURNAL_FORMAT

    @staticmethod
    def get_day_ordinal(day: int) -> str:
        """Return English ordinal suffix (``st``, ``nd``, ``rd``, ``th``) for ``day``."""
        if 11 <= day <= 13:
            return "th"
        suffixes = {1: "st", 2: "nd", 3: "rd"}
        return suffixes.get(day % 10, "th")

    def translate_to_python(self, clojure_format: str) -> str:
        """Map Logseq/Java-style pattern letters to a Python ``strftime``-compatible string."""
        py_format = clojure_format
        for clojure_token, python_token in sorted(
            self.TOKEN_MAP.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        ):
            py_format = py_format.replace(clojure_token, python_token)
        return py_format

    def format_timestamp(self, dt: datetime) -> str:
        """Format ``dt`` using the journal title format from config (including ordinal days)."""
        clojure_format = self.load_journal_format()
        py_format = self.translate_to_python(clojure_format)
        # Force English month tokens so strftime does not follow the process locale (Logseq links).
        if "%B" in py_format:
            py_format = py_format.replace("%B", _ENGLISH_MONTH_FULL[dt.month - 1])
        if "%b" in py_format:
            py_format = py_format.replace("%b", _ENGLISH_MONTH_ABBR[dt.month - 1])
        base_date = dt.strftime(py_format)
        if "{day_ordinal}" in base_date:
            suffix = self.get_day_ordinal(dt.day)
            base_date = re.sub(r"\{day_ordinal\}", f"{dt.day}{suffix}", base_date)
        return base_date


def logseq_agent_write(
    content: str,
    config_path: str,
    pages_dir: str,
    context_tags: list[str] | None = None,
) -> AgentWriteResult:
    """Append a single Logseq-style block to the weekly agent page (append-only, sandbox-friendly)."""
    now = datetime.now()
    reader = LogseqConfigReader(config_path)
    title = reader.format_timestamp(now)
    timestamp_tag = f"[[{title}]]"
    week_calendar = now.isocalendar()
    week_id = f"{week_calendar.year}-W{week_calendar.week:02d}"
    filename = f"{week_id}-agent.md"
    file_path = os.path.join(pages_dir, filename)

    tag_links = "".join(f" [[{tag}]]" for tag in (context_tags or []))
    block_lines = [f"- {timestamp_tag}{tag_links}"]
    if content.strip():
        block_lines.append(content.rstrip("\n"))
    block_text = "\n".join(block_lines) + "\n"

    try:
        os.makedirs(pages_dir, exist_ok=True)
        with open(file_path, mode="a", encoding="utf-8") as out:
            out.write(block_text)
    except OSError as exc:
        logger.exception("logseq_agent_write failed for path %s", file_path)
        return {"status": "error", "message": str(exc)}
    return {"status": "success", "path": file_path}


def _insertion_line_after_node(node: LogseqNode) -> int:
    """Return the 1-based line after ``node``'s contiguous properties and subtree."""
    return _deepest_line_end(node)


def _deepest_line_end(node: LogseqNode) -> int:
    """Return the 1-based ``line_end`` of the deepest last descendant (or ``node`` itself)."""
    cursor = node
    while cursor.children:
        cursor = cursor.children[-1]
    if cursor.line_end is None:
        msg = f"Node uuid={node.uuid} has no line_end for markdown splice"
        raise ValueError(msg)
    return cursor.line_end


def append_child_to_node(
    graph: LogseqGraph,
    target_uuid: str,
    content: str,
    *,
    dry_run: bool = False,
    max_source_bytes: int = DEFAULT_MAX_SOURCE_BYTES,
    max_content_bytes: int = DEFAULT_MAX_CONTENT_BYTES,
    max_target_depth: int = DEFAULT_MAX_TARGET_DEPTH,
) -> WriteProposal:
    """Build or apply one serialized, fail-closed child splice."""
    with graph._mutation_scope():
        return _append_child_to_node_locked(
            graph,
            target_uuid,
            content,
            dry_run=dry_run,
            max_source_bytes=max_source_bytes,
            max_content_bytes=max_content_bytes,
            max_target_depth=max_target_depth,
        )


def _append_child_to_node_locked(
    graph: LogseqGraph,
    target_uuid: str,
    content: str,
    *,
    dry_run: bool = False,
    max_source_bytes: int = DEFAULT_MAX_SOURCE_BYTES,
    max_content_bytes: int = DEFAULT_MAX_CONTENT_BYTES,
    max_target_depth: int = DEFAULT_MAX_TARGET_DEPTH,
) -> WriteProposal:
    """Build or apply a fail-closed child splice while graph coordination is held."""
    target_node = graph.get_node_by_uuid(target_uuid)
    if target_node is None:
        msg = f"No node registered for uuid={target_uuid}"
        raise ValueError(msg)
    if not target_node.source_path:
        msg = f"Node uuid={target_uuid} has no source_path"
        raise ValueError(msg)

    source_path, initial_stat = _validate_write_target(
        graph,
        Path(target_node.source_path),
        target_uuid=target_uuid,
    )
    if min(max_source_bytes, max_content_bytes, max_target_depth) < 1:
        raise ValueError("writer limits must be positive")
    if initial_stat.st_size > max_source_bytes:
        _raise_writer_error(
            DiagnosticCode.WRITER_INPUT_LIMIT_EXCEEDED,
            "Writer source exceeds the configured byte limit",
            graph=graph,
            source_path=source_path,
            context={"limit": str(max_source_bytes), "target_uuid": target_uuid},
        )
    if len(content.encode("utf-8")) > max_content_bytes:
        _raise_writer_error(
            DiagnosticCode.WRITER_INPUT_LIMIT_EXCEEDED,
            "Writer content exceeds the configured byte limit",
            graph=graph,
            source_path=source_path,
            context={"limit": str(max_content_bytes), "target_uuid": target_uuid},
        )
    insert_after_line = _insertion_line_after_node(target_node)
    child_level = target_node.indent_level + 1
    if child_level > max_target_depth:
        _raise_writer_error(
            DiagnosticCode.WRITER_INPUT_LIMIT_EXCEEDED,
            "Writer target exceeds the configured outline depth",
            graph=graph,
            source_path=source_path,
            context={"limit": str(max_target_depth), "target_uuid": target_uuid},
        )
    tab_size = graph.tab_size_for_node(target_node)
    indent = " " * (child_level * tab_size)
    new_line = f"{indent}- {content.rstrip()}"

    raw_text, initial_stat = _read_validated_target(
        graph,
        source_path,
        initial_stat,
        target_uuid=target_uuid,
    )
    if raw_text and not raw_text.endswith(("\n", "\r\n")):
        raw_text += "\n"
    lines = raw_text.splitlines(keepends=True)
    insert_index = insert_after_line
    if insert_index < 0 or insert_index > len(lines):
        msg = (
            f"Insertion index {insert_index} out of range for {source_path} "
            f"(lines={len(lines)}, target line_end={insert_after_line})"
        )
        raise ValueError(msg)

    lines.insert(insert_index, f"{new_line}\n")
    updated = "".join(lines)
    relative_path = source_path.relative_to(graph.graph_path.resolve()).as_posix()
    patch = "".join(
        unified_diff(
            raw_text.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=f"a/{relative_path}",
            tofile=f"b/{relative_path}",
        )
    )
    proposal = WriteProposal(path=source_path, unified_diff=patch, applied=not dry_run)
    if dry_run:
        return proposal
    logger.debug(
        "append_child_to_node target=%s path=%s insert_index=%s indent_level=%s",
        target_uuid,
        source_path,
        insert_index,
        child_level,
    )

    fd, temp_path = tempfile.mkstemp(
        dir=source_path.parent,
        prefix=f".{source_path.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(updated)
            handle.flush()
            os.fsync(handle.fileno())
            mode = stat.S_IMODE(initial_stat.st_mode)
            if hasattr(os, "fchmod"):
                os.fchmod(handle.fileno(), mode)
            else:
                os.chmod(temp_path, mode)
            if hasattr(os, "fchown"):
                os.fchown(handle.fileno(), initial_stat.st_uid, initial_stat.st_gid)
        current_path, current_stat = _validate_write_target(
            graph,
            source_path,
            target_uuid=target_uuid,
        )
        if current_path != source_path or _identity(current_stat) != _identity(initial_stat):
            _raise_writer_error(
                DiagnosticCode.WRITER_TARGET_CHANGED,
                "Writer target changed after it was read",
                graph=graph,
                source_path=current_path,
                context={"operation": "append_child", "target_uuid": target_uuid},
            )
        os.replace(temp_path, source_path)
    except (OSError, VaultWriteError):
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise

    graph.invalidate_and_reload_page(source_path)
    return proposal


def _demo() -> None:
    """Print a small table for manual checks (``python -m logseq_matryca_parser.agent_writer``)."""

    class _MockConfigReader(LogseqConfigReader):
        def load_journal_format(self) -> str:
            return "MMM do, yyyy"

    reader = _MockConfigReader("/path/to/config.edn")
    test_dates = [
        datetime(2026, 5, 1),
        datetime(2026, 5, 2),
        datetime(2026, 5, 3),
        datetime(2026, 5, 11),
        datetime(2026, 5, 22),
    ]
    print(f"{'Original Date':<20} | {'Logseq Format':<15} | {'Final Output'}")
    print("-" * 60)
    for dt in test_dates:
        fmt = reader.load_journal_format()
        output = reader.format_timestamp(dt)
        print(f"{dt.strftime('%Y-%m-%d'):<20} | {fmt:<15} | {output}")


if __name__ == "__main__":
    _demo()
