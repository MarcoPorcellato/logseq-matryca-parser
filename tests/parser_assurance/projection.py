"""Versioned, test-only semantic projections for the compatibility corpus."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping
from typing import Any, Literal, TypedDict, cast

from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage

ProjectionProfile = Literal["exact_parse_v1", "semantic_roundtrip_v1"]


class IdentityPolicy(TypedDict):
    """Fixture-specific identity guarantees used by the round-trip profile."""

    synthetic_uuid: Literal["stable", "recomputed"]
    source_uuid: Literal["preserve", "absent"]
    relations: Literal["direct_ids", "outline_paths"]


_CREATED_AT_KEYS = frozenset({"created_at", "created-at", "createdat"})
_UPDATED_AT_KEYS = frozenset({"updated_at", "updated-at", "updatedat"})
_REF_PROPERTY_KEYS = frozenset({"tags", "page-tags", "alias", "aliases"})


def _canonical_value(value: Any) -> Any:
    """Return a JSON-safe value without preserving incidental mapping order."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _canonical_value(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        canonical = [_canonical_value(item) for item in value]
        return sorted(canonical, key=lambda item: json.dumps(item, sort_keys=True))
    raise TypeError(f"unsupported projection value: {type(value).__name__}")


def _page_timestamp(page: LogseqPage, keys: frozenset[str], value: int | None) -> int | None:
    """Keep a page timestamp only when it was declared in Markdown properties."""
    return value if keys.intersection(page.properties) else None


def _normalize_ref_token(value: object) -> object:
    if not isinstance(value, str):
        return _canonical_value(value)
    token = value.strip()
    if token.startswith("[[") and token.endswith("]]"):
        token = token[2:-2]
    return token.lstrip("#")


def _split_reference_segments(value: str) -> list[str]:
    """Split comma-separated property references without splitting ``[[...]]``."""
    segments: list[str] = []
    start = 0
    reference_depth = 0
    index = 0
    while index < len(value):
        if value.startswith("[[", index):
            reference_depth += 1
            index += 2
            continue
        if reference_depth and value.startswith("]]", index):
            reference_depth -= 1
            index += 2
            continue
        if value[index] == "," and not reference_depth:
            segments.append(value[start:index])
            start = index + 1
        index += 1
    segments.append(value[start:])
    return [segment for segment in segments if segment.strip()]


def _reference_property_fragments(value: object) -> list[object]:
    """Return deterministic raw segments from a reference-shaped value."""
    if isinstance(value, (set, frozenset)):
        values: list[object] = sorted(
            value,
            key=lambda item: json.dumps(_canonical_value(item), sort_keys=True),
        )
    elif isinstance(value, (list, tuple)):
        values = list(value)
    else:
        values = [value]

    fragments: list[object] = []
    for item in values:
        fragments.extend(_split_reference_segments(item) if isinstance(item, str) else [item])
    return fragments


def _reference_property_sequence(value: object) -> list[object]:
    """Return a deterministic canonical sequence for a reference-shaped value."""
    return [_normalize_ref_token(fragment) for fragment in _reference_property_fragments(value)]


def _explicit_wikilinks(value: str) -> list[str]:
    """Independently collect unescaped ``[[target]]`` references from one fragment."""
    tokens: list[str] = []
    index = 0
    while index < len(value):
        if value.startswith("[[", index) and (index == 0 or value[index - 1] != "\\"):
            end = value.find("]]", index + 2)
            if end >= 0:
                target = value[index + 2 : end].split("#", 1)[0]
                if target:
                    tokens.append(target)
                index = end + 2
                continue
        index += 1
    return tokens


def _property_wikilink_occurrences(properties: Mapping[str, Any]) -> Counter[str]:
    """Count graph wikilinks attributable to properties without parser helper reuse."""
    occurrences: Counter[str] = Counter()
    for key, value in properties.items():
        if key in _REF_PROPERTY_KEYS:
            for fragment in _reference_property_fragments(value):
                if not isinstance(fragment, str):
                    continue
                token = _normalize_ref_token(fragment)
                if key in {"alias", "aliases"} and isinstance(token, str) and token:
                    occurrences[token] += 1
                occurrences.update(_explicit_wikilinks(fragment))
            continue
        fragments = [value] if isinstance(value, str) else value if isinstance(value, list) else []
        for fragment in fragments:
            if isinstance(fragment, str):
                occurrences.update(_explicit_wikilinks(fragment))
    return occurrences


def _semantic_properties(properties: Mapping[str, Any]) -> dict[str, Any]:
    projected: dict[str, Any] = {}
    for key in sorted(properties):
        value = properties[key]
        if key not in _REF_PROPERTY_KEYS:
            projected[key] = _canonical_value(value)
        else:
            projected[key] = _reference_property_sequence(value)
    return projected


def _content_wikilinks(node: LogseqNode) -> list[str]:
    """Remove only counted property-origin links, preserving equal content links."""
    property_occurrences = _property_wikilink_occurrences(node.properties)
    content_reversed: list[str] = []
    for token in reversed(node.wikilinks):
        if property_occurrences[token]:
            property_occurrences[token] -= 1
        else:
            content_reversed.append(token)
    return list(reversed(content_reversed))


def _exact_node(node: LogseqNode) -> dict[str, Any]:
    return {
        "uuid": node.uuid,
        "source_uuid": node.source_uuid,
        "synthetic_id": node.synthetic_id,
        "content": node.content,
        "clean_text": node.clean_text,
        "indent_level": node.indent_level,
        "properties": _canonical_value(node.properties),
        "properties_order": list(node.properties_order),
        "wikilinks": list(node.wikilinks),
        "tags": list(node.tags),
        "assets": list(node.assets),
        "block_refs": list(node.block_refs),
        "refs": list(node.refs),
        "task_status": node.task_status,
        "task_priority": node.task_priority,
        "scheduled_at": node.scheduled_at,
        "deadline_at": node.deadline_at,
        "repeater": node.repeater,
        "parent_id": node.parent_id,
        "left_id": node.left_id,
        "path": list(node.path),
        "line_start": node.line_start,
        "line_end": node.line_end,
        "outline_path": list(node.outline_path),
        "created_at": node.created_at,
        "updated_at": node.updated_at,
        "children": [_exact_node(child) for child in node.children],
    }


def _index_outline_paths(page: LogseqPage) -> dict[str, list[int]]:
    index: dict[str, list[int]] = {}

    def visit(node: LogseqNode) -> None:
        index[node.uuid] = list(node.outline_path)
        for child in node.children:
            visit(child)

    for root in page.root_nodes:
        visit(root)
    return index


def _semantic_node(
    node: LogseqNode,
    *,
    identity_policy: IdentityPolicy,
    outline_index: Mapping[str, list[int]],
) -> dict[str, Any]:
    projected: dict[str, Any] = {
        "source_uuid": node.source_uuid,
        "synthetic_id": node.synthetic_id,
        "content": node.content,
        "clean_text": node.clean_text,
        "indent_level": node.indent_level,
        "properties": _semantic_properties(node.properties),
        "properties_order": list(node.properties_order),
        "wikilinks": _content_wikilinks(node),
        "tags": list(node.tags),
        "assets": list(node.assets),
        "block_refs": list(node.block_refs),
        "refs": list(node.refs),
        "task_status": node.task_status,
        "task_priority": node.task_priority,
        "scheduled_at": node.scheduled_at,
        "deadline_at": node.deadline_at,
        "repeater": node.repeater,
        "outline_path": list(node.outline_path),
        "created_at": node.created_at,
        "updated_at": node.updated_at,
    }
    if identity_policy["synthetic_uuid"] == "stable":
        projected["uuid"] = node.uuid
    if identity_policy["relations"] == "direct_ids":
        projected["parent_id"] = node.parent_id
        projected["left_id"] = node.left_id
        projected["path"] = list(node.path)
    else:
        projected["parent_outline_path"] = (
            outline_index.get(node.parent_id) if node.parent_id is not None else None
        )
        projected["left_outline_path"] = (
            outline_index.get(node.left_id) if node.left_id is not None else None
        )
    projected["children"] = [
        _semantic_node(
            child,
            identity_policy=identity_policy,
            outline_index=outline_index,
        )
        for child in node.children
    ]
    return projected


def project_page(
    page: LogseqPage,
    *,
    profile: ProjectionProfile,
    identity_policy: IdentityPolicy | None = None,
) -> dict[str, Any]:
    """Project a parsed page under one explicit, versioned assurance profile."""
    base: dict[str, Any] = {
        "profile": profile,
        "snapshot_schema_version": 1,
        "page": {
            "title": page.title,
            "properties": _canonical_value(page.properties),
            "properties_order": list(page.properties_order),
            "refs": list(page.refs),
            "created_at": _page_timestamp(page, _CREATED_AT_KEYS, page.created_at),
            "updated_at": _page_timestamp(page, _UPDATED_AT_KEYS, page.updated_at),
            "namespace_chain": list(page.namespace_chain),
            "tab_size": page.tab_size,
        },
    }
    projected_page = cast(dict[str, Any], base["page"])
    if profile == "exact_parse_v1":
        projected_page["root_nodes"] = [_exact_node(node) for node in page.root_nodes]
        return base
    if profile != "semantic_roundtrip_v1":
        raise ValueError(f"unsupported projection profile: {profile}")
    if identity_policy is None:
        raise ValueError("semantic_roundtrip_v1 requires an identity policy")
    projected_page["properties"] = _semantic_properties(page.properties)
    outline_index = _index_outline_paths(page)
    projected_page["root_nodes"] = [
        _semantic_node(
            node,
            identity_policy=identity_policy,
            outline_index=outline_index,
        )
        for node in page.root_nodes
    ]
    return base
