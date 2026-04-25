"""FORGE exporters implemented with AST visitors."""

from __future__ import annotations

import json
from typing import Any

from .logos_core import ASTVisitor, LogseqNode


class JSONForgeVisitor(ASTVisitor):
    """Builds a nested JSON-serializable structure during AST traversal."""

    def __init__(self) -> None:
        self._roots: list[dict[str, Any]] = []
        self._stack: list[dict[str, Any]] = []

    def visit_node(self, node: LogseqNode) -> None:
        node_payload = node.model_dump(exclude={"children"})
        node_payload["children"] = []
        if self._stack:
            self._stack[-1]["children"].append(node_payload)
        else:
            self._roots.append(node_payload)
        self._stack.append(node_payload)

    def depart_node(self, node: LogseqNode) -> None:
        _ = node
        self._stack.pop()

    def get_data(self) -> list[dict[str, Any]]:
        return self._roots

    def get_json(self, indent: int = 2) -> str:
        return json.dumps(self._roots, indent=indent)


class FlatListForgeVisitor(ASTVisitor):
    """Collects nodes in preorder as a flat list."""

    def __init__(self) -> None:
        self._flat_items: list[dict[str, Any]] = []

    def visit_node(self, node: LogseqNode) -> None:
        self._flat_items.append(node.model_dump(exclude={"children"}))

    def depart_node(self, node: LogseqNode) -> None:
        _ = node

    def get_data(self) -> list[dict[str, Any]]:
        return self._flat_items


class MarkdownForgeVisitor(ASTVisitor):
    """Builds clean markdown output with topology-preserving indentation."""

    def __init__(self) -> None:
        self._lines: list[str] = []
        self._stack: list[str] = []

    def visit_node(self, node: LogseqNode) -> None:
        depth = len(self._stack)
        prefix = "  " * depth + "- "
        content = node.content.replace("\n", " ")
        self._lines.append(f"{prefix}{content}")
        if node.properties:
            for key, value in node.properties.items():
                if key != "id":
                    self._lines.append(f"  {'  ' * depth}  [:{key} {value}]")
        self._stack.append(node.uuid)

    def depart_node(self, node: LogseqNode) -> None:
        _ = node
        self._stack.pop()

    def get_markdown(self) -> str:
        return "\n".join(self._lines)

class ForgeExporter:
    """Transforms Logseq nodes into artifacts ready for AI ingestion."""

    @staticmethod
    def to_json(nodes: list[LogseqNode], indent: int = 2) -> str:
        """Export the full tree as structured JSON."""
        visitor = JSONForgeVisitor()
        for node in nodes:
            node.accept(visitor)
        return visitor.get_json(indent=indent)

    @staticmethod
    def to_flat_list(nodes: list[LogseqNode]) -> list[dict[str, Any]]:
        """Flatten the tree in preorder while preserving node metadata."""
        visitor = FlatListForgeVisitor()
        for node in nodes:
            node.accept(visitor)
        return visitor.get_data()

    @staticmethod
    def to_clean_markdown(nodes: list[LogseqNode]) -> str:
        """Render clean markdown preserving spatial hierarchy."""
        visitor = MarkdownForgeVisitor()
        for node in nodes:
            node.accept(visitor)
        return visitor.get_markdown()