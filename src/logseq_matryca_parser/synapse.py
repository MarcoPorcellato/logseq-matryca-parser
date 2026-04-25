"""SYNAPSE adapters implemented with AST visitors."""

from __future__ import annotations

from pathlib import Path
from typing import Any

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

from .logos_core import ASTVisitor, LogseqNode
from .logos_parser import LogosParser


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

    @classmethod
    def load_and_convert(cls, file_path: Path) -> list[Any]:
        """Parse a file and convert it to LangChain documents."""
        parser = LogosParser()
        nodes = parser.parse_file(file_path)
        return cls.to_langchain_documents(nodes, source_name=file_path.name)