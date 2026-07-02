"""Public package exports for logseq_matryca_parser."""

from __future__ import annotations

import sys

__version__ = "1.5.0"

from .agent_press import SessionAliasRegistry
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
from .logos_core import ASTVisitor, LogosNode, LogseqNode, LogseqPage, SovereignNotePackage
from .logos_parser import (
    LOGSEQ_PATTERNS,
    LogosParser,
    PageRegistry,
    StackMachineParser,
    clean_node_content,
    is_system_block,
)
from .logseq_markdown import (
    format_logseq_block_property_lines,
    format_logseq_page_properties,
    serialize_logseq_page,
    write_logseq_page,
)
from .logseq_paths import (
    decode_page_title_segment,
    derive_page_title_from_source_path,
    discover_graph_files,
    encode_page_title_segment,
    filename_to_page_title,
    is_excluded_graph_path,
    page_title_to_filename,
    page_title_to_relative_path,
)
from .synapse import SynapseAdapter, page_source_node_id

try:
    from .lens import GraphVisualizer
except ImportError:  # optional [viz] extra (networkx / pyvis)
    GraphVisualizer = None  # type: ignore[misc, assignment]


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
    "GraphVisualizer",
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
    "MarkdownForgeVisitor",
    "ObsidianForgeVisitor",
    "PageRegistry",
    "SessionAliasRegistry",
    "SovereignNotePackage",
    "StackMachineParser",
    "SynapseAdapter",
    "clean_node_content",
    "decode_page_title_segment",
    "derive_page_title_from_source_path",
    "discover_graph_files",
    "encode_page_title_segment",
    "ensure_aot_compatibility",
    "filename_to_page_title",
    "format_logseq_block_property_lines",
    "format_logseq_page_properties",
    "is_excluded_graph_path",
    "is_system_block",
    "logseq_agent_write",
    "page_source_node_id",
    "page_title_to_filename",
    "page_title_to_relative_path",
    "serialize_logseq_page",
    "write_logseq_page",
]
