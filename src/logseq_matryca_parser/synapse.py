"""SYNAPSE adapters implemented with AST visitors."""

from __future__ import annotations

import logging
import re
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, NotRequired, TypedDict

from logseq_matryca_parser.logos_core import ASTVisitor, LogseqNode, LogseqPage
from logseq_matryca_parser.logos_parser import LogosParser

if TYPE_CHECKING:
    from logseq_matryca_parser.graph import LogseqGraph

logger = logging.getLogger(__name__)

_PATH_JOIN = " > "
_REFS_JOIN = ", "


class SynapseMetadata(TypedDict, total=False):
    """Vector-store-safe metadata schema for LangChain / LlamaIndex exports."""

    uuid: str
    source_uuid: str | None
    parent_id: str | None
    indent_level: int
    source: str
    path: str
    left_id: str | None
    refs: str
    task_status: str | None
    task_priority: str | None
    scheduled_at: int | None
    deadline_at: int | None
    repeater: str | None
    created_at: int | None
    clean_text: NotRequired[str]
    page_title: NotRequired[str]
    source_path: NotRequired[str | None]
    line_start: NotRequired[int | None]
    effective_properties: NotRequired[dict[str, Any]]

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


def _serialize_metadata_value(value: Any) -> Any:
    """Coerce property values to JSON-safe scalars for vector-store filters."""
    if isinstance(value, list):
        return _REFS_JOIN.join(str(item) for item in value)
    if isinstance(value, dict):
        return {str(k): _serialize_metadata_value(v) for k, v in value.items()}
    return value


def _join_path_segments(segments: list[str]) -> str:
    return _PATH_JOIN.join(segments)


def _join_refs(refs: list[str]) -> str:
    return _REFS_JOIN.join(refs)


def build_synapse_metadata(
    node: LogseqNode,
    *,
    source: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a consistent, vector-store-safe metadata dict for a ``LogseqNode``."""
    metadata: dict[str, Any] = {
        key: _serialize_metadata_value(value) for key, value in node.properties.items()
    }
    metadata.update(
        {
            "uuid": node.uuid,
            "source_uuid": node.source_uuid,
            "parent_id": node.parent_id,
            "indent_level": node.indent_level,
            "source": source,
            "path": _join_path_segments(node.path),
            "left_id": node.left_id,
            "refs": _join_refs(node.refs),
            "task_status": node.task_status,
            "task_priority": node.task_priority,
            "scheduled_at": node.scheduled_at,
            "deadline_at": node.deadline_at,
            "repeater": node.repeater,
            "created_at": node.created_at,
        }
    )
    if extra:
        for key, value in extra.items():
            metadata[key] = _serialize_metadata_value(value)
    return metadata


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


def _expand_macros_and_embeds(
    text: str,
    graph: LogseqGraph,
    visited_uuids: set[str],
    *,
    embed_page_chain: frozenset[str] = frozenset(),
) -> str:
    """Expand ``{{embed ((uuid))}}`` / ``{{embed [[page]]}}`` for RAG text.

    Operates on raw block ``content`` (not ``clean_text``) so ``((uuid))`` inside macros is
    still visible to the scanner after parsing.
    """
    return _expand_macros_and_embeds_impl(text, graph, visited_uuids, embed_page_chain)


def _expand_macros_and_embeds_impl(
    text: str,
    graph: LogseqGraph,
    visited_uuids: set[str],
    embed_page_chain: frozenset[str],
) -> str:
    """Shared worker: ``visited_uuids`` breaks block cycles; ``embed_page_chain`` breaks page cycles."""
    from logseq_matryca_parser.synapse_embed import expand_macros_and_embeds_impl

    return expand_macros_and_embeds_impl(text, graph, visited_uuids, embed_page_chain)


def _build_breadcrumbs(graph: LogseqGraph, node: LogseqNode) -> tuple[str, LogseqPage | None]:
    """Build `Page > ancestor clean_text ...` using ``node.path`` and the graph registry."""
    page = graph.page_for_node(node)
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


def page_source_node_id(page_title: str, source_path: str | None = None) -> str:
    """Return a stable LlamaIndex ``SOURCE`` document id for a ``LogseqPage``."""
    seed = source_path if source_path else page_title
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"logseq-page:{seed}"))


class LangChainVisitor(ASTVisitor):
    """Build LangChain documents during AST traversal."""

    def __init__(self, source_name: str, document_cls: type[Any]) -> None:
        self._source_name = source_name
        self._document_cls = document_cls
        self._documents: list[Any] = []

    def visit_node(self, node: LogseqNode) -> None:
        metadata = build_synapse_metadata(node, source=self._source_name)
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
    """Build LlamaIndex nodes and inject parent/child/sibling/page topology relationships."""

    def __init__(
        self,
        text_node_cls: type[Any],
        node_relationship: Any,
        related_node_info_cls: type[Any],
        *,
        page_source_id: str | None = None,
        source_id_for_node: Callable[[LogseqNode], str] | None = None,
    ) -> None:
        self._text_node_cls = text_node_cls
        self._node_relationship = node_relationship
        self._related_node_info_cls = related_node_info_cls
        self._page_source_id = page_source_id
        self._source_id_for_node = source_id_for_node
        self._nodes_by_id: dict[str, Any] = {}
        self._ordered_nodes: list[Any] = []

    def visit_node(self, node: LogseqNode) -> None:
        text_node = self._text_node_cls(
            id_=node.uuid,
            text=node.clean_text,
            metadata=build_synapse_metadata(node, source=node.source_path or ""),
        )
        if not hasattr(text_node, "relationships") or text_node.relationships is None:
            text_node.relationships = {}

        source_id = self._page_source_id
        if self._source_id_for_node is not None:
            source_id = self._source_id_for_node(node)
        if source_id is not None:
            text_node.relationships[self._node_relationship.SOURCE] = self._related_node_info_cls(
                node_id=source_id
            )

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

        if node.left_id:
            text_node.relationships[self._node_relationship.PREVIOUS] = (
                self._related_node_info_cls(node_id=node.left_id)
            )
            previous_node = self._nodes_by_id.get(node.left_id)
            if previous_node is not None:
                previous_node.relationships[self._node_relationship.NEXT] = (
                    self._related_node_info_cls(node_id=node.uuid)
                )

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
    def to_llamaindex_nodes(
        nodes: list[LogseqNode],
        *,
        page_title: str | None = None,
        page_source_id: str | None = None,
    ) -> list[Any]:
        """Convert AST nodes to LlamaIndex nodes preserving topology links."""
        if TextNode is None or NodeRelationship is None or RelatedNodeInfo is None:
            raise ImportError("LlamaIndex non rilevato. Installa 'llama-index' per usare Synapse.")
        flat = _flatten_nodes_for_export(nodes)
        unique_paths = {node.source_path for node in flat if node.source_path}
        use_per_node_source = len(unique_paths) > 1
        source_ids_by_path: dict[str, str] = {}

        def _source_id_for_node(node: LogseqNode) -> str:
            path_key = node.source_path or ""
            if path_key not in source_ids_by_path:
                title_seed = page_title or (Path(path_key).stem if path_key else "untitled")
                source_ids_by_path[path_key] = page_source_node_id(title_seed, path_key or None)
            return source_ids_by_path[path_key]

        resolved_source_id = page_source_id
        if resolved_source_id is None and not use_per_node_source:
            first_path = next(iter(unique_paths), None)
            title = page_title or "untitled"
            resolved_source_id = page_source_node_id(title, first_path)
        visitor = LlamaIndexVisitor(
            text_node_cls=TextNode,
            node_relationship=NodeRelationship,
            related_node_info_cls=RelatedNodeInfo,
            page_source_id=None if use_per_node_source else resolved_source_id,
            source_id_for_node=_source_id_for_node if use_per_node_source else None,
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
            if graph.page_for_node(node) is None:
                logger.debug("context chunk skip orphan uuid=%s", node.uuid)
                continue
            breadcrumbs, page = _build_breadcrumbs(graph, node)
            source_name = Path(node.source_path).name if node.source_path else str(graph.graph_path.name)
            host_page = graph.page_for_node(node)
            embed_chain = (
                frozenset({host_page.title}) if host_page is not None else frozenset()
            )
            expanded_content = _expand_macros_and_embeds(
                node.content, graph, set(), embed_page_chain=embed_chain
            )
            page_content = format_template.format(
                breadcrumbs=breadcrumbs,
                content=expanded_content,
            )
            effective_properties = {
                key: _serialize_metadata_value(value)
                for key, value in graph.get_effective_properties(node.uuid).items()
            }
            metadata = build_synapse_metadata(
                node,
                source=source_name,
                extra={
                    "clean_text": node.clean_text,
                    "page_title": page.title if page is not None else "",
                    "source_path": node.source_path,
                    "line_start": node.line_start,
                    "effective_properties": effective_properties,
                },
            )
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