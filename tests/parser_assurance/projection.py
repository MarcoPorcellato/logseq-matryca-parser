"""Versioned, test-only semantic projections for the compatibility corpus."""

from __future__ import annotations

import json
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


def _semantic_properties(properties: Mapping[str, Any]) -> dict[str, Any]:
    projected: dict[str, Any] = {}
    for key in sorted(properties):
        value = properties[key]
        if key not in _REF_PROPERTY_KEYS:
            projected[key] = _canonical_value(value)
        elif isinstance(value, (set, frozenset)):
            normalized = [_normalize_ref_token(item) for item in value]
            projected[key] = sorted(
                normalized,
                key=lambda item: json.dumps(item, sort_keys=True),
            )
        elif isinstance(value, (list, tuple)):
            projected[key] = [_normalize_ref_token(item) for item in value]
        else:
            projected[key] = _normalize_ref_token(value)
    return projected


def _declared_tag_tokens(properties: Mapping[str, Any]) -> set[str]:
    """Return only tag tokens introduced by tag properties."""
    tokens: set[str] = set()
    semantic = _semantic_properties(properties)
    for key in ("tags", "page-tags"):
        value = semantic.get(key)
        values = value if isinstance(value, list) else [value]
        for item in values:
            if not isinstance(item, str):
                continue
            tokens.update(part.strip() for part in item.split(",") if part.strip())
    return tokens


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
    property_tag_tokens = _declared_tag_tokens(node.properties)
    projected: dict[str, Any] = {
        "source_uuid": node.source_uuid,
        "synthetic_id": node.synthetic_id,
        "content": node.content,
        "clean_text": node.clean_text,
        "indent_level": node.indent_level,
        "properties": _semantic_properties(node.properties),
        "properties_order": list(node.properties_order),
        "wikilinks": [token for token in node.wikilinks if token not in property_tag_tokens],
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
