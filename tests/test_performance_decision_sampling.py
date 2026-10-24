"""Scripted operations qualify sampling logic only, never native performance."""

from __future__ import annotations

import json
import weakref
from dataclasses import FrozenInstanceError, asdict, fields, replace
from hashlib import sha256
from typing import Any

import pytest

from tests.performance import comparison_contract as contract
from tests.performance.decision_sampling import SamplingBindings, sample_small_full_load
from tests.performance.decision_workload import describe_small_full_load_workload
from tests.test_performance_decision_workload import _expected_payload

COLD = "full_load_cold_instance"
REPEAT = "full_load_unchanged_repeat"
PHASES = ("end_to_end", "discovery", "read_hash", "parse", "model_transfer",
          "index_build", "operation")
PRIVATE = "/private/synthetic-owner/vault/secret-title-7f2c"
DESCRIPTOR = "276fcbc91b611b0f0958ebf90e557faa94242d794f470d04408a9671bdb2b70b"


def _workload(scenario: str = COLD) -> Any:
    return describe_small_full_load_workload(
        "vault-small-96-v1", scenario,
        generator_source_sha256="1" * 64, semantic_source_sha256="2" * 64,
    )


def _bindings() -> SamplingBindings:
    # All identities are synthetic vectors, not source/runtime admission.
    return SamplingBindings(
        "1" * 32, "2" * 64, "3" * 32, "4" * 64,
        contract.SourceIdentity(
            "MarcoPorcellato/logseq-matryca-parser", "5" * 40, "6" * 40,
            "7" * 64, "8" * 64, "9" * 64, True,
        ),
        contract.RuntimeIdentity("CPython", "3.12.13", "Darwin", "aarch64"),
        contract.DatasetIdentity(
            "synthetic_vault", "vault-small-96-v1", DESCRIPTOR, "1" * 64,
            "adcbc2e2085aad2533ad5f9f5961c0525b291ad4fd47a89eb7ac42ab7b77e583",
            96, 1107557, 3304,
        ),
        contract.ExecutorShape("threads_current", 4, "none"),
    )


class _Result:
    def __init__(self, index: int) -> None:
        self.index = index


class _Probe:
    """Finite deterministic callbacks; no clock, filesystem or Parser operation."""

    def __init__(self, durations: tuple[int, ...] = tuple(range(1, 22))) -> None:
        self.events: list[tuple[str, int]] = []
        self.loads = self.checks = self.reads = 0
        self.durations = durations
        self.load_fault: tuple[int, BaseException] | None = None
        self.verify_fault: tuple[int, BaseException | object] | None = None
        self.clock_faults: dict[int, Any] = {}
        self.refs: list[weakref.ReferenceType[_Result]] = []

    def load(self) -> _Result:
        index = self.loads
        self.loads += 1
        self.events.append(("load", index))
        if self.load_fault is not None and index == self.load_fault[0]:
            raise self.load_fault[1]
        result = _Result(index)
        self.refs.append(weakref.ref(result))
        return result

    def verify(self, result: _Result) -> Any:
        self.checks += 1
        self.events.append(("verify", result.index))
        if self.verify_fault is not None and result.index == self.verify_fault[0]:
            fault = self.verify_fault[1]
            if isinstance(fault, BaseException):
                raise fault
            return fault
        return None

    def clock(self) -> Any:
        index = self.reads
        self.reads += 1
        self.events.append(("clock", index))
        if index in self.clock_faults:
            fault = self.clock_faults[index]
            if isinstance(fault, BaseException):
                raise fault
            return fault
        base = 10000 * (index // 2 + 1)
        return base if index % 2 == 0 else base + self.durations[index // 2]

    def run(self, scenario: str = COLD, bindings: Any = None, workload: Any = None) -> Any:
        return sample_small_full_load(
            _workload(scenario) if workload is None else workload,
            _bindings() if bindings is None else bindings,
            load_fresh=self.load, verify_graph=self.verify, clock_ns=self.clock,
        )


def _hash(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _roundtrip(receipt: contract.ComparisonReceipt) -> None:
    parsed = contract.parse_comparison_json(json.dumps(asdict(receipt)))
    assert parsed.reasons == () and parsed.receipt == receipt
    assert tuple(p.name for p in receipt.timing.phases) == PHASES
    assert receipt.memory == contract.Memory("unavailable", "none", "unavailable", None, "none", None)


def _invalid(receipt: Any, reason: str, semantic: str, counts: tuple[int, int]) -> None:
    assert (receipt.outcome.availability, receipt.outcome.semantic, receipt.outcome.reason) == (
        "invalid", semantic, reason,
    )
    assert (receipt.timing.completed_warmups, receipt.timing.completed_samples) == counts
    assert all(p.availability == "unavailable" and p.reason == "invalid_observation"
               and p.samples_ns == () and p.median_ns is None and p.p95_ns is None
               for p in receipt.timing.phases)
    _roundtrip(receipt)


def test_bindings_are_exact_frozen_slotted_records() -> None:
    binding = _bindings()
    assert tuple(f.name for f in fields(binding)) == (
        "observation_id", "run_plan_sha256", "environment_group_id",
        "environment_evidence_sha256", "source", "runtime", "dataset", "executor",
    )
    assign = setattr
    with pytest.raises(FrozenInstanceError):
        assign(binding, "observation_id", "a" * 32)
    assert not hasattr(binding, "__dict__")
    assert _Probe().run(bindings=binding).source == binding.source


@pytest.mark.parametrize("scenario,untimed", [(COLD, 3), (REPEAT, 4)])
def test_cold_sequence_and_statistics(scenario: str, untimed: int) -> None:
    probe = _Probe()
    receipt = probe.run(scenario)
    expected: list[tuple[str, int]] = []
    for index in range(untimed):
        expected.extend((("load", index), ("verify", index)))
    for index in range(21):
        expected.extend((("clock", 2 * index), ("load", index + untimed),
                         ("clock", 2 * index + 1), ("verify", index + untimed)))
    assert probe.events == expected
    assert (probe.loads, probe.checks, probe.reads) == (untimed + 21, untimed + 21, 42)
    assert receipt.outcome == contract.Outcome("available", "passed", "none")
    assert (receipt.timing.completed_warmups, receipt.timing.completed_samples) == (3, 21)
    phase = receipt.timing.phases[0]
    assert (phase.samples_ns, phase.median_ns, phase.p95_ns) == (tuple(range(1, 22)), 11, 20)
    assert all(p.reason == "not_instrumented" and p.samples_ns == ()
               and p.median_ns is None and p.p95_ns is None
               for p in receipt.timing.phases[1:])
    _roundtrip(receipt)


def test_repeat_primes_once_before_all_warmups() -> None:
    probe = _Probe()
    receipt = probe.run(REPEAT)
    assert probe.events[:8] == [
        ("load", 0), ("verify", 0), ("load", 1), ("verify", 1),
        ("load", 2), ("verify", 2), ("load", 3), ("verify", 3),
    ]
    assert probe.events[8:12] == [("clock", 0), ("load", 4), ("clock", 1), ("verify", 4)]
    assert probe.loads == probe.checks == 25 and probe.reads == 42
    assert receipt.timing.completed_warmups == 3


@pytest.mark.parametrize("scenario", [COLD, REPEAT])
def test_workload_identity_is_helper_derived(scenario: str) -> None:
    # Shared test-only literal oracle does not consume the production helper output.
    expected = _expected_payload(scenario)
    actual = _Probe().run(scenario).workload
    assert asdict(actual) == {
        "scenario": scenario, "workload_manifest_sha256": _hash(expected),
        "operation_parameters_sha256": _hash(expected["operation"]),
        "parser_options_sha256": _hash(expected["parser_options"]),
        "semantic_contract_sha256": _hash(expected["semantics"]),
    }


@pytest.mark.parametrize("field,value", [
    ("kind", "regression_fixture"), ("descriptor_id", "vault-scale-1000-v1"),
    ("descriptor_sha256", "a" * 64), ("generator_source_sha256", "b" * 64),
    ("dataset_sha256", "c" * 64), ("file_count", 95),
    ("source_bytes", 1107558), ("expected_node_count", 3305),
])
def test_preflight_binds_each_dataset_field(field: str, value: Any) -> None:
    probe, binding = _Probe(), _bindings()
    wrong = replace(binding, dataset=replace(binding.dataset, **{field: value}))
    with pytest.raises(ValueError, match="^invalid small sampling input$"):
        probe.run(bindings=wrong)
    assert probe.events == []


@pytest.mark.parametrize("workers", [1, 2, 32, 0, 33, True, 1.0, "1"])
def test_current_thread_shape_is_closed(workers: Any) -> None:
    probe, binding = _Probe(), _bindings()
    binding = replace(binding, executor=contract.ExecutorShape("threads_current", workers, "none"))
    if type(workers) is int and workers in (1, 2, 32):
        assert probe.run(bindings=binding).executor.workers == workers
    else:
        with pytest.raises(ValueError, match="^invalid small sampling input$"):
            probe.run(bindings=binding)
        assert probe.events == []


@pytest.mark.parametrize("mode,start", [("serial", "none"), ("threads_fixed", "none"),
                                        ("processes_spawn", "spawn"), ("threads_current", "spawn")])
def test_other_executor_modes_reject_before_callbacks(mode: Any, start: Any) -> None:
    probe = _Probe()
    binding = replace(_bindings(), executor=contract.ExecutorShape(mode, 1, start))
    with pytest.raises(ValueError, match="^invalid small sampling input$"):
        probe.run(bindings=binding)
    assert probe.events == []


@pytest.mark.parametrize("bad", [{}, object(), PRIVATE, True])
def test_preflight_rejects_wrong_types_before_callbacks(bad: Any) -> None:
    probe = _Probe()
    with pytest.raises(TypeError, match="^invalid small sampling input$"):
        probe.run(bindings=bad)
    assert probe.events == []


@pytest.mark.parametrize("field,bad", [
    ("observation_id", PRIVATE), ("run_plan_sha256", "0" * 64),
    ("environment_group_id", True), ("environment_evidence_sha256", "A" * 64),
])
def test_input_errors_do_not_echo_values(field: str, bad: Any) -> None:
    probe = _Probe()
    with pytest.raises(ValueError) as error:
        probe.run(bindings=replace(_bindings(), **{field: bad}))
    assert str(error.value) == "invalid small sampling input"
    assert PRIVATE not in str(error.value) and error.value.__cause__ is None
    assert probe.events == []


@pytest.mark.parametrize("unit", [0, 2, 3, 13, 23])
@pytest.mark.parametrize("stage", ["load", "semantic", "verify", "false"])
def test_failure_stage_table(unit: int, stage: str) -> None:
    probe = _Probe()
    if stage == "load":
        probe.load_fault = (unit, AssertionError(PRIVATE))
    else:
        probe.verify_fault = (unit, AssertionError(PRIVATE) if stage == "semantic"
                              else RuntimeError(PRIVATE) if stage == "verify" else False)
    result = probe.run()
    counts = (unit, 0) if unit < 3 else (3, unit - 3)
    semantic = "failed" if stage == "semantic" else (
        "passed" if stage == "load" and unit else "not_run")
    _invalid(result, "semantic_mismatch" if stage == "semantic" else "worker_failure",
             semantic, counts)
    assert probe.loads == unit + 1
    assert probe.checks == unit + (stage != "load")
    assert PRIVATE not in json.dumps(asdict(result))


@pytest.mark.parametrize("stage", ["load", "semantic", "verify"])
def test_priming_failure_has_no_completed_units(stage: str) -> None:
    probe = _Probe()
    if stage == "load":
        probe.load_fault = (0, TimeoutError(PRIVATE))
    else:
        probe.verify_fault = (0, AssertionError(PRIVATE) if stage == "semantic"
                              else RuntimeError(PRIVATE))
    result = probe.run(REPEAT)
    _invalid(result, "semantic_mismatch" if stage == "semantic" else "worker_failure",
             "failed" if stage == "semantic" else "not_run", (0, 0))
    assert probe.loads == 1 and probe.reads == 0


def test_success_counts_advance_after_verification() -> None:
    probe = _Probe()
    probe.verify_fault = (23, AssertionError(PRIVATE))
    receipt = probe.run()
    _invalid(receipt, "semantic_mismatch", "failed", (3, 20))
    assert probe.loads == probe.checks == 24


@pytest.mark.parametrize("clock_index", [0, 20, 40])
def test_invalid_start_clock_never_loads(clock_index: int) -> None:
    probe = _Probe()
    probe.clock_faults[clock_index] = AssertionError(PRIVATE)
    receipt = probe.run()
    _invalid(receipt, "clock_invalid", "passed", (3, clock_index // 2))
    assert probe.loads == probe.checks == 3 + clock_index // 2
    assert probe.reads == clock_index + 1


@pytest.mark.parametrize("fault,reason,semantic", [
    (None, "clock_invalid", "passed"),
    (AssertionError(PRIVATE), "semantic_mismatch", "failed"),
    (RuntimeError(PRIVATE), "clock_invalid", "not_run"),
    (False, "clock_invalid", "not_run"),
])
def test_stop_clock_verifier_cofailure_precedence(fault: Any, reason: str, semantic: str) -> None:
    probe = _Probe()
    probe.clock_faults[1] = ValueError(PRIVATE)
    if fault is not None:
        probe.verify_fault = (3, fault)
    result = probe.run()
    _invalid(result, reason, semantic, (3, 0))
    assert probe.loads == probe.checks == 4 and probe.reads == 2


def test_invalid_stop_clock_still_inspects_result() -> None:
    probe = _Probe()
    probe.clock_faults[1] = -1
    _invalid(probe.run(), "clock_invalid", "passed", (3, 0))
    assert probe.events[-1] == ("verify", 3)


@pytest.mark.parametrize("clock_index,value", [
    (0, True), (0, False), (0, 1.0), (0, "10000"), (0, None), (0, -1),
    (1, True), (1, 1.0), (1, "10001"), (1, None), (1, -1),
    (1, 9999), (1, 10000 + 9007199254740992),
])
def test_clock_values_reject_bool_float_negative_backwards_and_overflow(
    clock_index: int, value: Any,
) -> None:
    probe = _Probe()
    probe.clock_faults[clock_index] = value
    _invalid(probe.run(), "clock_invalid", "passed", (3, 0))
    assert probe.loads == 3 + (clock_index == 1)
    assert probe.checks == probe.loads and probe.reads == clock_index + 1


def test_large_absolute_clock_base_preserves_small_delta() -> None:
    probe, readings = _Probe(), iter(
        stamp for index in range(21)
        for stamp in (9007199254741091 + index * 100, 9007199254741092 + index * 100)
    )
    receipt = sample_small_full_load(
        _workload(), _bindings(), load_fresh=probe.load,
        verify_graph=probe.verify, clock_ns=lambda: next(readings),
    )
    assert receipt.timing.phases[0].samples_ns == (1,) * 21
    _roundtrip(receipt)


@pytest.mark.parametrize("durations", [(0,) * 21, tuple(range(21, 0, -1))])
def test_zero_durations_and_permuted_sample_order(durations: tuple[int, ...]) -> None:
    receipt = _Probe(durations).run()
    assert receipt.timing.phases[0].samples_ns == durations
    assert (receipt.timing.phases[0].median_ns, receipt.timing.phases[0].p95_ns) == (
        (0, 0) if durations[0] == 0 else (11, 20)
    )
    _roundtrip(receipt)


def test_verification_is_outside_load_interval() -> None:
    ticks = 0
    events: list[str] = []

    def load() -> _Result:
        nonlocal ticks
        events.append("load")
        ticks += 7
        return _Result(0)

    def verify(result: _Result) -> None:
        nonlocal ticks
        assert result.index == 0
        events.append("verify")
        ticks += 1000000

    def clock() -> int:
        events.append("clock")
        return ticks

    receipt = sample_small_full_load(_workload(), _bindings(), load_fresh=load,
                                     verify_graph=verify, clock_ns=clock)
    assert receipt.timing.phases[0].samples_ns == (7,) * 21
    assert events == ["load", "verify"] * 3 + ["clock", "load", "clock", "verify"] * 21


@pytest.mark.parametrize("stage", [
    "priming_load", "priming_verify", "warmup_load", "warmup_verify",
    "start", "sample_load", "stop", "sample_verify", "cofailure_verify",
])
@pytest.mark.parametrize("exception", [KeyboardInterrupt, SystemExit])
def test_baseexception_propagates_without_receipt(stage: str, exception: Any) -> None:
    probe, abort = _Probe(), exception(PRIVATE)
    scenario = REPEAT if stage.startswith("priming") else COLD
    if stage.endswith("load"):
        probe.load_fault = (3 if stage == "sample_load" else 0, abort)
    elif stage.endswith("verify"):
        probe.verify_fault = (3 if stage in ("sample_verify", "cofailure_verify") else 0, abort)
        if stage == "cofailure_verify":
            probe.clock_faults[1] = ValueError(PRIVATE)
    else:
        probe.clock_faults[0 if stage == "start" else 1] = abort
    with pytest.raises(exception) as error:
        probe.run(scenario)
    assert error.value is abort
    traceback = error.value.__traceback__
    kernel_frames = 0
    while traceback is not None:
        frame = traceback.tb_frame
        if frame.f_code.co_filename == sample_small_full_load.__code__.co_filename:
            kernel_frames += 1
            assert frame.f_locals.get("result") is None
            assert frame.f_locals.get("verification") is None
            assert not any(isinstance(value, _Result) for value in frame.f_locals.values())
        traceback = traceback.tb_next
    assert kernel_frames >= 2
    # Callback traceback frames may retain their own argument. Do not clear them
    # or equate their weak-reference lifetime with kernel/native cleanup.


@pytest.mark.parametrize("failure", ["none", "load", "semantic", "infrastructure"])
def test_kernel_releases_own_results_before_next_start_and_on_exit(failure: str) -> None:
    refs: list[weakref.ReferenceType[_Result]] = []
    loads = 0
    readings = iter(stamp for index in range(21) for stamp in (100 * index, 100 * index + 1))

    def load() -> _Result:
        nonlocal loads
        assert all(reference() is None for reference in refs)
        loads += 1
        if failure == "load" and loads == 4:
            raise RuntimeError(PRIVATE)
        result = _Result(loads)
        refs.append(weakref.ref(result))
        return result

    def verify(result: _Result) -> None:
        if result.index == 4:
            if failure == "semantic":
                raise AssertionError(PRIVATE)
            if failure == "infrastructure":
                raise RuntimeError(PRIVATE)

    receipt = sample_small_full_load(_workload(), _bindings(), load_fresh=load,
                                     verify_graph=verify, clock_ns=lambda: next(readings))
    assert all(reference() is None for reference in refs)
    assert receipt.outcome.availability == ("available" if failure == "none" else "invalid")


def test_repeated_invocations_do_not_share_samples_or_counts() -> None:
    bad = _Probe()
    bad.verify_fault = (13, AssertionError(PRIVATE))
    _invalid(bad.run(), "semantic_mismatch", "failed", (3, 10))
    first, second = _Probe((7,) * 21).run(), _Probe((0,) * 21).run(REPEAT)
    assert first.timing.phases[0].samples_ns == (7,) * 21
    assert second.timing.phases[0].samples_ns == (0,) * 21
    assert first.outcome.availability == second.outcome.availability == "available"


@pytest.mark.parametrize("field,value", [
    ("schema", "other"), ("schema_version", True), ("profile_id", "vault-scale-1000-v1"),
    ("scenario", "content_search"), ("generator_source_sha256", "0" * 64),
    ("semantic_source_sha256", PRIVATE),
])
def test_forged_workloads_revalidate_before_callbacks(field: str, value: Any) -> None:
    workload, probe = _workload(), _Probe()
    object.__setattr__(workload, field, value)
    with pytest.raises(ValueError, match="^invalid small sampling input$"):
        probe.run(workload=workload)
    assert probe.events == []


def test_subclasses_and_missing_record_fields_reject_before_callbacks() -> None:
    class SubBindings(SamplingBindings):
        pass

    class SubSource(contract.SourceIdentity):
        pass

    original = _bindings()
    sub = SubBindings(*(getattr(original, f.name) for f in fields(original)))
    probe = _Probe()
    with pytest.raises(TypeError, match="^invalid small sampling input$"):
        probe.run(bindings=sub)
    subsource = SubSource(*(getattr(original.source, f.name) for f in fields(original.source)))
    with pytest.raises(TypeError, match="^invalid small sampling input$"):
        probe.run(bindings=replace(original, source=subsource))
    missing = _bindings()
    object.__delattr__(missing, "dataset")
    with pytest.raises(TypeError, match="^invalid small sampling input$"):
        probe.run(bindings=missing)
    assert probe.events == []


@pytest.mark.parametrize("argument", ["load_fresh", "verify_graph", "clock_ns"])
def test_noncallable_inputs_reject_before_callbacks(argument: str) -> None:
    probe = _Probe()
    callbacks: dict[str, Any] = {
        "load_fresh": probe.load, "verify_graph": probe.verify, "clock_ns": probe.clock,
    }
    callbacks[argument] = PRIVATE
    with pytest.raises(TypeError, match="^invalid small sampling input$"):
        sample_small_full_load(_workload(), _bindings(), **callbacks)
    assert probe.events == []


@pytest.mark.parametrize("architecture,expected", [
    ("arm64", "aarch64"), ("ARM64", "aarch64"), ("AMD64", "x86_64"),
])
def test_runtime_aliases_normalize_without_host_inspection(architecture: Any, expected: str) -> None:
    binding = _bindings()
    receipt = _Probe().run(bindings=replace(
        binding, runtime=replace(binding.runtime, architecture=architecture),
    ))
    assert receipt.runtime.architecture == expected
    _roundtrip(receipt)


@pytest.mark.parametrize("field,value", [
    ("python_implementation", "PyPy"), ("python_version", "3.14.0"),
    ("architecture", PRIVATE), ("system", "Other"),
])
def test_unsupported_runtime_is_preflight_rejection(field: str, value: Any) -> None:
    probe, binding = _Probe(), _bindings()
    with pytest.raises(ValueError, match="^invalid small sampling input$"):
        probe.run(bindings=replace(binding, runtime=replace(binding.runtime, **{field: value})))
    assert probe.events == []


@pytest.mark.parametrize("field,value", [("working_tree_clean", False), ("commit", PRIVATE),
                                        ("lock_sha256", True), ("harness_sha256", "0" * 64)])
def test_source_metadata_is_revalidated(field: str, value: Any) -> None:
    probe, binding = _Probe(), _bindings()
    with pytest.raises(ValueError, match="^invalid small sampling input$"):
        probe.run(bindings=replace(binding, source=replace(binding.source, **{field: value})))
    assert probe.events == []


@pytest.mark.parametrize("returned", [False, True, PRIVATE])
def test_non_none_verifier_return_is_not_semantic_success(returned: Any) -> None:
    probe = _Probe()
    probe.verify_fault = (3, returned)
    _invalid(probe.run(), "worker_failure", "not_run", (3, 0))


def test_receipts_and_explicit_errors_exclude_private_sentinels() -> None:
    probe = _Probe()
    probe.load_fault = (13, RuntimeError(PRIVATE + " 11111111-2222-3333-4444-555555555555"))
    receipt = probe.run()
    raw = json.dumps(asdict(receipt))
    assert PRIVATE not in raw and "11111111-2222-3333-4444-555555555555" not in raw
    assert set(asdict(receipt)) == {
        "schema", "schema_version", "observation_id", "run_plan_sha256",
        "environment_group_id", "environment_evidence_sha256", "source", "runtime",
        "dataset", "workload", "executor", "outcome", "timing", "memory",
    }


def test_internal_construction_rejection_is_fixed_invariant_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real = contract.validate_comparison_receipt
    calls = 0

    def reject_final(payload: object) -> contract.ReceiptValidation:
        nonlocal calls
        calls += 1
        if calls == 1:
            return real(payload)
        return contract.ReceiptValidation(None, ("schema_invalid",))

    monkeypatch.setattr(contract, "validate_comparison_receipt", reject_final)
    with pytest.raises(RuntimeError, match="^small sampling invariant failure$") as error:
        _Probe().run()
    assert error.value.__cause__ is None and calls == 2


def test_import_and_collection_are_operationally_lazy(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins
    import importlib
    import importlib.util
    import os
    import subprocess
    import sys
    import tempfile
    import time
    from pathlib import Path

    from tests.performance import decision_workload

    name = "tests.performance.decision_sampling"
    alias = "tests._sampling_collection_probe"
    parent = sys.modules["tests.performance"]
    original = sys.modules[name]
    saved_attribute = vars(parent)["decision_sampling"]
    old_alias = sys.modules.get(alias)
    calls: list[str] = []

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        calls.append("unexpected operation")
        raise AssertionError("operational import side effect")

    original_import = builtins.__import__

    def guarded_import(root: str, *args: Any, **kwargs: Any) -> Any:
        if root.startswith(("logseq_matryca_parser", "tests.performance.decision_vault",
                            "tests.performance.synthetic_vault", "tests.performance.runtime_evidence")):
            return forbidden()
        return original_import(root, *args, **kwargs)

    try:
        sys.modules.pop(name)
        delattr(parent, "decision_sampling")
        with monkeypatch.context() as guard:
            guard.setattr(builtins, "__import__", guarded_import)
            guard.setattr(os, "cpu_count", forbidden)
            guard.setattr(time, "perf_counter_ns", forbidden)
            guard.setattr(subprocess, "Popen", forbidden)
            guard.setattr(tempfile, "TemporaryDirectory", forbidden)
            guard.setattr(Path, "mkdir", forbidden)
            guard.setattr(Path, "write_text", forbidden)
            guard.setattr(Path, "write_bytes", forbidden)
            guard.setattr(decision_workload, "workload_payload", forbidden)
            fresh = importlib.import_module(name)
            guard.setattr(fresh, "sample_small_full_load", forbidden)
            spec = importlib.util.spec_from_file_location(alias, __file__)
            assert spec is not None and spec.loader is not None
            module = importlib.util.module_from_spec(spec)
            sys.modules[alias] = module
            spec.loader.exec_module(module)
            assert callable(module.test_cold_sequence_and_statistics)
        assert calls == []
    finally:
        sys.modules[name] = original
        vars(parent)["decision_sampling"] = saved_attribute
        if old_alias is None:
            sys.modules.pop(alias, None)
        else:
            sys.modules[alias] = old_alias


