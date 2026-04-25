"""Stack-machine parser for deterministic Logseq AST construction."""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from pathlib import Path
from typing import Any

from .exceptions import BlockReferenceError, LogseqIndentationError
from .logos_core import LogseqNode, LogseqPage

LOGSEQ_PATTERNS: dict[str, re.Pattern[str]] = {
    "property": re.compile(r"^([\w-]+)::\s*(.*)$"),
    "wikilink": re.compile(r"\[\[(.*?)\]\]"),
    "tag": re.compile(r"#(?:\[\[)?([^\]\s]+)(?:\]\])?"),
    "block_ref": re.compile(r"\(\(([a-f0-9\-]{36})\)\)"),
    "uuid_prop": re.compile(r"^id::\s*([a-f0-9\-]{36})$"),
}

SYSTEM_BLOCK_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*:(?:LOGBOOK|PROPERTIES):", re.IGNORECASE),
    re.compile(r"^\s*END:", re.IGNORECASE),
    re.compile(r"^\s*CLOCK:", re.IGNORECASE),
    re.compile(r"^\s*collapsed::", re.IGNORECASE),
)

BULLET_PATTERN: re.Pattern[str] = re.compile(r"^(\s*)[-*]\s+(.*)$")
logger = logging.getLogger(__name__)


def is_system_block(line: str) -> bool:
    """Return True for Logseq metadata/noise lines."""
    return any(pattern.match(line) for pattern in SYSTEM_BLOCK_PATTERNS)


def clean_node_content(raw_content: str, properties: dict[str, Any]) -> str:
    """Strip Logseq properties and bullet syntax from block text."""
    cleaned_lines: list[str] = []
    property_keys = tuple(properties.keys())

    for line in raw_content.splitlines():
        stripped = line.strip()
        if property_keys and any(stripped.startswith(f"{key}::") for key in property_keys):
            continue
        cleaned_line = re.sub(r"^\s*-\s+", "", line)
        cleaned_lines.append(cleaned_line)

    return "\n".join(cleaned_lines).strip()


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
        root_nodes: list[LogseqNode] = []
        current_node: LogseqNode | None = None

        for raw_line in text.splitlines():
            if not raw_line.strip() or is_system_block(raw_line):
                continue

            bullet_match = BULLET_PATTERN.match(raw_line)
            if bullet_match:
                indent_level = self._compute_indent_level(bullet_match.group(1))
                if stack and indent_level > (stack[-1].indent_level + 1):
                    raise LogseqIndentationError(
                        "Invalid indentation jump detected while parsing page."
                    )

                node = self._build_node(
                    block_text=bullet_match.group(2),
                    indent_level=indent_level,
                    page_title=page_title,
                )

                while stack and stack[-1].indent_level >= indent_level:
                    stack.pop()

                if stack:
                    parent = stack[-1]
                    node = node.model_copy(update={"parent_id": parent.uuid})
                    updated_parent = parent.model_copy(update={"children": [*parent.children, node]})
                    if len(stack) >= 2:
                        grand_parent = stack[-2]
                        grand_parent_children = list(grand_parent.children)
                        grand_parent_children[-1] = updated_parent
                        stack[-2] = grand_parent.model_copy(
                            update={"children": grand_parent_children}
                        )
                    else:
                        root_nodes[-1] = updated_parent
                    stack[-1] = updated_parent
                else:
                    root_nodes.append(node)

                stack.append(node)
                current_node = node
                self.registry.register(node)
                continue

            if current_node is None:
                continue

            property_match = LOGSEQ_PATTERNS["property"].match(raw_line.strip())
            if property_match:
                key, value = property_match.groups()
                properties = dict(current_node.properties)
                properties[key] = value

                node_uuid = current_node.uuid
                if key == "id":
                    node_uuid = value

                updated = current_node.model_copy(update={"properties": properties, "uuid": node_uuid})
                updated = updated.model_copy(
                    update={"clean_text": clean_node_content(updated.content, properties)}
                )
                self._replace_stack_tail_node(stack, root_nodes, updated)
                current_node = updated
                self.registry.register(updated)
                continue

            merged_content = f"{current_node.content}\n{raw_line}"
            updated = current_node.model_copy(update={"content": merged_content})
            updated = updated.model_copy(
                update={"clean_text": clean_node_content(updated.content, dict(updated.properties))}
            )
            self._replace_stack_tail_node(stack, root_nodes, updated)
            current_node = updated

        self._validate_references(root_nodes)
        return LogseqPage(title=page_title, raw_content=text, root_nodes=root_nodes)

    def parse_file(self, path: Path) -> list[LogseqNode]:
        """Compatibility API: parse file and return root nodes."""
        content = path.read_text(encoding="utf-8")
        if not content.strip():
            logger.warning("Il file %s è vuoto.", path)
            return []
        page = self.parse(content, page_title=path.stem)
        return page.root_nodes

    def _compute_indent_level(self, indentation: str) -> int:
        spaces = indentation.count(" ") + (indentation.count("\t") * self.tab_size)
        if spaces % self.tab_size != 0:
            raise LogseqIndentationError("Indentation is not aligned to tab_size.")
        return spaces // self.tab_size

    def _build_node(self, block_text: str, indent_level: int, page_title: str) -> LogseqNode:
        stripped_text = block_text.strip()
        properties: dict[str, Any] = {}

        uuid_match = LOGSEQ_PATTERNS["uuid_prop"].match(stripped_text)
        node_uuid = uuid_match.group(1) if uuid_match else self._deterministic_uuid(page_title, stripped_text)

        return LogseqNode(
            uuid=node_uuid,
            content=stripped_text,
            clean_text=clean_node_content(stripped_text, properties),
            indent_level=indent_level,
            properties=properties,
            wikilinks=LOGSEQ_PATTERNS["wikilink"].findall(stripped_text),
            tags=LOGSEQ_PATTERNS["tag"].findall(stripped_text),
            block_refs=LOGSEQ_PATTERNS["block_ref"].findall(stripped_text),
            parent_id=None,
            children=[],
        )

    def _deterministic_uuid(self, page_title: str, content: str) -> str:
        payload = f"{page_title}:{content}".encode("utf-8")
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

    def _validate_references(self, roots: list[LogseqNode]) -> None:
        stack: list[LogseqNode] = list(roots)
        while stack:
            node = stack.pop()
            for block_ref in node.block_refs:
                if self.registry.resolve(block_ref) is None:
                    raise BlockReferenceError(f"Unresolved block reference: {block_ref}")
            stack.extend(node.children)


# Backward-compatible alias.
LogosParser = StackMachineParser