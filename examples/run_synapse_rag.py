"""Run the three public SYNAPSE conversion paths against an offline fixture.

Run from the repository root after installing the optional AI integrations::

    uv sync --extra ai
    uv run python examples/run_synapse_rag.py

The temporary Logseq graph includes a resolved page embed so the contextual
export demonstrates transclusion without requiring a real vault or network.
"""

from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from logseq_matryca_parser import LogseqGraph, SynapseAdapter


def build_fixture(root: Path) -> LogseqGraph:
    """Create and load a minimal two-page Logseq graph."""
    pages = root / "pages"
    pages.mkdir(parents=True)
    (pages / "RAG Demo.md").write_text(
        "tags:: rag, demo\n\n"
        "- Retrieval context\n"
        "  - Include this knowledge: {{embed [[Shared Knowledge]]}}\n",
        encoding="utf-8",
    )
    (pages / "Shared Knowledge.md").write_text(
        "- Matryca preserves Logseq hierarchy and provenance.\n",
        encoding="utf-8",
    )
    return LogseqGraph.load_directory(root)


def run_demo() -> None:
    """Convert the fixture with LangChain, LlamaIndex, and contextual exports."""
    with TemporaryDirectory(prefix="logseq-matryca-synapse-") as directory:
        graph = build_fixture(Path(directory))
        page = graph.pages["RAG Demo"]

        langchain_documents = SynapseAdapter.to_langchain_documents(
            page.root_nodes,
            source_name=page.title,
        )
        llamaindex_nodes = SynapseAdapter.to_llamaindex_nodes(
            page.root_nodes,
            page_title=page.title,
        )
        contextual_chunks = SynapseAdapter.to_context_enriched_chunks(
            page.root_nodes,
            graph,
        )

        expanded = contextual_chunks[-1].page_content
        expected_embed = "Matryca preserves Logseq hierarchy and provenance."
        if expected_embed not in expanded or "{{embed" in expanded:
            raise RuntimeError("resolved page embed was not expanded in contextual output")

        print(f"LangChain documents: {len(langchain_documents)}")
        print(f"LlamaIndex nodes: {len(llamaindex_nodes)}")
        print(f"Context-enriched chunks: {len(contextual_chunks)}")
        print(f"Resolved page embed: {expanded}")


if __name__ == "__main__":
    try:
        run_demo()
    except ImportError as exc:
        print(
            "SYNAPSE AI dependencies are missing. "
            "Install them with `uv sync --extra ai` and run this script again. "
            f"Details: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
