"""Independent, bounded serialization/export integrity and oracle calibration."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any, TypeVar

import pytest
from hypothesis import Phase, given, settings
from hypothesis import strategies as st

from logseq_matryca_parser import (
    ForgeExporter,
    LogseqNode,
    LogseqPage,
    StackMachineParser,
    serialize_logseq_page,
)
from tests.parser_assurance.invariants import assert_tree_invariants
from tests.parser_assurance.projection import IdentityPolicy, project_page
from tests.parser_assurance.serialization_integrity import (
    S3Recipe,
    admit_native_image,
    admit_structured,
    assert_input_image,
    assert_input_state_unchanged,
    assert_native_semantics,
    assert_native_text,
    assert_structured_export,
    encode_recipe,
    freeze_input_state,
    native_image,
    structured_image,
    validate_recipe,
)

P1 = "10000000-0000-0000-0000-000000000001"
P2 = "10000000-0000-0000-0000-000000000002"
P3 = "10000000-0000-0000-0000-000000000003"
P4 = "10000000-0000-0000-0000-000000000004"
S1 = "20000000-0000-0000-0000-000000000001"
S2 = "20000000-0000-0000-0000-000000000002"


def literal_fields(
    label: str,
    identity: str,
    native_id: str,
    *,
    depth: int,
    parent: str | None,
    left: str | None,
    path: list[str],
    outline: list[int],
    start: int,
    end: int,
) -> dict[str, Any]:
    """Handwritten observation, independent of the image constructors/oracle."""
    return {
        "uuid": identity,
        "source_uuid": native_id,
        "synthetic_id": False,
        "content": f"{label} λ\nline café",
        "clean_text": f"clean {label}",
        "indent_level": depth,
        "properties": {"alpha": {"flags": [True, 1, None]}, "id": native_id, "zeta": label},
        "wikilinks": ["Target", "café"],
        "tags": ["topic"],
        "assets": ["synthetic/assets/icon.svg"],
        "block_refs": [S2],
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
        "properties_order": ["id", "zeta", "alpha"],
        "created_at": 3000,
        "updated_at": 4000,
    }


def literal_rich() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Literal preorder rows protect every current field, including deep nodes."""
    root = literal_fields(
        "Root", P1, S1, depth=0, parent=None, left=None, path=[P1], outline=[1], start=5, end=10
    )
    child = literal_fields(
        "Child",
        P2,
        S2,
        depth=1,
        parent=P1,
        left=None,
        path=[P1, P2],
        outline=[1, 1],
        start=11,
        end=14,
    )
    grand = literal_fields(
        "Grandchild",
        P3,
        "20000000-0000-0000-0000-000000000003",
        depth=2,
        parent=P2,
        left=None,
        path=[P1, P2, P3],
        outline=[1, 1, 1],
        start=15,
        end=18,
    )
    second = literal_fields(
        "Second",
        P4,
        "20000000-0000-0000-0000-000000000004",
        depth=0,
        parent=None,
        left=P1,
        path=[P4],
        outline=[2],
        start=19,
        end=22,
    )
    # Flat and nested literals are separately owned, not product transformations.
    flat = deepcopy([root, child, grand, second])
    grand["children"] = []
    child["children"] = [grand]
    root["children"] = [child]
    second["children"] = []
    return [root, second], flat


def test_calibration_recipe_records_only_validated_selectors() -> None:
    """Catch missing validation or selector/source leakage in replay evidence."""
    recipe = S3Recipe()
    validate_recipe(recipe)
    assert json.loads(encode_recipe(recipe, producer_sha256="a" * 64, baseline="b" * 40)) == {
        "schema": 1,
        "shape": 1,
        "text": 0,
        "order": 0,
        "tab_size": 2,
        "newline": 0,
        "producer_sha256": "a" * 64,
        "baseline": "b" * 40,
    }


@pytest.mark.parametrize(
    "field,bad",
    [
        ("schema", 2),
        ("schema", True),
        ("shape", -1),
        ("shape", 3),
        ("text", 2),
        ("order", -1),
        ("tab_size", 3),
        ("newline", 2),
        ("shape", True),
    ],
)
def test_calibration_recipe_rejects_invalid_selector_before_work(field: str, bad: int) -> None:
    with pytest.raises(ValueError, match="^recipe\\." + field + "$"):
        validate_recipe(replace(S3Recipe(), **{field: bad}))


def test_calibration_rich_and_empty_fields_match_handwritten_observations() -> None:
    image = structured_image(S3Recipe())
    nested, flat = literal_rich()
    assert_structured_export(image.expected_nested, nested, surface="calibration")
    assert_structured_export(image.expected_flat, flat, surface="calibration")
    assert_input_image(image.nodes, image)
    empty = structured_image(S3Recipe(shape=0))
    assert empty.nodes == empty.expected_nested == empty.expected_flat == []
    equal = structured_image(S3Recipe(shape=2))
    assert equal.nodes[0].content == equal.nodes[1].content == "Same λ\nline café"
    assert [(n.uuid, n.source_uuid, n.outline_path, n.left_id) for n in equal.nodes] == [
        (P1, S1, [1], None),
        (P2, S2, [2], P1),
    ]
    assert_input_image(equal.nodes, equal)


JSON_FAULTS = (
    ("hierarchy", "json[0].children.length"),
    ("content", "json[0].content.value"),
    ("uuid", "json[0].uuid.value"),
    ("source_uuid", "json[0].source_uuid.value"),
    ("synthetic_id", "json[0].synthetic_id.value"),
    ("path", "json[0].path.length"),
    ("left_id", "json[1].left_id.type"),
    ("refs", "json[0].refs.length"),
    ("bool_int", "json[0].properties.alpha.flags[0].type"),
    ("properties_order", "json[0].properties_order[0].value"),
    ("missing", "json[0].keys"),
    ("extra", "json[0].keys"),
)


@pytest.mark.parametrize("fault,message", JSON_FAULTS)
def test_calibration_json_controls_reject_designated_corruption(fault: str, message: str) -> None:
    observed, _ = literal_rich()
    expected = structured_image(S3Recipe()).expected_nested
    assert_structured_export(observed, expected, surface="json")
    if fault == "hierarchy":
        observed[0]["children"] = []
    elif fault == "content":
        observed[0]["content"] = "Root lambda\nline cafe"
    elif fault in {"uuid", "source_uuid"}:
        observed[0][fault] = "changed"
    elif fault == "synthetic_id":
        observed[0][fault] = True
    elif fault == "path":
        observed[0][fault] = []
    elif fault == "left_id":
        observed[1][fault] = None
    elif fault == "refs":
        observed[0][fault] = []
    elif fault == "bool_int":
        observed[0]["properties"]["alpha"]["flags"][0] = 1
    elif fault == "properties_order":
        observed[0][fault] = ["alpha", "id", "zeta"]
    elif fault == "missing":
        del observed[0]["created_at"]
    else:
        observed[0]["unexpected"] = None
    with pytest.raises(AssertionError, match="^" + re.escape(message) + "$") as caught:
        assert_structured_export(observed, expected, surface="json")
    assert str(caught.value) == message


@pytest.mark.parametrize(
    "fault,message",
    [
        ("preorder", "flat[0].uuid.value"),
        ("children", "flat[0].keys"),
        ("span", "flat[0].line_end.value"),
    ],
)
def test_calibration_flat_controls_reject_designated_corruption(fault: str, message: str) -> None:
    _, observed = literal_rich()
    expected = structured_image(S3Recipe()).expected_flat
    assert_structured_export(observed, expected, surface="flat")
    if fault == "preorder":
        observed[0], observed[1] = observed[1], observed[0]
    elif fault == "children":
        observed[0]["children"] = []
    else:
        observed[0]["line_end"] = 99
    with pytest.raises(AssertionError, match="^" + re.escape(message) + "$") as caught:
        assert_structured_export(observed, expected, surface="flat")
    assert str(caught.value) == message


def literal_native_page() -> LogseqPage:
    """Handwritten native semantic baseline; no parse/serialize/export call."""
    content = "TODO [#B] Root [[Target]] #topic\n  Continuation\n  laterproperty:: literal"
    root = LogseqNode(
        uuid=P1,
        source_uuid=S1,
        synthetic_id=False,
        content=content,
        clean_text="synthetic clean",
        indent_level=0,
        properties={"alpha": "a", "id": S1, "zeta": "Root"},
        properties_order=["id", "zeta", "alpha"],
        wikilinks=["Target"],
        tags=["B", "topic"],
        refs=["Target", "B", "topic"],
        task_status="TODO",
        task_priority="B",
        path=[P1],
        outline_path=[1],
        line_start=5,
        line_end=10,
    )
    child = LogseqNode(
        uuid=P2,
        source_uuid=S2,
        synthetic_id=False,
        content="Child",
        clean_text="Child",
        indent_level=1,
        properties={"alpha": "a", "id": S2, "zeta": "Child"},
        properties_order=["id", "zeta", "alpha"],
        parent_id=P1,
        path=[P1, P2],
        outline_path=[1, 1],
        line_start=11,
        line_end=14,
    )
    grand = LogseqNode(
        uuid=P3,
        source_uuid="20000000-0000-0000-0000-000000000003",
        synthetic_id=False,
        content="Grandchild",
        clean_text="Grandchild",
        indent_level=2,
        properties={
            "alpha": "a",
            "id": "20000000-0000-0000-0000-000000000003",
            "zeta": "Grandchild",
        },
        properties_order=["id", "zeta", "alpha"],
        parent_id=P2,
        path=[P1, P2, P3],
        outline_path=[1, 1, 1],
        line_start=15,
        line_end=18,
    )
    second = LogseqNode(
        uuid=P4,
        source_uuid="20000000-0000-0000-0000-000000000004",
        synthetic_id=False,
        content="Second",
        clean_text="Second",
        indent_level=0,
        properties={"alpha": "a", "id": "20000000-0000-0000-0000-000000000004", "zeta": "Second"},
        properties_order=["id", "zeta", "alpha"],
        left_id=P1,
        path=[P4],
        outline_path=[2],
        line_start=19,
        line_end=22,
    )
    child.children.append(grand)
    root.children.append(child)
    return LogseqPage(
        title="S3 Native",
        raw_content=native_literal_source(),
        properties={"alpha": "page-a", "title": "S3 Native", "zeta": "page-z"},
        properties_order=["title", "zeta", "alpha"],
        refs=["Target", "B", "topic"],
        root_nodes=[root, second],
    )


def native_literal_source() -> str:
    return (
        "title:: S3 Native\nzeta:: page-z\nalpha:: page-a\n\n"
        "- TODO [#B] Root [[Target]] #topic\n"
        "  id:: 20000000-0000-0000-0000-000000000001\n  zeta:: Root\n  alpha:: a\n"
        "  Continuation\n  laterproperty:: literal\n"
        "  - Child\n    id:: 20000000-0000-0000-0000-000000000002\n    zeta:: Child\n    alpha:: a\n"
        "    - Grandchild\n      id:: 20000000-0000-0000-0000-000000000003\n      zeta:: Grandchild\n      alpha:: a\n"
        "- Second\n  id:: 20000000-0000-0000-0000-000000000004\n  zeta:: Second\n  alpha:: a"
    )


def test_calibration_native_text_and_semantics_are_independent_literals() -> None:
    image = native_image(S3Recipe())
    assert image.source == native_literal_source()
    assert image.expected_serialized == native_literal_source() + "\n"
    assert_native_semantics(literal_native_page(), image.source_observation)
    assert_native_text(native_literal_source() + "\n", image.expected_serialized)


@pytest.mark.parametrize(
    "fault,message",
    [
        ("metadata", "native.page.properties.keys"),
        ("id", "native.nodes[0].source_uuid.type"),
        ("prose", "native.nodes[0].properties.keys"),
    ],
)
def test_calibration_native_controls_reject_designated_corruption(fault: str, message: str) -> None:
    page = literal_native_page()
    expected = native_image(S3Recipe()).source_observation
    assert_native_semantics(page, expected)
    if fault == "metadata":
        del page.properties["zeta"]
    elif fault == "id":
        page = page.model_copy(
            update={
                "root_nodes": [
                    page.root_nodes[0].model_copy(update={"source_uuid": None}),
                    page.root_nodes[1],
                ]
            }
        )
    else:
        page.root_nodes[0].properties["laterproperty"] = "literal"
    with pytest.raises(AssertionError, match="^" + re.escape(message) + "$") as caught:
        assert_native_semantics(page, expected)
    assert str(caught.value) == message


def test_calibration_authored_input_mutation_is_rejected() -> None:
    image = structured_image(S3Recipe())
    assert_input_image(image.nodes, image)
    image.nodes[0].properties["alpha"]["flags"][0] = 1
    message = "input[0].properties.alpha.flags[0].type"
    with pytest.raises(AssertionError, match="^" + re.escape(message) + "$") as caught:
        assert_input_image(image.nodes, image)
    assert str(caught.value) == message


def test_calibration_native_metadata_after_prose_is_rejected() -> None:
    expected = native_literal_source() + "\n"
    assert_native_text(expected, native_image(S3Recipe()).expected_serialized)
    misplaced = expected.replace("  alpha:: a\n  Continuation", "  Continuation\n  alpha:: a", 1)
    with pytest.raises(AssertionError, match="^native.serialized_text$") as caught:
        assert_native_text(misplaced, expected)
    assert str(caught.value) == "native.serialized_text"


@pytest.mark.parametrize(
    "fault,message",
    [
        ("clean", "native.input.root_nodes[0].clean_text.value"),
        ("identity", "native.input.root_nodes[0].uuid.value"),
        ("page_only", "native.input.properties.alpha.value"),
    ],
)
def test_calibration_full_state_native_mutation_controls(fault: str, message: str) -> None:
    page = literal_native_page()
    if fault == "page_only":
        page = page.model_copy(update={"root_nodes": []})
    before = freeze_input_state(page)
    assert_input_state_unchanged(page, before)
    if fault == "clean":
        page = page.model_copy(
            update={
                "root_nodes": [
                    page.root_nodes[0].model_copy(update={"clean_text": "changed"}),
                    page.root_nodes[1],
                ]
            }
        )
    elif fault == "identity":
        root, second = page.root_nodes
        child = root.children[0]
        grand = child.children[0].model_copy(
            update={"parent_id": "new-child", "path": ["new-root", "new-child", P3]}
        )
        child = child.model_copy(
            update={
                "uuid": "new-child",
                "parent_id": "new-root",
                "path": ["new-root", "new-child"],
                "children": [grand],
            }
        )
        root = root.model_copy(
            update={"uuid": "new-root", "path": ["new-root"], "children": [child]}
        )
        page = page.model_copy(
            update={"root_nodes": [root, second.model_copy(update={"left_id": "new-root"})]}
        )
    else:
        page.properties["alpha"] = "changed"
    with pytest.raises(AssertionError, match="^" + re.escape(message) + "$") as caught:
        assert_input_state_unchanged(page, before)
    assert str(caught.value) == message


@pytest.mark.parametrize(
    "bad,message",
    [
        ("nodes", "bounds.nodes"),
        ("depth", "bounds.depth"),
        ("keys", "bounds.keys"),
        ("list", "bounds.list"),
        ("nesting", "bounds.property_depth"),
        ("bytes", "bounds.structured_bytes"),
    ],
)
def test_calibration_structured_bounds_reject_before_product_calls(bad: str, message: str) -> None:
    nodes = structured_image(S3Recipe()).nodes
    admit_structured(nodes)
    if bad == "nodes":
        nodes.extend([nodes[1], nodes[1], nodes[1]])
    elif bad == "depth":
        nodes[0].children[0].children[0].children.append(nodes[1])
    elif bad == "keys":
        nodes[0].properties["fourth"] = "value"
    elif bad == "list":
        nodes[0].refs.append("fourth")
    elif bad == "nesting":
        nodes[0].properties["alpha"] = {"a": {"b": [1]}}
    else:
        nodes[0].properties["zeta"] = "x" * 8193
    with pytest.raises(ValueError, match="^" + re.escape(message) + "$"):
        admit_structured(nodes)


@pytest.mark.parametrize("field", ["source", "expected_serialized"])
def test_calibration_native_utf8_size_bound(field: str) -> None:
    image = native_image(S3Recipe())
    admit_native_image(image)
    with pytest.raises(ValueError, match="^bounds.native_bytes$"):
        oversized = (
            replace(image, source="λ" * 1025)
            if field == "source"
            else replace(image, expected_serialized="λ" * 1025)
        )
        admit_native_image(oversized)


def test_calibration_native_empty_page_only_and_equal_literals() -> None:
    recipe = S3Recipe(shape=0)
    empty = native_image(recipe, empty=True)
    assert empty.source == empty.expected_serialized == ""
    assert empty.source_observation.properties == empty.source_observation.nodes == ()
    page_only = native_image(recipe)
    assert page_only.source == "title:: S3 Native\nzeta:: page-z\nalpha:: page-a"
    assert page_only.expected_serialized == "title:: S3 Native\nzeta:: page-z\nalpha:: page-a\n"
    equal = native_image(S3Recipe(shape=2))
    assert equal.source == (
        "title:: S3 Native\nzeta:: page-z\nalpha:: page-a\n\n"
        "- Same\n  id:: 20000000-0000-0000-0000-000000000001\n  zeta:: Same\n  alpha:: a\n"
        "- Same\n  id:: 20000000-0000-0000-0000-000000000002\n  zeta:: Same\n  alpha:: a"
    )
    assert [
        (n.slot, n.source_uuid, n.line_start, n.line_end) for n in equal.source_observation.nodes
    ] == [
        ((0,), S1, 5, 8),
        ((1,), S2, 9, 12),
    ]


@pytest.mark.parametrize(
    "fault,message",
    [
        ("keys", "bounds.keys"),
        ("depth", "bounds.depth"),
        ("nodes", "bounds.nodes"),
        ("continuation", "bounds.continuation"),
        ("scalar", "bounds.native_scalar"),
        ("array", "bounds.list"),
    ],
)
def test_calibration_native_admission_limits(fault: str, message: str) -> None:
    image = native_image(S3Recipe())
    observation = image.source_observation
    node = observation.nodes[0]
    if fault == "keys":
        node = replace(node, properties=(*node.properties, ("fourth", "x")))
    elif fault == "depth":
        node = replace(node, slot=(0, 0, 0, 0))
    elif fault == "nodes":
        observation = replace(observation, nodes=(*observation.nodes, node))
    elif fault == "continuation":
        node = replace(node, content="a\nb\nc\nd")
    elif fault == "scalar":
        node = replace(node, properties=(("alpha", ""),))
    else:
        node = replace(node, refs=("a", "b", "c", "d"))
    if fault != "nodes":
        observation = replace(observation, nodes=(node, *observation.nodes[1:]))
    with pytest.raises(ValueError, match="^" + re.escape(message) + "$"):
        admit_native_image(replace(image, source_observation=observation))


BASELINE = "3d8a3d06124710de44367908f9000206604f6d28"
IDENTITY_POLICY: IdentityPolicy = {
    "synthetic_uuid": "recomputed",
    "source_uuid": "preserve",
    "relations": "outline_paths",
}


def producer_digest() -> str:
    helper = Path(__file__).parent / "parser_assurance" / "serialization_integrity.py"
    return hashlib.sha256(helper.read_bytes()).hexdigest()


@pytest.mark.parametrize("shape", [0, 1, 2])
def test_fixed_structured_preserves_full_fields_and_does_not_alias_input(
    shape: int,
    record_property: Callable[[str, object], None],
) -> None:
    """Catch visitor field loss, topology flattening, identity swaps and writable aliases."""
    recipe = S3Recipe(shape=shape)
    evidence = InvocationEvidence()
    evidence.replay = encode_recipe(recipe, producer_sha256=producer_digest(), baseline=BASELINE)
    try:
        evidence.run(lambda: exercise_structured(recipe, evidence))
    finally:
        record_property("s3_counts", evidence.record("fixed_structured"))


@pytest.mark.parametrize("empty,shape", [(True, 0), (False, 0), (False, 1)])
@pytest.mark.parametrize("tab_size", [2, 4])
@pytest.mark.parametrize("newline", [0, 1])
def test_fixed_native_preserves_independent_semantics_and_all_input_fields(
    empty: bool,
    shape: int,
    tab_size: int,
    newline: int,
    record_property: Callable[[str, object], None],
) -> None:
    """Catch scalar metadata/prose loss, newline/span errors and serializer mutation."""
    recipe = S3Recipe(shape=shape, tab_size=tab_size, newline=newline)
    evidence = InvocationEvidence()
    evidence.replay = encode_recipe(recipe, producer_sha256=producer_digest(), baseline=BASELINE)
    try:
        evidence.run(lambda: exercise_native(recipe, evidence, empty=empty))
    finally:
        record_property("s3_counts", evidence.record("fixed_native"))


def test_harness_body_25_is_refused_before_callback() -> None:
    evidence = InvocationEvidence()
    invocations: list[int] = []
    for _ in range(24):
        evidence.admit(lambda: invocations.append(1))
    with pytest.raises(AssertionError, match="^harness.body_budget$"):
        evidence.admit(lambda: invocations.append(2))
    assert invocations == [1] * 24
    assert evidence.evaluations == 24
    assert evidence.first_failure is not None
    assert evidence.first_failure["stage"] == "body_admission"
    assert evidence.calls == {"parser": 0, "serializer": 0, "json": 0, "flat": 0}


def test_harness_first_failure_survives_later_success_and_failure() -> None:
    evidence = InvocationEvidence()
    evidence.replay = "first synthetic selectors"
    evidence.stage = "first"
    with pytest.raises(ValueError, match="first"):
        evidence.run(lambda: (_ for _ in ()).throw(ValueError("first")))
    first = deepcopy(evidence.first_failure)
    evidence.replay = "second synthetic selectors"
    evidence.run(lambda: None)
    with pytest.raises(RuntimeError, match="later"):
        evidence.run(lambda: (_ for _ in ()).throw(RuntimeError("later")))
    assert evidence.first_failure == first
    assert evidence.first_failure is not None
    assert evidence.first_failure["recipe"] == "first synthetic selectors"
    assert evidence.first_failure["stage"] == "first"


def test_harness_admission_failure_precedes_product_callback() -> None:
    evidence = InvocationEvidence()
    reached: list[int] = []

    def body() -> None:
        evidence.stage = "recipe_admission"
        validate_recipe(S3Recipe(shape=3))
        evidence.call("parser", lambda: reached.append(1))

    with pytest.raises(ValueError, match="^recipe.shape$"):
        evidence.admit(body)
    assert reached == []
    assert evidence.calls["parser"] == evidence.completed["parser"] == 0
    assert evidence.first_failure is not None
    assert evidence.first_failure["stage"] == "recipe_admission"


def test_harness_product_exception_retains_attempt_count_and_recipe() -> None:
    evidence = InvocationEvidence()
    evidence.replay = encode_recipe(S3Recipe(), producer_sha256="a" * 64, baseline=BASELINE)
    with pytest.raises(RuntimeError, match="synthetic product failure"):
        evidence.run(
            lambda: evidence.call(
                "parser", lambda: (_ for _ in ()).throw(RuntimeError("synthetic product failure"))
            )
        )
    assert evidence.calls["parser"] == 1
    assert evidence.completed["parser"] == 0
    assert evidence.first_failure is not None
    assert evidence.first_failure["recipe"] == evidence.replay
    assert evidence.first_failure["stage"] == "call.parser"
    assert json.loads(evidence.record("calibration"))["first_failure"] == evidence.first_failure


T = TypeVar("T")


class InvocationEvidence:
    """Source-accounted calls and first failure, not runtime instrumentation."""

    def __init__(self) -> None:
        self.calls = dict.fromkeys(("parser", "serializer", "json", "flat"), 0)
        self.completed = self.calls.copy()
        self.evaluations = 0
        self.stage = "admission"
        self.replay: str | None = None
        self.first_failure: dict[str, Any] | None = None

    def run(self, callback: Callable[[], None]) -> None:
        try:
            callback()
        except BaseException as failure:
            if self.first_failure is None:
                self.first_failure = {
                    "stage": self.stage,
                    "recipe": self.replay,
                    "failure_type": type(failure).__name__,
                    "calls": self.calls.copy(),
                    "completed": self.completed.copy(),
                }
            raise

    def admit(self, callback: Callable[[], None]) -> None:
        def admitted() -> None:
            self.stage = "body_admission"
            if self.evaluations >= 24:
                raise AssertionError("harness.body_budget")
            self.evaluations += 1
            callback()

        self.run(admitted)

    def call(self, name: str, callback: Callable[[], T]) -> T:
        self.stage = f"call.{name}"
        self.calls[name] += 1
        result = callback()
        self.completed[name] += 1
        return result

    def record(self, kind: str) -> str:
        return json.dumps(
            {
                "kind": kind,
                "calls": self.calls,
                "completed": self.completed,
                "admissions": self.evaluations,
                "stage": self.stage,
                "recipe": self.replay,
                "first_failure": self.first_failure,
                "baseline_reference": BASELINE,
                "producer_sha256": producer_digest(),
                "test_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "lock_sha256": hashlib.sha256(
                    (Path(__file__).parents[1] / "uv.lock").read_bytes()
                ).hexdigest(),
            },
            sort_keys=True,
        )


def exercise_structured(recipe: S3Recipe, evidence: InvocationEvidence) -> None:
    evidence.stage = "structured.fixture_admission"
    image = structured_image(recipe)
    evidence.stage = "structured.input"
    assert_input_image(image.nodes, image)
    nested = json.loads(evidence.call("json", lambda: ForgeExporter.to_json(image.nodes)))
    evidence.stage = "structured.json_and_purity"
    assert_structured_export(nested, image.expected_nested, surface="json")
    assert_input_image(image.nodes, image)
    if nested:
        nested[0]["properties"]["alpha"]["flags"][0] = False
        assert_input_image(image.nodes, image)
    flat = evidence.call("flat", lambda: ForgeExporter.to_flat_list(image.nodes))
    evidence.stage = "structured.flat_and_purity"
    assert_structured_export(flat, image.expected_flat, surface="flat")
    assert_input_image(image.nodes, image)
    if flat:
        flat[0]["properties"]["alpha"]["flags"][0] = False
        assert_input_image(image.nodes, image)


def exercise_native(recipe: S3Recipe, evidence: InvocationEvidence, *, empty: bool = False) -> None:
    evidence.stage = "native.fixture_admission"
    image = native_image(recipe, empty=empty)
    page = evidence.call(
        "parser",
        lambda: StackMachineParser(tab_size=recipe.tab_size).parse(
            image.source,
            page_title=image.page_title,
        ),
    )
    evidence.stage = "native.source_semantics"
    assert_native_semantics(page, image.source_observation)
    assert page.tab_size == recipe.tab_size
    before = freeze_input_state(page)
    rendered = evidence.call(
        "serializer", lambda: serialize_logseq_page(page, tab_size=recipe.tab_size)
    )
    evidence.stage = "native.purity"
    assert_input_state_unchanged(page, before)
    evidence.stage = "native.serialized_text"
    assert_native_text(rendered, image.expected_serialized)
    reparsed = evidence.call(
        "parser",
        lambda: StackMachineParser(tab_size=recipe.tab_size).parse(
            rendered,
            page_title=image.page_title,
        ),
    )
    evidence.stage = "native.rendered_semantics"
    assert_native_semantics(reparsed, image.rendered_observation)
    assert reparsed.tab_size == recipe.tab_size
    assert_tree_invariants(page)
    assert_tree_invariants(reparsed)
    evidence.stage = "native.secondary_roundtrip"
    assert project_page(
        page, profile="semantic_roundtrip_v1", identity_policy=IDENTITY_POLICY
    ) == project_page(
        reparsed,
        profile="semantic_roundtrip_v1",
        identity_policy=IDENTITY_POLICY,
    )


def test_generated_serialization_preserves_authored_integrity(
    record_property: Callable[[str, object], None],
) -> None:
    """Catch preservation loss in finite combinations without unbounded shrinking."""
    evidence = InvocationEvidence()

    @settings(
        max_examples=16,
        derandomize=True,
        database=None,
        deadline=None,
        phases=(Phase.generate,),
        report_multiple_bugs=False,
        print_blob=True,
        suppress_health_check=(),
    )
    @given(
        st.builds(
            S3Recipe,
            shape=st.integers(0, 2),
            text=st.integers(0, 1),
            order=st.integers(0, 1),
            tab_size=st.sampled_from((2, 4)),
            newline=st.integers(0, 1),
        )
    )
    def probe(recipe: S3Recipe) -> None:
        evidence.replay = encode_recipe(
            recipe, producer_sha256=producer_digest(), baseline=BASELINE
        )

        def body() -> None:
            evidence.stage = "recipe_admission"
            validate_recipe(recipe)
            exercise_structured(recipe, evidence)
            exercise_native(recipe, evidence)

        evidence.admit(body)

    try:
        probe()
    finally:
        record_property("s3_counts", evidence.record("generated"))
