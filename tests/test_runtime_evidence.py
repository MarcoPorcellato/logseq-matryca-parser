"""Contracts for the private, source-free runtime evidence model."""

from __future__ import annotations

import json
from collections.abc import Callable
from itertools import cycle

import pytest

from tests.performance import runtime_evidence
from tests.performance.runtime_evidence import (
    ScenarioName,
    ScenarioReceipt,
    build_runtime_receipt,
    measure_scenario,
    percentile_p95_ns,
    resident_high_water_observation,
    run_runtime_evidence,
)
from tests.performance.synthetic_vault import build_synthetic_vault


def test_p95_uses_the_declared_nearest_rank_rule() -> None:
    assert percentile_p95_ns(tuple(range(1, 22))) == 20


def test_measurement_protocol_uses_three_warmups_and_twenty_one_samples() -> None:
    calls = 0

    def semantic_action() -> None:
        nonlocal calls
        calls += 1

    receipt = measure_scenario("cold_graph_load", semantic_action, clock_ns=lambda: calls * 10)

    assert calls == 24
    assert receipt.warmup_count == 3
    assert receipt.sample_count == 21
    assert receipt.availability == "available"
    assert receipt.semantic_gate_passed is True
    assert receipt.median_duration_ns == 10
    assert receipt.p95_duration_ns == 10


def test_semantic_failure_is_invalid_without_exception_disclosure() -> None:
    def failing_action() -> None:
        raise RuntimeError("private fixture content")

    receipt = measure_scenario("search_content", failing_action)

    assert receipt.availability == "invalid"
    assert receipt.semantic_gate_passed is False
    assert receipt.sample_count == 0
    assert receipt.median_duration_ns is None
    assert receipt.p95_duration_ns is None
    assert "exception" not in json.dumps(receipt.__dict__, sort_keys=True).casefold()
    assert "private fixture content" not in json.dumps(receipt.__dict__, sort_keys=True)


def test_negative_duration_invalidates_the_scenario() -> None:
    timestamps = cycle((20, 10))

    receipt = measure_scenario("cold_graph_load", lambda: None, clock_ns=lambda: next(timestamps))

    assert receipt.availability == "invalid"
    assert receipt.semantic_gate_passed is False
    assert receipt.sample_count == 0


def test_receipt_payload_is_source_free() -> None:
    vault = build_synthetic_vault()
    scenario = ScenarioReceipt(
        scenario="cold_graph_load",
        availability="available",
        unavailable_reason=None,
        semantic_gate_passed=True,
        warmup_count=3,
        sample_count=21,
        median_duration_ns=10,
        p95_duration_ns=20,
    )

    receipt = build_runtime_receipt(vault, (scenario,))
    payload = receipt.to_payload()
    rendered = json.dumps(payload, sort_keys=True)

    assert payload["source_sha256"] == vault.source_sha256
    assert vault.files[0][0].name not in rendered
    assert vault.files[0][1].decode("utf-8") not in rendered
    assert "exception" not in rendered.casefold()
    assert "hostname" not in rendered.casefold()
    assert "samples" not in rendered.casefold()


def test_missing_native_rss_is_explicitly_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runtime_evidence, "resource", None)

    assert resident_high_water_observation() == {"availability": "unavailable"}


def test_all_core_scenarios_are_semantically_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    def run_once(
        scenario: ScenarioName,
        semantic_action: Callable[[], None],
        *,
        clock_ns: Callable[[], int] | None = None,
    ) -> ScenarioReceipt:
        del clock_ns
        semantic_action()
        return ScenarioReceipt(
            scenario=scenario,
            availability="available",
            unavailable_reason=None,
            semantic_gate_passed=True,
            warmup_count=0,
            sample_count=0,
            median_duration_ns=None,
            p95_duration_ns=None,
        )

    monkeypatch.setattr(runtime_evidence, "measure_scenario", run_once)
    receipt = run_runtime_evidence()
    by_name = {scenario.scenario: scenario for scenario in receipt.scenarios}

    assert set(by_name) == {
        "deep_parse_1024",
        "cold_graph_load",
        "incremental_alias_move_reload",
        "search_content",
        "synapse_context_chunks",
    }
    for name, scenario in by_name.items():
        if name != "synapse_context_chunks":
            assert scenario.availability == "available"
            assert scenario.semantic_gate_passed is True
    synapse = by_name["synapse_context_chunks"]
    if runtime_evidence.synapse_module.Document is None:
        assert synapse.availability == "unavailable"
        assert synapse.semantic_gate_passed is False
    else:
        assert synapse.availability == "available"
        assert synapse.semantic_gate_passed is True


def test_optional_synapse_is_unavailable_not_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runtime_evidence.synapse_module, "Document", None)

    scenario = runtime_evidence.run_synapse_context_chunks()

    assert scenario.availability == "unavailable"
    assert scenario.unavailable_reason == "optional_adapter_unavailable"
    assert scenario.semantic_gate_passed is False
    assert scenario.sample_count == 0


def test_module_cli_emits_one_source_free_json_object(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    expected = build_runtime_receipt(build_synthetic_vault(), ())
    monkeypatch.setattr(runtime_evidence, "run_runtime_evidence", lambda: expected)

    assert runtime_evidence.main([]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["replay_command"] == "uv run python -m tests.performance.runtime_evidence"
    assert "exception" not in json.dumps(payload, sort_keys=True).casefold()
