"""Contracts for the private, source-free runtime evidence model."""

from __future__ import annotations

import json
from itertools import cycle

import pytest

from tests.performance import runtime_evidence
from tests.performance.runtime_evidence import (
    ScenarioReceipt,
    build_runtime_receipt,
    measure_scenario,
    percentile_p95_ns,
    resident_high_water_observation,
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
