"""Logseq-native Markdown serialization (frontmatter + block property layout)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage

logger = logging.getLogger(__name__)

_LOGSEQ_REF_PROPERTY_KEYS: frozenset[str] = frozenset({"tags", "alias", "aliases"})


def _normalize_logseq_ref_token(raw: str) -> str:
    """Strip Logseq tag/page-ref adornments from a single property token."""
    token = raw.strip()
    if token.startswith("#"):
        token = token.lstrip("#")
    if token.startswith("[[") and token.endswith("]]"):
        token = token[2:-2]
    return token.strip()


def _format_page_property_value(key: str, value: Any) -> str:
    """Serialize one page property value for Logseq markdown."""
    if isinstance(value, (list, set, tuple)):
        tokens = [str(item) for item in value]
        if key in _LOGSEQ_REF_PROPERTY_KEYS:
            tokens = [_normalize_logseq_ref_token(token) for token in tokens]
        return ", ".join(tokens)
    return str(value)


def format_logseq_page_properties(properties: dict[str, Any]) -> str:
    """Render page properties as raw ``key:: value`` lines followed by a blank line."""
    if not properties:
        return ""
    lines = [
        f"{key}:: {_format_page_property_value(key, value)}"
        for key, value in properties.items()
    ]
    logger.debug("Formatted %s page property lines", len(lines))
    return "\n".join(lines) + "\n\n"


def _block_property_indent(bullet_indent: str) -> str:
    """Block properties sit at parent leading whitespace plus exactly two spaces."""
    return f"{bullet_indent}  "


def format_logseq_block_property_lines(
    node: LogseqNode,
    bullet_indent: str,
) -> list[str]:
    """Render contiguous block properties before any child bullets."""
    if not node.properties:
        return []
    prop_indent = _block_property_indent(bullet_indent)
    if node.properties_order:
        ordered_keys = list(node.properties_order)
        missing_keys = [key for key in node.properties if key not in ordered_keys]
        ordered_keys.extend(missing_keys)
    else:
        ordered_keys = list(node.properties.keys())
    lines: list[str] = []
    seen: set[str] = set()
    for key in ordered_keys:
        if key not in node.properties or key in seen:
            continue
        seen.add(key)
        lines.append(f"{prop_indent}{key}:: {node.properties[key]}")
    logger.debug(
        "Formatted %s block property lines for uuid=%s indent=%r",
        len(lines),
        node.uuid,
        prop_indent,
    )
    return lines


def _serialize_logseq_node_lines(node: LogseqNode, tab_size: int) -> list[str]:
    indent = " " * (node.indent_level * tab_size)
    content_lines = node.content.splitlines()
    first_line = content_lines[0] if content_lines else ""
    continuation_indent = _block_property_indent(indent)
    lines = [f"{indent}- {first_line}"]
    for continuation in content_lines[1:]:
        lines.append(f"{continuation_indent}{continuation}")
    lines.extend(format_logseq_block_property_lines(node, indent))
    for child in node.children:
        lines.extend(_serialize_logseq_node_lines(child, tab_size))
    return lines


def serialize_logseq_page(page: LogseqPage, tab_size: int = 2) -> str:
    """Serialize a parsed page back into Logseq-compatible markdown."""
    parts: list[str] = []
    if page.properties:
        parts.extend(f"{key}:: {value}" for key, value in page.properties.items())
        parts.append("")
    for root in page.root_nodes:
        parts.extend(_serialize_logseq_node_lines(root, tab_size))
    if not parts:
        return ""
    return "\n".join(parts) + "\n"


def write_logseq_page(page: LogseqPage, destination: Path, tab_size: int = 2) -> None:
    """Write ``page`` to ``destination`` using UTF-8 and Logseq layout rules."""
    destination.write_text(serialize_logseq_page(page, tab_size=tab_size), encoding="utf-8")
    logger.debug("Wrote Logseq page title=%s path=%s", page.title, destination)
