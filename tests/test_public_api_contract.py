from __future__ import annotations

import inspect
from importlib.resources import files

import logseq_matryca_parser as package

EXPECTED_ROOT_EXPORTS = {
    "__version__",
    "ASTVisitor",
    "BlockReferenceError",
    "Diagnostic",
    "DiagnosticCode",
    "DiagnosticSeverity",
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
    "collect_graph_diagnostics",
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
}


def test_root_export_manifest_is_explicit_and_importable() -> None:
    assert set(package.__all__) == EXPECTED_ROOT_EXPORTS
    for name in package.__all__:
        assert hasattr(package, name), f"missing root export: {name}"


def test_installed_package_exposes_pep561_marker() -> None:
    assert files("logseq_matryca_parser").joinpath("py.typed").is_file()


def test_stable_parser_signature() -> None:
    signature = inspect.signature(package.StackMachineParser.parse)

    assert tuple(signature.parameters) == ("self", "text", "page_title")
    assert signature.parameters["page_title"].default == "untitled"


def test_stable_graph_loader_signature() -> None:
    signature = inspect.signature(package.LogseqGraph.load_directory)

    assert tuple(signature.parameters) == ("graph_path", "strict_refs")
    assert signature.parameters["strict_refs"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["strict_refs"].default is False
