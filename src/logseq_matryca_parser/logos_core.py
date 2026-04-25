"""Core models and interfaces for the LOGOS parser module."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ASTVisitor(ABC):
    """Visitor interface used by adapters and exporters."""

    @abstractmethod
    def visit_node(self, node: "LogseqNode") -> None:
        """Called when entering a node."""

    @abstractmethod
    def depart_node(self, node: "LogseqNode") -> None:
        """Called when leaving a node."""


class LogseqNode(BaseModel):
    """Single Logseq AST node."""

    model_config = ConfigDict(strict=True, frozen=True)

    uuid: str
    content: str
    clean_text: str = ""
    indent_level: int
    properties: dict[str, Any] = Field(default_factory=dict)
    wikilinks: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    block_refs: list[str] = Field(default_factory=list)
    parent_id: str | None = None
    children: list["LogseqNode"] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _derive_clean_text(cls, data: Any) -> Any:
        if isinstance(data, dict) and "clean_text" not in data:
            content = data.get("content", "")
            if isinstance(content, str):
                data["clean_text"] = content
        return data

    def accept(self, visitor: ASTVisitor) -> None:
        """Traverse this node with a visitor."""
        visitor.visit_node(self)
        for child in self.children:
            child.accept(visitor)
        visitor.depart_node(self)

    def add_child(self, node: "LogseqNode") -> "LogseqNode":
        """Return a copy with one additional child."""
        return self.model_copy(update={"children": [*self.children, node]})


class LogseqPage(BaseModel):
    """Container model for a parsed Logseq page."""

    model_config = ConfigDict(strict=True, frozen=True)

    title: str
    raw_content: str
    properties: dict[str, Any] = Field(default_factory=dict)
    root_nodes: list[LogseqNode] = Field(default_factory=list)


class SovereignNotePackage(BaseModel):
    """Universal payload exported from the parser."""

    model_config = ConfigDict(strict=True, frozen=True)

    slug: str
    raw_content: str
    parsed_ast: LogseqNode
    metadata: dict[str, Any] = Field(default_factory=dict)
    checksum: str
    version: str = "1.0.0"


class LogosNode(LogseqNode):
    """Backward-compatible mutable wrapper used by legacy callers/tests."""

    model_config = ConfigDict(strict=True, frozen=False)

    def add_child(self, node: "LogseqNode") -> "LogseqNode":
        self.children.append(node)
        return self

# Explicit model rebuild for recursive fields (Nuitka/AOT compatibility).
LogseqNode.model_rebuild()