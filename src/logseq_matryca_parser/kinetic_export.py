"""KINETIC export handlers — format-specific serialization (SRP slice)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from logseq_matryca_parser.forge import ForgeExporter
from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage
from logseq_matryca_parser.synapse import SynapseAdapter

if TYPE_CHECKING:
    from logseq_matryca_parser.graph import LogseqGraph


def export_json(pages: list[LogseqPage], output_path: Path) -> Path:
    payload: list[dict[str, Any]] = []
    for page in pages:
        page_payload = {
            "title": page.title,
            "source_path": page.source_path,
            "graph_root": page.graph_root,
            "properties": page.properties,
            "refs": page.refs,
            "created_at": page.created_at,
            "updated_at": page.updated_at,
            "ast": json.loads(ForgeExporter.to_json(page.root_nodes)),
        }
        payload.append(page_payload)
    destination = output_path / "graph.json"
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return destination


def export_markdown(pages: list[LogseqPage], output_path: Path) -> Path:
    destination = output_path / "graph.md"
    sections: list[str] = []
    for page in pages:
        sections.append(f"# {page.title}")
        sections.append(ForgeExporter.to_clean_markdown(page.root_nodes))
        sections.append("")
    destination.write_text("\n".join(sections).rstrip() + "\n", encoding="utf-8")
    return destination


def export_langchain(pages: list[LogseqPage], output_path: Path) -> Path:
    payload: list[dict[str, Any]] = []
    for page in pages:
        docs = SynapseAdapter.to_langchain_documents(page.root_nodes, source_name=page.title)
        payload.extend(
            {
                "page_content": doc.page_content,
                "metadata": doc.metadata,
            }
            for doc in docs
        )
    destination = output_path / "langchain.json"
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return destination


def export_langchain_enriched(graph: LogseqGraph, output_path: Path) -> tuple[Path, int]:
    """Serialize context-enriched LangChain documents for the full loaded graph."""
    all_roots: list[LogseqNode] = []
    for page in graph.iter_canonical_pages():
        all_roots.extend(page.root_nodes)
    docs = SynapseAdapter.to_context_enriched_chunks(all_roots, graph)
    payload: list[dict[str, Any]] = [
        {"page_content": doc.page_content, "metadata": doc.metadata} for doc in docs
    ]
    destination = output_path / "langchain_enriched.json"
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return destination, len(payload)


def _page_tree_contains_node_uuid(roots: list[LogseqNode], needle_uuid: str) -> bool:
    for node in roots:
        if node.uuid == needle_uuid:
            return True
        if node.children and _page_tree_contains_node_uuid(node.children, needle_uuid):
            return True
    return False


def _safe_obsidian_vault_relative_path(page_title: str) -> Path:
    segments = [
        re.sub(r'[<>:"|?*\\]', "_", segment) for segment in page_title.split("/") if segment
    ]
    if not segments:
        return Path("untitled.md")
    *parents, leaf = segments
    if not parents:
        return Path(f"{leaf}.md")
    return Path(*parents) / f"{leaf}.md"


def export_obsidian(graph: LogseqGraph, output_path: Path) -> int:
    """Write one Obsidian-compatible Markdown file per page (namespace folders)."""
    pages_list = list(graph.iter_canonical_pages())
    targets = ForgeExporter.vault_wide_embed_targets(pages_list)
    suffix_map = ForgeExporter.build_vault_obsidian_suffix_map(
        pages_list,
        vault_wide_ref_targets=targets,
    )

    def embed_resolver(ref: str) -> tuple[str, str] | None:
        node = graph.get_node_by_embed_ref(ref)
        if node is None:
            return None
        for page in pages_list:
            if _page_tree_contains_node_uuid(page.root_nodes, node.uuid):
                anchor = suffix_map.get(node.uuid, node.uuid.replace("-", "")[:8])
                return page.title, anchor
        return None

    count = 0
    for page in pages_list:
        props = {**page.properties, "title": page.title}
        md = ForgeExporter.to_obsidian_markdown(
            page.root_nodes,
            props,
            embed_resolver=embed_resolver,
            global_suffix_map=suffix_map,
            vault_wide_ref_targets=targets,
        )
        rel = _safe_obsidian_vault_relative_path(page.title)
        out_file = output_path / rel
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(md, encoding="utf-8")
        count += 1
    return count
