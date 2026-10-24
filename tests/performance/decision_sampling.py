"""Injected sampling logic only; no native operation, timer or admission is selected."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, replace
from hashlib import sha256
from typing import cast

from tests.performance import comparison_contract as contract
from tests.performance.decision_workload import (
    SmallFullLoadWorkload,
    workload_identity,
    workload_payload,
)


@dataclass(frozen=True, slots=True)
class SamplingBindings:
    observation_id: str
    run_plan_sha256: str
    environment_group_id: str
    environment_evidence_sha256: str
    source: contract.SourceIdentity
    runtime: contract.RuntimeIdentity
    dataset: contract.DatasetIdentity
    executor: contract.ExecutorShape


def _unavailable_phases(
    reason: contract.PhaseReason,
) -> tuple[contract.Phase, ...]:
    return tuple(contract.Phase(name, "unavailable", reason, (), None, None)
                 for name in contract._PHASE_NAMES)


def _checked_inputs(
    workload: SmallFullLoadWorkload, bindings: SamplingBindings,
    callbacks: tuple[object, object, object],
) -> contract.ComparisonReceipt:
    if type(workload) is not SmallFullLoadWorkload or type(bindings) is not SamplingBindings:
        raise TypeError("invalid small sampling input") from None
    if not all(callable(callback) for callback in callbacks):
        raise TypeError("invalid small sampling input") from None
    try:
        for name, expected in (
            ("source", contract.SourceIdentity), ("runtime", contract.RuntimeIdentity),
            ("dataset", contract.DatasetIdentity), ("executor", contract.ExecutorShape),
        ):
            if type(getattr(bindings, name)) is not expected:
                raise TypeError("invalid small sampling input")
    except AttributeError:
        raise TypeError("invalid small sampling input") from None
    try:
        payload = workload_payload(workload)
        identity = workload_identity(workload)
        descriptor = {
            "profile_id": "vault-small-96-v1", "total_pages": 96, "ordinary_pages": 95,
            "blocks_per_ordinary_page": 24, "deep_chain_nodes": 1024,
            "expected_node_count": 3304,
        }
        if payload["dataset"] != {
            **descriptor, "source_bytes": 1107557,
            "dataset_sha256": "adcbc2e2085aad2533ad5f9f5961c0525b291ad4fd47a89eb7ac42ab7b77e583",
        } or payload["parser_options"] != {
            "strict_refs": False, "strict_title_collisions": False,
            "file_tab_policy": "native_per_file",
        }:
            raise ValueError
        candidate = contract.ComparisonReceipt(
            "matryca-decision-observation", 1, bindings.observation_id,
            bindings.run_plan_sha256, bindings.environment_group_id,
            bindings.environment_evidence_sha256, bindings.source, bindings.runtime,
            bindings.dataset, identity, bindings.executor,
            contract.Outcome("invalid", "not_run", "worker_failure"),
            contract.Timing("perf_counter_ns", 0, 0, _unavailable_phases("invalid_observation")),
            contract.Memory("unavailable", "none", "unavailable", None, "none", None),
        )
        parsed = contract.validate_comparison_receipt(contract._frozen_payload(candidate)).receipt
        if parsed is None:
            raise ValueError
        descriptor_digest = sha256(json.dumps(
            descriptor, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")).hexdigest()
        expected_dataset = contract.DatasetIdentity(
            "synthetic_vault", "vault-small-96-v1", descriptor_digest,
            workload.generator_source_sha256,
            "adcbc2e2085aad2533ad5f9f5961c0525b291ad4fd47a89eb7ac42ab7b77e583",
            96, 1107557, 3304,
        )
        if parsed.dataset != expected_dataset or parsed.executor.mode != "threads_current":
            raise ValueError
        return parsed
    except (AttributeError, TypeError, ValueError, KeyError, contract._ValidationError):
        raise ValueError("invalid small sampling input") from None


def _clock_value(clock_ns: Callable[[], int]) -> int:
    value = clock_ns()
    if type(value) is not int or value < 0:
        raise ValueError("invalid sampling clock")
    return value


@dataclass(frozen=True, slots=True)
class _Step:
    outcome: contract.Outcome | None
    duration_ns: int | None = None


def _unit[GraphT](
    load_fresh: Callable[[], GraphT], verify_graph: Callable[[GraphT], object],
    clock_ns: Callable[[], int], *, measured: bool, prior_semantics: bool,
) -> _Step:
    prior: contract.SemanticStatus = "passed" if prior_semantics else "not_run"
    started = 0
    if measured:
        try:
            started = _clock_value(clock_ns)
        except Exception:
            return _Step(contract.Outcome("invalid", prior, "clock_invalid"))
    result: GraphT | None = None
    verification: object = None
    try:
        try:
            result = load_fresh()
        except Exception:
            return _Step(contract.Outcome("invalid", prior, "worker_failure"))
        bad_clock = False
        elapsed: int | None = None
        if measured:
            try:
                stopped = _clock_value(clock_ns)
                elapsed = stopped - started
                if not 0 <= elapsed <= 9007199254740991:
                    raise ValueError("invalid sampling clock")
            except Exception:
                bad_clock = True
        try:
            verification = verify_graph(cast(GraphT, result))
        except AssertionError:
            return _Step(contract.Outcome("invalid", "failed", "semantic_mismatch"))
        except Exception:
            return _Step(contract.Outcome(
                "invalid", "not_run", "clock_invalid" if bad_clock else "worker_failure",
            ))
        if verification is not None:
            return _Step(contract.Outcome(
                "invalid", "not_run", "clock_invalid" if bad_clock else "worker_failure",
            ))
        if bad_clock:
            return _Step(contract.Outcome("invalid", "passed", "clock_invalid"))
        return _Step(None, elapsed)
    finally:
        result = None
        verification = None


def _finish(
    base: contract.ComparisonReceipt, outcome: contract.Outcome,
    warmups: int, samples: tuple[int, ...],
) -> contract.ComparisonReceipt:
    phases = _unavailable_phases("invalid_observation")
    if outcome.availability == "available":
        ordered = sorted(samples)
        if len(ordered) != 21:
            raise RuntimeError("small sampling invariant failure") from None
        phases = (
            contract.Phase("end_to_end", "available", "none", samples, ordered[10], ordered[19]),
            *_unavailable_phases("not_instrumented")[1:],
        )
    receipt = replace(base, outcome=outcome,
                      timing=contract.Timing("perf_counter_ns", warmups, len(samples), phases))
    try:
        parsed = contract.validate_comparison_receipt(contract._frozen_payload(receipt)).receipt
    except (AttributeError, TypeError, ValueError, contract._ValidationError):
        raise RuntimeError("small sampling invariant failure") from None
    if parsed is None:
        raise RuntimeError("small sampling invariant failure") from None
    return parsed


def sample_small_full_load[GraphT](
    workload: SmallFullLoadWorkload,
    bindings: SamplingBindings,
    *,
    load_fresh: Callable[[], GraphT],
    verify_graph: Callable[[GraphT], None],
    clock_ns: Callable[[], int],
) -> contract.ComparisonReceipt:
    """Sequence one injected workload; structural output validity is not admission."""
    base = _checked_inputs(workload, bindings, (load_fresh, verify_graph, clock_ns))
    prior_semantics = False
    warmups = 0
    samples: list[int] = []
    if base.workload.scenario == "full_load_unchanged_repeat":
        step = _unit(load_fresh, verify_graph, clock_ns,
                     measured=False, prior_semantics=prior_semantics)
        if step.outcome is not None:
            return _finish(base, step.outcome, warmups, tuple(samples))
        prior_semantics = True
    for _ in range(3):
        step = _unit(load_fresh, verify_graph, clock_ns,
                     measured=False, prior_semantics=prior_semantics)
        if step.outcome is not None:
            return _finish(base, step.outcome, warmups, tuple(samples))
        prior_semantics = True
        warmups += 1
    for _sample_index in range(21):
        step = _unit(load_fresh, verify_graph, clock_ns,
                     measured=True, prior_semantics=prior_semantics)
        if step.outcome is not None:
            return _finish(base, step.outcome, warmups, tuple(samples))
        if step.duration_ns is None:
            raise RuntimeError("small sampling invariant failure") from None
        samples.append(step.duration_ns)
    return _finish(base, contract.Outcome("available", "passed", "none"), warmups, tuple(samples))
