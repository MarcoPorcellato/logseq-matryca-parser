"""Finite authored oracles for serialization; never a production-derived truth."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from typing import Any

from logseq_matryca_parser import LogseqNode, LogseqPage

NODE_FIELDS = (
    "uuid",
    "source_uuid",
    "synthetic_id",
    "content",
    "clean_text",
    "indent_level",
    "properties",
    "wikilinks",
    "tags",
    "assets",
    "block_refs",
    "refs",
    "task_status",
    "task_priority",
    "scheduled_at",
    "deadline_at",
    "repeater",
    "parent_id",
    "left_id",
    "path",
    "source_path",
    "line_start",
    "line_end",
    "outline_path",
    "properties_order",
    "created_at",
    "updated_at",
    "children",
)
FLAT_FIELDS = NODE_FIELDS[:-1]
PARSER_IDS = (
    "10000000-0000-0000-0000-000000000001",
    "10000000-0000-0000-0000-000000000002",
    "10000000-0000-0000-0000-000000000003",
    "10000000-0000-0000-0000-000000000004",
)
NATIVE_IDS = (
    "20000000-0000-0000-0000-000000000001",
    "20000000-0000-0000-0000-000000000002",
    "20000000-0000-0000-0000-000000000003",
    "20000000-0000-0000-0000-000000000004",
)
FrozenValue = tuple[str, Any]
NodeSpec = tuple[str, str, str, int, str | None, str | None, list[str], list[int], int, int]


@dataclass(frozen=True)
class S3Recipe:
    schema: int = 1
    shape: int = 1
    text: int = 0
    order: int = 0
    tab_size: int = 2
    newline: int = 0


def validate_recipe(recipe: S3Recipe) -> None:
    """Reject invalid selectors, including bool-as-int, before constructing data."""
    for name, value, allowed in (
        ("schema", recipe.schema, (1,)),
        ("shape", recipe.shape, (0, 1, 2)),
        ("text", recipe.text, (0, 1)),
        ("order", recipe.order, (0, 1)),
        ("tab_size", recipe.tab_size, (2, 4)),
        ("newline", recipe.newline, (0, 1)),
    ):
        if type(value) is not int or value not in allowed:
            raise ValueError(f"recipe.{name}")


def encode_recipe(recipe: S3Recipe, *, producer_sha256: str, baseline: str) -> str:
    validate_recipe(recipe)
    if re.fullmatch(r"[a-f0-9]{64}", producer_sha256) is None:
        raise ValueError("recipe.producer_sha256")
    if re.fullmatch(r"[a-f0-9]{40}", baseline) is None:
        raise ValueError("recipe.baseline")
    return json.dumps(
        {
            "schema": recipe.schema,
            "shape": recipe.shape,
            "text": recipe.text,
            "order": recipe.order,
            "tab_size": recipe.tab_size,
            "newline": recipe.newline,
            "producer_sha256": producer_sha256,
            "baseline": baseline,
        },
        sort_keys=True,
    )


def _freeze(value: Any) -> FrozenValue:
    """Own exact JSON/container types and insertion order without mutable aliases."""
    if type(value) in (type(None), bool, int, float, str):
        return type(value).__name__, value
    if type(value) in (list, tuple):
        return type(value).__name__, tuple(_freeze(v) for v in value)
    if type(value) is dict:
        return "dict", tuple((_freeze(k), _freeze(v)) for k, v in value.items())
    raise ValueError("bounds.json_value")


def _thaw(value: FrozenValue) -> Any:
    kind, data = value
    if kind == "dict":
        return {_thaw(k): _thaw(v) for k, v in data}
    if kind == "list":
        return [_thaw(v) for v in data]
    if kind == "tuple":
        return tuple(_thaw(v) for v in data)
    return data


def _compare(observed: Any, expected: Any, path: str, *, ordered_maps: bool = False) -> None:
    assert type(observed) is type(expected), f"{path}.type"
    if type(expected) is dict:
        assert set(observed) == set(expected), f"{path}.keys"
        if ordered_maps:
            assert tuple(observed) == tuple(expected), f"{path}.key_order"
        for key, value in expected.items():
            _compare(observed[key], value, f"{path}.{key}", ordered_maps=ordered_maps)
    elif type(expected) in (list, tuple):
        assert len(observed) == len(expected), f"{path}.length"
        for index, value in enumerate(expected):
            _compare(observed[index], value, f"{path}[{index}]", ordered_maps=ordered_maps)
    else:
        assert observed == expected, f"{path}.value"


def assert_structured_export(observed: object, expected: object, *, surface: str) -> None:
    _compare(observed, expected, surface)


def _observe_forest(nodes: list[LogseqNode]) -> Any:
    rows = [_observe_node(node) for node in nodes]
    return tuple(rows) if type(nodes) is tuple else rows


def _observe_node(node: LogseqNode) -> dict[str, Any]:
    """Read every field explicitly; no model_dump, schema discovery or visitor."""
    return {
        "uuid": node.uuid,
        "source_uuid": node.source_uuid,
        "synthetic_id": node.synthetic_id,
        "content": node.content,
        "clean_text": node.clean_text,
        "indent_level": node.indent_level,
        "properties": node.properties,
        "wikilinks": node.wikilinks,
        "tags": node.tags,
        "assets": node.assets,
        "block_refs": node.block_refs,
        "refs": node.refs,
        "task_status": node.task_status,
        "task_priority": node.task_priority,
        "scheduled_at": node.scheduled_at,
        "deadline_at": node.deadline_at,
        "repeater": node.repeater,
        "parent_id": node.parent_id,
        "left_id": node.left_id,
        "path": node.path,
        "source_path": node.source_path,
        "line_start": node.line_start,
        "line_end": node.line_end,
        "outline_path": node.outline_path,
        "properties_order": node.properties_order,
        "created_at": node.created_at,
        "updated_at": node.updated_at,
        "children": _observe_forest(node.children),
    }


@dataclass(frozen=True)
class FrozenInputState:
    fields: FrozenValue


def freeze_input_state(page: LogseqPage) -> FrozenInputState:
    """Mutation observation only; it supplies no expected parse semantics."""
    return FrozenInputState(
        _freeze(
            {
                "title": page.title,
                "raw_content": page.raw_content,
                "properties": page.properties,
                "properties_order": page.properties_order,
                "refs": page.refs,
                "created_at": page.created_at,
                "updated_at": page.updated_at,
                "namespace_chain": page.namespace_chain,
                "source_path": page.source_path,
                "graph_root": page.graph_root,
                "tab_size": page.tab_size,
                "root_nodes": _observe_forest(page.root_nodes),
            }
        )
    )


def assert_input_state_unchanged(page: LogseqPage, before: FrozenInputState) -> None:
    _compare(
        _thaw(freeze_input_state(page).fields),
        _thaw(before.fields),
        "native.input",
        ordered_maps=True,
    )


@dataclass(frozen=True)
class StructuredImage:
    nodes: list[LogseqNode]
    nested_facts: FrozenValue
    flat_facts: FrozenValue

    @property
    def expected_nested(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = _thaw(self.nested_facts)
        return result

    @property
    def expected_flat(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = _thaw(self.flat_facts)
        return result


def _input_node(
    label: str,
    index: int,
    depth: int,
    parent: str | None,
    left: str | None,
    path: list[str],
    outline: list[int],
    start: int,
    end: int,
    recipe: S3Recipe,
    children: list[LogseqNode],
) -> LogseqNode:
    """Actual synthetic constructor, not an expected export assembled from models."""
    body = f"{label} λ\nline café" if recipe.text == 0 else f"{label} café\nline λ"
    return LogseqNode(
        uuid=PARSER_IDS[index],
        source_uuid=NATIVE_IDS[index],
        synthetic_id=False,
        content=body,
        clean_text=f"clean {label}",
        indent_level=depth,
        properties={"alpha": {"flags": [True, 1, None]}, "id": NATIVE_IDS[index], "zeta": label},
        wikilinks=["Target", "café"],
        tags=["topic"],
        assets=["synthetic/assets/icon.svg"],
        block_refs=[NATIVE_IDS[1]],
        refs=["Target", "café", "topic"],
        task_status="TODO",
        task_priority="B",
        scheduled_at=1000,
        deadline_at=2000,
        repeater="+1d",
        parent_id=parent,
        left_id=left,
        path=path,
        source_path="synthetic.md",
        line_start=start,
        line_end=end,
        outline_path=outline,
        properties_order=["id", "zeta", "alpha"] if recipe.order == 0 else ["alpha", "zeta", "id"],
        created_at=3000,
        updated_at=4000,
        children=children,
    )


def _expected_row(spec: NodeSpec, recipe: S3Recipe) -> dict[str, Any]:
    """Authored field facts, separate from actual constructor and project output."""
    label, identity, source, depth, parent, left, path, outline, start, end = spec
    return {
        "uuid": identity,
        "source_uuid": source,
        "synthetic_id": False,
        "content": f"{label} λ\nline café" if recipe.text == 0 else f"{label} café\nline λ",
        "clean_text": f"clean {label}",
        "indent_level": depth,
        "properties": {"alpha": {"flags": [True, 1, None]}, "id": source, "zeta": label},
        "wikilinks": ["Target", "café"],
        "tags": ["topic"],
        "assets": ["synthetic/assets/icon.svg"],
        "block_refs": [NATIVE_IDS[1]],
        "refs": ["Target", "café", "topic"],
        "task_status": "TODO",
        "task_priority": "B",
        "scheduled_at": 1000,
        "deadline_at": 2000,
        "repeater": "+1d",
        "parent_id": parent,
        "left_id": left,
        "path": path,
        "source_path": "synthetic.md",
        "line_start": start,
        "line_end": end,
        "outline_path": outline,
        "properties_order": ["id", "zeta", "alpha"]
        if recipe.order == 0
        else ["alpha", "zeta", "id"],
        "created_at": 3000,
        "updated_at": 4000,
    }


def structured_image(recipe: S3Recipe) -> StructuredImage:
    validate_recipe(recipe)
    p1, p2, p3, p4 = PARSER_IDS
    s1, s2, s3, s4 = NATIVE_IDS
    specs: tuple[NodeSpec, ...]
    if recipe.shape == 0:
        return StructuredImage([], _freeze([]), _freeze([]))
    if recipe.shape == 1:
        grand = _input_node(
            "Grandchild", 2, 2, p2, None, [p1, p2, p3], [1, 1, 1], 15, 18, recipe, []
        )
        child = _input_node("Child", 1, 1, p1, None, [p1, p2], [1, 1], 11, 14, recipe, [grand])
        root = _input_node("Root", 0, 0, None, None, [p1], [1], 5, 10, recipe, [child])
        second = _input_node("Second", 3, 0, None, p1, [p4], [2], 19, 22, recipe, [])
        nodes = [root, second]
        # Independent literal preorder specifications, not traversed actual nodes.
        specs = (
            ("Root", p1, s1, 0, None, None, [p1], [1], 5, 10),
            ("Child", p2, s2, 1, p1, None, [p1, p2], [1, 1], 11, 14),
            ("Grandchild", p3, s3, 2, p2, None, [p1, p2, p3], [1, 1, 1], 15, 18),
            ("Second", p4, s4, 0, None, p1, [p4], [2], 19, 22),
        )
    else:
        nodes = [
            _input_node("Same", 0, 0, None, None, [p1], [1], 5, 8, recipe, []),
            _input_node("Same", 1, 0, None, p1, [p2], [2], 9, 12, recipe, []),
        ]
        specs = (
            ("Same", p1, s1, 0, None, None, [p1], [1], 5, 8),
            ("Same", p2, s2, 0, None, p1, [p2], [2], 9, 12),
        )
    flat = [_expected_row(spec, recipe) for spec in specs]
    # Build each expected view independently from authored specs, never an export.
    nested = [_expected_row(spec, recipe) | {"children": []} for spec in specs]
    if recipe.shape == 1:
        nested[1]["children"] = [nested[2]]
        nested[0]["children"] = [nested[1]]
        nested = [nested[0], nested[3]]
    image = StructuredImage(nodes, _freeze(nested), _freeze(flat))
    admit_structured(nodes)
    return image


def assert_input_image(nodes: list[LogseqNode], image: StructuredImage) -> None:
    _compare(_observe_forest(nodes), image.expected_nested, "input", ordered_maps=True)


def _property_bounds(value: Any, depth: int = 0) -> None:
    if type(value) in (list, dict):
        if depth + 1 > 2:
            raise ValueError("bounds.property_depth")
        if len(value) > 3:
            raise ValueError("bounds.list" if type(value) is list else "bounds.keys")
        for item in value.values() if type(value) is dict else value:
            _property_bounds(item, depth + 1)
    elif type(value) not in (type(None), str, bool, int, float) or (
        type(value) is float and not math.isfinite(value)
    ):
        raise ValueError("bounds.json_value")


def admit_structured(nodes: list[LogseqNode]) -> None:
    pending = [(node, 0) for node in reversed(nodes)]
    count = 0
    while pending:
        node, depth = pending.pop()
        if depth > 2:
            raise ValueError("bounds.depth")
        count += 1
        if len(node.properties) > 3:
            raise ValueError("bounds.keys")
        for values in (
            node.wikilinks,
            node.tags,
            node.assets,
            node.block_refs,
            node.refs,
            node.path,
            node.outline_path,
            node.properties_order,
            node.children,
        ):
            if len(values) > 3:
                raise ValueError("bounds.list")
        for value in node.properties.values():
            _property_bounds(value)
        pending.extend((child, depth + 1) for child in reversed(node.children))
    if count > 4:
        raise ValueError("bounds.nodes")
    if len(json.dumps(_observe_forest(nodes), ensure_ascii=False).encode("utf-8")) > 8192:
        raise ValueError("bounds.structured_bytes")


@dataclass(frozen=True)
class NativeNode:
    slot: tuple[int, ...]
    content: str
    properties: tuple[tuple[str, str], ...]
    properties_order: tuple[str, ...]
    source_uuid: str
    indent_level: int
    line_start: int
    line_end: int
    wikilinks: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    refs: tuple[str, ...] = ()
    task_status: str | None = None
    task_priority: str | None = None


@dataclass(frozen=True)
class NativeObservation:
    raw_content: str
    properties: tuple[tuple[str, str], ...]
    properties_order: tuple[str, ...]
    refs: tuple[str, ...]
    nodes: tuple[NativeNode, ...]
    title: str = "S3 Native"


@dataclass(frozen=True)
class NativeImage:
    source: str
    page_title: str
    expected_serialized: str
    source_observation: NativeObservation
    rendered_observation: NativeObservation


def native_image(recipe: S3Recipe, *, empty: bool = False) -> NativeImage:
    validate_recipe(recipe)
    page_properties = (("alpha", "page-a"), ("title", "S3 Native"), ("zeta", "page-z"))
    page_order = ("title", "zeta", "alpha") if recipe.order == 0 else ("alpha", "title", "zeta")
    block_order = ("id", "zeta", "alpha") if recipe.order == 0 else ("alpha", "zeta", "id")
    tokens = (
        ("Root", "Child", "Grandchild", "Second", "Continuation", "Same")
        if recipe.text == 0
        else (
            "Root λ",
            "Child café",
            "Grandchild λ",
            "Second café",
            "Continuation λ",
            "Same café",
        )
    )
    root, child, grand, second, continuation, same = tokens
    lines = [] if empty else [f"{k}:: {dict(page_properties)[k]}" for k in page_order]
    facts: list[NativeNode] = []
    if not empty and recipe.shape != 0:
        lines.append("")
        layout = (
            (
                ((0,), root, 0, 0, 5, 10),
                ((0, 0), child, 1, 1, 11, 14),
                ((0, 0, 0), grand, 2, 2, 15, 18),
                ((1,), second, 0, 3, 19, 22),
            )
            if recipe.shape == 1
            else (((0,), same, 0, 0, 5, 8), ((1,), same, 0, 1, 9, 12))
        )
        for slot, label, depth, index, start, end in layout:
            first = (
                f"TODO [#B] {label} [[Target]] #topic"
                if recipe.shape == 1 and index == 0
                else label
            )
            indent = " " * (depth * recipe.tab_size)
            lines.append(f"{indent}- {first}")
            properties = (("alpha", "a"), ("id", NATIVE_IDS[index]), ("zeta", label))
            lines.extend(f"{indent}  {k}:: {dict(properties)[k]}" for k in block_order)
            content = first
            if recipe.shape == 1 and index == 0:
                lines.extend((f"  {continuation}", "  laterproperty:: literal"))
                content += f"\n  {continuation}\n  laterproperty:: literal"
            facts.append(
                NativeNode(
                    slot,
                    content,
                    properties,
                    block_order,
                    NATIVE_IDS[index],
                    depth,
                    start,
                    end,
                    ("Target",) if index == 0 and recipe.shape == 1 else (),
                    ("B", "topic") if index == 0 and recipe.shape == 1 else (),
                    ("Target", "B", "topic") if index == 0 and recipe.shape == 1 else (),
                    "TODO" if index == 0 and recipe.shape == 1 else None,
                    "B" if index == 0 and recipe.shape == 1 else None,
                )
            )
    source_lf = "\n".join(lines)
    source = source_lf.replace("\n", "\r\n") if recipe.newline else source_lf
    rendered = source_lf + "\n" if lines else ""
    props = () if empty else page_properties
    order = () if empty else page_order
    refs = ("Target", "B", "topic") if facts and recipe.shape == 1 else ()
    image = NativeImage(
        source,
        "S3 Native",
        rendered,
        NativeObservation(source, props, order, refs, tuple(facts)),
        NativeObservation(rendered, props, order, refs, tuple(facts)),
    )
    admit_native_image(image)
    return image


def admit_native_image(image: NativeImage) -> None:
    if any(len(text.encode("utf-8")) > 2048 for text in (image.source, image.expected_serialized)):
        raise ValueError("bounds.native_bytes")
    for observation in (image.source_observation, image.rendered_observation):
        if len(observation.refs) > 3 or len(observation.properties_order) > 3:
            raise ValueError("bounds.list")
        if len(observation.nodes) > 4:
            raise ValueError("bounds.nodes")
        groups = [observation.properties, *(node.properties for node in observation.nodes)]
        for properties in groups:
            if len(properties) > 3:
                raise ValueError("bounds.keys")
            if any(
                type(v) is not str or not v.strip() or "\n" in v or "\r" in v for _, v in properties
            ):
                raise ValueError("bounds.native_scalar")
        for node in observation.nodes:
            if any(
                len(v) > 3 for v in (node.wikilinks, node.tags, node.refs, node.properties_order)
            ):
                raise ValueError("bounds.list")
            if len(node.slot) > 3:
                raise ValueError("bounds.depth")
            if len(node.content.splitlines()) > 3:
                raise ValueError("bounds.continuation")


def assert_native_text(observed: str, expected: str) -> None:
    assert observed == expected, "native.serialized_text"


def assert_native_semantics(page: LogseqPage, expected: NativeObservation) -> None:
    for page_name, page_actual, page_wanted in (
        ("title", page.title, expected.title),
        ("raw_content", page.raw_content, expected.raw_content),
        ("properties", page.properties, dict(expected.properties)),
        ("properties_order", page.properties_order, list(expected.properties_order)),
        ("refs", page.refs, list(expected.refs)),
    ):
        _compare(page_actual, page_wanted, f"native.page.{page_name}")
    slots: list[tuple[tuple[int, ...], LogseqNode]] = []

    def visit(nodes: list[LogseqNode], prefix: tuple[int, ...]) -> None:
        for index, node in enumerate(nodes):
            slot = (*prefix, index)
            slots.append((slot, node))
            visit(node.children, slot)

    visit(page.root_nodes, ())
    assert len(slots) == len(expected.nodes), "native.nodes.length"
    identities = [node.uuid for _, node in slots]
    assert all(type(v) is str and v for v in identities), "native.parser_ids.nonempty"
    assert len(set(identities)) == len(identities), "native.parser_ids.unique"
    assert set(identities).isdisjoint(node.source_uuid for _, node in slots), (
        "native.identity_separation"
    )
    index_by_slot = dict(slots)
    for index, ((slot, node), wanted) in enumerate(zip(slots, expected.nodes, strict=True)):
        path = f"native.nodes[{index}]"
        assert slot == wanted.slot, f"{path}.slot"
        for name, actual, value in (
            ("content", node.content, wanted.content),
            ("properties", node.properties, dict(wanted.properties)),
            ("properties_order", node.properties_order, list(wanted.properties_order)),
            ("source_uuid", node.source_uuid, wanted.source_uuid),
            ("synthetic_id", node.synthetic_id, False),
            ("indent_level", node.indent_level, wanted.indent_level),
            ("wikilinks", node.wikilinks, list(wanted.wikilinks)),
            ("tags", node.tags, list(wanted.tags)),
            ("refs", node.refs, list(wanted.refs)),
            ("block_refs", node.block_refs, []),
            ("assets", node.assets, []),
            ("task_status", node.task_status, wanted.task_status),
            ("task_priority", node.task_priority, wanted.task_priority),
            ("line_start", node.line_start, wanted.line_start),
            ("line_end", node.line_end, wanted.line_end),
            ("outline_path", node.outline_path, [part + 1 for part in wanted.slot]),
            ("parent_id", node.parent_id, index_by_slot[slot[:-1]].uuid if len(slot) > 1 else None),
            (
                "left_id",
                node.left_id,
                index_by_slot[(*slot[:-1], slot[-1] - 1)].uuid if slot[-1] else None,
            ),
            ("path", node.path, [index_by_slot[slot[:n]].uuid for n in range(1, len(slot) + 1)]),
        ):
            _compare(actual, value, f"{path}.{name}")
