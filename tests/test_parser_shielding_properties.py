"""Bounded generated assurance for inline shielding and duplicate references."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from itertools import islice, product

import pytest
from hypothesis import Phase, given, seed, settings
from hypothesis import strategies as st

from logseq_matryca_parser.logos_core import LogseqPage
from logseq_matryca_parser.logos_parser import StackMachineParser
from tests.parser_assurance.invariants import assert_tree_invariants
from tests.parser_assurance.projection import project_page

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
