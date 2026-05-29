"""Logseq-native Markdown serialization (frontmatter + block property layout)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage

logger = logging.getLogger(__name__)

_LOGSEQ_REF_PROPERTY_KEYS: frozenset[str] = frozenset({"tags", "alias", "aliases"})

# Parsed into AST fields or drawers — must not round-trip as ``key::`` block lines.
_DERIVED_BLOCK_PROPERTY_KEYS: frozenset[str] = frozenset(
    {
        "scheduled",
        "scheduled_journal_day",
        "scheduled_iso",
        "deadline",
        "deadline_journal_day",
        "deadline_iso",
        "repeater",
        "logbook",
        "clock",
        "heading_level",
    }
)

_LIST_SHAPED_BLOCK_PROPERTY_KEYS: frozenset[str] = frozenset(
    {"tags", "alias", "aliases", "page-tags"}
)


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


def _ordered_property_keys(
    properties: dict[str, Any],
    properties_order: list[str] | None = None,
) -> list[str]:
    """Merge declared property order with any runtime keys missing from the list."""
    if properties_order:
        ordered_keys = list(properties_order)
        missing_keys = [key for key in properties if key not in ordered_keys]
        ordered_keys.extend(missing_keys)
        return ordered_keys
    return list(properties.keys())


def format_logseq_page_properties(
    properties: dict[str, Any],
    properties_order: list[str] | None = None,
) -> str:
    """Render page properties as raw ``key:: value`` lines followed by a blank line."""
    if not properties:
        return ""
    lines: list[str] = []
    seen: set[str] = set()
    for key in _ordered_property_keys(properties, properties_order):
        if key not in properties or key in seen:
            continue
        seen.add(key)
        lines.append(f"{key}:: {_format_page_property_value(key, properties[key])}")
    logger.debug("Formatted %s page property lines", len(lines))
    return "\n".join(lines) + "\n\n"


def _block_property_indent(bullet_indent: str) -> str:
    """Block properties sit at parent leading whitespace plus exactly two spaces."""
    return f"{bullet_indent}  "


def _format_block_property_value(key: str, value: Any) -> str | None:
    """Return inline ``key:: value`` text, or ``None`` when value uses bullet-list layout."""
    if key in _DERIVED_BLOCK_PROPERTY_KEYS:
        return None
    if isinstance(value, (list, tuple, set)):
        if key in _LIST_SHAPED_BLOCK_PROPERTY_KEYS or len(value) > 0:
            return None
        return ""
    return str(value)


def _format_block_property_list_lines(
    key: str,
    value: Any,
    bullet_indent: str,
) -> list[str]:
    """Render Logseq bullet-list property values (``tags::`` + indented ``-`` lines)."""
    prop_indent = _block_property_indent(bullet_indent)
    item_indent = f"{prop_indent}  "
    lines = [f"{prop_indent}{key}::"]
    if isinstance(value, (list, tuple, set)):
        for item in value:
            token = _normalize_logseq_ref_token(str(item)) if key in _LOGSEQ_REF_PROPERTY_KEYS else str(item)
            lines.append(f"{item_indent}- {token}")
    return lines


def _format_logbook_drawer_lines(bullet_indent: str, entries: Any) -> list[str]:
    """Render ``:LOGBOOK:`` / ``:END:`` drawer blocks from parsed logbook metadata."""
    prop_indent = _block_property_indent(bullet_indent)
    lines = [f"{prop_indent}:LOGBOOK:"]
    if isinstance(entries, (list, tuple)):
        for entry in entries:
            if str(entry).strip():
                lines.append(f"{prop_indent}{entry}")
    lines.append(f"{prop_indent}:END:")
    return lines


def format_logseq_block_property_lines(
    node: LogseqNode,
    bullet_indent: str,
) -> list[str]:
    """Render contiguous block properties before any child bullets."""
    if not node.properties:
        return []
    prop_indent = _block_property_indent(bullet_indent)
    if node.properties_order:
        ordered_keys = _ordered_property_keys(node.properties, node.properties_order)
    else:
        ordered_keys = list(node.properties.keys())
    lines: list[str] = []
    seen: set[str] = set()
    for key in ordered_keys:
        if key not in node.properties or key in seen or key in _DERIVED_BLOCK_PROPERTY_KEYS:
            continue
        seen.add(key)
        value = node.properties[key]
        if key == "logbook":
            continue
        if isinstance(value, (list, tuple, set)):
            lines.extend(_format_block_property_list_lines(key, value, bullet_indent))
            continue
        inline = _format_block_property_value(key, value)
        if inline is None:
            continue
        lines.append(f"{prop_indent}{key}:: {inline}")
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
        # Soft-break lines may already include alignment spaces from the parse buffer.
        line = continuation
        prefix_len = len(continuation_indent)
        if prefix_len and line.startswith(" " * prefix_len):
            line = line[prefix_len:]
        lines.append(f"{continuation_indent}{line}")
    if "logbook" in node.properties:
        lines.extend(_format_logbook_drawer_lines(indent, node.properties["logbook"]))
    lines.extend(format_logseq_block_property_lines(node, indent))
    for child in node.children:
        lines.extend(_serialize_logseq_node_lines(child, tab_size))
    return lines


def _page_uses_yaml_frontmatter(page: LogseqPage) -> bool:
    """True when the source page began with a ``---`` YAML frontmatter fence."""
    return page.raw_content.lstrip().startswith("---")


def _format_yaml_frontmatter(
    properties: dict[str, Any],
    properties_order: list[str] | None = None,
) -> str:
    """Render page properties as YAML frontmatter (``key: value`` lines)."""
    lines = ["---"]
    for key in _ordered_property_keys(properties, properties_order):
        value = properties[key]
        if isinstance(value, (list, set, tuple)):
            rendered = ", ".join(str(item) for item in value)
        else:
            rendered = str(value)
        lines.append(f"{key}: {rendered}")
    lines.append("---")
    return "\n".join(lines)


def serialize_logseq_page(page: LogseqPage, tab_size: int = 2) -> str:
    """Serialize a parsed page back into Logseq-compatible markdown."""
    parts: list[str] = []
    if page.properties:
        if _page_uses_yaml_frontmatter(page):
            parts.append(
                _format_yaml_frontmatter(
                    page.properties,
                    page.properties_order or None,
                )
            )
        else:
            parts.append(
                format_logseq_page_properties(
                    page.properties,
                    page.properties_order or None,
                ).rstrip("\n")
            )
        if page.root_nodes:
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
