"""In-memory Logseq graph orchestration (no database)."""

from __future__ import annotations

import logging
import os
import re
import threading
import uuid
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, PrivateAttr

from logseq_matryca_parser.exceptions import BlockReferenceError
from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage
from logseq_matryca_parser.logos_parser import StackMachineParser
from logseq_matryca_parser.logseq_markdown import _normalize_logseq_ref_token
from logseq_matryca_parser.logseq_paths import discover_graph_files, is_excluded_graph_path

logger = logging.getLogger(__name__)

_DEFAULT_MAX_WORKERS = min(32, (os.cpu_count() or 1) + 4)
_WATCHER_DEBOUNCE_SECONDS = 0.5
_WATCHER_IGNORE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\.swp$"),
    re.compile(r"~$"),
    re.compile(r"\.tmp$"),
    re.compile(r"^\.DS_Store$"),
)


def _is_ignored_watcher_path(path: Path) -> bool:
    """Return True for editor swap/temp files that must not trigger graph reloads."""
    name = path.name
    return any(pattern.search(name) for pattern in _WATCHER_IGNORE_PATTERNS)


class _DebouncedGraphEventRouter:
    """Coalesce rapid filesystem events per path before invoking the reload callback."""

    def __init__(
        self,
        route: Callable[[Path], None],
        *,
        debounce_seconds: float = _WATCHER_DEBOUNCE_SECONDS,
    ) -> None:
        self._route = route
        self._debounce_seconds = debounce_seconds
        self._timers: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    def schedule(self, path: Path) -> None:
        resolved = path.expanduser().resolve()
        if self._debounce_seconds <= 0:
            self._route(resolved)
            return
        key = str(resolved)
        with self._lock:
            existing = self._timers.pop(key, None)
            if existing is not None:
                existing.cancel()
            timer = threading.Timer(self._debounce_seconds, self._fire, args=(key, resolved))
            self._timers[key] = timer
            timer.daemon = True
            timer.start()

    def _fire(self, key: str, path: Path) -> None:
        with self._lock:
            self._timers.pop(key, None)
        self._route(path)

    def cancel_all(self) -> None:
        with self._lock:
            for timer in self._timers.values():
                timer.cancel()
            self._timers.clear()


def _normalize_tag_query(tag: str) -> str:
    """Normalize a tag filter for case-insensitive ``#``-optional matching."""
    stripped = tag.strip()
    if stripped.startswith("#"):
        stripped = stripped[1:]
    return stripped.lower()


def _normalize_relative_link_target(current_page_title: str, link_target: str) -> str:
    """Resolve Logseq-style ``./`` and ``../`` segments against ``current_page_title``."""
    target = link_target.strip()
    segments = [part for part in current_page_title.split("/") if part]
    if target.startswith("./"):
        remainder = target[2:].lstrip("/")
        if not remainder:
            return current_page_title
        parent_segments = segments[:-1]
        return "/".join([*parent_segments, remainder]) if parent_segments else remainder
    if not target.startswith(("../", "..")) and target not in {".", ".."}:
        return target
    for part in target.split("/"):
        if part in {"", "."}:
            continue
        if part == "..":
            if segments:
                segments.pop()
            continue
        segments.append(part)
    return "/".join(segments)


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
        needle = _normalize_tag_query(tag)
        self._nodes = [
            n for n in self._nodes if any(_normalize_tag_query(t) == needle for t in n.tags)
        ]
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


def iter_canonical_pages_from_dict(pages: dict[str, LogseqPage]) -> Iterator[LogseqPage]:
    """Yield each physical ``LogseqPage`` once (dedupe alias keys in ``pages``)."""
    seen_page_ids: set[int] = set()
    for page in pages.values():
        page_id = id(page)
        if page_id in seen_page_ids:
            continue
        seen_page_ids.add(page_id)
        yield page


def _resolve_page_by_title(pages: dict[str, LogseqPage], title: str) -> LogseqPage | None:
    """Resolve a page title with case-insensitive fallback (pre-``lower_title_map``)."""
    stripped = title.strip()
    if not stripped:
        return None
    direct = pages.get(stripped)
    if direct is not None:
        return direct
    lower = stripped.lower()
    for page in iter_canonical_pages_from_dict(pages):
        if page.title.lower() == lower:
            return page
    return None


def _wikilink_backlink_keys(pages: dict[str, LogseqPage], link: str) -> list[str]:
    """Normalized backlink index keys for a wikilink (literal + canonical title + aliases)."""
    keys: list[str] = []
    seen: set[str] = set()
    primary = _normalize_backlink_key(link)
    if primary:
        keys.append(primary)
        seen.add(primary)
    page = _resolve_page_by_title(pages, link)
    if page is not None:
        for candidate in (page.title, *_collect_page_alias_tokens(page.properties)):
            key = _normalize_backlink_key(candidate)
            if key and key not in seen:
                keys.append(key)
                seen.add(key)
    return keys


def _build_node_registry_from_pages(pages: dict[str, LogseqPage]) -> dict[str, LogseqNode]:
    """Build the global node registry from indexed pages only (no title-collision ghosts)."""
    registry: dict[str, LogseqNode] = {}
    for page in iter_canonical_pages_from_dict(pages):
        for node in _flatten_nodes(page.root_nodes):
            registry[node.uuid] = node
    return registry


def _normalize_page_aliases(raw: Any) -> list[str]:
    """Flatten one ``alias`` / ``aliases`` property value into deduped page title tokens."""
    if isinstance(raw, str):
        segments = [part.strip() for part in raw.split(",")]
    elif isinstance(raw, (list, tuple, set)):
        segments = [str(item) for item in raw]
    else:
        return []
    result: list[str] = []
    seen: set[str] = set()
    for segment in segments:
        token = _normalize_logseq_ref_token(segment)
        if token and token not in seen:
            seen.add(token)
            result.append(token)
    return result


def _collect_page_alias_tokens(properties: dict[str, Any]) -> list[str]:
    """Read ``alias`` and ``aliases`` page properties in Logseq order."""
    tokens: list[str] = []
    seen: set[str] = set()
    for key in ("alias", "aliases"):
        if key not in properties:
            continue
        for token in _normalize_page_aliases(properties[key]):
            if token not in seen:
                seen.add(token)
                tokens.append(token)
    return tokens


def _apply_title_override(page: LogseqPage) -> tuple[LogseqPage, str | None]:
    """Return an updated page when frontmatter ``title::`` overrides the filename title."""
    raw = page.properties.get("title")
    if not isinstance(raw, str):
        return page, None
    custom = raw.strip()
    if not custom or custom == page.title:
        return page, None
    return page.model_copy(update={"title": custom}), page.title


def _enrich_pages_index(pages: dict[str, LogseqPage]) -> None:
    """Apply ``title::`` overrides and inject alias keys before backlink indexing."""
    snapshot = sorted(pages.items(), key=lambda item: item[1].source_path or "")
    seen_paths: set[str] = set()

    for old_key, page in snapshot:
        source_path = page.source_path
        if source_path:
            if source_path in seen_paths:
                continue
            seen_paths.add(source_path)

        updated, replaced_title = _apply_title_override(page)
        if replaced_title is None:
            continue

        new_key = updated.title
        existing = pages.get(new_key)
        if existing is not None and existing.source_path != updated.source_path:
            logger.debug(
                "pages index: title override skipped, %r already maps to another page",
                new_key,
            )
            continue

        if old_key in pages and pages[old_key] is page:
            del pages[old_key]
        pages[new_key] = updated

    canonical = sorted(
        ((key, page) for key, page in pages.items() if key == page.title),
        key=lambda item: item[1].source_path or "",
    )
    for _canonical_key, page in canonical:
        for alias in _collect_page_alias_tokens(page.properties):
            if alias == page.title:
                continue
            if alias in pages and pages[alias] is not page:
                logger.debug("pages index: alias %r collision, remapping", alias)
            pages[alias] = page


def _remove_page_keys_for_source_path(
    pages: dict[str, LogseqPage],
    resolved_file: Path,
) -> LogseqPage | None:
    """Drop every ``pages`` key that references ``resolved_file``; return one removed page."""
    removed_page: LogseqPage | None = None
    keys_to_drop = [
        key
        for key, page in pages.items()
        if page.source_path and Path(page.source_path).resolve() == resolved_file
    ]
    for key in keys_to_drop:
        if removed_page is None:
            removed_page = pages[key]
        del pages[key]
    return removed_page


def _page_for_source_path(pages: dict[str, LogseqPage], resolved_file: Path) -> LogseqPage | None:
    """Return the unique page loaded from ``resolved_file`` after enrichment."""
    found: LogseqPage | None = None
    seen_ids: set[int] = set()
    for page in pages.values():
        pid = id(page)
        if pid in seen_ids:
            continue
        if not page.source_path or Path(page.source_path).resolve() != resolved_file:
            continue
        seen_ids.add(pid)
        found = page
    return found


def _build_lower_title_map(pages: dict[str, LogseqPage]) -> dict[str, str]:
    """Map lowercased page titles to canonical ``page.title`` (Logseq case-insensitive routing)."""
    title_map: dict[str, str] = {}
    seen_page_ids: set[int] = set()
    for page in pages.values():
        page_id = id(page)
        if page_id in seen_page_ids:
            continue
        seen_page_ids.add(page_id)
        canonical = page.title
        lower = canonical.lower()
        if lower in title_map and title_map[lower] != canonical:
            logger.debug(
                "lower title map: collision %r vs %r, keeping %r",
                title_map[lower],
                canonical,
                title_map[lower],
            )
            continue
        title_map[lower] = canonical
    logger.debug("lower title map built: %s entries", len(title_map))
    return title_map


def _build_backlink_registry(pages: dict[str, LogseqPage]) -> dict[str, list[str]]:
    """Map normalized targets (page title lower or block UUID) to source node UUIDs."""
    registry: dict[str, list[str]] = {}
    for page in iter_canonical_pages_from_dict(pages):
        for node in _flatten_nodes(page.root_nodes):
            for link in node.wikilinks:
                for key in _wikilink_backlink_keys(pages, link):
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

    model_config = ConfigDict(strict=True, validate_assignment=True)

    graph_path: Path
    pages: dict[str, LogseqPage]

    _node_registry: dict[str, LogseqNode] = PrivateAttr(default_factory=dict)
    _backlink_registry: dict[str, list[str]] = PrivateAttr(default_factory=dict)
    _lower_title_map: dict[str, str] = PrivateAttr(default_factory=dict)

    def __init__(
        self,
        graph_path: Path,
        pages: dict[str, LogseqPage],
        *,
        node_registry: dict[str, LogseqNode] | None = None,
        backlink_registry: dict[str, list[str]] | None = None,
        lower_title_map: dict[str, str] | None = None,
    ) -> None:
        super().__init__(graph_path=graph_path, pages=pages)
        self._node_registry = dict(node_registry) if node_registry is not None else {}
        self._backlink_registry = (
            dict(backlink_registry) if backlink_registry is not None else {}
        )
        self._lower_title_map = (
            dict(lower_title_map)
            if lower_title_map is not None
            else _build_lower_title_map(pages)
        )

    @classmethod
    def load_directory(cls, graph_path: Path, *, strict_refs: bool = False) -> LogseqGraph:
        """Discover markdown under ``pages/`` and ``journals/``, parse concurrently, build indexes.

        When ``strict_refs`` is True, raise :class:`BlockReferenceError` if any block reference
        in the vault cannot be resolved against the loaded node registry (cross-page validation).
        """
        resolved = graph_path.expanduser().resolve()
        files = discover_graph_files(resolved)
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

        _enrich_pages_index(pages)
        node_registry = _build_node_registry_from_pages(pages)
        backlink_registry = _build_backlink_registry(pages)
        lower_title_map = _build_lower_title_map(pages)

        logger.debug(
            "LogseqGraph.load_directory: indexed %s pages, %s nodes",
            len(pages),
            len(node_registry),
        )
        graph = cls(
            graph_path=resolved,
            pages=pages,
            node_registry=node_registry,
            backlink_registry=backlink_registry,
            lower_title_map=lower_title_map,
        )
        if strict_refs:
            graph.raise_if_broken_references()
        return graph

    @property
    def tab_size(self) -> int:
        """Default outline tab width in spaces (per-page ``LogseqPage.tab_size`` may differ)."""
        return 2

    def tab_size_for_node(self, node: LogseqNode) -> int:
        """Return the detected tab width for the page that owns ``node``."""
        page = self._page_for_node(node)
        return page.tab_size if page is not None else self.tab_size

    def get_node_by_uuid(self, uuid: str) -> LogseqNode | None:
        """Return the node for ``uuid`` if present in the global registry."""
        return self._node_registry.get(uuid)

    def iter_canonical_pages(self) -> Iterator[LogseqPage]:
        """Yield each physical page once (dedupe ``pages`` alias keys)."""
        yield from iter_canonical_pages_from_dict(self.pages)

    def _iter_attached_nodes(self) -> Iterator[LogseqNode]:
        """Yield registry nodes that still belong to an indexed page (no collision ghosts)."""
        for node in self._node_registry.values():
            if self._page_for_node(node) is not None:
                yield node

    def get_broken_references(self) -> list[LogseqNode]:
        """Return nodes whose ``block_refs`` point at UUIDs missing from the node registry."""
        broken: list[LogseqNode] = []
        for node in self._iter_attached_nodes():
            if not node.block_refs:
                continue
            for ref in node.block_refs:
                if self.get_node_by_embed_ref(ref) is None:
                    broken.append(node)
                    logger.debug(
                        "get_broken_references origin=%s missing_ref=%s",
                        node.uuid,
                        ref,
                    )
                    break
        return broken

    def raise_if_broken_references(self) -> None:
        """Raise :class:`BlockReferenceError` when any vault block reference is unresolved."""
        broken = self.get_broken_references()
        if not broken:
            return
        node = broken[0]
        missing_ref = next(
            ref for ref in node.block_refs if self.get_node_by_embed_ref(ref) is None
        )
        raise BlockReferenceError(
            f"Unresolved block reference (({missing_ref})) on node {node.uuid}"
        )

    def page_for_node(self, node: LogseqNode) -> LogseqPage | None:
        """Return the indexed page that owns ``node`` (public API for adapters)."""
        return self._page_for_node(node)

    def get_node_by_embed_ref(self, block_ref: str) -> LogseqNode | None:
        """Resolve a Logseq block id: synthetic registry UUID, ``source_uuid``, or ``properties['id']``."""
        stripped = block_ref.strip()
        if not stripped:
            return None
        direct = self.get_node_by_uuid(stripped)
        if direct is not None:
            return direct
        try:
            canonical_uuid = str(uuid.UUID(stripped))
        except ValueError:
            canonical_uuid = None
        if canonical_uuid is not None:
            by_canonical = self.get_node_by_uuid(canonical_uuid)
            if by_canonical is not None:
                return by_canonical
        for node in self._node_registry.values():
            if node.source_uuid == stripped:
                return node
            if node.properties.get("id") == stripped:
                return node
            if canonical_uuid is not None:
                try:
                    if node.source_uuid and str(uuid.UUID(node.source_uuid)) == canonical_uuid:
                        return node
                except ValueError:
                    pass
                prop_id = node.properties.get("id")
                if isinstance(prop_id, str):
                    try:
                        if str(uuid.UUID(prop_id)) == canonical_uuid:
                            return node
                    except ValueError:
                        pass
        logger.debug("get_node_by_embed_ref: no node for ref=%s", stripped)
        return None

    def query(self) -> GraphQuery:
        """Return a fluent query over all nodes registered in the graph."""
        return GraphQuery(self, list(self._iter_attached_nodes()))

    def get_page(self, title: str) -> LogseqPage | None:
        """Return a page by title, using case-insensitive routing when needed."""
        stripped = title.strip()
        if not stripped:
            return None
        direct = self.pages.get(stripped)
        if direct is not None:
            return direct
        canonical = self._lower_title_map.get(stripped.lower())
        if canonical is None:
            return None
        return self.pages.get(canonical)

    def get_backlinks(self, target: str) -> list[LogseqNode]:
        """Return nodes that reference ``target`` via wikilinks, tags, or block refs.

        Page-title targets are matched case-insensitively (Datomic / Logseq parity).
        """
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
        return _page_for_source_path(self.pages, Path(node.source_path).resolve())

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
        """Return all nodes whose ``tags`` contain ``tag`` (case-insensitive, ``#`` optional)."""
        needle = _normalize_tag_query(tag)
        matches: list[LogseqNode] = []
        for node in self._iter_attached_nodes():
            if any(_normalize_tag_query(t) == needle for t in node.tags):
                matches.append(node)
        return matches

    def search_content(self, query: str) -> list[LogseqNode]:
        """Linear scan of ``clean_text`` for substring ``query`` (case-insensitive)."""
        if not query:
            return []
        needle = query.casefold()
        hits: list[LogseqNode] = []
        for node in self._iter_attached_nodes():
            if needle in node.clean_text.casefold():
                hits.append(node)
        return hits

    def resolve_relative_page_link(self, current_page_title: str, link_target: str) -> str | None:
        """Resolve a relative page title like Logseq OG: nested namespace shadowing beats global."""
        target = _normalize_relative_link_target(current_page_title, link_target.strip())
        if not target:
            return None
        segments = [part for part in current_page_title.split("/") if part]
        for prefix_len in range(len(segments), 0, -1):
            candidate = "/".join([*segments[:prefix_len], target])
            page = self.get_page(candidate)
            if page is not None:
                logger.debug(
                    "resolve_relative_page_link: contextual hit current=%s target=%s -> %s",
                    current_page_title,
                    link_target,
                    page.title,
                )
                return page.title
        page = self.get_page(target)
        if page is not None:
            logger.debug(
                "resolve_relative_page_link: global fallback current=%s target=%s",
                current_page_title,
                link_target,
            )
            return page.title
        return None

    def get_namespace_children(self, namespace_prefix: str) -> list[LogseqPage]:
        """Return direct child pages under ``namespace_prefix`` (one extra path segment only)."""
        prefix = namespace_prefix.strip().rstrip("/")
        if not prefix:
            return []
        prefix_lower = prefix.lower()
        needle_lower = f"{prefix_lower}/"
        children: list[LogseqPage] = []
        for page in self.iter_canonical_pages():
            title = page.title
            title_lower = title.lower()
            if title_lower == prefix_lower:
                continue
            if not title_lower.startswith(needle_lower):
                continue
            remainder = title_lower[len(needle_lower) :]
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
        if is_excluded_graph_path(resolved):
            return False
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
        """Return the canonical page title for ``resolved_file``, if indexed."""
        page = _page_for_source_path(self.pages, resolved_file)
        return page.title if page is not None else None

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
                for key in _wikilink_backlink_keys(self.pages, link):
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
        new_pages = dict(self.pages)
        old_page = _remove_page_keys_for_source_path(new_pages, resolved)
        stale: set[str] = set()
        if old_page is not None:
            stale = {n.uuid for n in _flatten_nodes(old_page.root_nodes)}
            self._purge_stale_page_uuids(stale)
        if not resolved.exists():
            self.pages = new_pages
            self._lower_title_map = _build_lower_title_map(new_pages)
            logger.debug("invalidate_and_reload_page: purged deleted path=%s", resolved)
            return
        fresh = StackMachineParser().parse_page_file(resolved)
        new_pages[fresh.title] = fresh
        _enrich_pages_index(new_pages)
        enriched = _page_for_source_path(new_pages, resolved) or fresh
        self.pages = new_pages
        self._lower_title_map = _build_lower_title_map(new_pages)
        self._register_page_nodes(enriched)
        self._append_page_backlinks(enriched)
        logger.debug(
            "Stack-Machine incremental re-hydrate: path=%s title=%s nodes=%s",
            resolved,
            enriched.title,
            len(list(_flatten_nodes(enriched.root_nodes))),
        )

    def start_watching(
        self,
        callback: Callable[[Path], None] | None = None,
        *,
        debounce_seconds: float = _WATCHER_DEBOUNCE_SECONDS,
    ) -> LogseqGraphWatcher:
        """Start a recursive filesystem observer over the graph (requires optional ``watchdog``)."""
        return LogseqGraphWatcher(self, callback, debounce_seconds=debounce_seconds).start()


class LogseqGraphWatcher:
    """Background ``watchdog`` observer that incremental-reloads touched Markdown pages."""

    def __init__(
        self,
        graph: LogseqGraph,
        callback: Callable[[Path], None] | None = None,
        *,
        debounce_seconds: float = _WATCHER_DEBOUNCE_SECONDS,
    ) -> None:
        self._graph = graph
        self._callback = callback
        self._debounce_seconds = debounce_seconds
        self._observer: Any = None
        self._debouncer: _DebouncedGraphEventRouter | None = None

    def start(self) -> LogseqGraphWatcher:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer

        graph = self._graph
        user_callback = self._callback

        def _route_event(path: Path) -> None:
            if not graph._resolved_path_is_tracked_markdown(path):
                logger.debug("Stack-Machine watcher: ignore path=%s", path)
                return
            logger.debug("Stack-Machine watcher: invalidate path=%s", path)
            graph.invalidate_and_reload_page(path)
            if user_callback is not None:
                user_callback(path)

        debouncer = _DebouncedGraphEventRouter(
            _route_event,
            debounce_seconds=self._debounce_seconds,
        )
        self._debouncer = debouncer

        def _enqueue_event(event: Any) -> None:
            if getattr(event, "is_directory", False):
                return
            path = Path(str(event.src_path))
            if _is_ignored_watcher_path(path):
                logger.debug("Stack-Machine watcher: ignore temp path=%s", path)
                return
            debouncer.schedule(path)

        class _MarkdownGraphHandler(FileSystemEventHandler):
            def on_modified(self, event: Any) -> None:
                _enqueue_event(event)

            def on_created(self, event: Any) -> None:
                _enqueue_event(event)

            def on_deleted(self, event: Any) -> None:
                _enqueue_event(event)

            def on_moved(self, event: Any) -> None:
                if getattr(event, "is_directory", False):
                    return
                src = getattr(event, "src_path", None)
                dest = getattr(event, "dest_path", None)
                if src is not None:
                    src_path = Path(str(src))
                    if not _is_ignored_watcher_path(src_path):
                        debouncer.schedule(src_path)
                if dest is not None:
                    dest_path = Path(str(dest))
                    if not _is_ignored_watcher_path(dest_path):
                        debouncer.schedule(dest_path)

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
        if self._debouncer is not None:
            self._debouncer.cancel_all()
            self._debouncer = None
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
            logger.debug("Stack-Machine watcher: stopped")
