"""Pure comparison-contract tests; every receipt/attestation here is synthetic metadata."""

from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError, asdict, is_dataclass, replace
from typing import Any, Literal, cast

import pytest

from tests.performance import comparison_contract as contract


def _payload() -> dict[str, Any]:
    """A synthetic cold-load receipt, never evidence that a workload ran."""
    names = (
        "end_to_end",
        "discovery",
        "read_hash",
        "parse",
        "model_transfer",
        "index_build",
        "operation",
    )
    phases: list[dict[str, Any]] = [
        {
            "name": name,
            "availability": "unavailable",
            "reason": "not_instrumented",
            "samples_ns": [],
            "median_ns": None,
            "p95_ns": None,
        }
        for name in names
    ]
    phases[0].update(
        availability="available",
        reason="none",
        samples_ns=list(range(1, 22)),
        median_ns=11,
        p95_ns=20,
    )
    return {
        "schema": "matryca-decision-observation",
        "schema_version": 1,
        "observation_id": "1" * 32,
        "run_plan_sha256": "2" * 64,
        "environment_group_id": "3" * 32,
        "environment_evidence_sha256": "4" * 64,
        "source": {
            "repository": "MarcoPorcellato/logseq-matryca-parser",
            "commit": "1" * 40,
            "tree": "2" * 40,
            "lock_sha256": "5" * 64,
            "harness_sha256": "6" * 64,
            "installed_runtime_sha256": "7" * 64,
            "working_tree_clean": True,
        },
        "runtime": {
            "python_implementation": "CPython",
            "python_version": "3.12.13",
            "system": "Darwin",
            "architecture": "aarch64",
        },
        "dataset": {
            "kind": "synthetic_vault",
            "descriptor_id": "vault-small-96-v1",
            "descriptor_sha256": "8" * 64,
            "generator_source_sha256": "9" * 64,
            "dataset_sha256": "a" * 64,
            "file_count": 96,
            "source_bytes": 100,
            "expected_node_count": 3304,
        },
        "workload": {
            "scenario": "full_load_cold_instance",
            "workload_manifest_sha256": "b" * 64,
            "operation_parameters_sha256": "c" * 64,
            "parser_options_sha256": "d" * 64,
            "semantic_contract_sha256": "e" * 64,
        },
        "executor": {"mode": "serial", "workers": 1, "start_method": "none"},
        "outcome": {"availability": "available", "semantic": "passed", "reason": "none"},
        "timing": {
            "clock": "perf_counter_ns",
            "completed_warmups": 3,
            "completed_samples": 21,
            "phases": phases,
        },
        "memory": {
            "availability": "unavailable",
            "coverage": "none",
            "method": "unavailable",
            "value": None,
            "unit": "none",
            "evidence_sha256": None,
        },
    }


def _failure_payload(
    availability: str = "invalid", reason: str = "clock_invalid", semantic: str = "passed"
) -> dict[str, Any]:
    data = _payload()
    data["outcome"] = {"availability": availability, "semantic": semantic, "reason": reason}
    data["timing"]["completed_warmups"] = 0 if availability == "unavailable" else 3
    data["timing"]["completed_samples"] = 0 if availability == "unavailable" else 5
    for phase in data["timing"]["phases"]:
        phase.update(
            availability="unavailable",
            reason=availability + "_observation",
            samples_ns=[],
            median_ns=None,
            p95_ns=None,
        )
    return data


def _receipt(data: dict[str, Any] | None = None) -> contract.ComparisonReceipt:
    validation = contract.validate_comparison_receipt(_payload() if data is None else data)
    assert validation.reasons == ()
    assert validation.receipt is not None
    return validation.receipt


def _assert_rejected(data: object, reason: str) -> None:
    validation = contract.validate_comparison_receipt(data)
    assert validation.receipt is None
    assert reason in validation.reasons


@pytest.mark.parametrize(
    ("profile", "pages", "blocks"),
    [
        ("vault-small-96-v1", 96, 3304),
        ("vault-scale-1000-v1", 1000, 25000),
        ("vault-scale-10000-v1", 10000, 241000),
    ],
)
def test_v01_profiles_enforce_exact_dimensions(profile: str, pages: int, blocks: int) -> None:
    data = _payload()
    data["dataset"].update(descriptor_id=profile, file_count=pages, expected_node_count=blocks)
    receipt = _receipt(data)
    assert (receipt.dataset.file_count, receipt.dataset.expected_node_count) == (pages, blocks)
    data["dataset"]["expected_node_count"] = blocks + 1
    _assert_rejected(data, "descriptor_mismatch")
    data["dataset"].update(expected_node_count=blocks, file_count=pages - 1)
    _assert_rejected(data, "descriptor_mismatch")


@pytest.mark.parametrize("bad", [True, False, 1.0, "1", None])
@pytest.mark.parametrize("where", ["worker", "sample", "count", "version"])
def test_v03_integer_domains_do_not_coerce(bad: object, where: str) -> None:
    data = _payload()
    if where == "worker":
        data["executor"]["workers"] = bad
    elif where == "sample":
        data["timing"]["phases"][0]["samples_ns"][0] = bad
    elif where == "version":
        data["schema_version"] = bad
    else:
        data["dataset"]["file_count"] = bad
    _assert_rejected(data, "invalid_type")


@pytest.mark.parametrize(
    "where",
    [
        "root",
        "source",
        "runtime",
        "dataset",
        "workload",
        "executor",
        "outcome",
        "timing",
        "phase",
        "memory",
    ],
)
def test_v04_nested_unknown_fields_are_not_echoed(where: str) -> None:
    data = _payload()
    target = (
        data
        if where == "root"
        else (data["timing"]["phases"][0] if where == "phase" else data[where])
    )
    target["source_path"] = "PRIVATE_SENTINEL_DO_NOT_ECHO"
    validation = contract.validate_comparison_receipt(data)
    assert validation.receipt is None
    assert "unknown_field" in validation.reasons
    assert "PRIVATE_SENTINEL_DO_NOT_ECHO" not in repr(validation)


@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize("same_value", [False, True])
def test_v05_duplicate_json_keys_rejected_before_mapping(nested: bool, same_value: bool) -> None:
    raw = json.dumps(_payload())
    if nested:
        literal = '"python_version": "3.12.13"'
        replacement = literal + ', "python_version": ' + ('"3.12.13"' if same_value else '"3.13.1"')
        raw = raw.replace(literal, replacement)
    else:
        raw = raw[:-1] + ', "schema_version": ' + ("1" if same_value else "2") + "}"
    validation = contract.parse_comparison_json(raw)
    assert validation.receipt is None
    assert validation.reasons == ("duplicate_key",)


@pytest.mark.parametrize("key", ["commit", "lock_sha256", "harness_sha256"])
def test_v06_missing_source_identity_rejected(key: str) -> None:
    data = _payload()
    del data["source"][key]
    _assert_rejected(data, "schema_invalid")


@pytest.mark.parametrize("bad", ["", "A" * 64, "0" * 64, "b" * 63, "b" * 65])
def test_v06_digest_spelling_and_zero_sentinel_rejected(bad: str) -> None:
    data = _payload()
    data["source"]["lock_sha256"] = bad
    _assert_rejected(data, "invalid_identity")


def test_v09_exact_statistics_preserve_sample_order() -> None:
    data = _payload()
    data["timing"]["phases"][0]["samples_ns"] = list(range(21, 0, -1))
    receipt = _receipt(data)
    phase = receipt.timing.phases[0]
    assert (phase.median_ns, phase.p95_ns) == (11, 20)
    assert phase.samples_ns == tuple(range(21, 0, -1))


@pytest.mark.parametrize(
    ("field", "bad", "reason"),
    [
        ("samples_ns", [-1] + list(range(2, 22)), "invalid_statistics"),
        ("samples_ns", list(range(1, 21)), "incomplete_samples"),
        ("samples_ns", list(range(1, 23)), "incomplete_samples"),
        ("samples_ns", [2**53] * 21, "invalid_statistics"),
        ("median_ns", 10, "invalid_statistics"),
        ("p95_ns", 21, "invalid_statistics"),
    ],
)
def test_v10_invalid_statistics_rejected(field: str, bad: object, reason: str) -> None:
    data = _payload()
    data["timing"]["phases"][0][field] = bad
    _assert_rejected(data, reason)


@pytest.mark.parametrize(
    ("reason", "semantic"),
    [
        ("semantic_mismatch", "failed"),
        ("timeout", "not_run"),
        ("clock_invalid", "passed"),
        ("worker_failure", "failed"),
    ],
)
def test_v11_v26_truthful_failure_receipt_remains_parseable(reason: str, semantic: str) -> None:
    receipt = _receipt(_failure_payload(reason=reason, semantic=semantic))
    assert receipt.outcome.availability == "invalid"
    assert receipt.outcome.semantic == semantic
    assert all(p.samples_ns == () and p.median_ns is None for p in receipt.timing.phases)


def test_v23_failed_observation_cannot_carry_successful_summaries() -> None:
    data = _failure_payload()
    data["timing"]["phases"][0] = _payload()["timing"]["phases"][0]
    _assert_rejected(data, "invalid_statistics")


def test_v27_unavailable_capability_needs_no_fabricated_success() -> None:
    receipt = _receipt(_failure_payload("unavailable", "optional_adapter_unavailable", "not_run"))
    assert receipt.outcome.semantic == "not_run"
    assert receipt.timing.completed_samples == 0
    assert all(p.reason == "unavailable_observation" for p in receipt.timing.phases)


@pytest.mark.parametrize(
    ("key", "bad"),
    [
        ("python_implementation", "PyPy"),
        ("python_version", "3.11.9"),
        ("system", "UNSUPPORTED_PRIVATE_SENTINEL"),
        ("architecture", "riscv64"),
    ],
)
def test_v28_unsupported_runtime_has_no_fabricated_receipt(key: str, bad: str) -> None:
    data = _payload()
    data["runtime"][key] = bad
    validation = contract.validate_comparison_receipt(data)
    assert validation.receipt is None
    assert validation.reasons == ("unsupported_platform",)
    assert "UNSUPPORTED_PRIVATE_SENTINEL" not in repr(validation)
    assert contract.GateRejection().verdict == "unavailable"
    assert contract.GateRejection().reasons == ("unsupported_platform",)


@pytest.mark.parametrize(
    ("alias", "expected"), [("arm64", "aarch64"), ("ARM64", "aarch64"), ("AMD64", "x86_64")]
)
def test_runtime_architecture_aliases_normalize(alias: str, expected: str) -> None:
    data = _payload()
    data["runtime"]["architecture"] = alias
    assert _receipt(data).runtime.architecture == expected


@pytest.mark.parametrize(
    "shape",
    [
        {"mode": "serial", "workers": 2, "start_method": "none"},
        {"mode": "processes_spawn", "workers": 16, "start_method": "spawn"},
        {"mode": "processes_spawn", "workers": 2, "start_method": "fork"},
        {"mode": "threads_fixed", "workers": 3, "start_method": "none"},
        {"mode": "threads_current", "workers": 33, "start_method": "none"},
    ],
)
def test_v08_forbidden_worker_shapes_rejected(shape: dict[str, object]) -> None:
    data = _payload()
    data["executor"] = shape
    _assert_rejected(data, "invalid_worker_shape")


def test_immutable_receipt_does_not_retain_caller_containers() -> None:
    data = _payload()
    receipt = _receipt(data)
    data["timing"]["phases"][0]["samples_ns"][0] = 999
    data["source"]["commit"] = "9" * 40
    assert receipt.timing.phases[0].samples_ns[0] == 1
    assert receipt.source.commit == "1" * 40
    with pytest.raises(FrozenInstanceError):
        receipt.observation_id = "0" * 32  # type: ignore[misc]


@pytest.mark.parametrize("raw", ["{", "null", "[]", "NaN", "[" * 2000 + "]" * 2000, "\ud800"])
def test_malformed_or_nonobject_json_fails_without_error_text(raw: str) -> None:
    validation = contract.parse_comparison_json(raw)
    assert validation.receipt is None
    assert validation.reasons


def test_json_character_and_utf8_byte_bounds_before_decoding() -> None:
    raw = json.dumps(_payload())
    padded = raw + " " * (65536 - len(raw))
    assert contract.parse_comparison_json(padded).receipt is not None
    assert contract.parse_comparison_json(padded + " ").reasons == ("schema_invalid",)
    multibyte = '{"PRIVATE_SENTINEL":"' + "é" * 33000 + '"}'
    assert len(multibyte) < 65536
    assert contract.parse_comparison_json(multibyte).reasons == ("schema_invalid",)


@pytest.mark.parametrize("count", [0, 2**53])
def test_positive_dataset_counts_reject_zero_and_overflow(count: int) -> None:
    data = _payload()
    data["dataset"]["source_bytes"] = count
    _assert_rejected(data, "invalid_statistics")


@pytest.mark.parametrize("unit", ["bytes", "KiB"])
def test_memory_preserves_native_units_and_rejects_normalization_overflow(unit: str) -> None:
    data = _payload()
    data["runtime"]["system"] = "Darwin" if unit == "bytes" else "Linux"
    data["memory"] = {
        "availability": "available",
        "coverage": "coordinator_only",
        "method": "native_self_high_water",
        "value": 1024,
        "unit": unit,
        "evidence_sha256": "f" * 64,
    }
    receipt = _receipt(data)
    assert (receipt.memory.value, receipt.memory.unit) == (1024, unit)
    data["memory"]["value"] = 2**53 - 1 if unit == "bytes" else (2**53 - 1) // 1024 + 1
    if unit == "bytes":
        assert _receipt(data).memory.value == 2**53 - 1
    else:
        _assert_rejected(data, "invalid_statistics")


def test_v24_memory_method_and_coverage_must_agree() -> None:
    data = _payload()
    data["memory"] = {
        "availability": "available",
        "coverage": "process_tree",
        "method": "native_self_high_water",
        "value": 1,
        "unit": "bytes",
        "evidence_sha256": "f" * 64,
    }
    _assert_rejected(data, "schema_invalid")


def _digest(value: Any) -> str:
    """Independent fixture-side canonical encoding, never the module's hash helper."""
    payload = asdict(value) if is_dataclass(value) and not isinstance(value, type) else value
    return hashlib.sha256(
        json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


def _policy_for(
    receipts: tuple[contract.ComparisonReceipt, ...],
) -> contract.AdmittedComparisonPolicy:
    first = receipts[0]
    invariants = contract.ComparisonInvariants(
        source=first.source,
        runtime=first.runtime,
        dataset=first.dataset,
        environment_group_id=first.environment_group_id,
        environment_evidence_sha256=first.environment_evidence_sha256,
        parser_options_sha256=first.workload.parser_options_sha256,
        semantic_contract_sha256=first.workload.semantic_contract_sha256,
        clock="perf_counter_ns",
        phase_interpretation="elapsed_wall_v1",
        instrumentation_sha256="b" * 64,
        os_cache_condition="uncontrolled",
    )
    cells = (
        contract.CellRequirement(
            cell_id="a" * 32,
            scenario=first.workload.scenario,
            executor=first.executor,
            workload_manifest_sha256=first.workload.workload_manifest_sha256,
            operation_parameters_sha256=first.workload.operation_parameters_sha256,
        ),
    )
    assignments = tuple(
        contract.ObservationAssignment(observation_id=r.observation_id, cell_id="a" * 32)
        for r in receipts
    )
    selection = {
        "cells": [asdict(x) for x in cells],
        "assignments": [asdict(x) for x in assignments],
    }
    policy = contract.ComparisonPolicy(
        policy_version=1,
        purpose="calibration",
        run_plan_sha256=first.run_plan_sha256,
        selection_manifest_sha256=_digest(selection),
        invariants=invariants,
        permitted_variation="none",
        cells=cells,
        assignments=assignments,
        minimum_independent_per_cell=3,
        thresholds=None,
    )
    return _admit_policy(policy)


def _admit_policy(policy: contract.ComparisonPolicy) -> contract.AdmittedComparisonPolicy:
    return contract.AdmittedComparisonPolicy(
        policy=policy,
        policy_sha256=_digest(policy),
        evidence_manifest_sha256="c" * 64,
        verified=True,
    )


def _attestation(
    receipt: contract.ComparisonReceipt, policy: contract.AdmittedComparisonPolicy
) -> contract.AdmissionAttestation:
    available = receipt.outcome.availability == "available"
    admitted = receipt.outcome.reason != "workload_not_admitted"
    return contract.AdmissionAttestation(
        observation_id=receipt.observation_id,
        outer_execution_id=f"{int(receipt.observation_id, 16) + 100:032x}",
        receipt_sha256=_digest(receipt),
        policy_sha256=policy.policy_sha256,
        evidence_manifest_sha256="d" * 64,
        source_verified=True,
        environment_verified=True,
        dataset_verified=admitted,
        workload_verified=admitted,
        actual_execution_verified=available,
        semantic_verified=available,
        independence_verified=True,
        cleanup_verified=True,
        worker_rule_verified=available,
        phase_interpretation_verified=available,
        os_cache_condition_verified=available,
        full_load_costs_verified=available,
        parse_attribution_verified=False,
        memory_coverage_verified=False,
    )


def test_v07_receipt_digest_cannot_be_replaced_by_syntactically_valid_hash() -> None:
    receipt = _receipt()
    policy = _policy_for((receipt,))
    good = _attestation(receipt, policy)
    assert contract.assess_observation(receipt, good, policy).verdict == "eligible"
    result = contract.assess_observation(receipt, replace(good, receipt_sha256="f" * 64), policy)
    assert result.verdict == "invalid"
    assert "admission_mismatch" in result.reasons


def test_policy_hash_excludes_enclosing_attestation_fields() -> None:
    receipt = _receipt()
    policy = _policy_for((receipt,))
    changed = replace(policy, evidence_manifest_sha256="e" * 64)
    assert (
        contract.assess_observation(receipt, _attestation(receipt, changed), changed).verdict
        == "eligible"
    )
    wrong = replace(policy, policy_sha256=_digest(policy))
    assert (
        contract.assess_observation(receipt, _attestation(receipt, wrong), wrong).verdict
        == "invalid"
    )


def test_admission_digest_binds_normalized_receipt_not_json_spelling() -> None:
    data = _payload()
    data["runtime"]["architecture"] = "ARM64"
    receipt = _receipt(data)
    policy = _policy_for((receipt,))
    admission = _attestation(receipt, policy)
    assert contract.assess_observation(receipt, admission, policy).verdict == "eligible"
    result = contract.assess_observation(
        receipt,
        replace(admission, receipt_sha256=_digest(data)),
        policy,
    )
    assert "admission_mismatch" in result.reasons


@pytest.mark.parametrize(
    ("flag", "reason"),
    [
        ("source_verified", "source_unverified"),
        ("environment_verified", "environment_unverified"),
        ("dataset_verified", "dataset_unverified"),
        ("workload_verified", "workload_unverified"),
        ("actual_execution_verified", "execution_unverified"),
        ("semantic_verified", "semantic_failure"),
        ("independence_verified", "independence_unverified"),
        ("cleanup_verified", "cleanup_unverified"),
        ("worker_rule_verified", "worker_rule_unverified"),
        ("phase_interpretation_verified", "phase_interpretation_unverified"),
        ("os_cache_condition_verified", "os_cache_unverified"),
        ("full_load_costs_verified", "phase_interpretation_unverified"),
    ],
)
def test_v08_v25_v33_unverified_observation_evidence_cannot_qualify(flag: str, reason: str) -> None:
    receipt = _receipt()
    policy = _policy_for((receipt,))
    changes: dict[str, Any] = {flag: False}
    admission = replace(_attestation(receipt, policy), **changes)
    result = contract.assess_observation(receipt, admission, policy)
    assert result.verdict == "invalid"
    assert reason in result.reasons


def test_v08_worker_shape_must_match_declared_cell() -> None:
    receipt = _receipt()
    policy = _policy_for((receipt,))
    changed = replace(receipt, executor=contract.ExecutorShape("threads_current", 2, "none"))
    result = contract.assess_observation(changed, _attestation(changed, policy), policy)
    assert result.verdict == "invalid"
    assert "policy_mismatch" in result.reasons


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("source", "commit", "incompatible_source"),
        ("source", "lock_sha256", "incompatible_source"),
        ("runtime", "python_version", "incompatible_environment"),
        ("dataset", "dataset_sha256", "incompatible_dataset"),
        ("workload", "parser_options_sha256", "incompatible_workload"),
    ],
)
def test_v02_v16_different_invariants_are_not_comparable(
    field: str, value: str, reason: str
) -> None:
    receipt = _receipt()
    policy = _policy_for((receipt,))
    old = getattr(receipt, field)
    new = "3.13.1" if value == "python_version" else ("f" * (40 if value == "commit" else 64))
    changed = replace(receipt, **{field: replace(old, **{value: new})})
    result = contract.assess_observation(changed, _attestation(changed, policy), policy)
    assert result.verdict == "incomparable"
    assert reason in result.reasons


def test_v29_selection_hash_binds_ordered_assignment_schedule() -> None:
    receipts = tuple(replace(_receipt(), observation_id=f"{i:032x}") for i in (1, 2, 3))
    policy = _policy_for(receipts)
    reordered = replace(policy.policy, assignments=tuple(reversed(policy.policy.assignments)))
    wrong = _admit_policy(reordered)
    result = contract.assess_observation(receipts[0], _attestation(receipts[0], wrong), wrong)
    assert result.verdict == "invalid"
    assert "policy_mismatch" in result.reasons


def test_duplicate_cell_ids_rejected_even_when_records_differ() -> None:
    receipt = _receipt()
    policy = _policy_for((receipt,))
    cell = policy.policy.cells[0]
    bad = replace(policy.policy, cells=(cell, replace(cell, operation_parameters_sha256="f" * 64)))
    wrapped = _admit_policy(bad)
    result = contract.assess_observation(receipt, _attestation(receipt, wrapped), wrapped)
    assert result.verdict == "invalid"
    assert "selection_mismatch" in result.reasons


def test_duplicate_observation_assignment_ids_rejected() -> None:
    receipt = _receipt()
    policy = _policy_for((receipt,))
    bad = replace(policy.policy, assignments=policy.policy.assignments * 2)
    wrapped = _admit_policy(bad)
    result = contract.assess_observation(receipt, _attestation(receipt, wrapped), wrapped)
    assert result.verdict == "invalid"
    assert "duplicate_observation" in result.reasons


@pytest.mark.parametrize("bad", [False, 1, "true"])
def test_admitted_policy_requires_actual_verified_boolean(bad: Any) -> None:
    receipt = _receipt()
    policy = replace(_policy_for((receipt,)), verified=bad)
    result = contract.assess_observation(receipt, _attestation(receipt, policy), policy)
    assert result.verdict == "invalid"
    assert ("comparison_policy_unverified" if bad is False else "invalid_type") in result.reasons


def test_manually_constructed_mutable_receipt_is_not_trusted() -> None:
    receipt = _receipt()
    policy = _policy_for((receipt,))
    changed = replace(
        receipt, timing=replace(receipt.timing, phases=cast(Any, list(receipt.timing.phases)))
    )
    result = contract.assess_observation(changed, _attestation(changed, policy), policy)
    assert result.verdict == "invalid"
    assert "invalid_type" in result.reasons


@pytest.mark.parametrize(
    "availability_reason", ["optional_adapter_unavailable", "workload_not_admitted"]
)
def test_v12_v22_v27_unavailable_observation_does_not_need_fabricated_execution(
    availability_reason: str,
) -> None:
    receipt = _receipt(_failure_payload("unavailable", availability_reason, "not_run"))
    policy = _policy_for((receipt,))
    admission = _attestation(receipt, policy)
    assert admission.actual_execution_verified is False
    assert admission.semantic_verified is False
    result = contract.assess_observation(receipt, admission, policy)
    assert result.verdict == "unavailable"
    assert result.reasons == (availability_reason,)


def test_v12_diagnostic_native_adapter_substitution_is_unverified() -> None:
    receipt = _receipt()
    policy = _policy_for((receipt,))
    admission = replace(_attestation(receipt, policy), workload_verified=False)
    result = contract.assess_observation(receipt, admission, policy)
    assert result.verdict == "invalid"
    assert "workload_unverified" in result.reasons


def _request(policy: contract.AdmittedComparisonPolicy) -> contract.ComparisonRequest:
    p = policy.policy
    return contract.ComparisonRequest(
        purpose=p.purpose,
        policy_sha256=policy.policy_sha256,
        run_plan_sha256=p.run_plan_sha256,
        selection_manifest_sha256=p.selection_manifest_sha256,
        expected_observation_ids=tuple(a.observation_id for a in p.assignments),
        comparison_key_sha256=_digest(p.invariants),
        thresholds_sha256=None if p.thresholds is None else p.thresholds.thresholds_sha256,
    )


def _bundle(
    purpose: contract.Purpose = "calibration",
    per_cell: int = 3,
) -> tuple[
    tuple[contract.ComparisonReceipt, ...],
    tuple[contract.AdmissionAttestation, ...],
    contract.ComparisonRequest,
    contract.AdmittedComparisonPolicy,
]:
    base = _receipt()
    shapes = [contract.ExecutorShape("serial", 1, "none")]
    scenarios: list[contract.ScenarioName] = ["full_load_cold_instance"]
    if purpose == "executor_design":
        shapes.append(contract.ExecutorShape("processes_spawn", 2, "spawn"))
        scenarios.append("full_load_cold_instance")
    elif purpose == "cache_design":
        shapes = [contract.ExecutorShape("threads_current", 2, "none")] * 2
        scenarios = ["full_load_cold_instance", "full_load_unchanged_repeat"]
    receipts_list: list[contract.ComparisonReceipt] = []
    cells: list[contract.CellRequirement] = []
    assignments: list[contract.ObservationAssignment] = []
    for index, (shape, scenario) in enumerate(zip(shapes, scenarios, strict=True)):
        cell_id = f"{index + 1:032x}"
        workload = replace(base.workload, scenario=scenario)
        if purpose == "cache_design" and index == 1:
            workload = replace(
                workload, workload_manifest_sha256="f" * 64, operation_parameters_sha256="f" * 64
            )
        cells.append(
            contract.CellRequirement(
                cell_id,
                scenario,
                shape,
                workload.workload_manifest_sha256,
                workload.operation_parameters_sha256,
            )
        )
        for sample in range(per_cell):
            receipt = replace(
                base,
                observation_id=f"{index * 100 + sample + 1:032x}",
                workload=workload,
                executor=shape,
            )
            if purpose == "cache_design" and index == 1:
                phases = list(receipt.timing.phases)
                phases[3] = replace(phases[0], name="parse")
                receipt = replace(receipt, timing=replace(receipt.timing, phases=tuple(phases)))
            if purpose == "executor_design":
                receipt = replace(
                    receipt,
                    memory=contract.Memory(
                        "available",
                        "process_tree",
                        "isolated_process_tree_peak_v1",
                        1024,
                        "bytes",
                        "f" * 64,
                    ),
                )
            receipts_list.append(receipt)
            assignments.append(contract.ObservationAssignment(receipt.observation_id, cell_id))
    receipts = tuple(receipts_list)
    original = _policy_for(receipts).policy
    variation: Literal["none", "executor_shape", "cache_preconditioning"] = (
        "none"
        if purpose == "calibration"
        else ("executor_shape" if purpose == "executor_design" else "cache_preconditioning")
    )
    selection = {
        "cells": [asdict(x) for x in cells],
        "assignments": [asdict(x) for x in assignments],
    }
    policy = _admit_policy(
        replace(
            original,
            purpose=purpose,
            permitted_variation=variation,
            cells=tuple(cells),
            assignments=tuple(assignments),
            selection_manifest_sha256=_digest(selection),
            thresholds=None
            if purpose == "calibration"
            else contract.ThresholdAdmission(
                "e" * 64,
                "f" * 64,
                True,
            ),
        )
    )
    admissions = tuple(
        replace(
            _attestation(r, policy),
            memory_coverage_verified=purpose == "executor_design",
            parse_attribution_verified=(
                purpose == "cache_design" and r.workload.scenario == "full_load_unchanged_repeat"
            ),
        )
        for r in receipts
    )
    return receipts, admissions, _request(policy), policy


@pytest.mark.parametrize("purpose", ["calibration", "executor_design", "cache_design"])
def test_v15_valid_synthetic_selection_eligible_for_declared_purpose(
    purpose: contract.Purpose,
) -> None:
    receipts, admissions, request, policy = _bundle(purpose)
    result = contract.assess_comparison(receipts, admissions, request, policy)
    assert result == contract.EligibilityResult("eligible", ())
    assert (
        contract.assess_comparison(
            tuple(reversed(receipts)), tuple(reversed(admissions)), request, policy
        )
        == result
    )


def test_v14_two_launches_are_diagnostic_not_eligible_comparison() -> None:
    receipts, admissions, request, policy = _bundle(per_cell=2)
    result = contract.assess_comparison(receipts, admissions, request, policy)
    assert result.verdict == "incomparable"
    assert result.reasons == ("insufficient_independent_observations",)


@pytest.mark.parametrize("duplicate", ["receipt", "admission", "outer_launch"])
def test_v13_v32_renaming_or_copying_cannot_create_independent_launches(duplicate: str) -> None:
    receipts, admissions, request, policy = _bundle()
    if duplicate == "receipt":
        receipts = receipts[:-1] + (receipts[0],)
    elif duplicate == "admission":
        admissions = admissions[:-1] + (admissions[0],)
    else:
        admissions = admissions[:-1] + (
            replace(admissions[-1], outer_execution_id=admissions[0].outer_execution_id),
        )
    result = contract.assess_comparison(receipts, admissions, request, policy)
    assert result.verdict == "invalid"
    assert "duplicate_observation" in result.reasons


@pytest.mark.parametrize("missing", ["receipt", "admission"])
def test_v07_v20_missing_selected_records_are_not_filtered(missing: str) -> None:
    receipts, admissions, request, policy = _bundle()
    if missing == "receipt":
        receipts = receipts[:-1]
    else:
        admissions = admissions[:-1]
    result = contract.assess_comparison(receipts, admissions, request, policy)
    assert result.verdict == "invalid"
    assert "selection_mismatch" in result.reasons


@pytest.mark.parametrize(
    ("availability", "reason", "semantic", "verdict", "expected"),
    [
        (
            "unavailable",
            "optional_adapter_unavailable",
            "not_run",
            "unavailable",
            "optional_adapter_unavailable",
        ),
        ("invalid", "semantic_mismatch", "failed", "invalid", "semantic_failure"),
        ("invalid", "timeout", "not_run", "invalid", "timeout"),
        ("invalid", "clock_invalid", "passed", "invalid", "clock_invalid"),
    ],
)
def test_v11_v20_v21_v26_failed_selected_attempts_remain_noneligible(
    availability: str,
    reason: str,
    semantic: str,
    verdict: str,
    expected: str,
) -> None:
    receipts, admissions, request, policy = _bundle()
    failure = replace(
        _receipt(_failure_payload(availability, reason, semantic)),
        observation_id=receipts[-1].observation_id,
    )
    receipts = receipts[:-1] + (failure,)
    admissions = admissions[:-1] + (_attestation(failure, policy),)
    result = contract.assess_comparison(receipts, admissions, request, policy)
    assert result.verdict == verdict
    assert expected in result.reasons
    assert "insufficient_independent_observations" in result.reasons


@pytest.mark.parametrize(
    ("coverage", "availability", "method", "value", "unit", "evidence", "reason"),
    [
        (
            "coordinator_only",
            "available",
            "native_self_high_water",
            1024,
            "bytes",
            "f" * 64,
            "memory_coverage_insufficient",
        ),
        ("none", "unavailable", "unavailable", None, "none", None, "memory_unavailable"),
    ],
)
def test_v17_v18_executor_requires_worker_inclusive_memory(
    coverage: contract.MemoryCoverage,
    availability: contract.Availability,
    method: contract.MemoryMethod,
    value: int | None,
    unit: contract.MemoryUnit,
    evidence: str | None,
    reason: str,
) -> None:
    receipts, admissions, request, policy = _bundle("executor_design")
    changed = replace(
        receipts[0],
        memory=contract.Memory(
            availability,
            coverage,
            method,
            value,
            unit,
            evidence,
        ),
    )
    receipts = (changed,) + receipts[1:]
    admissions = (_attestation(changed, policy),) + admissions[1:]
    result = contract.assess_comparison(receipts, admissions, request, policy)
    assert result.verdict == "unavailable"
    assert reason in result.reasons


def test_v24_claimed_tree_memory_requires_external_coverage_evidence() -> None:
    receipts, admissions, request, policy = _bundle("executor_design")
    admissions = (replace(admissions[0], memory_coverage_verified=False),) + admissions[1:]
    result = contract.assess_comparison(receipts, admissions, request, policy)
    assert result.verdict == "unavailable"
    assert "memory_coverage_insufficient" in result.reasons


def test_v31_executor_does_not_need_separate_transfer_or_spawn_samples() -> None:
    receipts, admissions, request, policy = _bundle("executor_design")
    assert all(r.timing.phases[4].availability == "unavailable" for r in receipts)
    assert all(a.full_load_costs_verified is True for a in admissions)
    assert contract.assess_comparison(receipts, admissions, request, policy).verdict == "eligible"


def test_v31_cache_repeat_requires_measured_parse_phase() -> None:
    receipts, admissions, request, policy = _bundle("cache_design")
    index = 3
    phases = list(receipts[index].timing.phases)
    phases[3] = contract.Phase("parse", "unavailable", "not_instrumented", (), None, None)
    changed = replace(receipts[index], timing=replace(receipts[index].timing, phases=tuple(phases)))
    receipts = receipts[:index] + (changed,) + receipts[index + 1 :]
    admissions = (
        admissions[:index]
        + (replace(_attestation(changed, policy), parse_attribution_verified=False),)
        + admissions[index + 1 :]
    )
    result = contract.assess_comparison(receipts, admissions, request, policy)
    assert result.verdict == "incomparable"
    assert "incompatible_timing" in result.reasons


def test_cache_repeat_parse_phase_requires_reviewed_attribution() -> None:
    receipts, admissions, request, policy = _bundle("cache_design")
    admissions = (
        admissions[:3]
        + (replace(admissions[3], parse_attribution_verified=False),)
        + admissions[4:]
    )
    result = contract.assess_comparison(receipts, admissions, request, policy)
    assert result.verdict == "invalid"
    assert "phase_interpretation_unverified" in result.reasons


def test_v19_v30_thresholds_are_predeclared_for_this_policy() -> None:
    receipts, _, _, original = _bundle("cache_design")
    assert original.policy.thresholds is not None
    policy = _admit_policy(
        replace(
            original.policy,
            thresholds=replace(
                original.policy.thresholds,
                predeclared_before_selected_runs=False,
            ),
        )
    )
    admissions = tuple(
        replace(_attestation(r, policy), parse_attribution_verified=True) for r in receipts
    )
    result = contract.assess_comparison(receipts, admissions, _request(policy), policy)
    assert result.verdict == "incomparable"
    assert "thresholds_not_predeclared" in result.reasons
    result = contract.assess_comparison(
        receipts,
        admissions,
        replace(_request(policy), thresholds_sha256="a" * 64),
        policy,
    )
    assert result.verdict == "invalid"
    assert "policy_mismatch" in result.reasons


@pytest.mark.parametrize(
    "field",
    ["policy_sha256", "run_plan_sha256", "selection_manifest_sha256", "comparison_key_sha256"],
)
def test_v29_request_cannot_choose_other_bound_identities(field: str) -> None:
    receipts, admissions, request, policy = _bundle()
    changes: dict[str, Any] = {field: "f" * 64}
    result = contract.assess_comparison(receipts, admissions, replace(request, **changes), policy)
    assert result.verdict == "invalid"
    assert "policy_mismatch" in result.reasons


def test_v29_request_cannot_change_assignment_order() -> None:
    receipts, admissions, request, policy = _bundle()
    changed = replace(
        request, expected_observation_ids=tuple(reversed(request.expected_observation_ids))
    )
    result = contract.assess_comparison(receipts, admissions, changed, policy)
    assert result.verdict == "invalid"
    assert "selection_mismatch" in result.reasons


def test_reason_precedence_preserves_all_applicable_codes_sorted_unique() -> None:
    receipts, admissions, request, policy = _bundle("executor_design")
    admissions = (
        replace(admissions[0], cleanup_verified=False, memory_coverage_verified=False),
    ) + admissions[1:]
    result = contract.assess_comparison(receipts, admissions, request, policy)
    assert result.verdict == "invalid"
    assert {
        "cleanup_unverified",
        "memory_coverage_insufficient",
        "insufficient_independent_observations",
    }.issubset(result.reasons)
    assert result.reasons == tuple(sorted(set(result.reasons)))


def test_comparison_input_cardinality_is_bounded_without_execution() -> None:
    receipts, admissions, request, policy = _bundle()
    result = contract.assess_comparison((receipts[0],) * 257, admissions, request, policy)
    assert result.verdict == "invalid"
    assert "selection_mismatch" in result.reasons


def test_operation_only_scenario_uses_operation_primary_and_serial_coordinator() -> None:
    data = _payload()
    data["workload"]["scenario"] = "content_search"
    end_to_end = data["timing"]["phases"][0]
    data["timing"]["phases"][6] = {**end_to_end, "name": "operation"}
    data["timing"]["phases"][0] = {
        "name": "end_to_end",
        "availability": "unavailable",
        "reason": "not_applicable",
        "samples_ns": [],
        "median_ns": None,
        "p95_ns": None,
    }
    receipt = _receipt(data)
    receipts = tuple(replace(receipt, observation_id=f"{i:032x}") for i in (1, 2, 3))
    policy = _policy_for(receipts)
    admissions = tuple(
        replace(_attestation(r, policy), full_load_costs_verified=False) for r in receipts
    )
    assert (
        contract.assess_comparison(receipts, admissions, _request(policy), policy).verdict
        == "eligible"
    )


def test_opaque_ids_are_labels_not_proof_and_allow_all_hex_spellings() -> None:
    data = _payload()
    data["observation_id"] = "0" * 32
    assert _receipt(data).observation_id == "0" * 32


@pytest.mark.parametrize(
    "field",
    [
        "root",
        "source",
        "runtime",
        "dataset",
        "workload",
        "executor",
        "outcome",
        "timing",
        "phase",
        "memory",
    ],
)
def test_every_nested_json_record_requires_all_its_keys(field: str) -> None:
    data = _payload()
    target = (
        data
        if field == "root"
        else (data["timing"]["phases"][0] if field == "phase" else data[field])
    )
    del target[next(iter(target))]
    _assert_rejected(data, "schema_invalid")


@pytest.mark.parametrize("bad", [1, "true", None])
def test_trusted_observation_flags_are_actual_booleans(bad: Any) -> None:
    receipt = _receipt()
    policy = _policy_for((receipt,))
    admission = replace(_attestation(receipt, policy), cleanup_verified=bad)
    result = contract.assess_observation(receipt, admission, policy)
    assert result.verdict == "invalid"
    assert "invalid_type" in result.reasons


@pytest.mark.parametrize("field", ["policy_version", "minimum_independent_per_cell"])
def test_manual_policy_integer_fields_never_accept_boolean(field: str) -> None:
    receipt = _receipt()
    policy = _policy_for((receipt,))
    changes: dict[str, Any] = {field: True}
    bad = _admit_policy(replace(policy.policy, **changes))
    result = contract.assess_observation(receipt, _attestation(receipt, bad), bad)
    assert result.verdict == "invalid"
    assert "invalid_type" in result.reasons


def test_v22_pathological_fixture_metadata_remains_unadmitted_without_real_manifest() -> None:
    data = _failure_payload("unavailable", "workload_not_admitted", "not_run")
    data["workload"]["scenario"] = "pathological_parse_1148"
    data["dataset"].update(
        kind="regression_fixture",
        descriptor_id="m87-pathological-1148-v1",
        file_count=1,
        expected_node_count=1,
    )
    receipt = _receipt(data)
    policy = _policy_for((receipt,))
    admission = _attestation(receipt, policy)
    assert admission.workload_verified is False
    assert admission.dataset_verified is False
    result = contract.assess_observation(receipt, admission, policy)
    assert result == contract.EligibilityResult("unavailable", ("workload_not_admitted",))


def test_v12_optional_native_context_capability_failure_is_not_a_zero_time_pass() -> None:
    data = _failure_payload("unavailable", "optional_adapter_unavailable", "not_run")
    data["workload"]["scenario"] = "context_with_embeds"
    receipt = _receipt(data)
    policy = _policy_for((receipt,))
    result = contract.assess_observation(receipt, _attestation(receipt, policy), policy)
    assert result == contract.EligibilityResult("unavailable", ("optional_adapter_unavailable",))
    assert receipt.timing.phases[6].samples_ns == ()


def test_selected_receipt_order_never_rewrites_declared_selection() -> None:
    receipts, admissions, request, policy = _bundle()
    original_assignments = policy.policy.assignments
    assert (
        contract.assess_comparison(tuple(reversed(receipts)), admissions, request, policy).verdict
        == "eligible"
    )
    assert policy.policy.assignments == original_assignments


def test_empty_comparison_is_not_vacuously_eligible() -> None:
    _, _, request, policy = _bundle()
    result = contract.assess_comparison((), (), request, policy)
    assert result.verdict == "invalid"
    assert "selection_mismatch" in result.reasons


@pytest.mark.parametrize(
    ("flag", "expected"),
    [
        ("cleanup_verified", "cleanup_unverified"),
        ("independence_verified", "independence_unverified"),
    ],
)
@pytest.mark.parametrize("reason", ["optional_adapter_unavailable", "workload_not_admitted"])
def test_review_unavailable_observation_retains_lifecycle_failures(
    flag: str,
    expected: str,
    reason: str,
) -> None:
    data = _failure_payload("unavailable", reason, "not_run")
    if reason == "optional_adapter_unavailable":
        data["workload"]["scenario"] = "context_with_embeds"
    receipt = _receipt(data)
    policy = _policy_for((receipt,))
    admitted = _attestation(receipt, policy)
    assert contract.assess_observation(receipt, admitted, policy).verdict == "unavailable"
    changes: dict[str, Any] = {flag: False}
    result = contract.assess_observation(receipt, replace(admitted, **changes), policy)
    assert result.verdict == "invalid"
    assert {reason, expected}.issubset(result.reasons)
    assert result.reasons == tuple(sorted(set(result.reasons)))


@pytest.mark.parametrize(
    ("flag", "expected"),
    [
        ("cleanup_verified", "cleanup_unverified"),
        ("independence_verified", "independence_unverified"),
    ],
)
@pytest.mark.parametrize("reason", ["optional_adapter_unavailable", "workload_not_admitted"])
def test_review_unavailable_selection_retains_lifecycle_failures(
    flag: str,
    expected: str,
    reason: str,
) -> None:
    receipts, _, _, policy = _bundle()
    if reason == "optional_adapter_unavailable":
        # A native context workload has operation-only timing, unlike a full load.
        data = _payload()
        data["workload"]["scenario"] = "context_with_embeds"
        phase = data["timing"]["phases"][0]
        data["timing"]["phases"][6] = {**phase, "name": "operation"}
        data["timing"]["phases"][0] = {
            "name": "end_to_end",
            "availability": "unavailable",
            "reason": "not_applicable",
            "samples_ns": [],
            "median_ns": None,
            "p95_ns": None,
        }
        operation = _receipt(data)
        receipts = tuple(replace(operation, observation_id=r.observation_id) for r in receipts)
        policy = _policy_for(receipts)
    failure_data = _failure_payload("unavailable", reason, "not_run")
    failure_data["workload"]["scenario"] = receipts[-1].workload.scenario
    failure = replace(_receipt(failure_data), observation_id=receipts[-1].observation_id)
    receipts = receipts[:-1] + (failure,)
    admissions = tuple(_attestation(r, policy) for r in receipts)
    request = _request(policy)
    assert (
        contract.assess_comparison(receipts, admissions, request, policy).verdict == "unavailable"
    )
    changes: dict[str, Any] = {flag: False}
    admissions = admissions[:-1] + (replace(admissions[-1], **changes),)
    result = contract.assess_comparison(receipts, admissions, request, policy)
    assert result.verdict == "invalid"
    assert {reason, expected, "insufficient_independent_observations"}.issubset(result.reasons)
    assert result.reasons == tuple(sorted(set(result.reasons)))


@pytest.mark.parametrize("cell_count", [10, 11])
def test_policy_cell_cardinality_exact_upper_boundary(cell_count: int) -> None:
    receipts, _, _, base = _bundle("executor_design")
    shape_values: list[contract.ExecutorShape] = [
        contract.ExecutorShape("serial", 1, "none"),
        contract.ExecutorShape("threads_current", 2, "none"),
        *(contract.ExecutorShape("threads_fixed", w, "none") for w in (1, 2, 4, 8)),
        *(contract.ExecutorShape("processes_spawn", w, "spawn") for w in (1, 2, 4, 8)),
        contract.ExecutorShape("threads_current", 3, "none"),
    ]
    cells = tuple(
        replace(
            base.policy.cells[0],
            cell_id=f"{index + 1:032x}",
            executor=shape,
        )
        for index, shape in enumerate(shape_values[:cell_count])
    )
    assignments = tuple(
        contract.ObservationAssignment(f"{index + 1:032x}", cell.cell_id)
        for index, cell in enumerate(cells)
    )
    selection = {
        "cells": [asdict(x) for x in cells],
        "assignments": [asdict(x) for x in assignments],
    }
    policy = _admit_policy(
        replace(
            base.policy,
            cells=cells,
            assignments=assignments,
            selection_manifest_sha256=_digest(selection),
        )
    )
    admission = replace(_attestation(receipts[0], policy), memory_coverage_verified=True)
    result = contract.assess_observation(receipts[0], admission, policy)
    assert result.verdict == ("eligible" if cell_count == 10 else "invalid")


@pytest.mark.parametrize("assignment_count", [256, 257])
def test_policy_assignment_cardinality_exact_upper_boundary(assignment_count: int) -> None:
    receipt = replace(_receipt(), observation_id=f"{1:032x}")
    base = _policy_for((receipt,))
    assignments = tuple(
        contract.ObservationAssignment(f"{i:032x}", base.policy.cells[0].cell_id)
        for i in range(1, assignment_count + 1)
    )
    selection = {
        "cells": [asdict(x) for x in base.policy.cells],
        "assignments": [asdict(x) for x in assignments],
    }
    policy = _admit_policy(
        replace(
            base.policy,
            assignments=assignments,
            selection_manifest_sha256=_digest(selection),
        )
    )
    result = contract.assess_observation(receipt, _attestation(receipt, policy), policy)
    assert result.verdict == ("eligible" if assignment_count == 256 else "invalid")
