"""In-memory Logseq graph orchestration (no database)."""

from __future__ import annotations

import logging
import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, PrivateAttr

from logseq_matryca_parser.kinetic import _discover_graph_files
from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage
from logseq_matryca_parser.logos_parser import StackMachineParser

logger = logging.getLogger(__name__)

_DEFAULT_MAX_WORKERS = min(32, (os.cpu_count() or 1) + 4)


def _flatten_nodes(nodes: list[LogseqNode]) -> list[LogseqNode]:
    """Depth-first flattening of a node tree."""
    flat: list[LogseqNode] = []
    for node in nodes:
        flat.append(node)
        if node.children:
            flat.extend(_flatten_nodes(node.children))
    return flat


def _normalize_backlink_key(token: str) -> str:
    """Normalize a wikilink title, tag, or block-ref string for the backlink registry."""
    stripped = token.strip()
    if not stripped:
        return ""
    try:
        return str(uuid.UUID(stripped))
    except ValueError:
        return stripped.lower()


def _append_backlink(registry: dict[str, list[str]], key: str, source_uuid: str) -> None:
    if key not in registry:
        registry[key] = []
    registry[key].append(source_uuid)
    logger.debug("backlink index: %s <- source=%s", key, source_uuid)


def _build_backlink_registry(pages: dict[str, LogseqPage]) -> dict[str, list[str]]:
    """Map normalized targets (page title lower or block UUID) to source node UUIDs."""
    registry: dict[str, list[str]] = {}
    for page in pages.values():
        for node in _flatten_nodes(page.root_nodes):
            for link in node.wikilinks:
                key = _normalize_backlink_key(link)
                if key:
                    _append_backlink(registry, key, node.uuid)
            for tag in node.tags:
                key = _normalize_backlink_key(tag)
                if key:
                    _append_backlink(registry, key, node.uuid)
            for block_ref in node.block_refs:
                key = _normalize_backlink_key(block_ref)
                if key:
                    _append_backlink(registry, key, node.uuid)
    logger.debug("backlink registry built: %s distinct targets", len(registry))
    return registry


def _parse_page_file_worker(path: Path) -> LogseqPage:
    """Parse a single markdown file in isolation (thread-safe)."""
    return StackMachineParser().parse_page_file(path)


class LogseqGraph(BaseModel):
    """Bulk-loaded Logseq vault: pages plus O(1) node lookup by synthetic UUID."""

    model_config = ConfigDict(strict=True, frozen=True)

    graph_path: Path
    pages: dict[str, LogseqPage]

    _node_registry: dict[str, LogseqNode] = PrivateAttr(default_factory=dict)
    _backlink_registry: dict[str, list[str]] = PrivateAttr(default_factory=dict)

    def __init__(
        self,
        graph_path: Path,
        pages: dict[str, LogseqPage],
        *,
        node_registry: dict[str, LogseqNode] | None = None,
        backlink_registry: dict[str, list[str]] | None = None,
    ) -> None:
        super().__init__(graph_path=graph_path, pages=pages)
        self._node_registry = dict(node_registry) if node_registry is not None else {}
        self._backlink_registry = (
            dict(backlink_registry) if backlink_registry is not None else {}
        )

    @classmethod
    def load_directory(cls, graph_path: Path) -> LogseqGraph:
        """Discover markdown under ``pages/`` and ``journals/``, parse concurrently, build indexes."""
        resolved = graph_path.expanduser().resolve()
        files = _discover_graph_files(resolved)
        pages: dict[str, LogseqPage] = {}
        node_registry: dict[str, LogseqNode] = {}

        if not files:
            logger.debug("LogseqGraph.load_directory: no markdown files under %s", resolved)
            return cls(
                graph_path=resolved,
                pages=pages,
                node_registry=node_registry,
                backlink_registry={},
            )

        max_workers = min(_DEFAULT_MAX_WORKERS, len(files))
        logger.debug(
            "LogseqGraph.load_directory: parsing %s files with max_workers=%s",
            len(files),
            max_workers,
        )

        path_page_pairs: list[tuple[Path, LogseqPage]] = []
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_to_path = {pool.submit(_parse_page_file_worker, p): p for p in files}
            for future in as_completed(future_to_path):
                source_path = future_to_path[future]
                page = future.result()
                path_page_pairs.append((source_path, page))

        path_page_pairs.sort(key=lambda item: str(item[0].resolve()))
        for _path, page in path_page_pairs:
            pages[page.title] = page
            for node in _flatten_nodes(page.root_nodes):
                node_registry[node.uuid] = node

        backlink_registry = _build_backlink_registry(pages)

        logger.debug(
            "LogseqGraph.load_directory: indexed %s pages, %s nodes",
            len(pages),
            len(node_registry),
        )
        return cls(
            graph_path=resolved,
            pages=pages,
            node_registry=node_registry,
            backlink_registry=backlink_registry,
        )

    def get_node_by_uuid(self, uuid: str) -> LogseqNode | None:
        """Return the node for ``uuid`` if present in the global registry."""
        return self._node_registry.get(uuid)

    def get_backlinks(self, target: str) -> list[LogseqNode]:
        """Return nodes that reference ``target`` via wikilinks, tags, or block refs."""
        key = _normalize_backlink_key(target)
        if not key:
            return []
        source_ids = self._backlink_registry.get(key, [])
        ordered_unique: list[str] = list(dict.fromkeys(source_ids))
        result: list[LogseqNode] = []
        for sid in ordered_unique:
            node = self._node_registry.get(sid)
            if node is not None:
                result.append(node)
        logger.debug("get_backlinks target=%s resolved=%s nodes", key, len(result))
        return result

    def _page_for_node(self, node: LogseqNode) -> LogseqPage | None:
        """Resolve the parsed page that owns ``node`` (same source file)."""
        if not node.source_path:
            return None
        node_path = Path(node.source_path).resolve()
        for page in self.pages.values():
            if page.source_path:
                if Path(page.source_path).resolve() == node_path:
                    return page
        return None

    def get_effective_properties(self, node_uuid: str) -> dict[str, Any]:
        """Merge page frontmatter with outline ancestors top-down; deeper blocks override."""
        node = self.get_node_by_uuid(node_uuid)
        if node is None:
            return {}
        merged: dict[str, Any] = {}
        page = self._page_for_node(node)
        if page is not None:
            merged.update(page.properties)
        for path_uuid in node.path:
            ancestor = self._node_registry.get(path_uuid)
            if ancestor is not None:
                merged = {**merged, **ancestor.properties}
        logger.debug(
            "get_effective_properties node_uuid=%s keys=%s",
            node_uuid,
            tuple(merged.keys()),
        )
        return merged

    def get_nodes_by_tag(self, tag: str) -> list[LogseqNode]:
        """Return all nodes whose ``tags`` contain ``tag``."""
        matches: list[LogseqNode] = []
        for node in self._node_registry.values():
            if tag in node.tags:
                matches.append(node)
        return matches

    def search_content(self, query: str) -> list[LogseqNode]:
        """Linear scan of ``clean_text`` for substring ``query``."""
        if not query:
            return []
        hits: list[LogseqNode] = []
        for node in self._node_registry.values():
            if query in node.clean_text:
                hits.append(node)
        return hits

    def resolve_relative_page_link(self, current_page_title: str, link_target: str) -> str | None:
        """Resolve a relative page title like Logseq OG: deepest namespace match wins."""
        target = link_target.strip()
        if not target:
            return None
        if target in self.pages:
            return target
        segments = [part for part in current_page_title.split("/") if part]
        for depth in range(len(segments), -1, -1):
            candidate = "/".join([*segments[:depth], target])
            if candidate in self.pages:
                return candidate
        return None

    def get_namespace_children(self, namespace_prefix: str) -> list[LogseqPage]:
        """Return direct child pages under ``namespace_prefix`` (one extra path segment only)."""
        prefix = namespace_prefix.strip().rstrip("/")
        if not prefix:
            return []
        needle = f"{prefix}/"
        children: list[LogseqPage] = []
        for title, page in self.pages.items():
            if not title.startswith(needle):
                continue
            remainder = title[len(needle) :]
            if remainder and "/" not in remainder:
                children.append(page)
        children.sort(key=lambda p: p.title)
        logger.debug(
            "get_namespace_children prefix=%s count=%s",
            prefix,
            len(children),
        )
        return children
