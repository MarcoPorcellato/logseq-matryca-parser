"""Bounds, replay, and failure sensitivity for malformed property generation."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from tests.parser_assurance import adversarial
from tests.parser_assurance import malformed_properties as malformed


@pytest.mark.parametrize("family", malformed.FAMILIES)
@settings(max_examples=30, derandomize=True, database=None, deadline=None)
@given(data=st.data())
def test_generated_recipes_keep_source_and_outline_within_budget(
    family: str, data: st.DataObject,
) -> None:
    recipe = data.draw(malformed.recipe_strategy(family))
    case = malformed.build_case(recipe)
    assert case.source_bytes <= 16_384
    assert sum(line.lstrip().startswith("- ") for line in case.source.splitlines()) <= 16
    assert max(
        len(line) - len(line.lstrip(" "))
        for line in case.source.splitlines() if line.lstrip().startswith("- ")
    ) <= 8
    assert case.input_kind == "malformed"
    assert case.semantic_roundtrip is False
    assert case.expected_classifications == (
        ("expected_parser_error",) if family == "unresolved-reference"
        else ("parsed", "expected_parser_error")
    )


def test_recipe_replay_preserves_exact_source_and_parser_options() -> None:
    recipe = malformed.Recipe("unresolved-reference", 1, 1, 1, 0, "lf", "ascii")
    case = malformed.build_case(recipe)
    replay = malformed.build_case(malformed.recipe_from_json(json.dumps(asdict(recipe))))
    assert case.source == "- node-0\n  - leaf-0-0 ((00000104-aaaa-bbbb-cccc-000000000000))\n"
    assert case.strict_refs is True
    assert replay == case


@pytest.mark.parametrize(
    "changes",
    [
        {"depth": 5}, {"width": 4}, {"delimiter_run": 17}, {"property_count": 5},
        {"depth": True}, {"family": "unknown"}, {"newline": "unknown"},
        {"token": "private text"},
    ],
)
def test_replay_rejects_out_of_budget_or_free_text_recipes(changes: dict[str, object]) -> None:
    payload = asdict(malformed.Recipe("incomplete-link", 1, 1, 1, 0, "lf", "ascii"))
    payload.update(changes)
    with pytest.raises(ValueError):
        malformed.recipe_from_json(json.dumps(payload))


def test_replay_rejects_extra_source_field_and_missing_parameters() -> None:
    payload = asdict(malformed.Recipe("incomplete-link", 1, 1, 1, 0, "lf", "ascii"))
    invalid_payloads: tuple[object, ...] = (
        {**payload, "source": "private text"}, {"family": "incomplete-link"}, [],
    )
    for invalid in invalid_payloads:
        with pytest.raises(ValueError):
            malformed.recipe_from_json(json.dumps(invalid))


def test_fast_generation_is_repeatable_and_covers_every_family() -> None:
    first = malformed.recipes_for_profile("fast")
    assert first == malformed.recipes_for_profile("fast")
    assert 5 <= len(first) <= 20
    assert {recipe.family for recipe in first} == set(malformed.FAMILIES)
    assert len(set(first)) == len(first)


@pytest.mark.parametrize("family", malformed.FAMILIES)
def test_each_malformed_family_uses_real_subprocess_classification(family: str) -> None:
    recipe = malformed.Recipe(family, 1, 1, 3, 2, "crlf", "unicode")
    case = malformed.build_case(recipe)
    result = adversarial.run_case(case)
    assert result.is_expected_for(case), asdict(result)
    if family == "unresolved-reference":
        assert result.classification == "expected_parser_error"
        assert result.exception_type == "BlockReferenceError"
    else:
        assert result.classification == "parsed"


@pytest.mark.parametrize("classification", [
    "unexpected_exception", "invariant_failure", "semantic_roundtrip_failure",
    "timeout", "runner_failure",
])
def test_unexpected_result_stops_profile_and_emits_source_free_replay(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    classification: adversarial.Classification,
) -> None:
    seen: list[adversarial.GeneratedCase] = []

    def failure(case: adversarial.GeneratedCase) -> adversarial.CaseResult:
        seen.append(case)
        return adversarial._base_result(
            case, classification=classification, exception_type="ValueError",
            semantic_roundtrip_checked=False,
        )

    monkeypatch.setattr(malformed, "run_case", failure)
    assert malformed.main(["--profile", "fast"]) == 1
    receipt = json.loads(capsys.readouterr().out)
    assert len(seen) == 1
    assert len(receipt["results"]) == 1
    entry = receipt["results"][0]
    assert entry["result"]["classification"] == classification
    assert "source" not in entry["result"]
    assert seen[0].source not in json.dumps(receipt)
    assert malformed.build_case(malformed.recipe_from_json(json.dumps(entry["recipe"]))) == seen[0]


def test_cli_replay_does_not_generate_or_rerun_other_cases(capsys: pytest.CaptureFixture[str]) -> None:
    recipe = malformed.Recipe("unresolved-reference", 1, 1, 1, 0, "lf", "ascii")
    assert malformed.main(["--recipe", json.dumps(asdict(recipe))]) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert len(receipt["results"]) == 1
    assert receipt["results"][0]["result"]["classification"] == "expected_parser_error"


@pytest.mark.parametrize("error_type,expected_exit", [
    ("BlockReferenceError", 0), ("LogseqIndentationError", 1), (None, 1),
])
def test_strict_reference_oracle_rejects_wrong_typed_error_without_retry(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    error_type: str | None, expected_exit: int,
) -> None:
    attempts: list[str] = []

    def typed_error(case: adversarial.GeneratedCase) -> adversarial.CaseResult:
        attempts.append(case.case_id)
        return adversarial._base_result(
            case, classification="expected_parser_error", exception_type=error_type,
            semantic_roundtrip_checked=False,
        )

    monkeypatch.setattr(malformed, "run_case", typed_error)
    recipe = malformed.Recipe("unresolved-reference", 1, 1, 1, 0, "lf", "ascii")
    assert malformed.main(["--recipe", json.dumps(asdict(recipe))]) == expected_exit
    assert len(attempts) == 1
    assert json.loads(capsys.readouterr().out)["results"][0]["result"]["exception_type"] == error_type


def test_broad_collection_keeps_independent_child_budget() -> None:
    recipes = malformed.recipes_for_profile("broad")
    assert 5 <= len(recipes) <= 60
    assert {recipe.family for recipe in recipes} == set(malformed.FAMILIES)


def test_collector_overcalling_cannot_expand_parser_recipe_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def overcalling_given(**_strategies: object) -> Callable[
        [Callable[[malformed.Recipe], None]], Callable[[], None]
    ]:
        def decorate(collect: Callable[[malformed.Recipe], None]) -> Callable[[], None]:
            def overcall() -> None:
                for run in range(1, 17):
                    collect(malformed.Recipe("incomplete-link", 1, 1, run, 0, "lf", "ascii"))
            return overcall
        return decorate

    def identity_settings(**_options: object) -> Callable[[Callable[[], None]], Callable[[], None]]:
        return lambda function: function

    monkeypatch.setattr(malformed, "given", overcalling_given)
    monkeypatch.setattr(malformed, "settings", identity_settings)
    recipes = malformed._collect_family("incomplete-link", 4)
    assert len(recipes) == 4
    assert [recipe.delimiter_run for recipe in recipes] == [1, 2, 3, 4]
