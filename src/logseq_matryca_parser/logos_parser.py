"""Stack-machine parser for deterministic Logseq AST construction."""

from __future__ import annotations

import hashlib
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from logseq_matryca_parser.logseq_paths import (
    derive_graph_root_from_source_path,
    derive_page_title_from_source_path,
)

from .logos_core import LogseqNode, LogseqPage

LOGSEQ_PATTERNS: dict[str, re.Pattern[str]] = {
    "property": re.compile(r"^([\w-]+)::\s*(.*)$"),
    "wikilink": re.compile(r"\[\[(.*?)\]\]"),
    "tag": re.compile(r"#\[\[([^\]]+)\]\]|#([^\s#\]]+)"),
    "block_ref": re.compile(
        r"(?:\[[^\]]+\])?\(\(\(([a-f0-9\-]{36})\)\)\)|\(\(([a-f0-9\-]{36})\)\)"
    ),
    "uuid_prop": re.compile(r"^id::\s*([a-f0-9\-]{36})$"),
    "inline_uuid_prop": re.compile(r"\bid::\s*([a-f0-9\-]{36})\b"),
}
TASK_STATUSES: tuple[str, ...] = (
    "TODO",
    "DOING",
    "DONE",
    "LATER",
    "NOW",
    "WAITING",
    "CANCELED",
)
TIME_PATTERN: re.Pattern[str] = re.compile(r"\b(SCHEDULED|DEADLINE):\s*(<[^>]+>)")
PRIORITY_PATTERN: re.Pattern[str] = re.compile(r"\[#([A-Z])\]")
_SHIELD_TOKEN_PREFIX = "___LOGOS_SHIELD_TOKEN_"
HEADING_PATTERN: re.Pattern[str] = re.compile(r"^(#{1,6})\s+(.+)$")
ALIASED_BLOCK_REF_PATTERN: re.Pattern[str] = re.compile(
    r"(\[[^\]]+\])\(\(\([a-f0-9\-]{36}\)\)\)"
)
PLAIN_BLOCK_REF_PATTERN: re.Pattern[str] = re.compile(r"\(\(([a-f0-9\-]{36})\)\)")

SYSTEM_BLOCK_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*:(?:LOGBOOK|PROPERTIES):", re.IGNORECASE),
    re.compile(r"^\s*END:", re.IGNORECASE),
    re.compile(r"^\s*CLOCK:", re.IGNORECASE),
    re.compile(r"^\s*collapsed::", re.IGNORECASE),
)

BULLET_PATTERN: re.Pattern[str] = re.compile(r"^(\s*)[-*]\s+(.*)$")
HEADING_BLOCK_PATTERN: re.Pattern[str] = re.compile(r"^(\s*)(#{1,6}\s+.+)$")
logger = logging.getLogger(__name__)


def _sanitize_line(raw_line: str) -> str:
    """Strip stray CR bytes from Windows-edited graph lines before tokenization."""
    return raw_line.rstrip("\r")

CREATED_AT_KEYS: tuple[str, ...] = ("created_at", "created-at", "createdat")
UPDATED_AT_KEYS: tuple[str, ...] = ("updated_at", "updated-at", "updatedat")
REPEATER_PATTERN: re.Pattern[str] = re.compile(r"(\.\+|\+\+|\+)\d+[hdwmy]")
CLOCK_PATTERN: re.Pattern[str] = re.compile(
    r"^\s*CLOCK:\s*\[([0-9]{4}-[0-9]{2}-[0-9]{2}\s+[A-Za-z]{3}\s+[0-9]{2}:[0-9]{2})\]\s*--\s*"
    r"\[([0-9]{4}-[0-9]{2}-[0-9]{2}\s+[A-Za-z]{3}\s+[0-9]{2}:[0-9]{2})\]\s*=>\s*([0-9]{2}:[0-9]{2}:[0-9]{2})\s*$"
)


def is_system_block(line: str) -> bool:
    """Return True for Logseq metadata/noise lines."""
    return any(pattern.match(line) for pattern in SYSTEM_BLOCK_PATTERNS)


def clean_node_content(raw_content: str, properties: dict[str, Any]) -> str:
    """Strip Logseq properties and bullet syntax from block text."""
    cleaned_lines: list[str] = []
    property_keys = tuple(properties.keys())
    in_code_block = False

    for line_index, line in enumerate(raw_content.splitlines()):
        stripped = line.strip()
        if _is_code_fence_line(stripped):
            in_code_block = not in_code_block
            cleaned_lines.append(stripped)
            continue
        if in_code_block:
            cleaned_lines.append(line)
            continue
        if property_keys and any(stripped.startswith(f"{key}::") for key in property_keys):
            continue
        cleaned_line = TIME_PATTERN.sub("", line)
        cleaned_line = LOGSEQ_PATTERNS["inline_uuid_prop"].sub("", cleaned_line)
        cleaned_line = ALIASED_BLOCK_REF_PATTERN.sub(r"\1", cleaned_line)
        cleaned_line = PLAIN_BLOCK_REF_PATTERN.sub("", cleaned_line)
        cleaned_line = re.sub(r"^\*\*(.+?)\s\*\*$", r"\1", cleaned_line.strip())
        cleaned_line = re.sub(r"^\s*-\s+", "", cleaned_line).strip()
        heading_match = HEADING_PATTERN.match(cleaned_line)
        if heading_match:
            cleaned_line = heading_match.group(2).strip()
        if line_index == 0:
            _, cleaned_line = _extract_task_status(cleaned_line)
            cleaned_line = PRIORITY_PATTERN.sub("", cleaned_line).strip()
        cleaned_line = re.sub(r"\s{2,}", " ", cleaned_line).strip()
        if not cleaned_line:
            continue
        cleaned_lines.append(cleaned_line)

    return "\n".join(cleaned_lines).strip()


def _is_code_fence_line(stripped_line: str) -> bool:
    return stripped_line.startswith("```")


def _try_open_fence_line(content: str, line_start: int, n: int) -> tuple[int, int] | None:
    """If the line starting at ``line_start`` opens a fenced code block, return (tick_index, tick_len)."""
    k = line_start
    while k < n and content[k] in " \t":
        k += 1
    if k >= n or content[k] != "`":
        return None
    tick_end = k
    while tick_end < n and content[tick_end] == "`":
        tick_end += 1
    tick_len = tick_end - k
    if tick_len < 3:
        return None
    return (k, tick_len)


def _fence_line_is_closing(line: str, tick_len: int) -> bool:
    stripped = line.strip()
    if not stripped or stripped[0] != "`":
        return False
    run = 0
    while run < len(stripped) and stripped[run] == "`":
        run += 1
    remainder = stripped[run:].strip()
    return run >= tick_len and remainder == ""


def _fence_region_end(content: str, tick_start: int, tick_len: int, n: int) -> int:
    """Return end index (exclusive) of a fenced code region opened at ``tick_start``."""
    line_end = content.find("\n", tick_start + tick_len)
    if line_end == -1:
        return n
    pos = line_end + 1
    while pos < n:
        next_nl = content.find("\n", pos)
        segment = content[pos:] if next_nl == -1 else content[pos:next_nl]
        if _fence_line_is_closing(segment, tick_len):
            return n if next_nl == -1 else next_nl + 1
        if next_nl == -1:
            return n
        pos = next_nl + 1
    return n


def _find_inline_code_close(content: str, body_start: int, tick_len: int, n: int) -> int:
    p = body_start
    while p < n:
        if content[p] == "`":
            q = p
            while q < n and content[q] == "`":
                q += 1
            if q - p == tick_len:
                return q
        p += 1
    return -1


def _consume_inline_code_span(content: str, i: int, n: int) -> tuple[str, int]:
    """Return the full span (including delimiters) and exclusive end index."""
    j = i
    while j < n and content[j] == "`":
        j += 1
    tick_len = j - i
    close = _find_inline_code_close(content, j, tick_len, n)
    if close == -1:
        return content[i:n], n
    return content[i:close], close


def _shield_inline_code(content: str) -> tuple[str, list[str]]:
    """Mask inline code, fenced code, and ``{{...}}`` macros for entity extraction only."""
    literals: list[str] = []
    parts: list[str] = []
    i = 0
    n = len(content)

    def emit_placeholder(segment: str) -> None:
        literals.append(segment)
        parts.append(f"{_SHIELD_TOKEN_PREFIX}{len(literals) - 1}___")

    while i < n:
        at_line_start = i == 0 or content[i - 1] == "\n"
        if at_line_start:
            line_start = i
            fence_open = _try_open_fence_line(content, line_start, n)
            if fence_open is not None:
                tick_start, tick_len = fence_open
                fence_end = _fence_region_end(content, tick_start, tick_len, n)
                emit_placeholder(content[i:fence_end])
                i = fence_end
                continue

        if i + 1 < n and content[i] == "{" and content[i + 1] == "{":
            close = content.find("}}", i + 2)
            if close == -1:
                emit_placeholder(content[i:n])
                break
            emit_placeholder(content[i : close + 2])
            i = close + 2
            continue

        if content[i] == "`":
            segment, end = _consume_inline_code_span(content, i, n)
            emit_placeholder(segment)
            i = end
            continue

        parts.append(content[i])
        i += 1

    return "".join(parts), literals


def _extract_task_status(first_line: str) -> tuple[str | None, str]:
    for status in TASK_STATUSES:
        prefix = f"{status} "
        if first_line.startswith(prefix):
            return status, first_line[len(prefix) :].strip()
    return None, first_line


def _extract_time_properties(raw_content: str) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    in_code_block = False
    for line in raw_content.splitlines():
        stripped = line.strip()
        if _is_code_fence_line(stripped):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        for key, value in TIME_PATTERN.findall(line):
            marker_lower = key.lower()
            marker_payload = value.strip("<>")
            properties[marker_lower] = value
            repeater_match = REPEATER_PATTERN.search(marker_payload)
            repeater = repeater_match.group(0) if repeater_match else None
            payload_without_repeater = (
                REPEATER_PATTERN.sub("", marker_payload).strip() if repeater else marker_payload
            )
            parsed_dt = _parse_logseq_datetime(payload_without_repeater)
            if parsed_dt is not None:
                properties[f"{marker_lower}_journal_day"] = int(parsed_dt.strftime("%Y%m%d"))
                properties[f"{marker_lower}_iso"] = parsed_dt.isoformat(timespec="seconds")
                properties[f"{marker_lower}_at"] = int(
                    parsed_dt.replace(tzinfo=timezone.utc).timestamp()
                )
            if repeater is not None:
                properties["repeater"] = repeater
    return properties


def _extract_tags(raw_content: str) -> list[str]:
    tags: list[str] = []
    shielded, _ = _shield_inline_code(raw_content)
    for bracketed, simple in LOGSEQ_PATTERNS["tag"].findall(shielded):
        tag = bracketed or simple
        if tag:
            tags.append(tag.rstrip(".,;:"))
    return tags


def _extract_block_refs(raw_content: str) -> list[str]:
    refs: list[str] = []
    shielded, _ = _shield_inline_code(raw_content)
    for alias_ref, plain_ref in LOGSEQ_PATTERNS["block_ref"].findall(shielded):
        block_ref = alias_ref or plain_ref
        if block_ref:
            refs.append(block_ref)
    return refs


def _extract_heading_level(content: str) -> int | None:
    first_line = content.splitlines()[0].strip() if content.splitlines() else ""
    match = HEADING_PATTERN.match(first_line)
    if match:
        return len(match.group(1))
    return None


def _strip_ordinal_suffix(value: str) -> str:
    return re.sub(r"\b([0-9]{1,2})(st|nd|rd|th)\b", r"\1", value, flags=re.IGNORECASE)


def _parse_logseq_datetime(raw_value: str) -> datetime | None:
    candidate = _strip_ordinal_suffix(raw_value.strip())
    datetime_formats = (
        "%Y-%m-%d %a %H:%M",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %a",
        "%Y-%m-%d",
        "%b %d, %Y",
        "%Y_%m_%d",
        "%a, %d-%m-%Y",
    )
    for fmt in datetime_formats:
        try:
            return datetime.strptime(candidate, fmt)
        except ValueError:
            continue
    return None


def resolve_journal_day(value: str) -> int | None:
    """Resolve a journal-like string into Logseq YYYYMMDD integer."""
    candidate = value.strip()
    if not candidate:
        return None
    if candidate.startswith("[[") and candidate.endswith("]]"):
        candidate = candidate[2:-2].strip()
    if candidate.lower().endswith(".md"):
        candidate = candidate[:-3]
    parsed = _parse_logseq_datetime(candidate)
    if parsed is None:
        return None
    return int(parsed.strftime("%Y%m%d"))


def normalize_logseq_timestamp(value: Any) -> int | None:
    """Normalize Logseq-style timestamp values to unix epoch seconds."""
    if value is None:
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        timestamp = int(value)
        return timestamp // 1000 if timestamp >= 10**12 else timestamp

    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None
        if candidate.isdigit():
            parsed = int(candidate)
            return parsed // 1000 if parsed >= 10**12 else parsed

        iso_candidate = candidate.replace("Z", "+00:00")
        try:
            parsed_datetime = datetime.fromisoformat(iso_candidate)
            if parsed_datetime.tzinfo is None:
                parsed_datetime = parsed_datetime.replace(tzinfo=timezone.utc)
            return int(parsed_datetime.timestamp())
        except ValueError:
            pass

        parsed_logseq_date = _parse_logseq_datetime(candidate)
        if parsed_logseq_date is not None:
            return int(parsed_logseq_date.replace(tzinfo=timezone.utc).timestamp())

        date_formats = ("%Y/%m/%d", "%Y%m%d")
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(candidate, fmt).replace(tzinfo=timezone.utc)
                return int(parsed_date.timestamp())
            except ValueError:
                continue

    return None


def _first_normalized_timestamp(properties: dict[str, Any], keys: tuple[str, ...]) -> int | None:
    for key in keys:
        if key in properties:
            normalized = normalize_logseq_timestamp(properties[key])
            if normalized is not None:
                return normalized
    return None


def _merge_refs(wikilinks: list[str], tags: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for token in [*wikilinks, *tags]:
        if token and token not in seen:
            seen.add(token)
            merged.append(token)
    return merged


def _extract_property_graph_tokens(
    properties: dict[str, Any],
) -> tuple[list[str], list[str], list[str]]:
    property_wikilinks: list[str] = []
    property_tags: list[str] = []
    property_block_refs: list[str] = []
    for value in properties.values():
        if not isinstance(value, str):
            continue
        property_wikilinks.extend(_extract_wikilinks(value))
        property_tags.extend(_extract_tags(value))
        property_block_refs.extend(_extract_block_refs(value))
    return property_wikilinks, property_tags, property_block_refs


def _extract_wikilinks(raw_content: str) -> list[str]:
    shielded, _ = _shield_inline_code(raw_content)
    return LOGSEQ_PATTERNS["wikilink"].findall(shielded)


class PageRegistry:
    """Track all nodes by uuid for local block-reference resolution."""

    def __init__(self) -> None:
        self.blocks: dict[str, LogseqNode] = {}

    def register(self, node: LogseqNode) -> None:
        if node.uuid:
            self.blocks[node.uuid] = node

    def resolve(self, node_uuid: str) -> LogseqNode | None:
        return self.blocks.get(node_uuid)


class StackMachineParser:
    """O(N) indentation parser that builds a strict immutable AST."""

    def __init__(self, tab_size: int = 2) -> None:
        self.tab_size = tab_size
        self.registry = PageRegistry()

    def parse(self, text: str, page_title: str = "untitled") -> LogseqPage:
        """Parse Logseq markdown text into a `LogseqPage`."""
        stack: list[LogseqNode] = []
        stack_columns: list[int] = []
        stack_indents: list[str] = []
        root_nodes: list[LogseqNode] = []
        page_properties: dict[str, Any] = {}
        page_properties_order: list[str] = []
        current_node: LogseqNode | None = None
        frontmatter_active = True
        property_list_indent_level: int | None = None
        in_code_block = False
        in_drawer = False

        for line_number, raw_line in enumerate(text.splitlines(), start=1):
            raw_line = _sanitize_line(raw_line)
            stripped_line = raw_line.strip()

            if in_code_block and current_node is not None:
                merged_content = f"{current_node.content}\n{raw_line}"
                updated = self._refresh_node(current_node, merged_content, line_end=line_number)
                self._replace_stack_tail_node(stack, root_nodes, updated)
                current_node = updated
                if _is_code_fence_line(stripped_line):
                    in_code_block = False
                frontmatter_active = False
                property_list_indent_level = None
                continue

            if in_drawer:
                if stripped_line.upper() == ":END:":
                    in_drawer = False
                    continue
                if BULLET_PATTERN.match(raw_line):
                    in_drawer = False
                else:
                    if current_node is not None:
                        properties = dict(current_node.properties)
                        logbook_entries = list(properties.get("logbook", []))
                        logbook_entries.append(stripped_line)
                        properties["logbook"] = logbook_entries
                        clock_match = CLOCK_PATTERN.match(stripped_line)
                        if clock_match:
                            start_text, end_text, duration_text = clock_match.groups()
                            start_dt = datetime.strptime(start_text, "%Y-%m-%d %a %H:%M")
                            end_dt = datetime.strptime(end_text, "%Y-%m-%d %a %H:%M")
                            hours, minutes, seconds = [int(part) for part in duration_text.split(":")]
                            duration_seconds = (hours * 3600) + (minutes * 60) + seconds
                            clock_entries = list(properties.get("clock", []))
                            clock_entries.append(
                                {
                                    "start_iso": start_dt.isoformat(timespec="seconds"),
                                    "end_iso": end_dt.isoformat(timespec="seconds"),
                                    "duration": duration_text,
                                    "duration_seconds": duration_seconds,
                                }
                            )
                            properties["clock"] = clock_entries
                        updated = self._refresh_node(
                            current_node,
                            current_node.content,
                            properties_override=properties,
                            line_end=line_number,
                        )
                        self._replace_stack_tail_node(stack, root_nodes, updated)
                        current_node = updated
                    continue

            if stripped_line.upper() == ":LOGBOOK:" and current_node is not None:
                in_drawer = True
                properties = dict(current_node.properties)
                properties.setdefault("logbook", [])
                updated = self._refresh_node(
                    current_node,
                    current_node.content,
                    properties_override=properties,
                    line_end=line_number,
                )
                self._replace_stack_tail_node(stack, root_nodes, updated)
                current_node = updated
                continue

            collapsed_match = re.match(r"^\s*collapsed::\s*(\S+)\s*$", raw_line, re.IGNORECASE)
            if collapsed_match and current_node is not None:
                collapsed_value = collapsed_match.group(1).lower() == "true"
                properties = dict(current_node.properties)
                properties["collapsed"] = collapsed_value
                updated = self._refresh_node(
                    current_node,
                    current_node.content,
                    properties_override=properties,
                    line_end=line_number,
                )
                self._replace_stack_tail_node(stack, root_nodes, updated)
                current_node = updated
                continue

            if not stripped_line or is_system_block(raw_line):
                continue

            bullet_match = BULLET_PATTERN.match(raw_line)
            if bullet_match:
                indent_level = self._compute_indent_level(bullet_match.group(1))
                if property_list_indent_level is not None and indent_level > property_list_indent_level:
                    indent_level -= 1
                else:
                    property_list_indent_level = None

                raw_indent = bullet_match.group(1)
                if (
                    stack_columns
                    and "\t" in stack_indents[-1]
                    and raw_indent
                    and "\t" not in raw_indent
                    and indent_level == stack_columns[-1] + 1
                ):
                    indent_level = stack_columns[-1]

                while stack_columns and stack_columns[-1] >= indent_level:
                    stack.pop()
                    stack_columns.pop()
                    stack_indents.pop()

                parent_uuid = self._resolve_parent_uuid_for_synthetic(stack)
                node = self._build_node(
                    block_text=bullet_match.group(2),
                    indent_level=indent_level,
                    page_title=page_title,
                    line_start=line_number,
                    parent_uuid=parent_uuid,
                )

                node = self._initialize_node_graph_fields(node, stack, root_nodes)
                if stack:
                    node = self._attach_node_to_parent(stack, root_nodes, node)
                else:
                    root_nodes.append(node)

                stack.append(node)
                stack_columns.append(indent_level)
                stack_indents.append(raw_indent)
                current_node = node
                self.registry.register(node)
                frontmatter_active = False
                continue

            heading_match = HEADING_BLOCK_PATTERN.match(raw_line)
            if heading_match:
                indent_level = self._compute_indent_level(heading_match.group(1))
                property_list_indent_level = None

                raw_indent = heading_match.group(1)

                while stack_columns and stack_columns[-1] >= indent_level:
                    stack.pop()
                    stack_columns.pop()
                    stack_indents.pop()

                parent_uuid = self._resolve_parent_uuid_for_synthetic(stack)
                node = self._build_node(
                    block_text=heading_match.group(2),
                    indent_level=indent_level,
                    page_title=page_title,
                    line_start=line_number,
                    parent_uuid=parent_uuid,
                )

                node = self._initialize_node_graph_fields(node, stack, root_nodes)
                if stack:
                    node = self._attach_node_to_parent(stack, root_nodes, node)
                else:
                    root_nodes.append(node)

                stack.append(node)
                stack_columns.append(indent_level)
                stack_indents.append(raw_indent)
                current_node = node
                self.registry.register(node)
                frontmatter_active = False
                continue

            property_match = LOGSEQ_PATTERNS["property"].match(raw_line.strip())
            if property_match:
                key, value = property_match.groups()
                value = _sanitize_line(value)

                if current_node is None and frontmatter_active:
                    page_properties[key] = value
                    if key not in page_properties_order:
                        page_properties_order.append(key)
                    continue

                if current_node is None:
                    frontmatter_active = False
                    continue

                properties = dict(current_node.properties)
                properties[key] = value
                properties_order = list(current_node.properties_order)
                if key not in properties_order:
                    properties_order.append(key)

                updated = self._refresh_node(
                    current_node,
                    current_node.content,
                    properties_override=properties,
                    properties_order_override=properties_order,
                    line_end=line_number,
                )
                if key == "id":
                    updated = updated.model_copy(
                        update={"source_uuid": value, "synthetic_id": False}
                    )
                self._replace_stack_tail_node(stack, root_nodes, updated)
                current_node = updated
                self.registry.register(updated)

                raw_indent = raw_line[: len(raw_line) - len(raw_line.lstrip(" \t"))]
                property_list_indent_level = (
                    self._compute_indent_level(raw_indent) if value.strip() == "" else None
                )
                frontmatter_active = False
                continue

            if not stack:
                frontmatter_active = False
                continue

            active_node = stack[-1]
            merged_content = f"{active_node.content}\n{raw_line}"
            updated = self._refresh_node(active_node, merged_content, line_end=line_number)
            self._replace_stack_tail_node(stack, root_nodes, updated)
            current_node = updated
            logger.debug(
                "Soft-break continuation merged into stack tip line=%s depth=%s",
                line_number,
                len(stack),
            )
            frontmatter_active = False
            property_list_indent_level = None
            if _is_code_fence_line(stripped_line):
                in_code_block = True

        self._validate_references(root_nodes)
        root_nodes = self._normalize_indent_levels(root_nodes)
        page_refs = self._collect_page_refs(root_nodes)
        created_at = _first_normalized_timestamp(page_properties, CREATED_AT_KEYS)
        updated_at = _first_normalized_timestamp(page_properties, UPDATED_AT_KEYS)
        title_segments = [segment for segment in page_title.split("/") if segment]
        namespace_chain = title_segments[:-1] if len(title_segments) > 1 else []
        return LogseqPage(
            title=page_title,
            raw_content=text,
            properties=page_properties,
            properties_order=page_properties_order,
            refs=page_refs,
            created_at=created_at,
            updated_at=updated_at,
            namespace_chain=namespace_chain,
            root_nodes=root_nodes,
        )

    def parse_file(self, path: Path | str) -> list[LogseqNode]:
        """Compatibility API: parse file and return root nodes."""
        page = self.parse_page_file(path)
        return page.root_nodes

    def parse_page_file(self, path: Path | str) -> LogseqPage:
        """Parse a markdown file and return a graph-native page model."""
        path = Path(path)
        content = path.read_text(encoding="utf-8")
        if not content.strip():
            logger.warning("Il file %s è vuoto.", path)
            page_title = derive_page_title_from_source_path(path)
            title_segments = [segment for segment in page_title.split("/") if segment]
            namespace_chain = title_segments[:-1] if len(title_segments) > 1 else []
            graph_root = self._derive_graph_root(path)
            return LogseqPage(
                title=page_title,
                raw_content=content,
                namespace_chain=namespace_chain,
                source_path=str(path.resolve()),
                graph_root=str(graph_root),
            )

        page_title = self._derive_page_title(path)
        page = self.parse(content, page_title=page_title)
        graph_root = self._derive_graph_root(path)
        created_at = page.created_at
        updated_at = page.updated_at
        if created_at is None:
            created_at = int(os.path.getctime(path))
        if updated_at is None:
            updated_at = int(os.path.getmtime(path))
        source_path = str(path.resolve())
        return page.model_copy(
            update={
                "source_path": source_path,
                "graph_root": str(graph_root),
                "created_at": created_at,
                "updated_at": updated_at,
                "root_nodes": self._apply_source_path(page.root_nodes, source_path),
            }
        )

    def _derive_page_title(self, path: Path) -> str:
        return derive_page_title_from_source_path(path)

    def _derive_graph_root(self, path: Path) -> Path:
        return derive_graph_root_from_source_path(path)

    def _apply_source_path(self, nodes: list[LogseqNode], source_path: str) -> list[LogseqNode]:
        return [
            node.model_copy(
                update={
                    "source_path": source_path,
                    "children": self._apply_source_path(node.children, source_path),
                }
            )
            for node in nodes
        ]

    def _compute_indent_level(self, indentation: str) -> int:
        spaces = indentation.count(" ") + (indentation.count("\t") * self.tab_size)
        logger.debug(
            "Computed indentation level via floor division: spaces=%s tab_size=%s level=%s",
            spaces,
            self.tab_size,
            spaces // self.tab_size,
        )
        return spaces // self.tab_size

    def _resolve_parent_uuid_for_synthetic(self, stack: list[LogseqNode]) -> str | None:
        """Return the parent block UUID for synthetic hashing; None at graph root (payload uses 'root')."""
        if not stack:
            logger.debug("Stack empty: synthetic UUID parent_uuid=None (hashed as root sentinel)")
            return None
        resolved_parent_uuid = stack[-1].uuid
        logger.debug(
            "Stack depth=%s: synthetic UUID parent_uuid=%s", len(stack), resolved_parent_uuid
        )
        return resolved_parent_uuid

    def _build_node(
        self,
        block_text: str,
        indent_level: int,
        page_title: str,
        line_start: int,
        parent_uuid: str | None,
    ) -> LogseqNode:
        stripped_text = block_text.strip()
        properties: dict[str, Any] = {}

        uuid_match = LOGSEQ_PATTERNS["uuid_prop"].match(stripped_text)
        inline_uuid_match = LOGSEQ_PATTERNS["inline_uuid_prop"].search(stripped_text)
        if inline_uuid_match is not None:
            inline_uuid = inline_uuid_match.group(1)
            properties["id"] = inline_uuid
            stripped_text = LOGSEQ_PATTERNS["inline_uuid_prop"].sub("", stripped_text).strip()
        source_uuid = (
            uuid_match.group(1)
            if uuid_match
            else (inline_uuid_match.group(1) if inline_uuid_match else None)
        )
        node_uuid = self._deterministic_uuid(page_title, line_start, stripped_text, parent_uuid)
        time_properties = _extract_time_properties(stripped_text)
        scheduled_at: int | None = None
        deadline_at: int | None = None
        if time_properties:
            scheduled_raw = time_properties.get("scheduled_at")
            deadline_raw = time_properties.get("deadline_at")
            scheduled_at = scheduled_raw if isinstance(scheduled_raw, int) else None
            deadline_at = deadline_raw if isinstance(deadline_raw, int) else None
            merge_time = {
                key: value
                for key, value in time_properties.items()
                if key not in ("scheduled_at", "deadline_at")
            }
            properties.update(merge_time)
        first_line = stripped_text.splitlines()[0].strip() if stripped_text else ""
        priority_match = PRIORITY_PATTERN.search(first_line)
        task_priority = priority_match.group(1) if priority_match else None
        task_status, _ = _extract_task_status(stripped_text)
        heading_level = _extract_heading_level(stripped_text)
        if heading_level is not None:
            properties["heading_level"] = heading_level
        property_wikilinks, property_tags, property_block_refs = _extract_property_graph_tokens(
            properties
        )
        wikilinks = [*_extract_wikilinks(stripped_text), *property_wikilinks]
        tags = [*_extract_tags(stripped_text), *property_tags]
        properties_order = ["id"] if "id" in properties else []

        return LogseqNode(
            uuid=node_uuid,
            source_uuid=source_uuid,
            synthetic_id=source_uuid is None,
            content=stripped_text,
            clean_text=clean_node_content(stripped_text, properties),
            indent_level=indent_level,
            properties=properties,
            properties_order=properties_order,
            wikilinks=wikilinks,
            tags=tags,
            refs=_merge_refs(wikilinks, tags),
            block_refs=[*_extract_block_refs(stripped_text), *property_block_refs],
            task_status=task_status,
            task_priority=task_priority,
            scheduled_at=scheduled_at,
            deadline_at=deadline_at,
            repeater=properties.get("repeater") if isinstance(properties.get("repeater"), str) else None,
            parent_id=None,
            line_start=line_start,
            line_end=line_start,
            created_at=_first_normalized_timestamp(properties, CREATED_AT_KEYS),
            updated_at=_first_normalized_timestamp(properties, UPDATED_AT_KEYS),
            children=[],
        )

    def _deterministic_uuid(
        self,
        page_title: str,
        line_start: int,
        content: str,
        parent_uuid: str | None,
    ) -> str:
        parent_token = "root" if parent_uuid is None else parent_uuid
        logger.debug(
            "Stack-Machine synthetic UUID payload parent_token=%s line_start=%s page_title=%s",
            parent_token,
            line_start,
            page_title,
        )
        payload = f"{page_title}:{line_start}:{parent_token}:{content}".encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, digest))

    def _replace_stack_tail_node(
        self,
        stack: list[LogseqNode],
        root_nodes: list[LogseqNode],
        updated_node: LogseqNode,
    ) -> None:
        if not stack:
            return

        stack[-1] = updated_node
        if len(stack) == 1:
            root_nodes[-1] = updated_node
            return

        parent = stack[-2]
        parent_children = list(parent.children)
        parent_children[-1] = updated_node
        updated_parent = parent.model_copy(update={"children": parent_children})
        stack[-2] = updated_parent

        if len(stack) == 2:
            root_nodes[-1] = updated_parent
            return

        grand_parent = stack[-3]
        grand_parent_children = list(grand_parent.children)
        grand_parent_children[-1] = updated_parent
        stack[-3] = grand_parent.model_copy(update={"children": grand_parent_children})

    def _attach_node_to_parent(
        self,
        stack: list[LogseqNode],
        root_nodes: list[LogseqNode],
        node: LogseqNode,
    ) -> LogseqNode:
        parent = stack[-1]
        attached_node = node.model_copy(update={"parent_id": parent.uuid})
        updated_ancestor = attached_node

        for idx in range(len(stack) - 1, -1, -1):
            ancestor = stack[idx]
            ancestor_children = list(ancestor.children)
            if idx == len(stack) - 1:
                ancestor_children.append(updated_ancestor)
            else:
                ancestor_children[-1] = updated_ancestor
            updated_ancestor = ancestor.model_copy(update={"children": ancestor_children})
            stack[idx] = updated_ancestor

        root_nodes[-1] = stack[0]
        return attached_node

    def _initialize_node_graph_fields(
        self,
        node: LogseqNode,
        stack: list[LogseqNode],
        root_nodes: list[LogseqNode],
    ) -> LogseqNode:
        left_id = self._resolve_left_sibling_id(stack, root_nodes)
        if stack:
            parent = stack[-1]
            path = [*parent.path, node.uuid]
            outline_path = [*parent.outline_path, len(parent.children) + 1]
        else:
            path = [node.uuid]
            outline_path = [len(root_nodes) + 1]
        return node.model_copy(
            update={"left_id": left_id, "path": path, "outline_path": outline_path}
        )

    def _resolve_left_sibling_id(
        self, stack: list[LogseqNode], root_nodes: list[LogseqNode]
    ) -> str | None:
        if stack:
            parent = stack[-1]
            return parent.children[-1].uuid if parent.children else None
        return root_nodes[-1].uuid if root_nodes else None

    def _collect_page_refs(self, roots: list[LogseqNode]) -> list[str]:
        collected: list[str] = []
        seen: set[str] = set()

        def visit(nodes: list[LogseqNode]) -> None:
            for node in nodes:
                for token in node.refs:
                    if token not in seen:
                        seen.add(token)
                        collected.append(token)
                visit(node.children)

        visit(roots)
        return collected

    def _validate_references(self, roots: list[LogseqNode]) -> None:
        _ = roots

    def _refresh_node(
        self,
        node: LogseqNode,
        content: str,
        properties_override: dict[str, Any] | None = None,
        properties_order_override: list[str] | None = None,
        line_end: int | None = None,
    ) -> LogseqNode:
        properties = dict(node.properties) if properties_override is None else dict(properties_override)
        properties_order = (
            list(node.properties_order)
            if properties_order_override is None
            else list(properties_order_override)
        )
        time_properties = _extract_time_properties(content)
        scheduled_at: int | None = None
        deadline_at: int | None = None
        if time_properties:
            scheduled_raw = time_properties.get("scheduled_at")
            deadline_raw = time_properties.get("deadline_at")
            scheduled_at = scheduled_raw if isinstance(scheduled_raw, int) else None
            deadline_at = deadline_raw if isinstance(deadline_raw, int) else None
            merge_time = {
                key: value
                for key, value in time_properties.items()
                if key not in ("scheduled_at", "deadline_at")
            }
            properties.update(merge_time)
        heading_level = _extract_heading_level(content)
        if heading_level is not None:
            properties["heading_level"] = heading_level
        first_line = content.splitlines()[0].strip() if content.splitlines() else ""
        priority_match = PRIORITY_PATTERN.search(first_line)
        task_priority = priority_match.group(1) if priority_match else None
        task_status, _ = _extract_task_status(content.splitlines()[0].strip())
        property_wikilinks, property_tags, property_block_refs = _extract_property_graph_tokens(
            properties
        )
        wikilinks = [*_extract_wikilinks(content), *property_wikilinks]
        tags = [*_extract_tags(content), *property_tags]
        return node.model_copy(
            update={
                "content": content,
                "properties": properties,
                "properties_order": properties_order,
                "clean_text": clean_node_content(content, properties),
                "task_status": task_status,
                "task_priority": task_priority,
                "scheduled_at": scheduled_at,
                "deadline_at": deadline_at,
                "repeater": (
                    properties.get("repeater") if isinstance(properties.get("repeater"), str) else None
                ),
                "wikilinks": wikilinks,
                "tags": tags,
                "refs": _merge_refs(wikilinks, tags),
                "block_refs": [*_extract_block_refs(content), *property_block_refs],
                "line_end": line_end if line_end is not None else node.line_end,
                "created_at": _first_normalized_timestamp(properties, CREATED_AT_KEYS),
                "updated_at": _first_normalized_timestamp(properties, UPDATED_AT_KEYS),
            }
        )

    def _normalize_indent_levels(
        self, nodes: list[LogseqNode], depth: int = 0
    ) -> list[LogseqNode]:
        normalized_nodes: list[LogseqNode] = []
        for node in nodes:
            normalized_children = self._normalize_indent_levels(node.children, depth + 1)
            normalized_nodes.append(
                node.model_copy(update={"indent_level": depth, "children": normalized_children})
            )
        return normalized_nodes


# Backward-compatible alias.
LogosParser = StackMachineParser
