"""Core models and interfaces for the LOGOS parser module."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path
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
    refs: list[str] = Field(default_factory=list)
    task_status: str | None = None
    repeater: str | None = None
    parent_id: str | None = None
    left_id: str | None = None
    path: list[str] = Field(default_factory=list)
    properties_order: list[str] = Field(default_factory=list)
    created_at: int | None = None
    updated_at: int | None = None
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
    refs: list[str] = Field(default_factory=list)
    created_at: int | None = None
    updated_at: int | None = None
    namespace_chain: list[str] = Field(default_factory=list)
    source_path: str | None = None
    graph_root: str | None = None
    root_nodes: list[LogseqNode] = Field(default_factory=list)

    def resolve_asset_path(self, asset_link: str) -> str | None:
        """Resolve a Logseq asset link to an absolute filesystem path."""
        normalized_link = asset_link.strip().replace("\\", "/")
        if not normalized_link:
            return None

        if normalized_link.startswith("file://"):
            filesystem_path = normalized_link.replace("file://", "", 1)
            if os.name == "nt" and filesystem_path.startswith("/"):
                filesystem_path = filesystem_path[1:]
            return str(Path(filesystem_path).resolve())

        graph_root = self._infer_graph_root()
        if graph_root is not None and (
            normalized_link.startswith("../assets/") or normalized_link.startswith("assets/")
        ):
            root_relative = normalized_link
            while root_relative.startswith("../"):
                root_relative = root_relative[3:]
            root_relative_path = Path(root_relative)
            return str((graph_root / root_relative_path).resolve())

        if self.source_path:
            local_candidate = (Path(self.source_path).parent / normalized_link).resolve()
            if local_candidate.exists():
                return str(local_candidate)

        if graph_root is not None:
            fallback_asset = (graph_root / "assets" / Path(normalized_link).name).resolve()
            if fallback_asset.exists():
                return str(fallback_asset)

        return None

    def _infer_graph_root(self) -> Path | None:
        if self.graph_root:
            return Path(self.graph_root).resolve()
        if not self.source_path:
            return None

        source_path = Path(self.source_path).resolve()
        marker_dirs = {"pages", "journals", "assets", "logseq"}
        for parent in source_path.parents:
            if parent.name in marker_dirs:
                return parent.parent.resolve()
        return None


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