"""Finite parser-reuse sequences; pure controls never execute target work."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from collections.abc import Callable, Iterator, Mapping
from dataclasses import asdict, dataclass, replace
from typing import Any, cast

import pytest

from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage
from logseq_matryca_parser.logos_parser import StackMachineParser
from tests.parser_assurance import composite_properties as composite
from tests.parser_assurance.adversarial import IDENTITY_POLICY
from tests.parser_assurance.invariants import assert_tree_invariants, walk_nodes
from tests.parser_assurance.projection import project_page

REAL_TEST = "test_generated_rich_pages_survive_mixed_page_parser_reuse"
ANCHORS = (
    composite.Recipe(104, "nested", "NOW", "C", "2026-08-20 Thu", "2026-08-22 Sat",
                     "plain-value", "Résumé", "caffè", "🙂", "lf"),
    composite.Recipe(104, "mixed-32", "CANCELED", "B", "2026-04-30 Thu", "2026-05-01 Fri",
                     "cafe-42", "Topic page", "work", "東京", "lf"),
)
SHAPES = frozenset({"root-child-sibling", "siblings", "nested", "mixed-8", "mixed-32"})
STAGES = ("first-a", "metadata", "empty", "repeat-a", "fresh-a")
METADATA_SOURCE = (
    "TiTlE:: Sprint Plan\n"
    "aLIas:: Sprint Board\n"
    "ReLaTeD:: [[Alpha]] and [Beta label]([[Beta]])\n"
)
METADATA_PROPERTIES = {
    "title": "Sprint Plan", "alias": "Sprint Board",
    "related": "[[Alpha]] and [Beta label]([[Beta]])",
}
MAX_CASES = 6
MAX_GENERATED = 4
MAX_BYTES = 16_384
MAX_NODES = 32
MAX_DEPTH = 8
Parse = Callable[[str, str], LogseqPage]
RegistryView = tuple[Mapping[str, LogseqNode], Callable[[str], LogseqNode | None]]


@dataclass(frozen=True)
class Sequence:
    """Test-local callbacks, not a production or worker protocol."""

    shared: Parse
    fresh: Parse
    registry: Callable[[], RegistryView]


def collect_cases(
    collector: Callable[[], tuple[composite.Recipe, ...]] | None = None,
) -> tuple[composite.Case, ...]:
    """Finish finite collection and admission before target work; never refill."""
    returned = collector() if collector is not None else composite.collect_recipes(seed=104, limit=4)
    if type(returned) is not tuple or len(returned) > MAX_GENERATED:
        raise ValueError("invalid collector tuple/count")
    recipes = tuple(checked_recipe(recipe) for recipe in returned)
    sources: set[str] = set()
    cases: list[composite.Case] = []
    for recipe in (*ANCHORS, *recipes):
        case = composite.build_case(replace(recipe, newline="lf"))
        admit_case(case)
        if case.source not in sources:
            cases.append(case)
            sources.add(case.source)
    if not 3 <= len(cases) <= MAX_CASES:
        raise ValueError("selection requires a generated non-anchor source")
    return tuple(cases)


def checked_recipe(recipe: composite.Recipe) -> composite.Recipe:
    if type(recipe) is not composite.Recipe:
        raise ValueError("invalid recipe type")
    validated = composite.recipe_from_json(json.dumps(asdict(recipe)))
    if validated.seed != 104 or validated.shape not in SHAPES:
        raise ValueError("recipe outside S4e seed/shape domain")
    return validated


def admit_case(case: composite.Case) -> None:
    checked_recipe(case.recipe)
    if case.recipe.newline != "lf" or type(case.source) is not str or "\r" in case.source:
        raise ValueError("case must be canonical LF")
    if not case.source.endswith("\n") or case.source.endswith("\n\n"):
        raise ValueError("case must have one final LF")
    if len(case.source.encode("utf-8")) > MAX_BYTES:
        raise ValueError("source exceeds byte budget")
    pending = list(case.expected)
    count = 0
    while pending:
        block = pending.pop()
        count += 1
        if count > MAX_NODES or not 0 <= block.depth <= MAX_DEPTH:
            raise ValueError("case exceeds node/depth budget")
        pending.extend(block.children)
    if count == 0:
        raise ValueError("rich case requires model nodes")


def assert_page(page: LogseqPage, kind: str, case: composite.Case) -> dict[str, Any]:
    assert page.tab_size == 2, "page.options"
    if kind == "rich":
        composite.assert_matches_model(page, case.expected)
        assert page.title == "s4e-reuse-a", "page.title"
        assert page.raw_content == case.source, "page.raw_content"
        assert page.properties == {} and page.properties_order == [], "page.rich_metadata"
    elif kind == "metadata":
        assert page.title == "Sprint Plan" and page.raw_content == METADATA_SOURCE, "page.metadata"
        assert page.properties == METADATA_PROPERTIES, "page.metadata"
        assert page.properties_order == ["title", "alias", "related"], "page.metadata"
        assert page.refs == ["Sprint Board", "Alpha", "Beta"] and page.root_nodes == [], "page.metadata"
    elif kind == "empty":
        assert (page.title, page.raw_content) == ("s4e-empty", ""), "page.empty"
        assert page.root_nodes == [] and page.properties == {}, "page.empty"
        assert page.properties_order == [] and page.refs == [] and page.namespace_chain == [], "page.empty"
    else:
        raise ValueError("unknown observation kind")
    assert_tree_invariants(page)
    assert_raw_metadata(page)
    return project_page(page, profile="semantic_roundtrip_v1", identity_policy=IDENTITY_POLICY)


def assert_registry(page: LogseqPage, view: RegistryView) -> None:
    blocks, resolve = view
    nodes = list(walk_nodes(page.root_nodes))
    assert set(blocks) == {node.uuid for node in nodes}, "registry.keys"
    assert all(blocks[node.uuid] is node and resolve(node.uuid) is node for node in nodes), "registry.identity"


def exercise_cases(
    cases: tuple[composite.Case, ...], factory: Callable[[composite.Case], Sequence],
    record: Callable[[dict[str, object]], None],
) -> None:
    """Run five stages per case, preserving the first failure and prior objects.

    Pure controls may select one literal case. The real test admits three to six
    through collect_cases(). Callback counters are never actual parser counts.
    """
    if type(cases) is not tuple or not 1 <= len(cases) <= MAX_CASES:
        raise ValueError("invalid case tuple/count")
    sources: set[str] = set()
    for case in cases:
        if type(case) is not composite.Case:
            raise ValueError("invalid case type")
        admit_case(case)
        if case.source in sources:
            raise ValueError("duplicate selected source")
        sources.add(case.source)
    if len(METADATA_SOURCE.encode("utf-8")) > MAX_BYTES:
        raise ValueError("metadata source exceeds byte budget")

    considered = entries = returned = completed = 0
    retained: list[tuple[LogseqPage, str, composite.Case, str]] = []
    context: dict[str, object] = {}

    def counts() -> dict[str, object]:
        return {"selected_cases": len(cases), "selected_calls": len(cases) * 5,
                "considered": considered, "callback_entries": entries,
                "returned": returned, "completed": completed}

    try:
        for case in cases:
            context = {"case_sha256": case.source_sha256,
                       "recipe_sha256": hashlib.sha256(
                           json.dumps(asdict(case.recipe), sort_keys=True).encode(),
                       ).hexdigest(), "stage": "factory"}
            sequence = factory(case)
            stages = (
                ("first-a", "rich", sequence.shared, case.source, "s4e-reuse-a"),
                ("metadata", "metadata", sequence.shared, METADATA_SOURCE, "s4e-metadata-input"),
                ("empty", "empty", sequence.shared, "", "s4e-empty"),
                ("repeat-a", "rich", sequence.shared, case.source, "s4e-reuse-a"),
                ("fresh-a", "rich", sequence.fresh, case.source, "s4e-reuse-a"),
            )
            baseline: dict[str, Any] | None = None
            for stage, kind, parse, source, title in stages:
                context.update({"stage": stage, "source_sha256": hashlib.sha256(source.encode()).hexdigest()})
                considered += 1
                record({"event": "considering", **context, **counts()})
                entries += 1
                page = parse(source, title)
                returned += 1
                record({"event": "observed", **context, **counts()})
                projection = assert_page(page, kind, case)
                if stage != "fresh-a":
                    assert_registry(page, sequence.registry())
                for earlier, earlier_kind, earlier_case, fingerprint in retained:
                    assert_page(earlier, earlier_kind, earlier_case)
                    assert retention_fingerprint(earlier) == fingerprint, "retention.fingerprint"
                if kind == "rich":
                    if baseline is None:
                        baseline = projection
                    else:
                        assert projection == baseline, "relation.semantic_projection"
                retained.append((page, kind, case, retention_fingerprint(page)))
                completed += 1
                record({"event": "stage_pass", **context, **counts()})
        record({"event": "complete", **counts()})
    except Exception as error:
        error.add_note(f"S4e case={context.get('case_sha256')} stage={context.get('stage')}")
        assertion = None
        if (isinstance(error, AssertionError) and len(error.args) == 1
                and isinstance(error.args[0], str)
                and re.fullmatch(r"(?:model|page|raw|registry|relation|retention)\.[a-z_]+", error.args[0])):
            assertion = error.args[0]
        try:
            record({"event": "failure", **context, **counts(),
                    "exception_type": type(error).__name__, "assertion": assertion})
        except Exception as reporting_error:
            error.add_note(f"S4e reporting failed: {type(reporting_error).__name__}")
        raise


@pytest.fixture(autouse=True)
def no_target_in_controls(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest,
) -> Iterator[None]:
    if request.node.name == REAL_TEST:
        yield
        return
    calls: list[str] = []

    def forbidden(*_args: object, **_kwargs: object) -> None:
        calls.append("target-or-process")
        raise AssertionError("real parser/process forbidden in S4e controls")

    monkeypatch.setattr(StackMachineParser, "parse", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    yield
    assert not calls, "a pure S4e control attempted target/process execution"


def assert_raw_metadata(page: LogseqPage) -> None:
    assert page.created_at is None and page.updated_at is None, "raw.page_timestamps"
    assert page.graph_root is None and page.source_path is None, "raw.page_context"
    assert all(node.source_path is None for node in walk_nodes(page.root_nodes)), "raw.node_context"


def retention_fingerprint(page: LogseqPage) -> str:
    """Detached same-object snapshot; never cross-parse synthetic-ID equality."""
    return json.dumps({
        "projection": project_page(page, profile="exact_parse_v1"),
        "raw": {
            "raw_content": page.raw_content, "source_path": page.source_path,
            "graph_root": page.graph_root, "created_at": page.created_at,
            "updated_at": page.updated_at,
            "nodes": [{"outline_path": list(node.outline_path), "source_path": node.source_path}
                      for node in walk_nodes(page.root_nodes)],
        },
    }, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def literal_case() -> composite.Case:
    return composite.build_case(composite.Recipe.literal_example())


def literal_page() -> LogseqPage:
    """Hand-authored observations, never converted from the expected block model."""
    child = LogseqNode(
        uuid="child", synthetic_id=True,
        content="DOING [#B] item-1 caffè [[Target]] #topic\n    continuation-1 東京",
        indent_level=1, properties={"literal-key": "kept"},
        wikilinks=["Target"], tags=["B", "topic"], refs=["Target", "B", "topic"],
        task_status="DOING", task_priority="B", parent_id="root-one",
        path=["root-one", "child"], outline_path=[1, 1], line_start=4, line_end=6,
    )
    first = LogseqNode(
        uuid="root-one", synthetic_id=True,
        content=("TODO [#A] item-0 caffè [[Target]] #topic SCHEDULED: <2026-04-30 Thu> "
                 "DEADLINE: <2026-05-01 Fri>\n  continuation-0 caffè"),
        indent_level=0,
        properties={
            "literal-key": "kept", "scheduled": "<2026-04-30 Thu>",
            "scheduled_journal_day": 20260430, "scheduled_iso": "2026-04-30T00:00:00",
            "deadline": "<2026-05-01 Fri>", "deadline_journal_day": 20260501,
            "deadline_iso": "2026-05-01T00:00:00",
        },
        wikilinks=["Target"], tags=["A", "topic"], refs=["Target", "A", "topic"],
        task_status="TODO", task_priority="A", scheduled_at=1777507200,
        deadline_at=1777593600, path=["root-one"], outline_path=[1],
        line_start=1, line_end=3, children=[child],
    )
    last = LogseqNode(
        uuid="root-two", synthetic_id=True,
        content="DONE [#C] item-2 caffè [[Target]] #topic\n  continuation-2 naïve",
        indent_level=0, properties={"literal-key": "kept"},
        wikilinks=["Target"], tags=["C", "topic"], refs=["Target", "C", "topic"],
        task_status="DONE", task_priority="C", left_id="root-one",
        path=["root-two"], outline_path=[2], line_start=7, line_end=9,
    )
    return LogseqPage(title="s4e-reuse-a", tab_size=2, raw_content=literal_case().source,
                      root_nodes=[first, last], refs=["Target", "A", "topic", "B", "C"])


@pytest.mark.parametrize("field", ("created_at", "updated_at", "graph_root", "nested_source_path"))
def test_raw_retention_faults_close_the_old_projection_blind_spot(field: str) -> None:
    page = literal_page()
    old_projection = project_page(page, profile="exact_parse_v1")
    before = retention_fingerprint(page)
    assert_raw_metadata(page)
    if field == "nested_source_path":
        child = page.root_nodes[0].children[0]
        page.root_nodes[0].children[0] = child.model_copy(update={"source_path": "synthetic.md"})
    else:
        # Explicit corruption of a hand-built frozen scalar, never production mutation.
        object.__setattr__(page, field, 1 if field.endswith("_at") else "synthetic-root")
    assert project_page(page, profile="exact_parse_v1") == old_projection
    with pytest.raises(AssertionError, match="raw\\."):
        assert_raw_metadata(page)
    assert retention_fingerprint(page) != before


def metadata_page() -> LogseqPage:
    return LogseqPage(
        title="Sprint Plan", raw_content=METADATA_SOURCE,
        properties={"title": "Sprint Plan", "alias": "Sprint Board",
                    "related": "[[Alpha]] and [Beta label]([[Beta]])"},
        properties_order=["title", "alias", "related"], refs=["Sprint Board", "Alpha", "Beta"],
    )


def empty_page() -> LogseqPage:
    return LogseqPage(title="s4e-empty", raw_content="")


class ScriptedSequence:
    """Specific hand-built observations exercise the oracle, never the parser."""

    def __init__(self) -> None:
        self.pages = [literal_page(), metadata_page(), empty_page(), literal_page(), literal_page()]
        self.calls: list[str] = []
        self.factory_calls = 0
        self.blocks: dict[str, LogseqNode] = {}
        self.resolve: Callable[[str], LogseqNode | None] = lambda uuid: self.blocks.get(uuid)
        self.on_call: Callable[[int], None] = lambda _: None

    def observe(self, role: str, source: str, title: str) -> LogseqPage:
        index = len(self.calls)
        assert index < 5
        assert role == ("fresh" if index == 4 else "shared")
        expected_source = METADATA_SOURCE if index == 1 else "" if index == 2 else literal_case().source
        expected_title = "s4e-metadata-input" if index == 1 else "s4e-empty" if index == 2 else "s4e-reuse-a"
        assert (source, title) == (expected_source, expected_title)
        self.calls.append(STAGES[index])
        page = self.pages[index]
        self.blocks = {node.uuid: node for node in walk_nodes(page.root_nodes)}
        self.on_call(index)
        return page

    def factory(self, case: composite.Case) -> Sequence:
        assert case == literal_case()
        self.factory_calls += 1
        return Sequence(
            lambda source, title: self.observe("shared", source, title),
            lambda source, title: self.observe("fresh", source, title),
            lambda: (self.blocks, self.resolve),
        )


def corrupt_last(page: LogseqPage, field: str, value: object) -> None:
    page.root_nodes[-1] = page.root_nodes[-1].model_copy(update={field: value})


def test_correct_hand_built_sequence_passes_with_source_free_ordered_counts() -> None:
    script = ScriptedSequence()
    events: list[dict[str, object]] = []
    exercise_cases((literal_case(),), script.factory, events.append)
    assert script.calls == list(STAGES)
    assert script.factory_calls == 1
    assert [event["stage"] for event in events if event["event"] == "stage_pass"] == list(STAGES)
    assert events[-1] == {
        "event": "complete", "selected_cases": 1, "selected_calls": 5,
        "considered": 5, "callback_entries": 5, "returned": 5, "completed": 5,
    }
    for event in events[:-1]:
        assert event["case_sha256"] == literal_case().source_sha256
        assert event["recipe_sha256"] == hashlib.sha256(
            json.dumps(asdict(literal_case().recipe), sort_keys=True).encode(),
        ).hexdigest()
    serialized = json.dumps(events)
    assert literal_case().source not in serialized and METADATA_SOURCE not in serialized
    assert not any("actual_parser_entries" in event for event in events)


@pytest.mark.parametrize(
    ("field", "value", "identifier"),
    (("task_status", "NOW", "model.task_status"),
     ("content", "wrong content", "model.content"),
     ("line_end", 8, "model.line_span")),
)
def test_common_mode_rich_corruption_cannot_pass_by_agreement(
    field: str, value: object, identifier: str,
) -> None:
    script = ScriptedSequence()
    for index in (0, 3, 4):
        corrupt_last(script.pages[index], field, value)
    projections = [project_page(script.pages[index], profile="semantic_roundtrip_v1",
                                identity_policy=IDENTITY_POLICY) for index in (0, 3, 4)]
    assert projections[0] == projections[1] == projections[2]
    with pytest.raises(AssertionError, match=identifier):
        exercise_cases((literal_case(),), script.factory, lambda _: None)
    assert script.calls == ["first-a"]


@pytest.mark.parametrize("field", ("properties", "properties_order"))
def test_rich_replay_rejects_page_metadata_leak_with_correct_nodes(field: str) -> None:
    script = ScriptedSequence()
    value: object = {"alias": "leaked"} if field == "properties" else ["alias"]
    script.pages[3] = script.pages[3].model_copy(update={field: value})
    composite.assert_matches_model(script.pages[3], literal_case().expected)
    with pytest.raises(AssertionError, match="page.rich_metadata"):
        exercise_cases((literal_case(),), script.factory, lambda _: None)
    assert script.calls == list(STAGES[:4])


@pytest.mark.parametrize("fault", ("metadata", "roots", "stale-registry"))
def test_empty_observation_must_not_retain_previous_page_state(fault: str) -> None:
    script = ScriptedSequence()
    if fault == "metadata":
        script.pages[2] = script.pages[2].model_copy(update={"properties": {"alias": "leaked"}})
    elif fault == "roots":
        script.pages[2] = script.pages[2].model_copy(update={"root_nodes": literal_page().root_nodes})
    else:
        def leave_registry(index: int) -> None:
            if index == 2:
                script.blocks = {"root-one": script.pages[0].root_nodes[0]}
        script.on_call = leave_registry
    with pytest.raises(AssertionError, match="registry.keys" if fault == "stale-registry" else "page.empty"):
        exercise_cases((literal_case(),), script.factory, lambda _: None)
    assert script.calls == list(STAGES[:3])


@pytest.mark.parametrize("fault", ("extra", "earlier-node", "wrong-resolver"))
def test_current_registry_requires_exact_keys_and_identical_returned_nodes(fault: str) -> None:
    script = ScriptedSequence()

    def corrupt(index: int) -> None:
        if index != 3:
            return
        if fault == "extra":
            script.blocks["stale"] = script.pages[0].root_nodes[0]
        elif fault == "earlier-node":
            script.blocks["root-one"] = script.pages[0].root_nodes[0]
        else:
            script.resolve = lambda _: script.pages[0].root_nodes[0]

    script.on_call = corrupt
    with pytest.raises(AssertionError, match="registry.keys" if fault == "extra" else "registry.identity"):
        exercise_cases((literal_case(),), script.factory, lambda _: None)
    assert script.calls == list(STAGES[:4])


@pytest.mark.parametrize("stage", (1, 2, 3, 4))
def test_later_good_result_cannot_hide_mutation_of_earlier_rich_object(stage: int) -> None:
    script = ScriptedSequence()

    def mutate(index: int) -> None:
        if index == stage:
            corrupt_last(script.pages[0], "clean_text", "retained-only change")

    script.on_call = mutate
    with pytest.raises(AssertionError, match="retention.fingerprint"):
        exercise_cases((literal_case(),), script.factory, lambda _: None)
    assert script.calls == list(STAGES[:stage + 1])


@pytest.mark.parametrize("field", ("properties", "properties_order", "refs"))
def test_later_good_rich_result_cannot_hide_mutated_metadata_object(field: str) -> None:
    script = ScriptedSequence()

    def mutate(index: int) -> None:
        if index == 3:
            getattr(script.pages[1], field).clear()

    script.on_call = mutate
    with pytest.raises(AssertionError, match="page.metadata"):
        exercise_cases((literal_case(),), script.factory, lambda _: None)
    assert script.calls == list(STAGES[:4])


@pytest.mark.parametrize("page_index", (0, 1, 2))
@pytest.mark.parametrize("field", ("created_at", "updated_at", "graph_root", "source_path"))
def test_raw_page_metadata_is_required_on_initial_and_retained_observations(
    page_index: int, field: str,
) -> None:
    script = ScriptedSequence()
    object.__setattr__(script.pages[page_index], field, 1 if field.endswith("_at") else "synthetic")
    with pytest.raises(AssertionError, match=r"raw\."):
        exercise_cases((literal_case(),), script.factory, lambda _: None)
    assert script.calls == list(STAGES[:page_index + 1])


@pytest.mark.parametrize("page_index", (0, 1, 2))
@pytest.mark.parametrize("field", ("created_at", "updated_at", "graph_root"))
def test_retained_raw_page_mutations_are_not_hidden_by_projection_normalization(
    page_index: int, field: str,
) -> None:
    script = ScriptedSequence()
    before: dict[str, Any] = {}

    def mutate(index: int) -> None:
        if index == 3:
            page = script.pages[page_index]
            before.update(project_page(page, profile="exact_parse_v1"))
            object.__setattr__(page, field, 1 if field.endswith("_at") else "synthetic-root")
            assert project_page(page, profile="exact_parse_v1") == before

    script.on_call = mutate
    with pytest.raises(AssertionError, match=r"raw\."):
        exercise_cases((literal_case(),), script.factory, lambda _: None)
    assert before and script.calls == list(STAGES[:4])


def test_retained_nested_path_mutation_is_checked_after_a_later_good_result() -> None:
    script = ScriptedSequence()

    def mutate(index: int) -> None:
        if index == 3:
            page = script.pages[0]
            before = project_page(page, profile="exact_parse_v1")
            node = page.root_nodes[0].children[0]
            page.root_nodes[0].children[0] = node.model_copy(update={"source_path": "synthetic.md"})
            assert project_page(page, profile="exact_parse_v1") == before

    script.on_call = mutate
    with pytest.raises(AssertionError, match="raw.node_context"):
        exercise_cases((literal_case(),), script.factory, lambda _: None)
    assert script.calls == list(STAGES[:4])


def test_omitted_model_field_is_relational_not_independent_evidence() -> None:
    script = ScriptedSequence()
    corrupt_last(script.pages[3], "clean_text", "relational change")
    composite.assert_matches_model(script.pages[3], literal_case().expected)
    with pytest.raises(AssertionError, match="relation.semantic_projection"):
        exercise_cases((literal_case(),), script.factory, lambda _: None)
    assert script.calls == list(STAGES[:4])


@pytest.mark.parametrize("stage", range(5))
@pytest.mark.parametrize("reporting_failure", (False, True))
def test_first_callback_error_stops_and_survives_reporting_failure(
    stage: int, reporting_failure: bool,
) -> None:
    script = ScriptedSequence()
    original = RuntimeError("private synthetic callback failure")
    events: list[dict[str, object]] = []

    def fail(index: int) -> None:
        if index == stage:
            raise original

    def record(event: dict[str, object]) -> None:
        events.append(event)
        if reporting_failure and event["event"] == "failure":
            raise OSError("private synthetic reporting failure")

    script.on_call = fail
    with pytest.raises(RuntimeError) as caught:
        exercise_cases((literal_case(),), script.factory, record)
    assert caught.value is original
    assert script.calls == list(STAGES[:stage + 1])
    assert events[-1]["stage"] == STAGES[stage]
    assert events[-1]["callback_entries"] == stage + 1
    assert events[-1]["returned"] == events[-1]["completed"] == stage
    assert events[-1]["exception_type"] == "RuntimeError"
    assert "private synthetic" not in json.dumps(events)
    if reporting_failure:
        assert any("OSError" in note for note in original.__notes__)


@pytest.mark.parametrize("stage", range(5))
def test_first_model_or_literal_error_stops_later_callbacks(stage: int) -> None:
    script = ScriptedSequence()
    identifier = "model.content" if stage in (0, 3, 4) else "page.metadata" if stage == 1 else "page.empty"
    if stage in (0, 3, 4):
        corrupt_last(script.pages[stage], "content", "wrong current result")
    else:
        script.pages[stage].properties["leaked"] = True
    events: list[dict[str, object]] = []

    def record(event: dict[str, object]) -> None:
        events.append(event)
        if event["event"] == "failure":
            raise OSError("reporter unavailable")

    with pytest.raises(AssertionError, match=identifier) as caught:
        exercise_cases((literal_case(),), script.factory, record)
    assert script.calls == list(STAGES[:stage + 1])
    assert events[-1]["returned"] == stage + 1 and events[-1]["completed"] == stage
    assert any("OSError" in note for note in caught.value.__notes__)


@pytest.mark.parametrize("stage", range(4))
def test_first_registry_error_stops_before_later_callbacks(stage: int) -> None:
    script = ScriptedSequence()

    def corrupt(index: int) -> None:
        if index == stage:
            script.blocks["stale"] = literal_page().root_nodes[0]

    script.on_call = corrupt
    with pytest.raises(AssertionError, match="registry.keys"):
        exercise_cases((literal_case(),), script.factory, lambda _: None)
    assert script.calls == list(STAGES[:stage + 1])


@pytest.mark.parametrize("stage", range(5))
def test_reporting_only_failure_stops_before_the_selected_callback(stage: int) -> None:
    script = ScriptedSequence()
    original = OSError("reporter unavailable")

    def record(event: dict[str, object]) -> None:
        if event["event"] == "considering" and event["stage"] == STAGES[stage]:
            raise original

    with pytest.raises(OSError) as caught:
        exercise_cases((literal_case(),), script.factory, record)
    assert caught.value is original
    assert script.calls == list(STAGES[:stage])


def test_reporting_only_failure_after_completed_target_work_still_fails() -> None:
    script = ScriptedSequence()
    original = OSError("final report unavailable")

    def record(event: dict[str, object]) -> None:
        if event["event"] == "complete":
            raise original

    with pytest.raises(OSError) as caught:
        exercise_cases((literal_case(),), script.factory, record)
    assert caught.value is original and script.calls == list(STAGES)


def test_collection_canonicalizes_before_dedup_and_keeps_both_anchors() -> None:
    recipe = composite.Recipe.literal_example()
    calls: list[str] = []

    def collect() -> tuple[composite.Recipe, ...]:
        calls.append("collect")
        return recipe, replace(recipe, newline="crlf"), ANCHORS[0]

    cases = collect_cases(collect)
    assert calls == ["collect"]
    assert tuple(case.recipe for case in cases) == (*ANCHORS, recipe)
    assert len({case.source for case in cases}) == 3
    assert 2 + 3 - len(cases) == 2


def test_default_collection_requests_seed_104_limit_four_once(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[int, int]] = []

    def collect(*, seed: int, limit: int) -> tuple[composite.Recipe, ...]:
        calls.append((seed, limit))
        return (composite.Recipe.literal_example(),)

    monkeypatch.setattr(composite, "collect_recipes", collect)
    assert len(collect_cases()) == 3
    assert calls == [(104, 4)]


def test_collection_retains_four_distinct_generated_sources_within_six_case_cap() -> None:
    recipes = tuple(replace(composite.Recipe.literal_example(), task=task)
                    for task in ("TODO", "DOING", "DONE", "LATER"))
    cases = collect_cases(lambda: recipes)
    assert len(cases) == len({case.source_sha256 for case in cases}) == 6
    assert tuple(case.recipe for case in cases) == (*ANCHORS, *recipes)


@pytest.mark.parametrize("recipes", ((), (ANCHORS[0],), (ANCHORS[1], ANCHORS[0])))
def test_collection_refuses_post_dedup_shortfall_without_refill(
    recipes: tuple[composite.Recipe, ...],
) -> None:
    calls: list[str] = []

    def collect() -> tuple[composite.Recipe, ...]:
        calls.append("collect")
        return recipes

    with pytest.raises(ValueError, match="generated non-anchor"):
        collect_cases(collect)
    assert calls == ["collect"]


@pytest.mark.parametrize(
    "returned",
    ([], None, ("free text",), (composite.Recipe.literal_example(),) * 5,
     (replace(composite.Recipe.literal_example(), seed=True),),
     (replace(composite.Recipe.literal_example(), seed=105),),
     (replace(composite.Recipe.literal_example(), shape="wide-32"),),
     (replace(composite.Recipe.literal_example(), shape="unknown"),),
     (replace(composite.Recipe.literal_example(), task="unknown"),),
     (replace(composite.Recipe.literal_example(), newline="bare-cr"),),
     (replace(composite.Recipe.literal_example(), literal="free text"),),
     (composite.Recipe.literal_example(), replace(composite.Recipe.literal_example(), seed=105))),
)
def test_whole_invalid_collection_is_rejected_before_any_build(
    monkeypatch: pytest.MonkeyPatch, returned: object,
) -> None:
    builds: list[object] = []

    def forbidden(recipe: composite.Recipe) -> composite.Case:
        builds.append(recipe)
        raise AssertionError("build before admission")

    monkeypatch.setattr(composite, "build_case", forbidden)
    with pytest.raises(ValueError):
        collect_cases(lambda: cast(tuple[composite.Recipe, ...], returned))
    assert builds == []


@pytest.mark.parametrize("fault", ("bytes", "nodes", "depth"))
def test_collection_rejects_model_or_utf8_byte_overflow_before_target_work(
    monkeypatch: pytest.MonkeyPatch, fault: str,
) -> None:
    build = composite.build_case

    def corrupt(recipe: composite.Recipe) -> composite.Case:
        case = build(recipe)
        if fault == "bytes":
            return replace(case, source="🙂" * 4096 + "\n")
        if fault == "nodes":
            return replace(case, expected=case.expected * 33)
        return replace(case, expected=(replace(case.expected[0], depth=9),))

    monkeypatch.setattr(composite, "build_case", corrupt)
    with pytest.raises(ValueError, match="budget"):
        collect_cases(lambda: (composite.Recipe.literal_example(),))


@pytest.mark.parametrize("fault", ("bytes", "nodes", "depth"))
def test_all_selected_cases_are_admitted_before_any_factory_or_callback(fault: str) -> None:
    case = literal_case()
    bad = replace(case, source="🙂" * 4096 + "\n")
    if fault == "nodes":
        bad = replace(case, source="different\n", expected=case.expected * 33)
    elif fault == "depth":
        bad = replace(case, source="different\n", expected=(replace(case.expected[0], depth=9),))
    script = ScriptedSequence()
    with pytest.raises(ValueError, match="budget"):
        exercise_cases((case, bad), script.factory, lambda _: None)
    assert script.factory_calls == 0 and script.calls == []


@pytest.mark.parametrize("cases", ((), (literal_case(),) * 7, (literal_case(),) * 2, (None,)))
def test_loop_rejects_empty_oversized_duplicate_or_malformed_case_sets(cases: object) -> None:
    script = ScriptedSequence()
    with pytest.raises(ValueError):
        exercise_cases(cast(tuple[composite.Case, ...], cases), script.factory, lambda _: None)
    assert script.factory_calls == 0 and script.calls == []


def test_fixed_metadata_input_is_admitted_before_any_target_callback(monkeypatch: pytest.MonkeyPatch) -> None:
    script = ScriptedSequence()
    monkeypatch.setattr(sys.modules[__name__], "METADATA_SOURCE", "🙂" * 4097)
    with pytest.raises(ValueError, match="metadata source exceeds byte budget"):
        exercise_cases((literal_case(),), script.factory, lambda _: None)
    assert script.factory_calls == 0 and script.calls == []


@pytest.mark.parametrize(("field", "value", "identifier"), (
    ("title", "wrong title", "page.title"),
    ("tab_size", 4, "page.options"),
    ("raw_content", "wrong raw text", "page.raw_content"),
))
def test_rich_page_requires_fixed_title_options_and_original_raw_content(
    field: str, value: object, identifier: str,
) -> None:
    script = ScriptedSequence()
    script.pages[0] = script.pages[0].model_copy(update={field: value})
    with pytest.raises(AssertionError, match=identifier):
        exercise_cases((literal_case(),), script.factory, lambda _: None)
    assert script.calls == ["first-a"]


def test_generated_rich_pages_survive_mixed_page_parser_reuse(
    record_property: Callable[[str, object], None],
) -> None:
    """One finite real invocation; generation finishes before direct parse calls."""
    returned: tuple[composite.Recipe, ...] = ()
    instances: list[StackMachineParser] = []
    actual_calls: list[tuple[StackMachineParser, str, str, str]] = []
    selection: dict[str, object] = {}

    def collect() -> tuple[composite.Recipe, ...]:
        nonlocal returned
        returned = composite.collect_recipes(seed=104, limit=4)
        return returned

    def record(event: dict[str, object]) -> None:
        record_property("s4e_summary", json.dumps({
            "execution_lane": "ordinary_in_process", "selection": selection,
            "actual_parser_entries": len(actual_calls), **event,
        }, sort_keys=True))

    def factory(_case: composite.Case) -> Sequence:
        shared = StackMachineParser(tab_size=2, strict_refs=False)
        fresh = StackMachineParser(tab_size=2, strict_refs=False)
        instances.extend((shared, fresh))

        def parse(parser: StackMachineParser, role: str, source: str, title: str) -> LogseqPage:
            # These entries count this direct call site, not an independent observer.
            actual_calls.append((parser, role, hashlib.sha256(source.encode()).hexdigest(), title))
            return parser.parse(source, page_title=title)

        return Sequence(
            lambda source, title: parse(shared, "shared", source, title),
            lambda source, title: parse(fresh, "fresh", source, title),
            lambda: (shared.registry.blocks, shared.registry.resolve),
        )

    try:
        cases = collect_cases(collect)
        selection.update({
            "fixed": 2, "collector_returned": len(returned), "retained": len(cases),
            "generated_retained": len(cases) - 2, "duplicates": 2 + len(returned) - len(cases),
            "source_sha256": [case.source_sha256 for case in cases],
            "shapes": [case.recipe.shape for case in cases],
        })
        record({"event": "selection"})
        exercise_cases(cases, factory, record)
        record({"event": "parser_reuse_observation", "instances": len(instances),
                "distinct_instances": len({id(parser) for parser in instances}),
                "shared_entries": sum(role == "shared" for _, role, _, _ in actual_calls),
                "fresh_entries": sum(role == "fresh" for _, role, _, _ in actual_calls)})
        assert 3 <= len(cases) <= 6
        assert len(actual_calls) == len(cases) * 5 <= 30
        assert len(instances) == len({id(parser) for parser in instances}) == len(cases) * 2 <= 12
        assert all(parser.tab_size == 2 and not parser.strict_refs for parser in instances)
        for index, case in enumerate(cases):
            calls = actual_calls[index * 5:(index + 1) * 5]
            assert all(call[0] is instances[index * 2] for call in calls[:4])
            assert calls[4][0] is instances[index * 2 + 1]
            assert [call[1] for call in calls] == ["shared"] * 4 + ["fresh"]
            assert [call[2] for call in calls] == [
                case.source_sha256, hashlib.sha256(METADATA_SOURCE.encode()).hexdigest(),
                hashlib.sha256(b"").hexdigest(), case.source_sha256, case.source_sha256,
            ]
            assert [call[3] for call in calls] == [
                "s4e-reuse-a", "s4e-metadata-input", "s4e-empty", "s4e-reuse-a", "s4e-reuse-a",
            ]
        record({"event": "real_complete"})
    except Exception as error:
        try:
            record({"event": "real_failure", "exception_type": type(error).__name__})
        except Exception as reporting_error:
            error.add_note(f"S4e final reporting failed: {type(reporting_error).__name__}")
        raise
