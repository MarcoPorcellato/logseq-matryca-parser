"""Opt-in, bounded malformed Markdown generation with source-free recipe replay.

Hypothesis collects recipes before any parser child is launched. The collector
has a separate hard output cap: Hypothesis replay or shrinking cannot multiply
subprocess calls. Parser failures stop the profile without automatic retries or
minimization. These are robustness checks, not semantic or conformance oracles.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass, fields

import hypothesis
from hypothesis import Phase, given, settings
from hypothesis import strategies as st

from tests.parser_assurance.adversarial import (
    DEFAULT_TIMEOUT_SECONDS,
    CaseResult,
    GeneratedCase,
    run_case,
)

SCHEMA_VERSION = 1
FAMILIES = (
    "incomplete-link", "open-fence", "unresolved-reference", "broken-property", "delimiter-run",
)
PROFILE_EXAMPLES = {"fast": 4, "broad": 12}
TOKENS = {"ascii": "node", "unicode": "caffè東京🙂"}
NEWLINES = {"lf": "\n", "crlf": "\r\n"}


@dataclass(frozen=True)
class Recipe:
    """Only finite vocabulary and bounded numbers; never user-provided text."""

    family: str
    depth: int
    width: int
    delimiter_run: int
    property_count: int
    newline: str
    token: str


def _validate(recipe: Recipe) -> None:
    for value, choices in (
        (recipe.family, FAMILIES), (recipe.newline, NEWLINES), (recipe.token, TOKENS),
    ):
        if not isinstance(value, str) or value not in choices:
            raise ValueError("unknown recipe vocabulary")
    for number, minimum, maximum in (
        (recipe.depth, 1, 4), (recipe.width, 1, 3),
        (recipe.delimiter_run, 1, 16), (recipe.property_count, 0, 4),
    ):
        if type(number) is not int or not minimum <= number <= maximum:
            raise ValueError("recipe exceeds generation budget")


def recipe_from_json(raw: str) -> Recipe:
    """Reject free text, missing fields, and expanded budgets before replay."""
    payload = json.loads(raw)
    if not isinstance(payload, dict) or set(payload) != {field.name for field in fields(Recipe)}:
        raise ValueError("invalid recipe fields")
    recipe = Recipe(**payload)
    _validate(recipe)
    return recipe


def recipe_strategy(family: str) -> st.SearchStrategy[Recipe]:
    """Generate budgeted shapes directly, without rejection-heavy filters."""
    if family not in FAMILIES:
        raise ValueError("unknown malformed family")
    return st.builds(
        Recipe, family=st.just(family), depth=st.integers(1, 4), width=st.integers(1, 3),
        delimiter_run=st.integers(1, 16), property_count=st.integers(0, 4),
        newline=st.sampled_from(tuple(NEWLINES)), token=st.sampled_from(tuple(TOKENS)),
    )


def build_case(recipe: Recipe) -> GeneratedCase:
    """Render one original synthetic case, independent of Hypothesis versions."""
    _validate(recipe)
    token = TOKENS[recipe.token]
    newline = NEWLINES[recipe.newline]
    lines: list[str] = []
    for level in range(recipe.depth):
        lines.append(f"{'  ' * level}- {token}-{level}")
        for index in range(recipe.width):
            lines.append(f"{'  ' * (level + 1)}- leaf-{level}-{index}")
    suffixes = {
        "incomplete-link": " [[Unclosed",
        "open-fence": "",
        "unresolved-reference": " ((00000104-aaaa-bbbb-cccc-000000000000))",
        "broken-property": "",
        "delimiter-run": f" {'`' * recipe.delimiter_run}[[Unclosed",
    }
    lines[-1] += suffixes[recipe.family]
    indent = "  " * (recipe.depth + 1)
    for index in range(recipe.property_count):
        lines.append(f"{indent}property-{index}:: [[Unclosed")
    if recipe.family == "open-fence":
        lines.extend((f"{indent}```text", f"{indent}[[LiteralOnly]]"))
    elif recipe.family == "broken-property":
        lines.append(f"{indent}:: [[Unclosed")
    source = newline.join(lines) + newline
    if len(source.encode("utf-8")) > 16_384:
        raise ValueError("generated source exceeds byte budget")
    digest = hashlib.sha256(json.dumps(asdict(recipe), sort_keys=True).encode()).hexdigest()
    return GeneratedCase(
        case_id=f"hypothesis-malformed-v{SCHEMA_VERSION}-{digest}", family=recipe.family,
        seed=0, index=0, source=source, input_kind="malformed",
        strict_refs=recipe.family == "unresolved-reference", semantic_roundtrip=False,
        expected_classifications=(
            ("expected_parser_error",) if recipe.family == "unresolved-reference"
            else ("parsed", "expected_parser_error")
        ),
    )


def _collect_family(family: str, limit: int) -> tuple[Recipe, ...]:
    collected: list[Recipe] = []

    @settings(
        max_examples=limit, derandomize=True, database=None, deadline=None,
        phases=(Phase.generate,),
    )
    @given(recipe=recipe_strategy(family))
    def collect(recipe: Recipe) -> None:
        if len(collected) < limit and recipe not in collected:
            collected.append(recipe)

    collect()
    if not collected:
        raise RuntimeError("recipe collection returned no cases")
    return tuple(collected)


def recipes_for_profile(profile: str) -> tuple[Recipe, ...]:
    """Collect at most 20/60 recipes; guarantee at least one per family."""
    if profile not in PROFILE_EXAMPLES:
        raise ValueError("unknown generation profile")
    return tuple(
        recipe for family in FAMILIES for recipe in _collect_family(family, PROFILE_EXAMPLES[profile])
    )


def is_accepted(case: GeneratedCase, result: CaseResult) -> bool:
    """Keep the strict-reference oracle specific without tightening other families."""
    return result.is_expected_for(case) and (
        case.family != "unresolved-reference" or result.exception_type == "BlockReferenceError"
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Print source-free receipts, including exact recipes for future replay."""
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--profile", choices=tuple(PROFILE_EXAMPLES), default="fast")
    selection.add_argument("--recipe", help="Replay the exact JSON recipe from a receipt.")
    args = parser.parse_args(argv)
    recipes = (
        (recipe_from_json(args.recipe),) if args.recipe is not None
        else recipes_for_profile(args.profile)
    )
    entries: list[dict[str, object]] = []
    failed = False
    for recipe in recipes:
        case = build_case(recipe)
        result: CaseResult = run_case(case)
        entries.append({"recipe": asdict(recipe), "result": asdict(result)})
        if not is_accepted(case, result):
            failed = True
            break
    print(json.dumps({
        "recipe_schema_version": SCHEMA_VERSION, "hypothesis_version": hypothesis.__version__,
        "profile": "replay" if args.recipe is not None else args.profile,
        "child_timeout_seconds": DEFAULT_TIMEOUT_SECONDS, "results": entries,
    }, sort_keys=True))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
