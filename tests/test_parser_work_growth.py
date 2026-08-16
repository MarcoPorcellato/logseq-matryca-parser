"""Contracts for the deterministic, test-only parser work-growth laboratory."""

from __future__ import annotations

import subprocess
from dataclasses import asdict, replace

import pytest

from tests.parser_assurance import work_growth


def test_fixed_cases_are_bounded_and_canonically_ordered() -> None:
    cases = work_growth.cases_for_profile("fixed")

    assert len(cases) == len(work_growth.FAMILY_GENERATORS) * len(work_growth.SIZE_STEPS)
    assert [case.family for case in cases] == sorted(case.family for case in cases)
    for offset in range(0, len(cases), len(work_growth.SIZE_STEPS)):
        assert tuple(case.size for case in cases[offset : offset + len(work_growth.SIZE_STEPS)]) == (
            work_growth.SIZE_STEPS
        )
    assert all(case.source_bytes <= work_growth.MAX_CASE_BYTES for case in cases)
    assert all(case.seed == work_growth.FIXED_SEED for case in cases)


def test_fixed_profile_proves_declared_growth_and_semantic_contracts() -> None:
    receipts = work_growth.run_profile("fixed")

    work_growth.assert_growth_contract(receipts)
    assert all(receipt.classification == "parsed" for receipt in receipts)
    assert all(receipt.structural_invariants_checked for receipt in receipts)
    assert all(receipt.semantic_roundtrip_checked for receipt in receipts)
    assert all(receipt.work is not None for receipt in receipts)
    assert all(receipt.elapsed_seconds is not None for receipt in receipts)
    assert all(receipt.platform_system for receipt in receipts)
    assert all(receipt.python_version for receipt in receipts)


def test_deep_chain_declares_and_proves_the_immutable_ancestor_exception() -> None:
    receipts = [
        receipt
        for receipt in work_growth.run_profile("fixed")
        if receipt.family == "deep-chain"
    ]

    for receipt in receipts:
        assert receipt.growth_policy == "immutable-ancestor-rebuild-v1"
        assert receipt.work is not None
        assert receipt.work.node_builds == receipt.size
        assert receipt.work.immutable_ancestor_rebuild_steps == receipt.size * (receipt.size - 1) // 2


def test_growth_contract_rejects_unexplained_superlinear_linear_work() -> None:
    receipts = list(work_growth.run_profile("fixed"))
    target_index = next(
        index
        for index, receipt in enumerate(receipts)
        if receipt.family == "flat-blocks" and receipt.size == 16
    )
    target = receipts[target_index]
    assert target.work is not None
    receipts[target_index] = replace(
        target,
        work=replace(target.work, input_lines=target.work.input_lines * 10),
    )

    with pytest.raises(AssertionError, match="linear work exceeded"):
        work_growth.assert_growth_contract(receipts)


def test_receipts_are_source_free_and_label_observations() -> None:
    receipt = work_growth.run_profile("fixed")[0]
    payload = asdict(receipt)

    assert "source" not in payload
    assert payload["source_sha256"]
    assert payload["source_bytes"] > 0
    assert receipt.work_model_schema_version == work_growth.WORK_MODEL_SCHEMA_VERSION
    assert receipt.work_generator_version == work_growth.WORK_GENERATOR_VERSION
    assert receipt.case_id in receipt.replay_command
    if receipt.resident_high_water is None:
        assert receipt.resident_high_water_unit is None
    else:
        assert receipt.resident_high_water_unit in {"bytes", "KiB"}


def test_bounded_runner_executes_a_real_case_without_exposing_source() -> None:
    case = work_growth.cases_for_profile("fixed")[0]
    receipt = work_growth.run_bounded_case(case)

    assert receipt.classification == "parsed"
    assert receipt.work is not None
    assert receipt.source_sha256 == case.source_sha256
    assert receipt.source_bytes == case.source_bytes


def test_bounded_runner_classifies_timeout_without_accepting_partial_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = work_growth.cases_for_profile("fixed")[0]

    def timeout(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired("parser-work", 0.01)

    monkeypatch.setattr(work_growth.subprocess, "run", timeout)
    receipt = work_growth.run_bounded_case(case, timeout_seconds=0.01)

    assert receipt.classification == "timeout"
    assert receipt.work is None
    assert receipt.structural_invariants_checked is False
    assert receipt.semantic_roundtrip_checked is False


def test_replay_rejects_an_unknown_case_id() -> None:
    with pytest.raises(ValueError, match="case not found"):
        work_growth.run_profile("fixed", case_id="m4-missing")
