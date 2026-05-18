"""FORGE exporters implemented with AST visitors."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from typing import Any

from .logos_core import ASTVisitor, LogseqNode, LogseqPage
from .logos_parser import LOGSEQ_PATTERNS

logger = logging.getLogger(__name__)

EmbedResolver = Callable[[str], tuple[str, str] | None]
"""Maps a Logseq block id string to (Obsidian page title, anchor without leading ^)."""


def _flatten_nodes_preorder(nodes: list[LogseqNode]) -> list[LogseqNode]:
    flat: list[LogseqNode] = []
    for node in nodes:
        flat.append(node)
        if node.children:
            flat.extend(_flatten_nodes_preorder(node.children))
    return flat


def _node_identity_keys(node: LogseqNode) -> set[str]:
    keys: set[str] = {node.uuid.lower()}
    if node.source_uuid:
        keys.add(node.source_uuid.lower())
    raw_id = node.properties.get("id")
    if isinstance(raw_id, str) and len(raw_id) == 36:
        keys.add(raw_id.lower())
    return keys


def _outgoing_embed_ids(node: LogseqNode) -> set[str]:
    found: set[str] = {r.lower() for r in node.block_refs}
    for match in LOGSEQ_PATTERNS["block_ref"].finditer(node.clean_text):
        uid = match.group(1) or match.group(2)
        if uid:
            found.add(uid.lower())
    return found


def _nodes_needing_trailing_anchor(
    flat: list[LogseqNode],
    *,
    vault_wide_ref_targets: set[str] | None = None,
) -> set[str]:
    """Synthetic UUIDs of nodes that should receive a trailing Obsidian block id.

    When ``vault_wide_ref_targets`` is provided (lowercased embed ids used anywhere in the
    vault), any node whose identity keys intersect that set is marked — so cross-page
    ``((uuid))`` references still get a stable ``^`` anchor on the target block's line.
    """
    if vault_wide_ref_targets is not None:
        return {
            n.uuid for n in flat if _node_identity_keys(n) & {t.lower() for t in vault_wide_ref_targets}
        }
    need: set[str] = set()
    for target in flat:
        target_keys = _node_identity_keys(target)
        for referrer in flat:
            if referrer.uuid == target.uuid:
                continue
            if target_keys & _outgoing_embed_ids(referrer):
                need.add(target.uuid)
                break
    return need


def _allocate_obsidian_suffixes(flat: list[LogseqNode], need_anchor: set[str]) -> dict[str, str]:
    """Return mapping synthetic uuid -> suffix (without ^) unique within this page."""
    used: set[str] = set()
    result: dict[str, str] = {}
    for node in flat:
        if node.uuid not in need_anchor:
            continue
        base = node.uuid.replace("-", "")[:8]
        candidate = base
        if candidate in used:
            candidate = node.uuid.replace("-", "")
        if candidate in used:
            candidate = node.uuid
        n = 0
        while candidate in used:
            n += 1
            candidate = f"{base}{n}"
        used.add(candidate)
        result[node.uuid] = candidate
    return result


def _yaml_quote_key(key: str) -> str:
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", key):
        return key
    return json.dumps(key, ensure_ascii=False)


def _yaml_quote_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, str):
        if "\n" in value:
            lines = value.split("\n")
            body = "\n".join("  " + line for line in lines)
            return "|\n" + body
        if re.search(r'[:#"\[\]{}]|^\s|\s$', value) or value in ("true", "false", "null"):
            return json.dumps(value, ensure_ascii=False)
        return value
    return json.dumps(value, default=str, ensure_ascii=False)


def _page_properties_to_yaml_frontmatter(properties: dict[str, Any]) -> str:
    if not properties:
        return ""
    lines = ["---", *[f"{_yaml_quote_key(str(k))}: {_yaml_quote_value(v)}" for k, v in properties.items()], "---"]
    return "\n".join(lines) + "\n\n"


def _build_local_embed_index(flat: list[LogseqNode]) -> dict[str, LogseqNode]:
    index: dict[str, LogseqNode] = {}
    for node in flat:
        index[node.uuid.lower()] = node
        if node.source_uuid:
            index[node.source_uuid.lower()] = node
        raw_id = node.properties.get("id")
        if isinstance(raw_id, str) and len(raw_id) == 36:
            index[raw_id.lower()] = node
    return index


def _replace_block_refs_in_text(
    text: str,
    page_title: str,
    local_index: dict[str, LogseqNode],
    suffix_map: dict[str, str],
    embed_resolver: EmbedResolver | None,
) -> str:
    block_ref_pattern = LOGSEQ_PATTERNS["block_ref"]

    def repl(match: re.Match[str]) -> str:
        uid = match.group(1) or match.group(2)
        if not uid:
            return match.group(0)
        uid_lower = uid.lower()
        if embed_resolver is not None:
            resolved = embed_resolver(uid)
            if resolved is not None:
                other_title, resolved_anchor = resolved
                logger.debug(
                    "embed_resolver mapped ref=%s -> [[%s#^%s]]",
                    uid,
                    other_title,
                    resolved_anchor,
                )
                return f"[[{other_title}#^{resolved_anchor}]]"
        target = local_index.get(uid_lower)
        if target is None:
            logger.debug("Unresolved block ref %s in Obsidian export (same-page index miss)", uid)
            return match.group(0)
        block_anchor = suffix_map.get(target.uuid)
        if block_anchor is None:
            block_anchor = target.uuid.replace("-", "")[:8]
        logger.debug("Same-page block ref %s -> [[%s#^%s]]", uid, page_title, block_anchor)
        return f"[[{page_title}#^{block_anchor}]]"

    return block_ref_pattern.sub(repl, text)


def _obsidian_line_source(node: LogseqNode) -> str:
    """Prefer the first line of ``content`` so ``((uuid))`` survives when stripped from ``clean_text``."""
    if node.content:
        first = node.content.split("\n", 1)[0]
    else:
        first = node.clean_text
    stripped = LOGSEQ_PATTERNS["inline_uuid_prop"].sub("", first)
    return stripped.replace("\n", " ").strip()


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
        line_text = node.clean_text.replace("\n", " ")
        self._lines.append(f"{prefix}{line_text}")
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


class ObsidianForgeVisitor(ASTVisitor):
    """Builds Obsidian-friendly Markdown: YAML frontmatter, list body, ``^`` block ids."""

    def __init__(
        self,
        *,
        page_title: str,
        suffix_map: dict[str, str],
        needs_suffix: set[str],
        local_index: dict[str, LogseqNode],
        embed_resolver: EmbedResolver | None,
        header: str,
    ) -> None:
        self._page_title = page_title
        self._suffix_map = suffix_map
        self._needs_suffix = needs_suffix
        self._local_index = local_index
        self._embed_resolver = embed_resolver
        self._header = header
        self._lines: list[str] = []
        self._stack: list[str] = []

    def visit_node(self, node: LogseqNode) -> None:
        depth = len(self._stack)
        prefix = "  " * depth + "- "
        line_core = _replace_block_refs_in_text(
            _obsidian_line_source(node),
            self._page_title,
            self._local_index,
            self._suffix_map,
            self._embed_resolver,
        )
        if node.uuid in self._needs_suffix:
            anchor = self._suffix_map.get(node.uuid, node.uuid.replace("-", "")[:8])
            line_core = f"{line_core.rstrip()} ^{anchor}"
            logger.debug("Obsidian trailing block id uuid=%s ^%s", node.uuid, anchor)
        self._lines.append(f"{prefix}{line_core}")
        self._stack.append(node.uuid)

    def depart_node(self, node: LogseqNode) -> None:
        _ = node
        self._stack.pop()

    def get_markdown(self) -> str:
        return self._header + "\n".join(self._lines)


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

    @staticmethod
    def vault_wide_embed_targets(pages: list[LogseqPage]) -> set[str]:
        """Lowercased block ids referenced via ``((uuid))`` or ``block_refs`` anywhere in ``pages``."""
        targets: set[str] = set()
        for page in pages:
            for node in _flatten_nodes_preorder(page.root_nodes):
                targets |= _outgoing_embed_ids(node)
        return targets

    @staticmethod
    def build_vault_obsidian_suffix_map(
        pages: list[LogseqPage],
        *,
        vault_wide_ref_targets: set[str] | None = None,
    ) -> dict[str, str]:
        """Map every block synthetic ``uuid`` to a per-vault-stable ``^`` anchor suffix string."""
        targets = (
            vault_wide_ref_targets
            if vault_wide_ref_targets is not None
            else ForgeExporter.vault_wide_embed_targets(pages)
        )
        merged: dict[str, str] = {}
        for page in pages:
            flat = _flatten_nodes_preorder(page.root_nodes)
            need = _nodes_needing_trailing_anchor(flat, vault_wide_ref_targets=targets)
            merged.update(_allocate_obsidian_suffixes(flat, need))
        return merged

    @staticmethod
    def to_obsidian_markdown(
        nodes: list[LogseqNode],
        page_properties: dict[str, Any],
        *,
        embed_resolver: EmbedResolver | None = None,
        global_suffix_map: dict[str, str] | None = None,
        vault_wide_ref_targets: set[str] | None = None,
    ) -> str:
        """Render Obsidian-compatible Markdown (YAML frontmatter, ``^`` block ids, wikilinks preserved)."""
        props = dict(page_properties)
        page_title = str(props.get("title") or "Untitled")
        flat = _flatten_nodes_preorder(nodes)
        need_suffix = _nodes_needing_trailing_anchor(
            flat,
            vault_wide_ref_targets=vault_wide_ref_targets,
        )
        local_alloc = _allocate_obsidian_suffixes(flat, need_suffix)
        suffix_map: dict[str, str] = {}
        for n in flat:
            if n.uuid not in need_suffix:
                continue
            if global_suffix_map is not None and n.uuid in global_suffix_map:
                suffix_map[n.uuid] = global_suffix_map[n.uuid]
            else:
                suffix_map[n.uuid] = local_alloc[n.uuid]
        local_index = _build_local_embed_index(flat)
        header = _page_properties_to_yaml_frontmatter(props)
        visitor = ObsidianForgeVisitor(
            page_title=page_title,
            suffix_map=suffix_map,
            needs_suffix=need_suffix,
            local_index=local_index,
            embed_resolver=embed_resolver,
            header=header,
        )
        for node in nodes:
            node.accept(visitor)
        return visitor.get_markdown()