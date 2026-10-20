"""Finite, in-process EOF relations; controls never execute a parser or process."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections.abc import Callable, Iterator
from dataclasses import asdict, replace
from typing import Any, cast

import pytest

from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage
from logseq_matryca_parser.logos_parser import StackMachineParser
from tests.parser_assurance import composite_properties as composite
from tests.parser_assurance.adversarial import IDENTITY_POLICY
from tests.parser_assurance.invariants import assert_tree_invariants
from tests.parser_assurance.projection import project_page

REAL_TEST = "test_generated_rich_sources_preserve_semantics_at_eof"
ANCHORS = (
    composite.Recipe(104, "nested", "NOW", "C", "2026-08-20 Thu", "2026-08-22 Sat",
                     "plain-value", "Résumé", "caffè", "🙂", "lf"),
    composite.Recipe(104, "mixed-32", "CANCELED", "B", "2026-04-30 Thu", "2026-05-01 Fri",
                     "cafe-42", "Topic page", "work", "東京", "lf"),
)
SHAPES = frozenset({"root-child-sibling", "siblings", "nested", "mixed-8", "mixed-32"})
MAX_CASES = 8
MAX_GENERATED = 6
MAX_BYTES = 16_384
MAX_NODES = 32
MAX_DEPTH = 8


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
        raise AssertionError("real parser/process forbidden in S4d controls")

    monkeypatch.setattr(StackMachineParser, "parse", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    yield
    assert not calls, "a pure S4d control attempted target/process execution"


def collect_cases(
    collector: Callable[[], tuple[composite.Recipe, ...]] | None = None,
) -> tuple[composite.Case, ...]:
    """Admit the complete finite collection before building; never refill it."""
    returned = collector() if collector is not None else composite.collect_recipes(seed=104, limit=6)
    if type(returned) is not tuple or len(returned) > MAX_GENERATED:
        raise ValueError("invalid collector tuple/count")
    recipes = tuple(checked_recipe(recipe) for recipe in returned)
    cases: list[composite.Case] = []
    sources: set[str] = set()
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
        raise ValueError("recipe outside S4d seed/shape domain")
    return validated


def admit_case(case: composite.Case) -> None:
    checked_recipe(case.recipe)
    if case.recipe.newline != "lf":
        raise ValueError("case must be canonical LF")
    pending = list(case.expected)
    count = 0
    while pending:
        block = pending.pop()
        count += 1
        if count > MAX_NODES or not 0 <= block.depth <= MAX_DEPTH:
            raise ValueError("case exceeds node/depth budget")
        pending.extend(block.children)
    if count == 0:
        raise ValueError("case has no model nodes")
    source_variants(case)


def source_variants(case: composite.Case) -> tuple[tuple[str, str], ...]:
    """Remove one known terminator; never strip content or terminal spaces."""
    source = case.source
    if (not isinstance(source, str) or not source.endswith("\n") or source == "\n"
            or source.endswith("\n\n") or "\r" in source):
        raise ValueError("source must have one canonical final LF")
    crlf = source.replace("\n", "\r\n")
    variants = (
        ("lf-final", source), ("lf-eof", source[:-1]),
        ("crlf-final", crlf), ("crlf-eof", crlf[:-2]),
    )
    if any(len(text.encode("utf-8")) > MAX_BYTES for _, text in variants):
        raise ValueError("source variant exceeds byte budget")
    return variants


def assert_variant_page(page: LogseqPage, case: composite.Case) -> dict[str, Any]:
    assert (page.title, page.tab_size) == ("s4d-eof-metamorphic", 2), "page.identity_options"
    composite.assert_matches_model(page, case.expected)
    assert_tree_invariants(page)
    return project_page(page, profile="semantic_roundtrip_v1", identity_policy=IDENTITY_POLICY)


def exercise_cases(
    cases: tuple[composite.Case, ...], parse: Callable[[str], LogseqPage],
    record: Callable[[dict[str, object]], None],
) -> None:
    """Admit everything first, then stop at the first callback/oracle/report error.

    Callback entries are not independently observed parser or process starts.
    The real test supplies the parser; pure controls supply literal observations.
    """
    if type(cases) is not tuple or not 1 <= len(cases) <= MAX_CASES:
        raise ValueError("invalid case tuple/count")
    prepared: list[tuple[composite.Case, tuple[tuple[str, str], ...]]] = []
    sources: set[str] = set()
    for case in cases:
        if type(case) is not composite.Case:
            raise ValueError("invalid case type")
        admit_case(case)
        if case.source_sha256 in sources:
            raise ValueError("duplicate selected source")
        sources.add(case.source_sha256)
        prepared.append((case, source_variants(case)))

    considered = entries = completed = 0

    def counts() -> dict[str, object]:
        return {"selected_cases": len(cases), "selected_variants": len(cases) * 4,
                "considered": considered, "callback_entries": entries, "completed": completed}

    for case, variants in prepared:
        baseline: dict[str, Any] | None = None
        for tag, source in variants:
            considered += 1
            context: dict[str, object] = {
                "case_sha256": case.source_sha256, "recipe": asdict(case.recipe),
                "variant": tag, "variant_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
            }
            try:
                record({"event": "considering", **context, **counts()})
                entries += 1
                page = parse(source)
                record({"event": "observed", **context, **counts()})
                projection = assert_variant_page(page, case)
                if baseline is None:
                    baseline = projection
                else:
                    assert projection == baseline, "relation.semantic_projection"
                completed += 1
                record({"event": "variant_pass", **context, **counts()})
            except Exception as error:
                error.add_note(f"S4d case={case.source_sha256} variant={tag}")
                assertion = None
                if (isinstance(error, AssertionError) and len(error.args) == 1
                        and isinstance(error.args[0], str)
                        and re.fullmatch(r"(?:model|relation|page)\.[a-z_]+", error.args[0])):
                    assertion = error.args[0]
                try:
                    record({"event": "failure", **context, **counts(),
                            "exception_type": type(error).__name__, "assertion": assertion})
                except Exception as reporting_error:
                    error.add_note(f"S4d reporting failed: {type(reporting_error).__name__}")
                raise
    record({"event": "complete", **counts()})


@pytest.mark.parametrize(
    ("index", "tag", "source"),
    (
        (0, "lf-final", "- café 🙂  \n"),
        (1, "lf-eof", "- café 🙂  "),
        (2, "crlf-final", "- café 🙂  \r\n"),
        (3, "crlf-eof", "- café 🙂  "),
    ),
)
def test_variants_preserve_literal_utf8_and_last_content_spaces(
    index: int, tag: str, source: str,
) -> None:
    case = replace(composite.build_case(composite.Recipe.literal_example()), source="- café 🙂  \n")
    variants = source_variants(case)
    assert len(variants) == 4
    assert variants[index] == (tag, source)
    assert variants[index][1].encode("utf-8") == source.encode("utf-8")


def test_variants_preserve_internal_line_endings_and_remove_only_final_terminator() -> None:
    case = replace(composite.build_case(composite.Recipe.literal_example()), source="- café\n  tail  \n")
    assert source_variants(case) == (
        ("lf-final", "- café\n  tail  \n"),
        ("lf-eof", "- café\n  tail  "),
        ("crlf-final", "- café\r\n  tail  \r\n"),
        ("crlf-eof", "- café\r\n  tail  "),
    )


@pytest.mark.parametrize("source", ("", "- tail", "- tail\r\n", "- tail\n\n", "\n"))
def test_variants_refuse_noncanonical_lf_source(source: str) -> None:
    case = replace(composite.build_case(composite.Recipe.literal_example()), source=source)
    with pytest.raises(ValueError, match="canonical"):
        source_variants(case)


def test_variants_refuse_crlf_byte_overflow_even_when_lf_fits() -> None:
    case = replace(composite.build_case(composite.Recipe.literal_example()), source="x\n" * 6_000)
    assert len(case.source.encode()) == 12_000
    with pytest.raises(ValueError, match="byte budget"):
        source_variants(case)


def test_collect_canonicalizes_before_source_dedup_and_preserves_anchors() -> None:
    recipe = composite.Recipe.literal_example()
    calls: list[str] = []

    def collect() -> tuple[composite.Recipe, ...]:
        calls.append("collect")
        return recipe, replace(recipe, newline="crlf"), ANCHORS[0]

    cases = collect_cases(collect)
    assert calls == ["collect"]
    assert tuple(case.recipe for case in cases) == (*ANCHORS, recipe)
    assert len({case.source for case in cases}) == 3
    assert all(case.recipe.newline == "lf" for case in cases)


def test_default_collection_uses_existing_seed_and_limit_once(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[int, int]] = []

    def collect(*, seed: int, limit: int) -> tuple[composite.Recipe, ...]:
        calls.append((seed, limit))
        return (composite.Recipe.literal_example(),)

    monkeypatch.setattr(composite, "collect_recipes", collect)
    assert len(collect_cases()) == 3
    assert calls == [(104, 6)]


def test_collect_retains_six_distinct_generated_sources_within_eight_case_cap() -> None:
    recipes = tuple(replace(composite.Recipe.literal_example(), task=task) for task in composite.TASKS)
    cases = collect_cases(lambda: recipes)
    assert len(cases) == 8
    assert len({case.source_sha256 for case in cases}) == 8
    assert tuple(case.recipe for case in cases[:2]) == ANCHORS
    assert tuple(case.recipe for case in cases[2:]) == recipes


@pytest.mark.parametrize("recipes", ((), (ANCHORS[0],), (ANCHORS[1], ANCHORS[0])))
def test_collect_refuses_shortfall_without_refill(recipes: tuple[composite.Recipe, ...]) -> None:
    calls: list[str] = []

    def collect() -> tuple[composite.Recipe, ...]:
        calls.append("collect")
        return recipes

    with pytest.raises(ValueError, match="generated non-anchor"):
        collect_cases(collect)
    assert calls == ["collect"]


@pytest.mark.parametrize(
    "returned",
    (
        [], None, ("free text",), (composite.Recipe.literal_example(),) * 7,
        (replace(composite.Recipe.literal_example(), seed=True),),
        (replace(composite.Recipe.literal_example(), seed=105),),
        (replace(composite.Recipe.literal_example(), shape="wide-32"),),
        (replace(composite.Recipe.literal_example(), shape="unknown"),),
        (replace(composite.Recipe.literal_example(), newline="bare-cr"),),
        (replace(composite.Recipe.literal_example(), literal="free text"),),
        (composite.Recipe.literal_example(), replace(composite.Recipe.literal_example(), seed=105)),
    ),
)
def test_invalid_collection_is_refused_before_building(
    monkeypatch: pytest.MonkeyPatch, returned: object,
) -> None:
    builds: list[object] = []

    def forbidden(recipe: composite.Recipe) -> composite.Case:
        builds.append(recipe)
        raise AssertionError("build before collection admission")

    monkeypatch.setattr(composite, "build_case", forbidden)
    with pytest.raises(ValueError):
        collect_cases(lambda: cast(tuple[composite.Recipe, ...], returned))
    assert builds == []


@pytest.mark.parametrize("fault", ("nodes", "depth", "bytes"))
def test_collect_rejects_built_cases_outside_limits(
    monkeypatch: pytest.MonkeyPatch, fault: str,
) -> None:
    build = composite.build_case

    def corrupt(recipe: composite.Recipe) -> composite.Case:
        case = build(recipe)
        if fault == "nodes":
            return replace(case, expected=case.expected * 33)
        if fault == "depth":
            return replace(case, expected=(replace(case.expected[0], depth=9),))
        return replace(case, source="x\n" * 6_000)

    monkeypatch.setattr(composite, "build_case", corrupt)
    with pytest.raises(ValueError, match="budget"):
        collect_cases(lambda: (composite.Recipe.literal_example(),))


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
    return LogseqPage(title="s4d-eof-metamorphic", tab_size=2, raw_content="",
                      root_nodes=[first, last])


def corrupt_last(page: LogseqPage, field: str, value: object) -> LogseqPage:
    last = page.root_nodes[-1].model_copy(update={field: value})
    return page.model_copy(update={"root_nodes": [*page.root_nodes[:-1], last]})


def literal_case() -> composite.Case:
    return composite.build_case(composite.Recipe.literal_example())


def test_correct_literal_observation_passes_the_independent_oracle() -> None:
    result = assert_variant_page(literal_page(), literal_case())
    assert result["profile"] == "semantic_roundtrip_v1"
    assert result["page"]["title"] == "s4d-eof-metamorphic"


@pytest.mark.parametrize(
    ("field", "value", "identifier"),
    (("content", "lost last continuation", "model.content"),
     ("line_end", 8, "model.line_span")),
)
def test_common_mode_tail_corruption_cannot_pass_by_variant_agreement(
    field: str, value: object, identifier: str,
) -> None:
    calls: list[str] = []
    records: list[dict[str, object]] = []
    wrong = corrupt_last(literal_page(), field, value)

    def observe(source: str) -> LogseqPage:
        calls.append(source)
        return wrong

    with pytest.raises(AssertionError, match=identifier):
        exercise_cases((literal_case(),), observe, records.append)
    assert len(calls) == 1
    assert records[-1]["event"] == "failure"
    assert records[-1]["assertion"] == identifier
    assert records[-1]["completed"] == 0


@pytest.mark.parametrize(("field", "value"), (("title", "wrong"), ("tab_size", 4)))
def test_oracle_requires_fixed_page_identity_and_options(field: str, value: object) -> None:
    page = literal_page().model_copy(update={field: value})
    with pytest.raises(AssertionError, match="page.identity_options"):
        assert_variant_page(page, literal_case())


def test_loop_exercises_all_four_variants_and_reports_callback_counts() -> None:
    case = literal_case()
    calls: list[str] = []
    records: list[dict[str, object]] = []

    def observe(source: str) -> LogseqPage:
        calls.append(source)
        return literal_page()

    exercise_cases((case,), observe, records.append)
    assert calls == [text for _, text in source_variants(case)]
    complete = records[-1]
    assert complete["event"] == "complete"
    assert (complete["selected_cases"], complete["considered"], complete["callback_entries"],
            complete["completed"]) == (1, 4, 4, 4)
    assert not any("qualified" in key or "actual_parser_entries" in key for key in complete)
    assert [event["variant"] for event in records if event["event"] == "variant_pass"] == [
        "lf-final", "lf-eof", "crlf-final", "crlf-eof",
    ]


@pytest.mark.parametrize("failure_index", (0, 2))
@pytest.mark.parametrize("reporting_failure", (False, True))
def test_first_parser_error_stops_and_survives_recording_failure(
    failure_index: int, reporting_failure: bool,
) -> None:
    case = literal_case()
    original = RuntimeError("synthetic parser failure")
    calls: list[str] = []
    records: list[dict[str, object]] = []

    def observe(source: str) -> LogseqPage:
        calls.append(source)
        if len(calls) - 1 == failure_index:
            raise original
        return literal_page()

    def record(event: dict[str, object]) -> None:
        records.append(event)
        if reporting_failure and event["event"] == "failure":
            raise OSError("synthetic reporter failure")

    with pytest.raises(RuntimeError) as caught:
        exercise_cases((case,), observe, record)
    assert caught.value is original
    assert len(calls) == failure_index + 1
    event = records[-1]
    assert event["event"] == "failure"
    assert event["case_sha256"] == case.source_sha256
    assert event["recipe"] == asdict(case.recipe)
    assert event["variant"] == ("lf-final", "lf-eof", "crlf-final")[failure_index]
    assert event["variant_sha256"] == hashlib.sha256(calls[-1].encode()).hexdigest()
    assert event["completed"] == failure_index
    assert event["callback_entries"] == failure_index + 1
    assert event["exception_type"] == "RuntimeError"
    assert any(case.source_sha256 in note for note in original.__notes__)
    if reporting_failure:
        assert any("OSError" in note for note in original.__notes__)
    serialized = json.dumps(records)
    assert case.source not in serialized
    assert "synthetic parser failure" not in serialized
    assert "synthetic reporter failure" not in serialized


def test_model_error_is_not_replaced_by_a_reporting_error() -> None:
    records: list[dict[str, object]] = []

    def record(event: dict[str, object]) -> None:
        records.append(event)
        if event["event"] == "failure":
            raise OSError("synthetic reporting failure")

    with pytest.raises(AssertionError, match="model.line_span") as caught:
        exercise_cases((literal_case(),), lambda _: corrupt_last(literal_page(), "line_end", 8), record)
    assert records[-1]["assertion"] == "model.line_span"
    assert any("OSError" in note for note in caught.value.__notes__)


def test_reporting_failure_alone_fails_before_another_callback() -> None:
    calls: list[str] = []
    original = OSError("synthetic recorder unavailable")

    def observe(source: str) -> LogseqPage:
        calls.append(source)
        return literal_page()

    def record(_event: dict[str, object]) -> None:
        raise original

    with pytest.raises(OSError) as caught:
        exercise_cases((literal_case(),), observe, record)
    assert caught.value is original
    assert calls == []


def test_all_variants_are_admitted_before_the_first_callback() -> None:
    case = literal_case()
    bad = replace(case, source="x\n" * 6_000)
    calls: list[str] = []

    def observe(source: str) -> LogseqPage:
        calls.append(source)
        return literal_page()

    with pytest.raises(ValueError, match="byte budget"):
        exercise_cases((case, bad), observe, lambda _: None)
    assert calls == []


@pytest.mark.parametrize("cases", ((), (literal_case(),) * 9, (literal_case(),) * 2))
def test_loop_refuses_empty_oversized_or_duplicate_sets(cases: tuple[composite.Case, ...]) -> None:
    calls: list[str] = []

    def observe(source: str) -> LogseqPage:
        calls.append(source)
        return literal_page()

    with pytest.raises(ValueError):
        exercise_cases(cases, observe, lambda _: None)
    assert calls == []


def test_projection_only_difference_is_not_mislabeled_as_independent_model_coverage() -> None:
    calls: list[str] = []
    records: list[dict[str, object]] = []

    def observe(source: str) -> LogseqPage:
        calls.append(source)
        page = literal_page()
        return page if len(calls) == 1 else corrupt_last(page, "clean_text", "relational difference")

    with pytest.raises(AssertionError, match="relation.semantic_projection"):
        exercise_cases((literal_case(),), observe, records.append)
    assert len(calls) == 2
    assert records[-1]["completed"] == 1


def test_generated_rich_sources_preserve_semantics_at_eof(
    record_property: Callable[[str, object], None],
) -> None:
    """One finite real invocation; no target work occurs inside Hypothesis."""
    returned: tuple[composite.Recipe, ...] = ()
    instances: list[StackMachineParser] = []
    actual_parser_entries = 0
    selection: dict[str, object] = {}

    def collect() -> tuple[composite.Recipe, ...]:
        nonlocal returned
        returned = composite.collect_recipes(seed=104, limit=6)
        return returned

    def record(event: dict[str, object]) -> None:
        payload = {"execution_lane": "ordinary_in_process", "selection": selection,
                   "actual_parser_entries": actual_parser_entries, **event}
        record_property("s4d_summary", json.dumps(payload, sort_keys=True))

    def parse(source: str) -> LogseqPage:
        nonlocal actual_parser_entries
        parser = StackMachineParser(tab_size=2, strict_refs=False)
        instances.append(parser)
        actual_parser_entries += 1
        return parser.parse(source, page_title="s4d-eof-metamorphic")

    try:
        cases = collect_cases(collect)
        selection.update({
            "fixed": 2, "collector_returned": len(returned), "retained": len(cases),
            "generated_retained": len(cases) - 2, "duplicates": 2 + len(returned) - len(cases),
            "source_sha256": [case.source_sha256 for case in cases],
            "shapes": [case.recipe.shape for case in cases],
        })
        record({"event": "selection"})
        exercise_cases(cases, parse, record)
        record({"event": "fresh_parser_observation", "instances": len(instances),
                "distinct_instances": len({id(parser) for parser in instances})})
        assert len(instances) == actual_parser_entries == len(cases) * 4 <= 32
        assert len({id(parser) for parser in instances}) == len(instances)
        assert all(parser.tab_size == 2 and not parser.strict_refs for parser in instances)
        record({"event": "real_complete"})
    except Exception as error:
        try:
            record({"event": "real_failure", "exception_type": type(error).__name__})
        except Exception as reporting_error:
            error.add_note(f"S4d final reporting failed: {type(reporting_error).__name__}")
        raise
