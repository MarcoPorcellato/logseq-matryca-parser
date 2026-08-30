"""Downstream typing smoke test executed against the built wheel."""

from pathlib import Path

from logseq_matryca_parser import LogseqGraph, LogseqPage, StackMachineParser

parser: StackMachineParser = StackMachineParser()
page: LogseqPage = parser.parse("- typed block", page_title="Typed")
graph_path: Path = Path("/tmp/example")
graph: LogseqGraph = LogseqGraph.load_directory(graph_path, strict_refs=False)
graph_from_string: LogseqGraph = LogseqGraph.load_directory(str(graph_path), strict_refs=False)

assert page.title == "Typed"
assert isinstance(graph, LogseqGraph)
assert isinstance(graph_from_string, LogseqGraph)
