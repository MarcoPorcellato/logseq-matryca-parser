"""Agent-native "Printing Press" exports: UUID aliases and ultra-dense X-Ray AST text."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from logseq_matryca_parser.exceptions import SessionAliasRegistryError
from logseq_matryca_parser.logos_core import LogseqNode

logger = logging.getLogger(__name__)

XRAY_STATE_FILENAME = ".matryca_xray_state.json"


def _flatten_subtrees(nodes: list[LogseqNode]) -> list[LogseqNode]:
    """Depth-first list of nodes under each root, preserving outline order."""
    flat: list[LogseqNode] = []
    seen: set[str] = set()

    def walk(node: LogseqNode) -> None:
        if node.uuid in seen:
            return
        seen.add(node.uuid)
        flat.append(node)
        for child in node.children:
            walk(child)

    for root in nodes:
        walk(root)
    return flat


def _normalize_alias_payload(raw: Any) -> dict[str, Any]:
    """Coerce on-disk JSON into a flat ``alias_str -> uuid`` mapping."""
    if not isinstance(raw, dict):
        msg = "X-Ray state file must contain a JSON object mapping aliases to UUIDs"
        raise SessionAliasRegistryError(msg)
    if set(raw.keys()) == {"aliases"} and isinstance(raw.get("aliases"), dict):
        logger.warning(
            "SessionAliasRegistry.load_from_disk: unwrap legacy 'aliases' wrapper key"
        )
        raw = raw["aliases"]
    if not isinstance(raw, dict):
        msg = "X-Ray state 'aliases' value must be a JSON object"
        raise SessionAliasRegistryError(msg)
    return raw


class SessionAliasRegistry:
    """Maps sequential integer aliases to Logseq block UUIDs for a single agent session."""

    def __init__(self) -> None:
        self._alias_to_uuid: dict[int, str] = {}
        self._uuid_to_alias: dict[str, int] = {}

    def generate_aliases(self, nodes: list[LogseqNode]) -> dict[int, str]:
        """Assign ``0..n-1`` to each unique node UUID (including nested children)."""
        self._alias_to_uuid.clear()
        self._uuid_to_alias.clear()
        next_alias = 0
        for node in _flatten_subtrees(nodes):
            if node.uuid in self._uuid_to_alias:
                continue
            self._alias_to_uuid[next_alias] = node.uuid
            self._uuid_to_alias[node.uuid] = next_alias
            logger.debug("SessionAliasRegistry alias=%s uuid=%s", next_alias, node.uuid)
            next_alias += 1
        return dict(self._alias_to_uuid)

    def resolve_alias(self, alias: int) -> str | None:
        """Return the Logseq UUID for ``alias``, or ``None`` if unknown."""
        return self._alias_to_uuid.get(alias)

    def alias_for_uuid(self, node_uuid: str) -> int | None:
        """Return the session alias for ``node_uuid``, or ``None`` if unregistered."""
        return self._uuid_to_alias.get(node_uuid)

    def save_to_disk(self, filepath: Path) -> None:
        """Persist ``alias -> uuid`` mapping as JSON for cross-invocation state."""
        payload = {str(alias): uuid for alias, uuid in self._alias_to_uuid.items()}
        filepath.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        logger.debug("SessionAliasRegistry saved %s aliases to %s", len(payload), filepath)

    @classmethod
    def load_from_disk(cls, filepath: Path) -> SessionAliasRegistry:
        """Reconstruct a registry from a JSON file written by :meth:`save_to_disk`."""
        raw_text = filepath.read_text(encoding="utf-8").strip()
        if not raw_text:
            logger.warning("SessionAliasRegistry.load_from_disk: empty state file %s", filepath)
            return cls()
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            msg = f"Invalid JSON in X-Ray state file: {filepath}"
            raise SessionAliasRegistryError(msg) from exc
        raw = _normalize_alias_payload(parsed)
        registry = cls()
        seen_uuids: set[str] = set()
        ordered_aliases: list[int] = []
        for alias_str in raw:
            if not isinstance(alias_str, str):
                logger.warning(
                    "SessionAliasRegistry.load_from_disk: skip non-string alias key=%r",
                    alias_str,
                )
                continue
            try:
                ordered_aliases.append(int(alias_str))
            except ValueError:
                logger.warning(
                    "SessionAliasRegistry.load_from_disk: skip non-integer alias key=%s",
                    alias_str,
                )

        for alias in sorted(ordered_aliases):
            alias_str = str(alias)
            node_uuid = raw[alias_str]
            if not isinstance(node_uuid, str) or not node_uuid.strip():
                logger.warning(
                    "SessionAliasRegistry.load_from_disk: skip invalid uuid for alias=%s",
                    alias_str,
                )
                continue
            if node_uuid in seen_uuids:
                logger.warning(
                    "SessionAliasRegistry.load_from_disk: skip duplicate uuid=%s alias=%s",
                    node_uuid,
                    alias_str,
                )
                continue
            seen_uuids.add(node_uuid)
            registry._alias_to_uuid[alias] = node_uuid
            registry._uuid_to_alias[node_uuid] = alias
        logger.debug(
            "SessionAliasRegistry loaded %s aliases from %s",
            len(registry._alias_to_uuid),
            filepath,
        )
        return registry


def to_xray_markdown(nodes: list[LogseqNode], registry: SessionAliasRegistry) -> str:
    """Serialize outline topology as ``{indent}[{alias}] {clean_text}`` lines only."""
    lines: list[str] = []

    def emit(node: LogseqNode) -> None:
        alias = registry.alias_for_uuid(node.uuid)
        if alias is None:
            logger.debug("to_xray_markdown skip unregistered uuid=%s", node.uuid)
            return
        indent = "  " * node.indent_level
        text = node.clean_text.strip()
        if text:
            lines.append(f"{indent}[{alias}] {text}")
        for child in node.children:
            emit(child)

    for root in nodes:
        emit(root)

    return "\n".join(lines)
