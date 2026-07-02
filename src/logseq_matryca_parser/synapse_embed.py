"""SYNAPSE embed expansion strategies (OCP slice for block and page embeds)."""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from logseq_matryca_parser.logos_core import LogseqNode

if TYPE_CHECKING:
    from logseq_matryca_parser.graph import LogseqGraph

logger = logging.getLogger(__name__)

BLOCK_EMBED_PATTERN = re.compile(
    r"\{\{\s*embed\s+\(\((?P<uuid>[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\)\)\s*\}\}",
    re.IGNORECASE,
)
PAGE_EMBED_PATTERN = re.compile(r"\{\{\s*embed\s+\[\[(?P<title>[^\]]+)\]\]\s*\}\}")


def _flatten_nodes_for_export(nodes: list[LogseqNode]) -> list[LogseqNode]:
    flat: list[LogseqNode] = []
    for node in nodes:
        flat.append(node)
        if node.children:
            flat.extend(_flatten_nodes_for_export(node.children))
    return flat


@dataclass(frozen=True)
class EmbedMatch:
    """A single embed token match inside raw block content."""

    start: int
    end: int
    kind: str


class EmbedExpander(ABC):
    """Strategy for resolving one embed kind to replacement text."""

    kind: str

    @abstractmethod
    def find_earliest(self, text: str) -> EmbedMatch | None:
        """Return the leftmost match for this strategy, if any."""

    @abstractmethod
    def expand(
        self,
        text: str,
        match: EmbedMatch,
        graph: LogseqGraph,
        visited_uuids: set[str],
        embed_page_chain: frozenset[str],
        expand_impl: Callable[[str, LogseqGraph, set[str], frozenset[str]], str],
    ) -> str:
        """Return replacement text for ``match`` within ``text``."""


class BlockEmbedExpander(EmbedExpander):
    """Expand ``{{embed ((uuid))}}`` using the node registry."""

    kind = "block"

    def find_earliest(self, text: str) -> EmbedMatch | None:
        found = BLOCK_EMBED_PATTERN.search(text)
        if found is None:
            return None
        return EmbedMatch(start=found.start(), end=found.end(), kind=self.kind)

    def expand(
        self,
        text: str,
        match: EmbedMatch,
        graph: LogseqGraph,
        visited_uuids: set[str],
        embed_page_chain: frozenset[str],
        expand_impl: Callable[[str, LogseqGraph, set[str], frozenset[str]], str],
    ) -> str:
        block_match = BLOCK_EMBED_PATTERN.search(text, match.start)
        if block_match is None:
            return text
        uid = block_match.group("uuid")
        if uid in visited_uuids:
            logger.debug("Stack-Machine embed: cyclic block uuid=%s", uid)
            replacement = ""
        else:
            target = graph.get_node_by_embed_ref(uid)
            if target is None:
                logger.debug("Stack-Machine embed: unresolved block uuid=%s", uid)
                replacement = ""
            else:
                next_seen = set(visited_uuids)
                next_seen.add(uid)
                replacement = expand_impl(target.content, graph, next_seen, embed_page_chain)
        return text[: block_match.start()] + replacement + text[block_match.end() :]


class PageEmbedExpander(EmbedExpander):
    """Expand ``{{embed [[Page]]}}`` by concatenating expanded page blocks."""

    kind = "page"

    def find_earliest(self, text: str) -> EmbedMatch | None:
        found = PAGE_EMBED_PATTERN.search(text)
        if found is None:
            return None
        return EmbedMatch(start=found.start(), end=found.end(), kind=self.kind)

    def expand(
        self,
        text: str,
        match: EmbedMatch,
        graph: LogseqGraph,
        visited_uuids: set[str],
        embed_page_chain: frozenset[str],
        expand_impl: Callable[[str, LogseqGraph, set[str], frozenset[str]], str],
    ) -> str:
        page_match = PAGE_EMBED_PATTERN.search(text, match.start)
        if page_match is None:
            return text
        title = page_match.group("title").strip()
        page = graph.get_page(title)
        canonical_title = page.title if page is not None else title
        if canonical_title in embed_page_chain:
            logger.debug("Stack-Machine embed: cyclic page title=%s", canonical_title)
            replacement = ""
        elif page is None:
            logger.debug("Stack-Machine embed: unknown page title=%s", title)
            replacement = ""
        else:
            next_chain = embed_page_chain | frozenset({canonical_title})
            shared_blocks = set(visited_uuids)
            pieces: list[str] = []
            for node in _flatten_nodes_for_export(page.root_nodes):
                frag = expand_impl(node.content, graph, shared_blocks, next_chain)
                stripped = frag.strip()
                if stripped:
                    pieces.append(stripped)
            replacement = "\n".join(pieces)
        return text[: page_match.start()] + replacement + text[page_match.end() :]


_DEFAULT_EXPANDERS: tuple[EmbedExpander, ...] = (BlockEmbedExpander(), PageEmbedExpander())


def expand_macros_and_embeds_impl(
    text: str,
    graph: LogseqGraph,
    visited_uuids: set[str],
    embed_page_chain: frozenset[str],
    *,
    expanders: tuple[EmbedExpander, ...] = _DEFAULT_EXPANDERS,
) -> str:
    """Shared worker: ``visited_uuids`` breaks block cycles; ``embed_page_chain`` breaks page cycles."""
    result = text
    while True:
        candidates: list[tuple[int, EmbedExpander, EmbedMatch]] = []
        for expander in expanders:
            found = expander.find_earliest(result)
            if found is not None:
                candidates.append((found.start, expander, found))
        if not candidates:
            break
        _, chosen, match = min(candidates, key=lambda item: item[0])
        result = chosen.expand(
            result,
            match,
            graph,
            visited_uuids,
            embed_page_chain,
            expand_macros_and_embeds_impl,
        )
    return result
