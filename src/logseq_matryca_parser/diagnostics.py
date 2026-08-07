"""Stable, serializable diagnostics for parser and graph integrations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path, PurePosixPath, PureWindowsPath
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from logseq_matryca_parser.graph import LogseqGraph


class DiagnosticSeverity(StrEnum):
    """Stable severity values used by diagnostics and machine-readable output."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class DiagnosticCode(StrEnum):
    """Stable diagnostic codes currently emitted by the public API."""

    GRAPH_BROKEN_BLOCK_REFERENCE = "graph.broken_block_reference"
    GRAPH_PAGE_TITLE_COLLISION = "graph.page_title_collision"
    WRITER_INPUT_LIMIT_EXCEEDED = "writer.input_limit_exceeded"
    WRITER_TARGET_CHANGED = "writer.target_changed"
    WRITER_VAULT_ESCAPE = "writer.vault_escape"


@dataclass(frozen=True)
class Diagnostic:
    """Immutable diagnostic payload safe to serialize outside the parser process.

    ``source_path`` is either ``None`` or a vault-relative POSIX path. Absolute
    paths and parent traversal are rejected so diagnostics cannot accidentally
    disclose data outside the user-selected vault.
    """

    code: str
    severity: DiagnosticSeverity
    message: str
    source_path: str | None = None
    line: int | None = None
    context: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.code:
            raise ValueError("diagnostic code must not be empty")
        if self.line is not None and self.line < 1:
            raise ValueError("diagnostic line must be positive")
        if self.source_path is not None:
            normalized = self.source_path.replace("\\", "/")
            path = PurePosixPath(normalized)
            windows_path = PureWindowsPath(self.source_path)
            if (
                not normalized
                or path.is_absolute()
                or windows_path.is_absolute()
                or bool(windows_path.drive)
                or ".." in path.parts
            ):
                raise ValueError("diagnostic source_path must be vault-relative")
            object.__setattr__(self, "source_path", path.as_posix())
        object.__setattr__(
            self,
            "context",
            MappingProxyType(dict(sorted(self.context.items()))),
        )

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic JSON-compatible representation."""
        return {
            "code": str(self.code),
            "severity": self.severity.value,
            "source_path": self.source_path,
            "line": self.line,
            "message": self.message,
            "context": dict(self.context),
        }


def _vault_relative_source(graph_path: Path, source_path: str | None) -> str | None:
    if source_path is None:
        return None
    try:
        return Path(source_path).resolve().relative_to(graph_path.resolve()).as_posix()
    except ValueError:
        return None


def collect_graph_diagnostics(graph: LogseqGraph) -> list[Diagnostic]:
    """Collect deterministic graph diagnostics without changing graph behavior."""
    diagnostics = list(graph.index_diagnostics)
    for node in graph.get_broken_references():
        page = graph.page_for_node(node)
        source_path = _vault_relative_source(graph.graph_path, node.source_path)
        page_title = page.title if page is not None else "<unknown>"
        for ref in node.block_refs:
            if graph.get_node_by_embed_ref(ref) is not None:
                continue
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCode.GRAPH_BROKEN_BLOCK_REFERENCE,
                    severity=DiagnosticSeverity.ERROR,
                    source_path=source_path,
                    line=node.line_start,
                    message=f"Unresolved block reference (({ref}))",
                    context={
                        "missing_ref": ref,
                        "node_uuid": node.uuid,
                        "page_title": page_title,
                    },
                )
            )
    return sorted(
        diagnostics,
        key=lambda item: (
            item.source_path or "",
            item.line or 0,
            item.code,
            tuple(item.context.items()),
        ),
    )
