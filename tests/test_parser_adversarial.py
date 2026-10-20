"""Contracts for the deterministic, subprocess-bounded parser laboratory."""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict

import pytest

from tests.parser_assurance import adversarial


def test_generated_cases_are_bounded_and_order_independent() -> None:
    forward = adversarial.generate_cases(
        104,
        cases_per_family=3,
        families=tuple(adversarial.FAMILY_GENERATORS),
    )
    reversed_families = adversarial.generate_cases(
        104,
        cases_per_family=3,
        families=tuple(reversed(adversarial.FAMILY_GENERATORS)),
    )

    assert forward == reversed_families
    assert len({case.case_id for case in forward}) == len(forward)
    assert all(case.source_bytes <= adversarial.MAX_CASE_BYTES for case in forward)
    delimiter_sources = [case.source for case in forward if case.family == "escapes-delimiters"]
    assert any("`a ``" in source for source in delimiter_sources)
    assert any("``outer `" in source for source in delimiter_sources)


def test_fast_profile_has_expected_classifications_and_semantic_roundtrips() -> None:
    cases = adversarial.cases_for_profile("fast")
    results = [adversarial.run_case(case) for case in cases]

    unexpected_results = [
        {**asdict(result), "expected_classifications": case.expected_classifications}
        for case, result in zip(cases, results, strict=True)
        if not result.is_expected_for(case)
    ]
    assert not unexpected_results, json.dumps(
        {"unexpected_results": unexpected_results}, sort_keys=True
    )
    unchecked_semantic_roundtrips = [
        asdict(result)
        for case, result in zip(cases, results, strict=True)
        if case.semantic_roundtrip and not result.semantic_roundtrip_checked
    ]
    assert not unchecked_semantic_roundtrips, json.dumps(
        {"unchecked_semantic_roundtrips": unchecked_semantic_roundtrips}, sort_keys=True
    )
    assert any(result.classification == "expected_parser_error" for result in results)


def test_timeout_is_classified_without_accepting_a_partial_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = adversarial.cases_for_profile("fast")[0]

    def timeout(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired("parser", 0.01)

    monkeypatch.setattr(adversarial.subprocess, "run", timeout)
    result = adversarial.run_case(case, timeout_seconds=0.01)

    assert result.classification == "timeout"
    assert result.semantic_roundtrip_checked is False


@pytest.mark.parametrize(
    ("classification", "exception_type", "receipt_key"),
    [
        ("timeout", None, "unexpected_results"),
        ("runner_failure", "exit-1", "unexpected_results"),
        ("unexpected_exception", "ValueError", "unexpected_results"),
        ("invariant_failure", "AssertionError", "unexpected_results"),
        ("semantic_roundtrip_failure", None, "unexpected_results"),
        ("parsed", None, "unchecked_semantic_roundtrips"),
    ],
)
def test_fast_profile_failure_reports_source_free_case_receipt(
    monkeypatch: pytest.MonkeyPatch,
    classification: adversarial.Classification,
    exception_type: str | None,
    receipt_key: str,
) -> None:
    cases = adversarial.cases_for_profile("fast")
    failed_case = next(case for case in cases if case.semantic_roundtrip)

    def classified_result(case: adversarial.GeneratedCase) -> adversarial.CaseResult:
        failed = case.case_id == failed_case.case_id
        return adversarial._base_result(
            case,
            classification=classification if failed else case.expected_classifications[0],
            exception_type=exception_type if failed else None,
            semantic_roundtrip_checked=case.semantic_roundtrip and not failed,
        )

    # Replace only process execution; exercise the real profile assertions.
    monkeypatch.setattr(adversarial, "run_case", classified_result)
    with pytest.raises(AssertionError) as failure:
        test_fast_profile_has_expected_classifications_and_semantic_roundtrips()

    message = str(failure.value)
    receipt = json.loads(message.splitlines()[0])[receipt_key]
    assert len(receipt) == 1
    assert receipt[0]["case_id"] == failed_case.case_id
    assert receipt[0]["classification"] == classification
    assert receipt[0]["exception_type"] == exception_type
    assert receipt[0]["source_sha256"] == failed_case.source_sha256
    assert receipt[0]["source_bytes"] == failed_case.source_bytes
    assert "source" not in receipt[0]
    assert failed_case.source not in message


def test_minimization_is_deterministic_and_preserves_the_given_predicate() -> None:
    case = adversarial.GeneratedCase(
        case_id="minimize",
        family="test",
        seed=1,
        index=0,
        source="- keep needle\n- discard one\n- discard two\n",
        input_kind="malformed",
        strict_refs=False,
        semantic_roundtrip=False,
        expected_classifications=("unexpected_exception",),
    )

    def predicate(source: str) -> bool:
        return "needle" in source

    minimized = adversarial.minimize_source(case, preserves_failure=predicate)

    assert minimized.source == "- keep needle\n"
    assert predicate(minimized.source)


def test_unexpected_minimization_preserves_classification_and_exception_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = adversarial.GeneratedCase(
        case_id="unexpected-minimize",
        family="test",
        seed=1,
        index=0,
        source="- keep-classification\n- keep-exception\n- discard\n",
        input_kind="malformed",
        strict_refs=False,
        semantic_roundtrip=False,
        expected_classifications=("parsed",),
    )
    original = adversarial._base_result(
        case,
        classification="unexpected_exception",
        exception_type="ExpectedError",
        semantic_roundtrip_checked=False,
    )

    observed_timeouts: list[float] = []

    def replay(candidate: adversarial.GeneratedCase, *, timeout_seconds: float) -> adversarial.CaseResult:
        observed_timeouts.append(timeout_seconds)
        return adversarial._base_result(
            candidate,
            classification=(
                "unexpected_exception"
                if "keep-classification" in candidate.source
                else "invariant_failure"
            ),
            exception_type=(
                "ExpectedError" if "keep-exception" in candidate.source else "OtherError"
            ),
            semantic_roundtrip_checked=False,
        )

    monkeypatch.setattr(adversarial, "run_case", replay)
    minimized = adversarial._minimize_unexpected(case, original, timeout_seconds=0.2)

    expected_source = "- keep-classification\n- keep-exception\n"
    assert observed_timeouts
    assert set(observed_timeouts) == {0.2}
    assert minimized.minimized_source_bytes == len(expected_source.encode("utf-8"))
    assert minimized.minimized_source_sha256 == adversarial.GeneratedCase(
        case_id=case.case_id,
        family=case.family,
        seed=case.seed,
        index=case.index,
        source=expected_source,
        input_kind=case.input_kind,
        strict_refs=case.strict_refs,
        semantic_roundtrip=case.semantic_roundtrip,
        expected_classifications=case.expected_classifications,
    ).source_sha256


def test_replay_rejects_unknown_case_id() -> None:
    with pytest.raises(ValueError, match="case not found"):
        adversarial.run_profile("fast", case_id="m3-missing")
