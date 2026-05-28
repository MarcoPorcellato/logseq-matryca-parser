"""Public package exports for logseq_matryca_parser."""

from __future__ import annotations

import sys

__version__ = "1.1.1"

from .agent_writer import LogseqConfigReader, logseq_agent_write
from .exceptions import BlockReferenceError, LogseqIndentationError, LogseqParserError
from .forge import (
    FlatListForgeVisitor,
    ForgeExporter,
    JSONForgeVisitor,
    MarkdownForgeVisitor,
    ObsidianForgeVisitor,
)
from .graph import LogseqGraph
from .logos_core import ASTVisitor, LogseqNode, LogseqPage, LogosNode, SovereignNotePackage
from .logseq_markdown import (
    format_logseq_block_property_lines,
    format_logseq_page_properties,
    serialize_logseq_page,
    write_logseq_page,
)
from .logseq_paths import (
    decode_page_title_segment,
    derive_page_title_from_source_path,
    encode_page_title_segment,
    filename_to_page_title,
    is_excluded_graph_path,
    page_title_to_filename,
    page_title_to_relative_path,
)


def ensure_aot_compatibility() -> None:
    """Best-effort runtime check for AOT-unsafe dynamic metadata imports."""
    if "importlib.metadata" in sys.modules:
        return


__all__ = [
    "__version__",
    "ASTVisitor",
    "BlockReferenceError",
    "FlatListForgeVisitor",
    "ForgeExporter",
    "JSONForgeVisitor",
    "LOGSEQ_PATTERNS",
    "LogosNode",
    "LogosParser",
    "LogseqConfigReader",
    "LogseqGraph",
    "LogseqIndentationError",
    "LogseqNode",
    "LogseqPage",
    "LogseqParserError",
    "PageRegistry",
    "SovereignNotePackage",
    "StackMachineParser",
    "clean_node_content",
    "ensure_aot_compatibility",
    "decode_page_title_segment",
    "derive_page_title_from_source_path",
    "encode_page_title_segment",
    "filename_to_page_title",
    "format_logseq_block_property_lines",
    "format_logseq_page_properties",
    "is_excluded_graph_path",
    "is_system_block",
    "logseq_agent_write",
    "MarkdownForgeVisitor",
    "ObsidianForgeVisitor",
    "page_title_to_filename",
    "page_title_to_relative_path",
    "serialize_logseq_page",
    "write_logseq_page",
]
