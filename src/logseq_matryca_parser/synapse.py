"""SYNAPSE adapters implemented with AST visitors."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from logseq_matryca_parser.logos_core import ASTVisitor, LogseqNode, LogseqPage
from logseq_matryca_parser.logos_parser import LogosParser

if TYPE_CHECKING:
    from logseq_matryca_parser.graph import LogseqGraph

logger = logging.getLogger(__name__)

_BLOCK_EMBED_PATTERN = re.compile(
    r"\{\{\s*embed\s+\(\((?P<uuid>[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\)\)\s*\}\}",
    re.IGNORECASE,
)
_PAGE_EMBED_PATTERN = re.compile(r"\{\{\s*embed\s+\[\[(?P<title>[^\]]+)\]\]\s*\}\}")

Document: type[Any] | None
NodeRelationship: Any
RelatedNodeInfo: type[Any] | None
TextNode: type[Any] | None

try:
    from langchain_core.documents import Document  # type: ignore
except ImportError:
    Document = None

try:
    from llama_index.core.schema import (  # type: ignore
        NodeRelationship,
        RelatedNodeInfo,
        TextNode,
    )
except ImportError:
    NodeRelationship = None
    RelatedNodeInfo = None
    TextNode = None


def _flatten_nodes_for_export(nodes: list[LogseqNode]) -> list[LogseqNode]:
    """Depth-first flattening of a node tree (same order as graph indexing)."""
    flat: list[LogseqNode] = []
    for node in nodes:
        flat.append(node)
        if node.children:
            flat.extend(_flatten_nodes_for_export(node.children))
    return flat


def _strip_markdown_for_embedding(text: str) -> str:
    """Remove common markdown noise from breadcrumb fragments for embedding-friendly strings."""
    s = text.strip()
    s = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", s)
    s = re.sub(r"`([^`]+)`", r"\1", s)
    s = re.sub(r"#([^\s#]+)", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _expand_macros_and_embeds(text: str, graph: LogseqGraph, visited_uuids: set[str]) -> str:
    """Expand ``{{embed ((uuid))}}`` / ``{{embed [[page]]}}`` for RAG text.

    Operates on raw block ``content`` (not ``clean_text``) so ``((uuid))`` inside macros is
    still visible to the scanner after parsing.
    """
    return _expand_macros_and_embeds_impl(text, graph, visited_uuids, set())


def _expand_macros_and_embeds_impl(
    text: str,
    graph: LogseqGraph,
    visited_uuids: set[str],
    visited_pages: set[str],
) -> str:
    """Shared worker: ``visited_uuids`` breaks block cycles; ``visited_pages`` breaks page cycles."""
    result = text
    while True:
        bm = _BLOCK_EMBED_PATTERN.search(result)
        pm = _PAGE_EMBED_PATTERN.search(result)
        if bm is None and pm is None:
            break
        use_block = bm is not None and (pm is None or bm.start() <= pm.start())
        if use_block:
            assert bm is not None
            match = bm
            uid = match.group("uuid")
            if uid in visited_uuids:
                logger.debug("Stack-Machine embed: cyclic block uuid=%s", uid)
                replacement = ""
            else:
                target = graph.get_node_by_embed_ref(uid)
                if target is None:
                    logger.debug("Stack-Machine embed: unresolved block uuid=%s", uid)
                    replacement = match.group(0)
                else:
                    next_seen = set(visited_uuids)
                    next_seen.add(uid)
                    replacement = _expand_macros_and_embeds_impl(
                        target.content, graph, next_seen, visited_pages
                    )
            result = result[: match.start()] + replacement + result[match.end() :]
        else:
            assert pm is not None
            match = pm
            title = match.group("title").strip()
            if title in visited_pages:
                logger.debug("Stack-Machine embed: cyclic page title=%s", title)
                replacement = ""
            else:
                page = graph.pages.get(title)
                if page is None:
                    logger.debug("Stack-Machine embed: unknown page title=%s", title)
                    replacement = match.group(0)
                else:
                    visited_pages.add(title)
                    try:
                        shared_blocks = set(visited_uuids)
                        pieces: list[str] = []
                        for n in _flatten_nodes_for_export(page.root_nodes):
                            frag = _expand_macros_and_embeds_impl(
                                n.content, graph, shared_blocks, visited_pages
                            )
                            stripped = frag.strip()
                            if stripped:
                                pieces.append(stripped)
                        replacement = "\n".join(pieces)
                    finally:
                        visited_pages.discard(title)
            result = result[: match.start()] + replacement + result[match.end() :]
    return result


def _build_breadcrumbs(graph: LogseqGraph, node: LogseqNode) -> tuple[str, LogseqPage | None]:
    """Build `Page > ancestor clean_text ...` using ``node.path`` and the graph registry."""
    page = graph._page_for_node(node)
    page_title = page.title if page is not None else ""
    parts: list[str] = []
    if page_title:
        parts.append(_strip_markdown_for_embedding(page_title))
    for ancestor_uuid in node.path[:-1]:
        ancestor = graph.get_node_by_uuid(ancestor_uuid)
        if ancestor is None:
            continue
        stripped = _strip_markdown_for_embedding(ancestor.clean_text)
        if stripped:
            parts.append(stripped)
    return " > ".join(parts), page


class LangChainVisitor(ASTVisitor):
    """Build LangChain documents during AST traversal."""

    def __init__(self, source_name: str, document_cls: type[Any]) -> None:
        self._source_name = source_name
        self._document_cls = document_cls
        self._documents: list[Any] = []

    def visit_node(self, node: LogseqNode) -> None:
        metadata = {
            **node.properties,
            "uuid": node.uuid,
            "parent_id": node.parent_id,
            "indent_level": node.indent_level,
            "source": self._source_name,
            "path": node.path,
            "left_id": node.left_id,
            "refs": node.refs,
            "task_status": node.task_status,
            "repeater": node.repeater,
            "created_at": node.created_at,
        }
        self._documents.append(
            self._document_cls(
                page_content=node.clean_text,
                metadata=metadata,
            )
        )

    def depart_node(self, node: LogseqNode) -> None:
        _ = node

    def get_documents(self) -> list[Any]:
        return self._documents


class LlamaIndexVisitor(ASTVisitor):
    """Build LlamaIndex nodes and inject parent/child topology relationships."""

    def __init__(
        self,
        text_node_cls: type[Any],
        node_relationship: Any,
        related_node_info_cls: type[Any],
    ) -> None:
        self._text_node_cls = text_node_cls
        self._node_relationship = node_relationship
        self._related_node_info_cls = related_node_info_cls
        self._nodes_by_id: dict[str, Any] = {}
        self._ordered_nodes: list[Any] = []

    def visit_node(self, node: LogseqNode) -> None:
        text_node = self._text_node_cls(
            id_=node.uuid,
            text=node.clean_text,
            metadata={
                **node.properties,
                "uuid": node.uuid,
                "indent_level": node.indent_level,
                "path": node.path,
                "left_id": node.left_id,
                "refs": node.refs,
                "task_status": node.task_status,
                "repeater": node.repeater,
                "created_at": node.created_at,
            },
        )
        if not hasattr(text_node, "relationships") or text_node.relationships is None:
            text_node.relationships = {}

        if node.parent_id:
            text_node.relationships[self._node_relationship.PARENT] = self._related_node_info_cls(
                node_id=node.parent_id
            )
            parent_node = self._nodes_by_id.get(node.parent_id)
            if parent_node is not None:
                child_relationships = parent_node.relationships.get(
                    self._node_relationship.CHILD, []
                )
                child_relationships.append(self._related_node_info_cls(node_id=node.uuid))
                parent_node.relationships[self._node_relationship.CHILD] = child_relationships

        self._nodes_by_id[node.uuid] = text_node
        self._ordered_nodes.append(text_node)

    def depart_node(self, node: LogseqNode) -> None:
        _ = node

    def get_nodes(self) -> list[Any]:
        return self._ordered_nodes


class SynapseAdapter:
    """Transform Logseq hierarchy into framework-native AI objects."""

    @staticmethod
    def to_langchain_documents(nodes: list[LogseqNode], source_name: str) -> list[Any]:
        """Convert AST nodes to LangChain documents using `LangChainVisitor`."""
        if Document is None:
            raise ImportError("LangChain non rilevato. Installa 'langchain-core' per usare Synapse.")
        visitor = LangChainVisitor(source_name=source_name, document_cls=Document)
        for node in nodes:
            node.accept(visitor)
        return visitor.get_documents()

    @staticmethod
    def to_llamaindex_nodes(nodes: list[LogseqNode]) -> list[Any]:
        """Convert AST nodes to LlamaIndex nodes preserving topology links."""
        if TextNode is None or NodeRelationship is None or RelatedNodeInfo is None:
            raise ImportError("LlamaIndex non rilevato. Installa 'llama-index' per usare Synapse.")
        visitor = LlamaIndexVisitor(
            text_node_cls=TextNode,
            node_relationship=NodeRelationship,
            related_node_info_cls=RelatedNodeInfo,
        )
        for node in nodes:
            node.accept(visitor)
        return visitor.get_nodes()

    @staticmethod
    def to_context_enriched_chunks(
        nodes: list[LogseqNode],
        graph: LogseqGraph,
        format_template: str = "[{breadcrumbs}] {content}",
    ) -> list[Any]:
        """Flatten ``nodes`` and emit LangChain ``Document``s with breadcrumb-enriched ``page_content``."""
        if Document is None:
            raise ImportError("LangChain non rilevato. Installa 'langchain-core' per usare Synapse.")
        documents: list[Any] = []
        flat = _flatten_nodes_for_export(nodes)
        for node in flat:
            breadcrumbs, page = _build_breadcrumbs(graph, node)
            source_name = Path(node.source_path).name if node.source_path else str(graph.graph_path.name)
            expanded_content = _expand_macros_and_embeds(node.content, graph, set())
            page_content = format_template.format(
                breadcrumbs=breadcrumbs,
                content=expanded_content,
            )
            effective_properties = dict(graph.get_effective_properties(node.uuid))
            metadata = {
                **node.properties,
                "uuid": node.uuid,
                "parent_id": node.parent_id,
                "indent_level": node.indent_level,
                "source": source_name,
                "path": node.path,
                "left_id": node.left_id,
                "refs": node.refs,
                "task_status": node.task_status,
                "repeater": node.repeater,
                "created_at": node.created_at,
                "clean_text": node.clean_text,
                "page_title": page.title if page is not None else "",
                "source_path": node.source_path,
                "line_start": node.line_start,
                "effective_properties": effective_properties,
            }
            documents.append(Document(page_content=page_content, metadata=metadata))
            logger.debug(
                "context chunk uuid=%s breadcrumbs_len=%s effective_keys=%s",
                node.uuid,
                len(breadcrumbs),
                tuple(effective_properties.keys()),
            )
        return documents

    @classmethod
    def load_and_convert(cls, file_path: Path) -> list[Any]:
        """Parse a file and convert it to LangChain documents."""
        parser = LogosParser()
        nodes = parser.parse_file(file_path)
        return cls.to_langchain_documents(nodes, source_name=file_path.name)