"""Bounded generated assurance for inline shielding and duplicate references."""

from __future__ import annotations

import hashlib
import json
import os
import selectors
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass, replace
from itertools import islice, product
from pathlib import Path
from typing import Any, cast

import pytest
from hypothesis import Phase, given, seed, settings
from hypothesis import strategies as st

import tests.parser_assurance.randomized_shielding as randomized_shielding
from logseq_matryca_parser.logos_core import LogseqPage
from logseq_matryca_parser.logos_parser import StackMachineParser
from tests.parser_assurance.invariants import assert_tree_invariants
from tests.parser_assurance.projection import project_page
from tests.parser_assurance.randomized_shielding import (
    MAX_ATTEMPT_EVIDENCE,
    MAX_CAMPAIGN_TRANSFER,
    MAX_CHILD_OUTPUT,
    MAX_CLI_SUMMARY,
    CampaignResult,
    ShieldingCase,
    ShieldingObservation,
    SourceContext,
    SpanRecipe,
    SupervisorOutcome,
    WorkerResult,
    _campaign_result_from_supervisor,
    _campaign_work,
    _candidate_receipt_passes,
    _ChildError,
    _dependency_manifest_digest,
    _generate_supervised,
    _OwnedAttemptDirectory,
    _run_bounded_child,
    _source_manifest_digest,
    _supervise_process,
    assert_observation,
    build_case,
    collect_recipes,
    main,
    observe,
    run_worker,
)

_MAX_RECIPES = 20
_MAX_SOURCE_BYTES = 2 * 1024
_PRIMARY = ("Beta", "Cedar", "Éclair")
_SECONDARY = ("Alpha", "Maple", "Orchid")
_CATEGORIES = ("Topic", "delta", "Étiquette")
_LITERAL_WRAPPERS = {
    "backticks": ("`", "`"),
    "comment": ("<!--", "-->"),
    "single-dollar": ("$", "$"),
    "double-dollar": ("$$", "$$"),
}
_POSIX_PROCESS_SUPERVISION = os.name == "posix" and hasattr(os, "killpg")
_OWNED_DIRECTORY_CAPABILITY = (
    os.name == "posix"
    and hasattr(os, "O_NOFOLLOW")
    and hasattr(os, "O_DIRECTORY")
    and os.open in os.supports_dir_fd
    and os.mkdir in os.supports_dir_fd
)


class _MemoryAttemptDirectory:
    def __init__(self) -> None:
        self.files: dict[str, bytearray] = {}

    def write_new(self, name: str, payload: bytes) -> None:
        if name in self.files and name != "results.jsonl":
            raise FileExistsError(name)
        self.files.setdefault(name, bytearray()).extend(payload)


def _run_campaign_work(seed_value: int, attempt_path: Path, started: float | None = None):
    campaign_start = time.monotonic() if started is None else started
    del attempt_path
    owned = cast(_OwnedAttemptDirectory, _MemoryAttemptDirectory())
    return _campaign_work(seed_value, owned, campaign_start, campaign_start + 60.0)


def _synthetic_campaign_receipt(monkeypatch: pytest.MonkeyPatch, attempt_path: Path) -> dict[str, Any]:
    recipes = _fixed_campaign_recipes()
    context = SourceContext(
        "a" * 40, "b" * 64, True, "3.12", "1.11.0", "6.0",
        "c" * 64, (("hypothesis", "6.0"),),
    )
    monkeypatch.setattr(
        randomized_shielding, "_generate_supervised", lambda seed, timeout: recipes
    )
    monkeypatch.setattr(randomized_shielding, "capture_source_context", lambda: context)

    def fake_worker(case: ShieldingCase, worker_context: SourceContext, *, timeout: float) -> WorkerResult:
        return WorkerResult(case.sha256, worker_context.digest, "parsed", 1, case.expected)

    monkeypatch.setattr(randomized_shielding, "_worker_supervised", fake_worker)
    provisional = _run_campaign_work(104, attempt_path)
    return json.loads(json.dumps(provisional.receipt))


@dataclass(frozen=True)
class Recipe:
    """One complete, bounded single-line source and its independent facts."""

    family: str
    source: str
    content: str
    wikilinks: tuple[str, ...]
    tags: tuple[str, ...]
    refs: tuple[str, ...]
    primary: str
    secondary: str
    category: str


@dataclass(frozen=True)
class Observation:
    """Copied parser-visible facts used by the independent assertion oracle."""

    root_count: int
    child_counts: tuple[int, ...]
    content: str
    raw_content: str
    line_start: int | None
    line_end: int | None
    wikilinks: tuple[str, ...]
    tags: tuple[str, ...]
    node_refs: tuple[str, ...]
    page_refs: tuple[str, ...]


# The complete rendered strings and all three expected lists are deliberately
# literals. Their asymmetry proves links-first ref collection and occurrence
# preservation without borrowing the parser's extraction logic.
_ANCHORS = (
    Recipe(
        "backticks",
        "- lead #Topic [[Beta]] [[Alpha]] [[Beta]] `[[Beta]] #Topic [[HiddenOnly]] #hiddenOnly` #Beta #Topic\n",
        "lead #Topic [[Beta]] [[Alpha]] [[Beta]] `[[Beta]] #Topic [[HiddenOnly]] #hiddenOnly` #Beta #Topic",
        ("Beta", "Alpha", "Beta"),
        ("Topic", "Beta", "Topic"),
        ("Beta", "Alpha", "Topic"),
        "Beta",
        "Alpha",
        "Topic",
    ),
    Recipe(
        "comment",
        "- lead #Topic [[Beta]] [[Alpha]] [[Beta]] <!--[[Beta]] #Topic [[HiddenOnly]] #hiddenOnly--> #Beta #Topic\n",
        "lead #Topic [[Beta]] [[Alpha]] [[Beta]] <!--[[Beta]] #Topic [[HiddenOnly]] #hiddenOnly--> #Beta #Topic",
        ("Beta", "Alpha", "Beta"),
        ("Topic", "Beta", "Topic"),
        ("Beta", "Alpha", "Topic"),
        "Beta",
        "Alpha",
        "Topic",
    ),
    Recipe(
        "single-dollar",
        "- lead #Topic [[Beta]] [[Alpha]] [[Beta]] $[[Beta]] #Topic [[HiddenOnly]] #hiddenOnly$ #Beta #Topic\n",
        "lead #Topic [[Beta]] [[Alpha]] [[Beta]] $[[Beta]] #Topic [[HiddenOnly]] #hiddenOnly$ #Beta #Topic",
        ("Beta", "Alpha", "Beta"),
        ("Topic", "Beta", "Topic"),
        ("Beta", "Alpha", "Topic"),
        "Beta",
        "Alpha",
        "Topic",
    ),
    Recipe(
        "double-dollar",
        "- lead #Topic [[Beta]] [[Alpha]] [[Beta]] $$[[Beta]] #Topic [[HiddenOnly]] #hiddenOnly$$ #Beta #Topic\n",
        "lead #Topic [[Beta]] [[Alpha]] [[Beta]] $$[[Beta]] #Topic [[HiddenOnly]] #hiddenOnly$$ #Beta #Topic",
        ("Beta", "Alpha", "Beta"),
        ("Topic", "Beta", "Topic"),
        ("Beta", "Alpha", "Topic"),
        "Beta",
        "Alpha",
        "Topic",
    ),
)

_ANCHOR_BASELINE = Observation(
    root_count=1,
    child_counts=(0,),
    content="lead #Topic [[Beta]] [[Alpha]] [[Beta]] `[[Beta]] #Topic [[HiddenOnly]] #hiddenOnly` #Beta #Topic",
    raw_content="- lead #Topic [[Beta]] [[Alpha]] [[Beta]] `[[Beta]] #Topic [[HiddenOnly]] #hiddenOnly` #Beta #Topic\n",
    line_start=1,
    line_end=1,
    wikilinks=("Beta", "Alpha", "Beta"),
    tags=("Topic", "Beta", "Topic"),
    node_refs=("Beta", "Alpha", "Topic"),
    page_refs=("Beta", "Alpha", "Topic"),
)


def _validate_recipe(recipe: Recipe) -> None:
    assert recipe.family in _LITERAL_WRAPPERS
    assert recipe.primary in _PRIMARY
    assert recipe.secondary in _SECONDARY
    assert recipe.category in _CATEGORIES
    assert recipe.primary != recipe.secondary
    assert recipe.source.endswith(("\n", "\r\n"))
    assert recipe.source.count("\n") == 1
    assert len(recipe.source.encode("utf-8")) <= _MAX_SOURCE_BYTES
    if recipe not in _ANCHORS:
        opening, closing = _LITERAL_WRAPPERS[recipe.family]
        expected_content = (
            f"lead #{recipe.category} [[{recipe.primary}]] [[{recipe.secondary}]] "
            f"[[{recipe.primary}]] {opening}[[{recipe.primary}]] #Topic "
            f"[[HiddenOnly]] #hiddenOnly{closing} #{recipe.secondary} #{recipe.category}"
        )
        terminator = "\r\n" if recipe.source.endswith("\r\n") else "\n"
        assert recipe.content == expected_content
        assert recipe.source == f"- {expected_content}{terminator}"
        assert recipe.wikilinks == (recipe.primary, recipe.secondary, recipe.primary)
        assert recipe.tags == (recipe.category, recipe.secondary, recipe.category)
        assert recipe.refs == (recipe.primary, recipe.secondary, recipe.category)


def _generated_recipe_strategy() -> st.SearchStrategy[Recipe]:
    @st.composite
    def build(draw: st.DrawFn) -> Recipe:
        return _generated_recipe(
            draw(st.sampled_from(tuple(_LITERAL_WRAPPERS))),
            draw(st.sampled_from(_PRIMARY)),
            draw(st.sampled_from(_SECONDARY)),
            draw(st.sampled_from(_CATEGORIES)),
            draw(st.sampled_from(("\n", "\r\n"))),
        )

    return build()


def _generated_recipe(
    family: str,
    primary: str,
    secondary: str,
    category: str,
    terminator: str,
) -> Recipe:
    opening, closing = _LITERAL_WRAPPERS[family]
    content = (
        f"lead #{category} [[{primary}]] [[{secondary}]] [[{primary}]] "
        f"{opening}[[{primary}]] #Topic [[HiddenOnly]] #hiddenOnly{closing} "
        f"#{secondary} #{category}"
    )
    recipe = Recipe(
        family,
        f"- {content}{terminator}",
        content,
        (primary, secondary, primary),
        (category, secondary, category),
        (primary, secondary, category),
        primary,
        secondary,
        category,
    )
    _validate_recipe(recipe)
    return recipe


def _collect_recipes(candidates: tuple[Recipe, ...]) -> tuple[Recipe, ...]:
    """Retain anchors, deduplicate candidates, and cap before parser work."""
    selected: list[Recipe] = []
    seen: set[Recipe] = set()
    for recipe in (*_ANCHORS, *candidates):
        _validate_recipe(recipe)
        if recipe in seen:
            continue
        if len(selected) == _MAX_RECIPES:
            break
        seen.add(recipe)
        selected.append(recipe)
    return tuple(selected)


def _observation(page: LogseqPage) -> Observation:
    roots = page.root_nodes
    return Observation(
        len(roots),
        tuple(len(root.children) for root in roots),
        roots[0].content if roots else "",
        page.raw_content,
        roots[0].line_start if roots else None,
        roots[0].line_end if roots else None,
        tuple(roots[0].wikilinks) if roots else (),
        tuple(roots[0].tags) if roots else (),
        tuple(roots[0].refs) if roots else (),
        tuple(page.refs),
    )


def _expected_observation(recipe: Recipe) -> Observation:
    return Observation(
        1,
        (0,),
        recipe.content,
        recipe.source,
        1,
        1,
        recipe.wikilinks,
        recipe.tags,
        recipe.refs,
        recipe.refs,
    )


def _assert_observation(actual: Observation, recipe: Recipe) -> None:
    expected = _expected_observation(recipe)
    assert actual == expected


@contextmanager
def _recipe_context(recipe: Recipe) -> Iterator[None]:
    try:
        yield
    except BaseException as exc:
        exc.add_note(f"selected recipe: {recipe!r}")
        raise


def _generate_candidates() -> tuple[Recipe, ...]:
    generated: list[Recipe] = []

    @seed(104)
    @settings(
        max_examples=16,
        deadline=None,
        database=None,
        phases=(Phase.generate,),
    )
    @given(recipe=_generated_recipe_strategy())
    def collect_only(recipe: Recipe) -> None:
        generated.append(recipe)

    collect_only()
    return tuple(generated)


def test_collector_caps_deduplicates_and_keeps_literal_anchors() -> None:
    candidates = tuple(
        _generated_recipe(*values)
        for values in islice(
            product(
                tuple(_LITERAL_WRAPPERS),
                _PRIMARY,
                _SECONDARY,
                _CATEGORIES,
                ("\n", "\r\n"),
            ),
            24,
        )
    )
    selected = _collect_recipes((*_ANCHORS, *candidates, *_ANCHORS, *candidates))

    assert selected[:4] == _ANCHORS
    assert len(selected) == _MAX_RECIPES
    assert len(set(selected)) == len(selected)


def test_recipe_validation_rejects_out_of_vocabulary_values() -> None:
    invalid = replace(_ANCHORS[0], primary="[[outside]]")

    with pytest.raises(AssertionError):
        _validate_recipe(invalid)


def test_recipe_validation_rejects_source_over_two_kibibytes() -> None:
    oversized = replace(_ANCHORS[0], source=f"- {'x' * _MAX_SOURCE_BYTES}\n")

    with pytest.raises(AssertionError):
        _validate_recipe(oversized)


def test_independent_oracle_accepts_baseline_observation() -> None:
    recipe = _ANCHORS[0]
    _assert_observation(_ANCHOR_BASELINE, recipe)


@pytest.mark.parametrize(
    "mutation",
    (
        "hidden-leak",
        "hidden-tag-leak",
        "duplicate-loss",
        "occurrence-order",
        "ref-order",
        "content",
        "raw-content",
        "span",
        "root-count",
        "nonempty-children",
    ),
)
def test_independent_oracle_rejects_corrupted_observation(mutation: str) -> None:
    recipe = _ANCHORS[0]
    observed = _expected_observation(recipe)
    corrupted: dict[str, Observation] = {
        "hidden-leak": replace(observed, wikilinks=(*observed.wikilinks, "HiddenOnly")),
        "hidden-tag-leak": replace(observed, tags=(*observed.tags, "hiddenOnly")),
        "duplicate-loss": replace(observed, wikilinks=("Beta", "Alpha")),
        "occurrence-order": replace(observed, tags=("Beta", "Topic", "Topic")),
        "ref-order": replace(observed, node_refs=("Topic", "Beta", "Alpha")),
        "content": replace(observed, content="changed"),
        "raw-content": replace(observed, raw_content=observed.raw_content.rstrip("\n")),
        "span": replace(observed, line_end=2),
        "root-count": replace(observed, root_count=0),
        "nonempty-children": replace(observed, child_counts=(1,)),
    }

    with pytest.raises(AssertionError):
        _assert_observation(corrupted[mutation], recipe)


def test_generated_inline_shielding_preserves_order_and_exact_parse_identity() -> None:
    candidates = _generate_candidates()
    recipes = _collect_recipes(candidates)
    parser = StackMachineParser()

    for recipe in recipes:
        with _recipe_context(recipe):
            assert len(recipe.source.encode("utf-8")) <= _MAX_SOURCE_BYTES
            first = parser.parse(recipe.source, page_title="shielding-generated")
            first_observation = _observation(first)
            _assert_observation(first_observation, recipe)
            assert_tree_invariants(first)

            second = parser.parse(recipe.source, page_title="shielding-generated")
            second_observation = _observation(second)
            _assert_observation(second_observation, recipe)
            assert_tree_invariants(second)
            assert project_page(first, profile="exact_parse_v1") == project_page(
                second, profile="exact_parse_v1"
            )


def test_multiline_oracle_accepts_baseline() -> None:
    recipe = SpanRecipe(
        seed=104,
        span_kinds=("comment",),
        payload_counts=(1,),
        primary="Beta",
        secondary="Alpha",
        category="Topic",
        unicode_text="Éclair",
        fence_length=3,
    )
    expected = build_case(recipe, "\n").expected
    baseline = ShieldingObservation(
        root_count=1,
        child_counts=(0,),
        root_properties=(),
        page_properties=(),
        content=(
            "lead #Topic [[Beta]] [[Alpha]] [[Beta]]\n"
            "  <!--\n"
            "  [[Beta]] [[Alpha]] [[Beta]] #Topic #Alpha #Topic [[HiddenOnly]] #hiddenOnly Éclair\n"
            "  -->\n"
            "  #Alpha #Topic"
        ),
        raw_content=(
            "- lead #Topic [[Beta]] [[Alpha]] [[Beta]]\n"
            "  <!--\n"
            "  [[Beta]] [[Alpha]] [[Beta]] #Topic #Alpha #Topic [[HiddenOnly]] #hiddenOnly Éclair\n"
            "  -->\n"
            "  #Alpha #Topic\n"
        ),
        line_start=1,
        line_end=5,
        wikilinks=("Beta", "Alpha", "Beta"),
        tags=("Topic", "Alpha", "Topic"),
        node_refs=("Beta", "Alpha", "Topic"),
        page_refs=("Beta", "Alpha", "Topic"),
        parent_ids=(None,),
        left_ids=(None,),
        paths=((1, True),),
    )

    assert_observation(baseline, expected)


@pytest.mark.parametrize(
    "field,value",
    (
        ("wikilinks", ("Beta", "Alpha", "Beta", "HiddenOnly")),
        ("tags", ("Topic", "Alpha", "Topic", "hiddenOnly")),
        ("wikilinks", ("Beta", "Alpha")),
        ("wikilinks", ("Alpha", "Beta", "Beta")),
        ("node_refs", ("Topic", "Alpha", "Beta")),
        ("page_refs", ("Topic", "Alpha", "Beta")),
        ("content", "lead #Topic [[Beta]] [[Alpha]] [[Beta]]\n <!--"),
        ("raw_content", "- lead #Topic [[Beta]] [[Alpha]] [[Beta]]\n"),
        ("raw_content", "- lead #Topic [[Beta]] [[Alpha]] [[Beta]]\r\n"),
        ("line_end", 4),
        ("root_count", 0),
        ("child_counts", (1,)),
        ("root_properties", (("title", "wrong"),)),
        ("page_properties", (("title", "wrong"),)),
        ("parent_ids", ("unexpected-parent",)),
        ("left_ids", ("unexpected-left",)),
        ("paths", ((0, 1),)),
    ),
)
def test_multiline_oracle_rejects_corrupted_projection(
    field: str, value: object
) -> None:
    baseline = ShieldingObservation(
        root_count=1,
        child_counts=(0,),
        root_properties=(),
        page_properties=(),
        content=(
            "lead #Topic [[Beta]] [[Alpha]] [[Beta]]\n"
            "  <!--\n"
            "  [[HiddenOnly]] #hiddenOnly\n"
            "  -->\n"
            "  #Alpha #Topic"
        ),
        raw_content=(
            "- lead #Topic [[Beta]] [[Alpha]] [[Beta]]\n"
            "  <!--\n"
            "  [[HiddenOnly]] #hiddenOnly\n"
            "  -->\n"
            "  #Alpha #Topic\n"
        ),
        line_start=1,
        line_end=5,
        wikilinks=("Beta", "Alpha", "Beta"),
        tags=("Topic", "Alpha", "Topic"),
        node_refs=("Beta", "Alpha", "Topic"),
        page_refs=("Beta", "Alpha", "Topic"),
        parent_ids=(None,),
        left_ids=(None,),
        paths=((0, False),),
    )

    with pytest.raises(AssertionError):
        corrupted = cast(Any, replace)(baseline, **{field: value})
        assert_observation(corrupted, baseline)


def test_multiline_builder_rejects_zero_spans() -> None:
    recipe = SpanRecipe(
        seed=104,
        span_kinds=(),
        payload_counts=(),
        primary="Beta",
        secondary="Alpha",
        category="Topic",
        unicode_text="Éclair",
        fence_length=3,
    )

    with pytest.raises(ValueError):
        build_case(recipe, "\n")


def test_multiline_recipe_builder_enforces_grammar_and_budgets() -> None:
    recipe = SpanRecipe(
        seed=104,
        span_kinds=("comment", "fence-backtick-3"),
        payload_counts=(1, 1),
        primary="Beta",
        secondary="Alpha",
        category="Topic",
        unicode_text="Éclair λ",
        fence_length=3,
    )
    case = build_case(recipe, "\r\n")

    assert case.source.startswith("- lead #Topic [[Beta]] [[Alpha]] [[Beta]]\r\n")
    assert case.source.endswith("  #Alpha #Topic\r\n")
    assert (
        "  [[Beta]] [[Alpha]] [[Beta]] #Topic #Alpha #Topic "
        "[[HiddenOnly]] #hiddenOnly Éclair λ\r\n"
    ) in case.source
    assert case.content == case.source[:-2].replace("\r\n", "\n")[2:]
    assert case.line_start == 1
    assert case.line_end == 8
    assert case.source_bytes == len(case.source.encode("utf-8"))
    assert len(case.source.splitlines()) <= 12
    assert case.source_bytes <= 1024

    full_lines = SpanRecipe(
        seed=104,
        span_kinds=("comment", "fence-tilde-3"),
        payload_counts=(3, 3),
        primary="Beta",
        secondary="Alpha",
        category="Topic",
        unicode_text="λ",
        fence_length=3,
    )
    assert len(build_case(full_lines, "\n").source.splitlines()) == 12
    with pytest.raises(ValueError):
        build_case(replace(full_lines, payload_counts=(3, 4)), "\n")
    with pytest.raises(ValueError):
        build_case(replace(recipe, span_kinds=("invalid", "comment")), "\n")
    with pytest.raises(ValueError):
        build_case(replace(recipe, span_kinds=(), payload_counts=()), "\n")

    byte_boundary = replace(recipe, span_kinds=("comment",), payload_counts=(1,), unicode_text="x")
    boundary_base = build_case(byte_boundary, "\n")
    exact_text = "x" * (1024 - boundary_base.source_bytes + 1)
    exact_bytes = build_case(replace(byte_boundary, unicode_text=exact_text), "\n")
    assert exact_bytes.source_bytes == 1024
    with pytest.raises(ValueError):
        build_case(replace(byte_boundary, unicode_text=f"{exact_text}x"), "\n")


def test_multiline_collector_caps_and_deduplicates_without_refill() -> None:
    selected = collect_recipes(seed=104)

    assert len(selected) <= 8
    assert len(set(selected)) == len(selected)
    assert collect_recipes(seed=104) == selected
    assert all(len(build_case(recipe, "\n").source.encode("utf-8")) <= 1024 for recipe in selected)
    assert all(len(build_case(recipe, "\n").source.splitlines()) <= 12 for recipe in selected)
    assert len(collect_recipes(seed=2**32 - 1)) <= 8


def test_multiline_collector_stops_after_sixteen_duplicate_examples() -> None:
    from tests.parser_assurance.randomized_shielding import (
        _generate_recipes,
        _select_recipes,
    )

    recipe = SpanRecipe(
        seed=104,
        span_kinds=("comment",),
        payload_counts=(1,),
        primary="Beta",
        secondary="Alpha",
        category="Topic",
        unicode_text="Éclair",
        fence_length=3,
    )

    @st.composite
    def repeated_but_distinct(draw: st.DrawFn) -> SpanRecipe:
        draw(st.integers(min_value=0, max_value=15))
        return recipe

    candidates = _generate_recipes(seed=104, strategy=repeated_but_distinct())

    assert len(candidates) == 16
    assert _select_recipes(candidates) == (recipe,)


def test_multiline_observer_copies_only_declared_page_projection() -> None:
    page = LogseqPage(
        title="synthetic",
        raw_content="raw",
        properties={"alias": "PageAlias"},
        refs=["PageAlias"],
        root_nodes=[],
    )

    observed = observe(page)

    assert observed.root_count == 0
    assert observed.page_properties == (("alias", "PageAlias"),)
    assert observed.page_refs == ("PageAlias",)


def test_parse_only_worker_calls_parser_once(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace

    case = build_case(
        SpanRecipe(104, ("comment",), (1,), "Beta", "Alpha", "Topic", "Éclair", 3),
        "\n",
    )
    node = SimpleNamespace(
        uuid="node-1", source_uuid=None, content=case.expected.content,
        clean_text=case.expected.content, indent_level=0, properties={},
        wikilinks=list(case.wikilinks), tags=list(case.tags), assets=[], block_refs=[],
        refs=list(case.refs), task_status=None, task_priority=None, scheduled_at=None,
        deadline_at=None, repeater=None, parent_id=None, left_id=None,
        path=["node-1"], source_path=None, line_start=case.line_start,
        line_end=case.line_end, outline_path=[1], properties_order=[], created_at=None,
        updated_at=None, children=[],
    )
    page = SimpleNamespace(
        title="synthetic", raw_content=case.source, properties={}, properties_order=[],
        refs=list(case.refs), created_at=None, updated_at=None, namespace_chain=[],
        source_path=None, graph_root=None, tab_size=2, root_nodes=[node],
    )
    calls: list[str] = []

    class FakeParser:
        def parse(self, source: str, page_title: str = "untitled") -> object:
            calls.append(source)
            return page

    monkeypatch.setattr("tests.parser_assurance.randomized_shielding.StackMachineParser", FakeParser)
    context = SourceContext("a" * 40, "b" * 64, True, "3.12", "1.11.0")
    monkeypatch.setattr("tests.parser_assurance.randomized_shielding.capture_source_context", lambda: context)

    result = run_worker(case, context)

    assert result.classification == "parsed"
    assert calls == [case.source]


def test_worker_envelope_rejects_wrong_source_or_context() -> None:
    case = build_case(
        SpanRecipe(104, ("comment",), (1,), "Beta", "Alpha", "Topic", "Éclair", 3),
        "\n",
    )
    context = SourceContext("a" * 40, "b" * 64, True, "3.12", "1.11.0")

    wrong_source = replace(case, source=case.source + "tampered")
    with pytest.raises((ValueError, AssertionError)):
        run_worker(wrong_source, context)
    with pytest.raises((ValueError, AssertionError)):
        run_worker(case, SourceContext("c" * 40, "b" * 64, True, "3.12", "1.11.0"))


def test_parent_deadline_covers_generation_worker_evidence_and_cleanup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    now = [0.0]
    generation_timeouts: list[float] = []
    worker_timeouts: list[float] = []

    def fake_clock() -> float:
        return now[0]

    def fake_generate(seed: int, timeout: float) -> tuple[SpanRecipe, ...]:
        generation_timeouts.append(timeout)
        now[0] += timeout
        return _fixed_campaign_recipes()

    def fake_worker(case: ShieldingCase, context: SourceContext, *, timeout: float) -> WorkerResult:
        worker_timeouts.append(timeout)
        now[0] += timeout
        return WorkerResult(case.sha256, context.digest, "parsed", 1, case.expected)

    monkeypatch.setattr("tests.parser_assurance.randomized_shielding.time.monotonic", fake_clock)
    monkeypatch.setattr("tests.parser_assurance.randomized_shielding._generate_supervised", fake_generate)
    monkeypatch.setattr("tests.parser_assurance.randomized_shielding._worker_supervised", fake_worker)
    context = SourceContext("a" * 40, "b" * 64, True, "3.12", "1.11.0")
    monkeypatch.setattr("tests.parser_assurance.randomized_shielding.capture_source_context", lambda: context)

    owned = _MemoryAttemptDirectory()
    result = randomized_shielding._campaign_work(
        104, cast(_OwnedAttemptDirectory, owned), 0.0, 60.0
    )

    assert generation_timeouts == [5.0]
    assert len(worker_timeouts) == 16
    assert all(0 < timeout <= 3.0 for timeout in worker_timeouts)
    assert result.receipt["classification"] == "provisional-pass"
    assert result.elapsed_seconds < 53.0
    assert len(owned.files["results.jsonl"].decode().splitlines()) == 16
    assert result.cleanup == "reaped"


def _fixed_campaign_recipes() -> tuple[SpanRecipe, ...]:
    kinds = ("comment", "fence-backtick-3", "fence-backtick-4", "fence-tilde-3")
    primaries = ("Beta", "Cedar", "Éclair")
    secondaries = ("Alpha", "Maple", "Orchid")
    categories = ("Topic", "delta", "Étiquette")
    return tuple(
        SpanRecipe(
            104, (kind := kinds[index % len(kinds)],), (index % 3 + 1,),
            primaries[index % len(primaries)], secondaries[index % len(secondaries)],
            categories[index % len(categories)], ("Éclair", "λambda", "naïve")[index % 3],
            4 if kind.endswith("-4") else 3,
        )
        for index in range(8)
    )


def test_campaign_stops_after_first_nonpass_without_retry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    recipes = _fixed_campaign_recipes()
    calls: list[str] = []

    def fake_worker(case: ShieldingCase, context: SourceContext, *, timeout: float) -> WorkerResult:
        calls.append(case.sha256)
        return WorkerResult(case.sha256, context.digest, "timeout", 1, None)

    monkeypatch.setattr("tests.parser_assurance.randomized_shielding._generate_supervised", lambda seed, timeout: recipes)
    monkeypatch.setattr("tests.parser_assurance.randomized_shielding._worker_supervised", fake_worker)
    monkeypatch.setattr("tests.parser_assurance.randomized_shielding.capture_source_context", lambda: SourceContext("a" * 40, "b" * 64, True, "3.12", "1.11.0"))

    result = _run_campaign_work(104, tmp_path / "attempt")

    assert len(calls) == 1
    assert result.receipt["classification"] == "provisional-incomplete"
    assert result.attempted_count == 1


def test_campaign_receipt_binds_seed_recipes_sources_runtime_revision(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    recipes = _fixed_campaign_recipes()
    context = SourceContext("a" * 40, "b" * 64, True, "3.12", "1.11.0")
    monkeypatch.setattr("tests.parser_assurance.randomized_shielding._generate_supervised", lambda seed, timeout: recipes)
    monkeypatch.setattr("tests.parser_assurance.randomized_shielding.capture_source_context", lambda: context)
    def fake_worker(case: ShieldingCase, source_context: SourceContext, *, timeout: float) -> WorkerResult:
        return WorkerResult(case.sha256, source_context.digest, "parsed", 1, case.expected)

    monkeypatch.setattr(
        "tests.parser_assurance.randomized_shielding._worker_supervised", fake_worker
    )

    result = _run_campaign_work(104, tmp_path / "attempt")
    receipt = result.receipt

    assert result.receipt["classification"] == "provisional-pass"
    assert receipt["seed"] == 104
    assert receipt["source_context"]["head"] == context.head
    assert receipt["source_context"]["manifest_sha256"] == context.manifest_sha256
    assert receipt["source_context"]["python_version"] == context.python_version
    assert len(receipt["cases"]) == 16
    assert all(entry["source_sha256"] == entry["worker"]["source_sha256"] for entry in receipt["cases"])


def test_candidate_receipt_requires_recipe_context_and_result_binding(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    recipes = _fixed_campaign_recipes()
    context = SourceContext(
        "a" * 40, "b" * 64, True, "3.12", "1.11.0", "6.0",
        "c" * 64, (("hypothesis", "6.0"),),
    )
    monkeypatch.setattr(
        "tests.parser_assurance.randomized_shielding._generate_supervised",
        lambda seed, timeout: recipes,
    )
    monkeypatch.setattr(
        "tests.parser_assurance.randomized_shielding.capture_source_context",
        lambda: context,
    )

    def fake_worker(case: ShieldingCase, source_context: SourceContext, *, timeout: float) -> WorkerResult:
        return WorkerResult(case.sha256, source_context.digest, "parsed", 1, case.expected)

    monkeypatch.setattr(
        "tests.parser_assurance.randomized_shielding._worker_supervised", fake_worker
    )
    result = _run_campaign_work(104, tmp_path / "attempt")
    receipt = json.loads(json.dumps(result.receipt))

    assert _candidate_receipt_passes(receipt)
    receipt_bytes = (json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n").encode()
    receipt_digest = hashlib.sha256(receipt_bytes).hexdigest()
    started = time.monotonic()
    supervised = _campaign_result_from_supervisor(
        SupervisorOutcome(
            {
                "ack": "randomized-shielding-receipt-ack-v1",
                "receipt_sha256": receipt_digest,
                "receipt": receipt,
                "durable": True,
            },
            "completed", 0, len(receipt_bytes), 0.2, "reaped", receipt_bytes,
        ),
        started=started,
        deadline=started + 60,
    )
    assert supervised.classification == "pass"
    assert supervised.receipt_sha256 == receipt_digest
    receipt["cases"][0]["source"] += "tamper"
    assert not _candidate_receipt_passes(receipt)


def test_candidate_receipt_rejects_interleaved_recipe_pairs_with_valid_hashes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    receipt = _synthetic_campaign_receipt(monkeypatch, tmp_path / "attempt")
    interleaved = (0, 3, 1, 2, *range(4, 16))
    receipt["cases"] = [receipt["cases"][index] for index in interleaved]
    receipt["results"] = [receipt["results"][index] for index in interleaved]

    assert all(
        case["source_sha256"] == result["source_sha256"] == result["worker"]["source_sha256"]
        for case, result in zip(receipt["cases"], receipt["results"], strict=True)
    )
    assert not _candidate_receipt_passes(receipt)


def test_incomplete_collection_never_passes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "tests.parser_assurance.randomized_shielding._generate_supervised",
        lambda seed, timeout: _fixed_campaign_recipes()[:3],
    )

    result = _run_campaign_work(104, tmp_path / "attempt")

    assert result.receipt["classification"] == "provisional-incomplete"
    assert result.attempted_count == 0


def test_oversized_child_output_never_passes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("tests.parser_assurance.randomized_shielding._generate_supervised", lambda seed, timeout: _fixed_campaign_recipes())
    monkeypatch.setattr(
        "tests.parser_assurance.randomized_shielding._worker_supervised",
        lambda case, context, **kwargs: WorkerResult(
            case.sha256, context.digest, "parsed", 1, case.expected, output_bytes=16_385
        ),
    )

    result = _run_campaign_work(104, tmp_path / "attempt")

    assert result.receipt["classification"] == "provisional-incomplete"
    assert result.attempted_count == 1


@pytest.mark.skipif(not _POSIX_PROCESS_SUPERVISION, reason="POSIX pipe supervision is required")
def test_generation_supervisor_allows_five_second_budget() -> None:
    recipes = _generate_supervised(104, 5.0)

    assert len(recipes) <= 8
    assert len(recipes) == len(set(recipes))


@pytest.mark.skipif(not _POSIX_PROCESS_SUPERVISION, reason="POSIX process groups are required")
def test_outer_supervisor_rejects_ack_before_delayed_exit() -> None:
    script = (
        "import json,time; print(json.dumps({'ack':'durable-v1'}),flush=True); "
        "time.sleep(30)"
    )
    started = time.monotonic()
    outcome = _supervise_process(
        [sys.executable, "-c", script], b"", deadline=started + 3.0,
        cleanup_reserve=1.0, output_limit=1024,
    )

    assert outcome.packet == {"ack": "durable-v1"}
    assert outcome.classification == "incomplete"
    assert outcome.cleanup == "reaped"
    assert outcome.elapsed_seconds < 4.0


@pytest.mark.skipif(not _POSIX_PROCESS_SUPERVISION, reason="POSIX process groups are required")
def test_outer_supervisor_rejects_receipt_written_after_work_cutoff(tmp_path: Path) -> None:
    marker = tmp_path / "ready"
    script = (
        "import json,os,signal,sys,time; "
        "signal.signal(signal.SIGTERM, lambda *args: "
        "(print(json.dumps({'ack':'late-receipt'}),flush=True),sys.exit(0))); "
        "f=open(sys.argv[1]+'.pending','x'); f.write('ready'); f.close(); "
        "os.replace(sys.argv[1]+'.pending',sys.argv[1]); time.sleep(30)"
    )
    started = time.monotonic()
    outcome = _supervise_process(
        [sys.executable, "-c", script, str(marker)], b"", deadline=started + 3.0,
        cleanup_reserve=1.0, output_limit=1024,
    )

    assert marker.read_text() == "ready"
    assert outcome.returncode == 0
    assert outcome.packet is None
    assert outcome.classification == "incomplete"
    assert outcome.cleanup == "reaped"


@pytest.mark.skipif(not _POSIX_PROCESS_SUPERVISION, reason="POSIX pipe supervision is required")
def test_outer_supervisor_caps_output_while_receiving() -> None:
    script = "import os,time; os.write(1,b'x'*100000); time.sleep(30)"
    started = time.monotonic()
    outcome = _supervise_process(
        [sys.executable, "-c", script], b"", deadline=started + 3.0,
        cleanup_reserve=1.0, output_limit=128,
    )

    assert outcome.classification == "incomplete"
    assert outcome.output_bytes == 129
    assert outcome.stdout == b"x" * 129
    assert outcome.cleanup == "reaped"


@pytest.mark.skipif(not _POSIX_PROCESS_SUPERVISION, reason="POSIX process groups are required")
def test_outer_supervisor_cleans_descendant_process_group() -> None:
    script = (
        "import subprocess,sys,time; p=subprocess.Popen([sys.executable,'-c',"
        "'import time; time.sleep(30)']); print(p.pid,flush=True); time.sleep(30)"
    )
    started = time.monotonic()
    outcome = _supervise_process(
        [sys.executable, "-c", script], b"", deadline=started + 3.0,
        cleanup_reserve=1.0, output_limit=1024,
    )

    assert outcome.classification == "incomplete"
    assert outcome.cleanup == "reaped"
    descendant = int(outcome.stdout.strip())
    with pytest.raises(ProcessLookupError):
        os.kill(descendant, 0)


@pytest.mark.skipif(not _POSIX_PROCESS_SUPERVISION, reason="POSIX process groups are required")
@pytest.mark.parametrize("failure_kind", ["exception", "cancellation"])
def test_outer_supervisor_reaps_group_after_selector_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    failure_kind: str,
) -> None:
    marker = tmp_path / "children.txt"
    child_script = (
        "import os,subprocess,sys,time; "
        "p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']); "
        "f=open(sys.argv[1]+'.pending','x');f.write(str(os.getpid())+' '+str(p.pid));"
        "f.close();os.replace(sys.argv[1]+'.pending',sys.argv[1]);time.sleep(30)"
    )
    real_selector = selectors.DefaultSelector
    real_popen = randomized_shielding.subprocess.Popen
    owned_processes: list[subprocess.Popen[bytes]] = []

    class InjectedSelector:
        def __init__(self) -> None:
            self.inner = real_selector()

        def register(self, *args: Any, **kwargs: Any) -> Any:
            return self.inner.register(*args, **kwargs)

        def get_map(self) -> Any:
            return self.inner.get_map()

        def select(self, timeout: float | None = None) -> Any:
            wait_until = started + 4.0
            ready = False
            while time.monotonic() < wait_until:
                try:
                    fields = marker.read_text().split()
                except FileNotFoundError:
                    fields = []
                if len(fields) == 2 and all(field.isdecimal() and int(field) > 0 for field in fields):
                    ready = True
                    break
                time.sleep(0.005)
            if not ready:
                raise RuntimeError("harmless child fixture did not start")
            if failure_kind == "cancellation":
                raise KeyboardInterrupt
            raise RuntimeError("injected selector failure")

        def close(self) -> None:
            self.inner.close()

    def tracking_popen(*args: Any, **kwargs: Any) -> subprocess.Popen[bytes]:
        process = real_popen(*args, **kwargs)
        owned_processes.append(process)
        return process

    monkeypatch.setattr(randomized_shielding.selectors, "DefaultSelector", InjectedSelector)
    monkeypatch.setattr(randomized_shielding.subprocess, "Popen", tracking_popen)
    started = time.monotonic()
    try:
        outcomes: list[SupervisorOutcome] = []
        failures: list[BaseException] = []

        def supervise() -> None:
            try:
                outcomes.append(_supervise_process(
                    [sys.executable, "-c", child_script, str(marker)], b"",
                    deadline=started + 6.0, cleanup_reserve=1.0, output_limit=1024,
                ))
            except BaseException as error:
                failures.append(error)

        thread = threading.Thread(target=supervise)
        thread.start()
        thread.join(timeout=7.0)
        assert not thread.is_alive()
        assert not failures
        assert len(outcomes) == 1
        outcome = outcomes[0]
        assert outcome.classification == "incomplete"
        assert outcome.cleanup == "reaped"
        assert len(owned_processes) == 1
        assert owned_processes[0].poll() is not None
        parent_pid, descendant_pid = map(int, marker.read_text().split())
        assert parent_pid == owned_processes[0].pid
        with pytest.raises(ProcessLookupError):
            os.kill(descendant_pid, 0)
    finally:
        for process in owned_processes:
            if process.poll() is None:
                with suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=1.0)


def test_source_manifest_detects_parser_and_lock_drift(tmp_path: Path) -> None:
    parser = tmp_path / "src" / "logseq_matryca_parser" / "logos_parser.py"
    lock = tmp_path / "uv.lock"
    parser.parent.mkdir(parents=True)
    parser.write_bytes(b"parser version one")
    lock.write_bytes(b"locked dependencies one")
    paths = ("src/logseq_matryca_parser/logos_parser.py", "uv.lock")

    initial = _source_manifest_digest(tmp_path, paths)
    parser.write_bytes(b"parser version two")
    changed_parser = _source_manifest_digest(tmp_path, paths)
    lock.write_bytes(b"locked dependencies two")
    changed_lock = _source_manifest_digest(tmp_path, paths)

    assert initial != changed_parser
    assert changed_parser != changed_lock


def test_dependency_manifest_detects_same_version_byte_drift(tmp_path: Path) -> None:
    installed_file = tmp_path / "dependency.py"
    installed_file.write_bytes(b"same-version bytes one")
    initial = _dependency_manifest_digest({"example-dependency==1.0": (installed_file,)})
    installed_file.write_bytes(b"same-version bytes two")

    assert initial != _dependency_manifest_digest({"example-dependency==1.0": (installed_file,)})


@pytest.mark.skipif(not _OWNED_DIRECTORY_CAPABILITY, reason="no-follow directory descriptors are required")
def test_owned_attempt_directory_survives_symlink_substitution(tmp_path: Path) -> None:
    attempt = tmp_path / "attempt"
    decoy = tmp_path / "decoy"
    decoy.mkdir()
    owned = _OwnedAttemptDirectory.create(attempt)
    try:
        owned.write_new("plan.jsonl", b"plan")
        attempt.rename(tmp_path / "original-attempt")
        attempt.symlink_to(decoy, target_is_directory=True)
        owned.write_new("results.jsonl", b"results")

        with pytest.raises(OSError):
            owned.verify_path()
        assert (tmp_path / "original-attempt" / "plan.jsonl").read_bytes() == b"plan"
        assert (tmp_path / "original-attempt" / "results.jsonl").read_bytes() == b"results"
        assert not (decoy / "results.jsonl").exists()
    finally:
        owned.close()


def test_optimized_runtime_rejected_before_assertion_based_qualification() -> None:
    completed = subprocess.run(
        [sys.executable, "-O", "-c", (
            "from tests.parser_assurance.randomized_shielding import "
            "_ensure_assertions_enabled; _ensure_assertions_enabled()"
        )],
        capture_output=True,
        text=True,
        check=False,
        timeout=10.0,
    )

    assert completed.returncode == 1
    assert "RuntimeError: optimized Python disables required parser-assurance assertions" in completed.stderr


def test_provisional_receipt_without_verified_group_cleanup_never_passes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    receipt = _synthetic_campaign_receipt(monkeypatch, tmp_path / "attempt")
    receipt_bytes = (json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n").encode()
    digest = hashlib.sha256(receipt_bytes).hexdigest()
    outcome = SupervisorOutcome(
        {
            "ack": "randomized-shielding-receipt-ack-v1",
            "receipt_sha256": digest,
            "receipt": receipt,
            "durable": True,
        },
        "completed", 0, len(receipt_bytes), 0.1, "reaped", receipt_bytes,
    )

    class FakeClock:
        @staticmethod
        def monotonic() -> float:
            return 10.0

    monkeypatch.setattr(randomized_shielding, "time", FakeClock)
    baseline = _campaign_result_from_supervisor(outcome, started=9.0, deadline=20.0)
    assert baseline.classification == "pass"
    assert baseline.receipt_sha256 == digest
    result = _campaign_result_from_supervisor(
        replace(outcome, cleanup="unconfirmed"), started=9.0, deadline=20.0
    )
    assert result.classification == "incomplete"
    assert result.receipt_sha256 == digest
    assert (result.attempted_count, result.completed_count) == (16, 16)


def test_supervisor_rechecks_deadline_after_receipt_validation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    receipt = _synthetic_campaign_receipt(monkeypatch, tmp_path / "attempt")
    receipt_bytes = (json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n").encode()
    digest = hashlib.sha256(receipt_bytes).hexdigest()
    now = [10.0]

    class FakeClock:
        @staticmethod
        def monotonic() -> float:
            return now[0]

    original_check = randomized_shielding._candidate_receipt_passes

    def delayed_check(candidate: dict[str, Any]) -> bool:
        now[0] = 10.6
        return original_check(candidate)

    monkeypatch.setattr(randomized_shielding, "time", FakeClock)
    monkeypatch.setattr(randomized_shielding, "_candidate_receipt_passes", delayed_check)
    outcome = SupervisorOutcome(
        {
            "ack": "randomized-shielding-receipt-ack-v1",
            "receipt_sha256": digest,
            "receipt": receipt,
            "durable": True,
        },
        "completed", 0, len(receipt_bytes), 0.2, "reaped", receipt_bytes,
    )

    result = _campaign_result_from_supervisor(outcome, started=9.9, deadline=10.5)

    assert result.classification == "incomplete"


@pytest.mark.skipif(not _POSIX_PROCESS_SUPERVISION, reason="POSIX pipe supervision is required")
def test_campaign_transfer_cap_accepts_synthetic_sixteen_case_envelope(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    receipt = _synthetic_campaign_receipt(monkeypatch, tmp_path / "attempt")
    receipt_bytes = (json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n").encode()
    packet = {
        "ack": "randomized-shielding-receipt-ack-v1",
        "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
        "receipt": receipt,
        "durable": True,
    }
    transfer = json.dumps(packet, sort_keys=True, separators=(",", ":")).encode()
    assert len(transfer) > MAX_CHILD_OUTPUT
    assert len(transfer) <= MAX_CAMPAIGN_TRANSFER <= MAX_ATTEMPT_EVIDENCE
    started = time.monotonic()
    outcome = _supervise_process(
        [sys.executable, "-c", "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())"],
        transfer,
        deadline=started + 3.0,
        cleanup_reserve=0.25,
        output_limit=MAX_CAMPAIGN_TRANSFER,
    )

    assert outcome.classification == "completed"
    assert outcome.output_bytes == len(transfer)
    assert outcome.packet == packet


@pytest.mark.skipif(not _POSIX_PROCESS_SUPERVISION, reason="POSIX pipe supervision is required")
def test_worker_output_cap_stays_sixteen_kibibytes() -> None:
    with pytest.raises(_ChildError) as caught:
        _run_bounded_child(
            [sys.executable, "-c", "import os; os.write(1,b'x'*16385)"],
            {},
            3.0,
        )
    assert caught.value.classification == "runner_failure"
    assert caught.value.output_bytes == 16385
    assert caught.value.cleanup == "reaped"


def test_cli_reports_final_supervisor_summary_not_provisional_receipt(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    receipt = {
        "protocol": "randomized-shielding-v1",
        "classification": "provisional-pass",
        "attempted_count": 16,
        "completed_count": 16,
    }
    receipt_bytes = (json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n").encode()
    final = CampaignResult(
        "pass", 16, 16, 2.5, receipt, "reaped",
        hashlib.sha256(receipt_bytes).hexdigest(), "outer-verified",
    )
    monkeypatch.setattr(randomized_shielding, "run_pilot", lambda seed, output_dir: final)

    exit_code = main([
        "--protocol", "randomized-shielding-v1", "--opt-in", "--seed", "104",
        "--output-dir", "/tmp/synthetic-attempt",
    ])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output == {
        "classification": "pass",
        "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
        "supervisor_status": "outer-verified",
        "elapsed_seconds": 2.5,
        "cleanup": "reaped",
        "attempted_count": 16,
        "completed_count": 16,
        "count_basis": "receipt-bound",
    }


def test_cli_labels_opaque_attempt_count_as_conservative_upper_bound(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    result = CampaignResult(
        "incomplete", 16, 0, 60.0, {}, "unconfirmed", None, "unconfirmed"
    )
    monkeypatch.setattr(randomized_shielding, "run_pilot", lambda seed, output_dir: result)

    assert main([
        "--protocol", "randomized-shielding-v1", "--opt-in", "--seed", "104",
        "--output-dir", "/tmp/synthetic-attempt",
    ]) != 0
    output = json.loads(capsys.readouterr().out)

    assert output["classification"] == "incomplete"
    assert output["attempted_count"] == 16
    assert output["completed_count"] == 0
    assert output["count_basis"] == "conservative-upper-bound"
    assert output["receipt_sha256"] is None


def test_cli_reports_receipt_bound_partial_counts(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    receipt = {
        "protocol": "randomized-shielding-v1",
        "classification": "provisional-incomplete",
        "attempted_count": 1,
        "completed_count": 0,
    }
    receipt_bytes = (json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n").encode()
    digest = hashlib.sha256(receipt_bytes).hexdigest()
    result = CampaignResult(
        "incomplete", 1, 0, 3.0, receipt, "unconfirmed", digest, "unconfirmed"
    )
    monkeypatch.setattr(randomized_shielding, "run_pilot", lambda seed, output_dir: result)

    assert main([
        "--protocol", "randomized-shielding-v1", "--opt-in", "--seed", "104",
        "--output-dir", "/tmp/synthetic-attempt",
    ]) != 0
    output = json.loads(capsys.readouterr().out)

    assert output["attempted_count"] == 1
    assert output["completed_count"] == 0
    assert output["count_basis"] == "receipt-bound"
    assert output["receipt_sha256"] == digest


def test_cli_rejects_malformed_counts_and_downgrades_to_upper_bound(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    receipt = {
        "protocol": "randomized-shielding-v1",
        "classification": "provisional-pass",
        "attempted_count": 17,
        "completed_count": 17,
    }
    receipt_bytes = (json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n").encode()
    result = CampaignResult(
        "pass", 17, 17, 2.5, receipt, "reaped",
        hashlib.sha256(receipt_bytes).hexdigest(), "outer-verified",
    )
    monkeypatch.setattr(randomized_shielding, "run_pilot", lambda seed, output_dir: result)

    assert main([
        "--protocol", "randomized-shielding-v1", "--opt-in", "--seed", "104",
        "--output-dir", "/tmp/synthetic-attempt",
    ]) != 0
    output = json.loads(capsys.readouterr().out)

    assert output["classification"] == "incomplete"
    assert output["attempted_count"] == 16
    assert output["completed_count"] == 0
    assert output["count_basis"] == "conservative-upper-bound"
    assert output["receipt_sha256"] is None


def test_cli_summary_sanitizes_oversized_untrusted_fields(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    malformed = CampaignResult(
        "pass", 16, 16, 1e300, {}, "z" * 5000, "d" * 5000, "x" * 5000
    )
    monkeypatch.setattr(randomized_shielding, "run_pilot", lambda seed, output_dir: malformed)

    exit_code = main([
        "--protocol", "randomized-shielding-v1", "--opt-in", "--seed", "104",
        "--output-dir", "/tmp/synthetic-attempt",
    ])
    text = capsys.readouterr().out
    output = json.loads(text)

    assert exit_code != 0
    assert len(text.encode("utf-8")) <= MAX_CLI_SUMMARY
    assert output["classification"] == "incomplete"
    assert output["receipt_sha256"] is None
    assert output["supervisor_status"] == "unverified"
    assert output["cleanup"] == "unconfirmed"
    assert output["attempted_count"] == 16
    assert output["completed_count"] == 0
    assert output["count_basis"] == "conservative-upper-bound"


def test_timeout_preserves_bound_attempt_count_or_uses_safe_upper_bound() -> None:
    receipt = {
        "protocol": "randomized-shielding-v1",
        "classification": "provisional-incomplete",
        "attempted_count": 1,
        "completed_count": 0,
    }
    receipt_bytes = (json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n").encode()
    packet = {
        "ack": "randomized-shielding-receipt-ack-v1",
        "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
        "receipt": receipt,
        "durable": True,
    }
    started = time.monotonic()
    timed_out = SupervisorOutcome(
        packet, "incomplete", None, len(receipt_bytes), 60.0, "reaped", receipt_bytes
    )
    opaque = SupervisorOutcome(None, "incomplete", None, 0, 60.0, "unconfirmed", b"")

    known = _campaign_result_from_supervisor(
        timed_out, started=started, deadline=started + 60.0
    )
    unknown = _campaign_result_from_supervisor(
        opaque, started=started, deadline=started + 60.0
    )

    assert (known.classification, known.attempted_count, known.completed_count) == (
        "incomplete", 1, 0
    )
    assert (unknown.classification, unknown.attempted_count, unknown.completed_count) == (
        "incomplete", 16, 0
    )
