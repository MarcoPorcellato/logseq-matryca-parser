"""In-memory Logseq graph orchestration (no database)."""

from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

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


def _parse_page_file_worker(path: Path) -> LogseqPage:
    """Parse a single markdown file in isolation (thread-safe)."""
    return StackMachineParser().parse_page_file(path)


class LogseqGraph(BaseModel):
    """Bulk-loaded Logseq vault: pages plus O(1) node lookup by synthetic UUID."""

    model_config = ConfigDict(strict=True, frozen=True)

    graph_path: Path
    pages: dict[str, LogseqPage]

    _node_registry: dict[str, LogseqNode] = PrivateAttr(default_factory=dict)

    def __init__(
        self,
        graph_path: Path,
        pages: dict[str, LogseqPage],
        *,
        node_registry: dict[str, LogseqNode] | None = None,
    ) -> None:
        super().__init__(graph_path=graph_path, pages=pages)
        self._node_registry = dict(node_registry) if node_registry is not None else {}

    @classmethod
    def load_directory(cls, graph_path: Path) -> LogseqGraph:
        """Discover markdown under ``pages/`` and ``journals/``, parse concurrently, build indexes."""
        resolved = graph_path.expanduser().resolve()
        files = _discover_graph_files(resolved)
        pages: dict[str, LogseqPage] = {}
        node_registry: dict[str, LogseqNode] = {}

        if not files:
            logger.debug("LogseqGraph.load_directory: no markdown files under %s", resolved)
            return cls(graph_path=resolved, pages=pages, node_registry=node_registry)

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

        logger.debug(
            "LogseqGraph.load_directory: indexed %s pages, %s nodes",
            len(pages),
            len(node_registry),
        )
        return cls(graph_path=resolved, pages=pages, node_registry=node_registry)

    def get_node_by_uuid(self, uuid: str) -> LogseqNode | None:
        """Return the node for ``uuid`` if present in the global registry."""
        return self._node_registry.get(uuid)

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
