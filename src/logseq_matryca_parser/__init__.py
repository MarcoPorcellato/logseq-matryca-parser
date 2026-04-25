"""Public package exports for logseq_matryca_parser."""

from __future__ import annotations

import sys

from .exceptions import BlockReferenceError, LogseqIndentationError, LogseqParserError
from .logos_core import ASTVisitor, LogseqNode, LogseqPage, LogosNode, SovereignNotePackage
from .logos_parser import (
    LOGSEQ_PATTERNS,
    LogosParser,
    PageRegistry,
    StackMachineParser,
    clean_node_content,
    is_system_block,
)


def ensure_aot_compatibility() -> None:
    """Best-effort runtime check for AOT-unsafe dynamic metadata imports."""
    if "importlib.metadata" in sys.modules:
        return


__all__ = [
    "ASTVisitor",
    "BlockReferenceError",
    "LOGSEQ_PATTERNS",
    "LogosNode",
    "LogosParser",
    "LogseqIndentationError",
    "LogseqNode",
    "LogseqPage",
    "LogseqParserError",
    "PageRegistry",
    "SovereignNotePackage",
    "StackMachineParser",
    "clean_node_content",
    "ensure_aot_compatibility",
    "is_system_block",
]
