"""In-memory Logseq graph orchestration (no database)."""

from __future__ import annotations

import logging
import os
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, PrivateAttr

from logseq_matryca_parser.kinetic import _discover_graph_files
from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage
from logseq_matryca_parser.logos_parser import StackMachineParser

logger = logging.getLogger(__name__)

_DEFAULT_MAX_WORKERS = min(32, (os.cpu_count() or 1) + 4)


class GraphQuery:
    """Fluent, chainable filter pipeline over a fixed slice of ``LogseqNode`` instances."""

    def __init__(self, graph: LogseqGraph, nodes: list[LogseqNode]) -> None:
        self._graph = graph
        self._nodes: list[LogseqNode] = list(nodes)
        logger.debug(
            "GraphQuery init graph_path=%s seed_nodes=%s",
            self._graph.graph_path,
            len(self._nodes),
        )

    def has_tag(self, tag: str) -> Self:
        self._nodes = [n for n in self._nodes if tag in n.tags]
        logger.debug("GraphQuery.has_tag tag=%s remaining=%s", tag, len(self._nodes))
        return self

    def with_priority(self, priority: str) -> Self:
        self._nodes = [n for n in self._nodes if n.task_priority == priority]
        logger.debug("GraphQuery.with_priority priority=%s remaining=%s", priority, len(self._nodes))
        return self

    def under_parent(self, parent_uuid: str) -> Self:
        """Keep nodes whose ancestry chain (``path`` sans self) contains ``parent_uuid``."""
        self._nodes = [n for n in self._nodes if len(n.path) > 1 and parent_uuid in n.path[:-1]]
        logger.debug("GraphQuery.under_parent parent=%s remaining=%s", parent_uuid, len(self._nodes))
        return self

    def is_task_state(self, status: str) -> Self:
        self._nodes = [n for n in self._nodes if n.task_status == status]
        logger.debug("GraphQuery.is_task_state status=%s remaining=%s", status, len(self._nodes))
        return self

    def execute(self) -> list[LogseqNode]:
        return list(self._nodes)


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

    def get_node_by_embed_ref(self, block_ref: str) -> LogseqNode | None:
        """Resolve a Logseq block id: synthetic registry UUID, ``source_uuid``, or ``properties['id']``."""
        stripped = block_ref.strip()
        if not stripped:
            return None
        direct = self.get_node_by_uuid(stripped)
        if direct is not None:
            return direct
        for node in self._node_registry.values():
            if node.source_uuid == stripped:
                return node
            if node.properties.get("id") == stripped:
                return node
        logger.debug("get_node_by_embed_ref: no node for ref=%s", stripped)
        return None

    def query(self) -> GraphQuery:
        """Return a fluent query over all nodes registered in the graph."""
        return GraphQuery(self, list(self._node_registry.values()))

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
        """Resolve a relative page title like Logseq OG: nested namespace shadowing beats global."""
        target = link_target.strip()
        if not target:
            return None
        segments = [part for part in current_page_title.split("/") if part]
        for prefix_len in range(len(segments), 0, -1):
            candidate = "/".join([*segments[:prefix_len], target])
            if candidate in self.pages:
                logger.debug(
                    "resolve_relative_page_link: contextual hit current=%s target=%s -> %s",
                    current_page_title,
                    link_target,
                    candidate,
                )
                return candidate
        if target in self.pages:
            logger.debug(
                "resolve_relative_page_link: global fallback current=%s target=%s",
                current_page_title,
                link_target,
            )
            return target
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

    def _resolved_path_is_tracked_markdown(self, path: Path) -> bool:
        """True when ``path`` is a ``.md`` file under this graph's ``pages/`` or ``journals/``."""
        resolved = path.resolve()
        if resolved.suffix.lower() != ".md":
            return False
        graph_root = self.graph_path.resolve()
        for folder in ("pages", "journals"):
            root = graph_root / folder
            if not root.is_dir():
                continue
            try:
                resolved.relative_to(root)
                return True
            except ValueError:
                continue
        return False

    def _page_title_for_source_path(self, resolved_file: Path) -> str | None:
        """Return the ``pages`` dict key for the page loaded from ``resolved_file``, if any."""
        for title, page in self.pages.items():
            sp = page.source_path
            if sp and Path(sp).resolve() == resolved_file:
                return title
        return None

    def _purge_stale_page_uuids(self, stale: set[str]) -> None:
        """Remove stale node UUIDs from the node registry and scrub backlink source lists."""
        for uid in stale:
            self._node_registry.pop(uid, None)
        dead_keys: list[str] = []
        for key, sources in self._backlink_registry.items():
            filtered = [s for s in sources if s not in stale]
            if filtered:
                self._backlink_registry[key] = filtered
            else:
                dead_keys.append(key)
        for key in dead_keys:
            del self._backlink_registry[key]
        logger.debug(
            "Stack-Machine incremental purge: stale_uuids=%s dead_backlink_keys=%s",
            len(stale),
            len(dead_keys),
        )

    def _register_page_nodes(self, page: LogseqPage) -> None:
        for node in _flatten_nodes(page.root_nodes):
            self._node_registry[node.uuid] = node

    def _append_page_backlinks(self, page: LogseqPage) -> None:
        for node in _flatten_nodes(page.root_nodes):
            for link in node.wikilinks:
                key = _normalize_backlink_key(link)
                if key:
                    _append_backlink(self._backlink_registry, key, node.uuid)
            for tag in node.tags:
                key = _normalize_backlink_key(tag)
                if key:
                    _append_backlink(self._backlink_registry, key, node.uuid)
            for block_ref in node.block_refs:
                key = _normalize_backlink_key(block_ref)
                if key:
                    _append_backlink(self._backlink_registry, key, node.uuid)

    def invalidate_and_reload_page(self, file_path: Path) -> None:
        """Re-parse a single file, purge its old nodes/backlinks, and merge fresh indexes."""
        resolved = Path(file_path).expanduser().resolve()
        if not self._resolved_path_is_tracked_markdown(resolved):
            logger.debug("invalidate_and_reload_page: skip non-tracked path=%s", resolved)
            return
        fresh = StackMachineParser().parse_page_file(resolved)
        old_title = self._page_title_for_source_path(resolved)
        stale: set[str] = set()
        if old_title is not None:
            old_page = self.pages[old_title]
            stale = {n.uuid for n in _flatten_nodes(old_page.root_nodes)}
            self._purge_stale_page_uuids(stale)
        new_pages = dict(self.pages)
        if old_title is not None:
            del new_pages[old_title]
        new_pages[fresh.title] = fresh
        object.__setattr__(self, "pages", new_pages)
        self._register_page_nodes(fresh)
        self._append_page_backlinks(fresh)
        logger.debug(
            "Stack-Machine incremental re-hydrate: path=%s title=%s nodes=%s",
            resolved,
            fresh.title,
            len(list(_flatten_nodes(fresh.root_nodes))),
        )

    def start_watching(self, callback: Callable[[Path], None] | None = None) -> LogseqGraphWatcher:
        """Start a recursive filesystem observer over the graph (requires optional ``watchdog``)."""
        return LogseqGraphWatcher(self, callback).start()


class LogseqGraphWatcher:
    """Background ``watchdog`` observer that incremental-reloads touched Markdown pages."""

    def __init__(self, graph: LogseqGraph, callback: Callable[[Path], None] | None = None) -> None:
        self._graph = graph
        self._callback = callback
        self._observer: Any = None

    def start(self) -> LogseqGraphWatcher:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer

        graph = self._graph
        user_callback = self._callback

        def _route_event(event: Any) -> None:
            if getattr(event, "is_directory", False):
                return
            path = Path(str(event.src_path))
            if not graph._resolved_path_is_tracked_markdown(path):
                logger.debug("Stack-Machine watcher: ignore path=%s", path)
                return
            logger.debug("Stack-Machine watcher: invalidate path=%s", path)
            graph.invalidate_and_reload_page(path)
            if user_callback is not None:
                user_callback(path)

        class _MarkdownGraphHandler(FileSystemEventHandler):
            def on_modified(self, event: Any) -> None:
                _route_event(event)

            def on_created(self, event: Any) -> None:
                _route_event(event)

        observer = Observer()
        observer.schedule(
            _MarkdownGraphHandler(),
            str(graph.graph_path.resolve()),
            recursive=True,
        )
        observer.start()
        self._observer = observer
        logger.debug("Stack-Machine watcher: started on graph_path=%s", graph.graph_path)
        return self

    def stop(self) -> None:
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
            logger.debug("Stack-Machine watcher: stopped")
