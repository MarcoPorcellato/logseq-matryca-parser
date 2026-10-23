"""Pure, private decision-observation contracts; no measurements or runtime admission.

These records validate metadata, not the truth of external evidence. They do not
replace the legacy diagnostic protocol or authorize any workload execution.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, fields, is_dataclass
from typing import Literal, NoReturn, cast

type ReasonCode = Literal[
    "schema_invalid",
    "unknown_field",
    "duplicate_key",
    "unsupported_version",
    "invalid_type",
    "invalid_identity",
    "descriptor_mismatch",
    "invalid_worker_shape",
    "invalid_statistics",
    "incomplete_samples",
    "semantic_failure",
    "admission_missing",
    "admission_mismatch",
    "comparison_policy_unverified",
    "policy_mismatch",
    "execution_unverified",
    "source_unverified",
    "environment_unverified",
    "dataset_unverified",
    "workload_unverified",
    "independence_unverified",
    "cleanup_unverified",
    "worker_rule_unverified",
    "phase_interpretation_unverified",
    "os_cache_unverified",
    "unsupported_platform",
    "optional_adapter_unavailable",
    "workload_not_admitted",
    "memory_unavailable",
    "memory_coverage_insufficient",
    "selection_mismatch",
    "duplicate_observation",
    "insufficient_independent_observations",
    "incompatible_environment",
    "incompatible_source",
    "incompatible_dataset",
    "incompatible_workload",
    "incompatible_timing",
    "thresholds_not_predeclared",
    "clock_invalid",
    "worker_launch_failure",
    "worker_failure",
    "timeout",
]
type ScenarioName = Literal[
    "full_load_cold_instance",
    "full_load_unchanged_repeat",
    "incremental_single_page_reload",
    "content_search",
    "tag_search",
    "context_without_embeds",
    "context_with_embeds",
    "deep_parse_1024",
    "pathological_parse_1148",
    "deep_refresh_fixture",
]
type PhaseName = Literal[
    "end_to_end", "discovery", "read_hash", "parse", "model_transfer", "index_build", "operation"
]
type OutcomeAvailability = Literal["available", "invalid", "unavailable"]
type SemanticStatus = Literal["passed", "failed", "not_run"]
type OutcomeReason = Literal[
    "none",
    "semantic_mismatch",
    "worker_launch_failure",
    "timeout",
    "worker_failure",
    "clock_invalid",
    "incomplete_samples",
    "optional_adapter_unavailable",
    "workload_not_admitted",
]
type PhaseReason = Literal[
    "none", "not_applicable", "not_instrumented", "invalid_observation", "unavailable_observation"
]
type Availability = Literal["available", "unavailable"]
type ExecutorMode = Literal["serial", "threads_fixed", "threads_current", "processes_spawn"]
type StartMethod = Literal["none", "spawn"]
type MemoryCoverage = Literal["coordinator_only", "process_tree", "none"]
type MemoryMethod = Literal[
    "native_self_high_water", "isolated_process_tree_peak_v1", "unavailable"
]
type MemoryUnit = Literal["bytes", "KiB", "none"]
type SystemName = Literal["Darwin", "Linux", "Windows"]
type Architecture = Literal["aarch64", "x86_64"]

_MAX_COUNT = 2**53 - 1
_MAX_JSON = 65_536
_PHASE_NAMES: tuple[PhaseName, ...] = (
    "end_to_end",
    "discovery",
    "read_hash",
    "parse",
    "model_transfer",
    "index_build",
    "operation",
)
_SCENARIOS: tuple[ScenarioName, ...] = (
    "full_load_cold_instance",
    "full_load_unchanged_repeat",
    "incremental_single_page_reload",
    "content_search",
    "tag_search",
    "context_without_embeds",
    "context_with_embeds",
    "deep_parse_1024",
    "pathological_parse_1148",
    "deep_refresh_fixture",
)
_EXECUTORS: tuple[ExecutorMode, ...] = (
    "serial",
    "threads_fixed",
    "threads_current",
    "processes_spawn",
)


@dataclass(frozen=True, slots=True)
class VaultDescriptor:
    profile_id: str
    total_pages: int
    ordinary_pages: int
    blocks_per_ordinary_page: int
    deep_chain_nodes: int
    expected_node_count: int


_VAULT_PROFILES = (
    VaultDescriptor("vault-small-96-v1", 96, 95, 24, 1024, 3304),
    VaultDescriptor("vault-scale-1000-v1", 1000, 999, 24, 1024, 25000),
    VaultDescriptor("vault-scale-10000-v1", 10000, 9999, 24, 1024, 241000),
)


@dataclass(frozen=True, slots=True)
class SourceIdentity:
    repository: Literal["MarcoPorcellato/logseq-matryca-parser"]
    commit: str
    tree: str
    lock_sha256: str
    harness_sha256: str
    installed_runtime_sha256: str
    working_tree_clean: bool


@dataclass(frozen=True, slots=True)
class RuntimeIdentity:
    python_implementation: Literal["CPython"]
    python_version: str
    system: SystemName
    architecture: Architecture


@dataclass(frozen=True, slots=True)
class DatasetIdentity:
    kind: Literal["synthetic_vault", "regression_fixture"]
    descriptor_id: str
    descriptor_sha256: str
    generator_source_sha256: str
    dataset_sha256: str
    file_count: int
    source_bytes: int
    expected_node_count: int


@dataclass(frozen=True, slots=True)
class WorkloadIdentity:
    scenario: ScenarioName
    workload_manifest_sha256: str
    operation_parameters_sha256: str
    parser_options_sha256: str
    semantic_contract_sha256: str


@dataclass(frozen=True, slots=True)
class ExecutorShape:
    mode: ExecutorMode
    workers: int
    start_method: StartMethod


@dataclass(frozen=True, slots=True)
class Outcome:
    availability: OutcomeAvailability
    semantic: SemanticStatus
    reason: OutcomeReason


@dataclass(frozen=True, slots=True)
class Phase:
    name: PhaseName
    availability: Availability
    reason: PhaseReason
    samples_ns: tuple[int, ...]
    median_ns: int | None
    p95_ns: int | None


@dataclass(frozen=True, slots=True)
class Timing:
    clock: Literal["perf_counter_ns"]
    completed_warmups: int
    completed_samples: int
    phases: tuple[Phase, ...]


@dataclass(frozen=True, slots=True)
class Memory:
    availability: Availability
    coverage: MemoryCoverage
    method: MemoryMethod
    value: int | None
    unit: MemoryUnit
    evidence_sha256: str | None


@dataclass(frozen=True, slots=True)
class ComparisonReceipt:
    schema: Literal["matryca-decision-observation"]
    schema_version: int
    observation_id: str
    run_plan_sha256: str
    environment_group_id: str
    environment_evidence_sha256: str
    source: SourceIdentity
    runtime: RuntimeIdentity
    dataset: DatasetIdentity
    workload: WorkloadIdentity
    executor: ExecutorShape
    outcome: Outcome
    timing: Timing
    memory: Memory


@dataclass(frozen=True, slots=True)
class ReceiptValidation:
    receipt: ComparisonReceipt | None
    reasons: tuple[ReasonCode, ...]


@dataclass(frozen=True, slots=True)
class GateRejection:
    verdict: Literal["unavailable"] = "unavailable"
    reasons: tuple[Literal["unsupported_platform"], ...] = ("unsupported_platform",)


@dataclass(frozen=True, slots=True)
class EligibilityResult:
    verdict: Literal["eligible", "invalid", "unavailable", "incomparable"]
    reasons: tuple[ReasonCode, ...]


class _ValidationError(Exception):
    def __init__(self, *reasons: ReasonCode) -> None:
        self.reasons: tuple[ReasonCode, ...] = tuple(sorted(set(reasons)))
        super().__init__()


def _fail(*reasons: ReasonCode) -> NoReturn:
    raise _ValidationError(*reasons)


def _object(value: object, keys: str) -> dict[str, object]:
    if type(value) is not dict:
        _fail("invalid_type")
    result = cast(dict[str, object], value)
    if any(type(k) is not str for k in result):
        _fail("invalid_type")
    expected, actual = set(keys.split()), set(result)
    reasons: list[ReasonCode] = []
    if actual - expected:
        reasons.append("unknown_field")
    if expected - actual:
        reasons.append("schema_invalid")
    if reasons:
        _fail(*reasons)
    return result


def _text(value: object) -> str:
    if type(value) is not str:
        _fail("invalid_type")
    return cast(str, value)


def _choice[Choice: str](value: object, options: tuple[Choice, ...]) -> Choice:
    text = _text(value)
    if text not in options:
        _fail("schema_invalid")
    return cast(Choice, text)


def _count(value: object, *, positive: bool = False) -> int:
    if type(value) is not int:
        _fail("invalid_type")
    number = cast(int, value)
    if not (int(positive) <= number <= _MAX_COUNT):
        _fail("invalid_statistics")
    return number


def _boolean(value: object) -> bool:
    if type(value) is not bool:
        _fail("invalid_type")
    return cast(bool, value)


def _identity(value: object, size: int = 64) -> str:
    text = _text(value)
    if re.fullmatch("[0-9a-f]{" + str(size) + "}", text) is None or (
        size == 64 and text == "0" * size
    ):
        _fail("invalid_identity")
    return text


def _version(value: object) -> int:
    number = _count(value, positive=True)
    if number != 1:
        _fail("unsupported_version")
    return number


def _array(value: object) -> list[object]:
    if type(value) is not list:
        _fail("invalid_type")
    return cast(list[object], value)


def _source(value: object) -> SourceIdentity:
    d = _object(
        value,
        "repository commit tree lock_sha256 harness_sha256 installed_runtime_sha256 working_tree_clean",
    )
    clean = _boolean(d["working_tree_clean"])
    if not clean:
        _fail("source_unverified")
    return SourceIdentity(
        _choice(d["repository"], ("MarcoPorcellato/logseq-matryca-parser",)),
        _identity(d["commit"], 40),
        _identity(d["tree"], 40),
        _identity(d["lock_sha256"]),
        _identity(d["harness_sha256"]),
        _identity(d["installed_runtime_sha256"]),
        clean,
    )


def _runtime(value: object) -> RuntimeIdentity:
    d = _object(value, "python_implementation python_version system architecture")
    implementation = _text(d["python_implementation"])
    version = _text(d["python_version"])
    system = _text(d["system"])
    architecture = _text(d["architecture"])
    architecture = {"arm64": "aarch64", "ARM64": "aarch64", "AMD64": "x86_64"}.get(
        architecture, architecture
    )
    if (
        implementation != "CPython"
        or re.fullmatch(r"3\.(12|13)\.(0|[1-9][0-9]*)", version) is None
        or system not in ("Darwin", "Linux", "Windows")
        or architecture not in ("aarch64", "x86_64")
    ):
        _fail("unsupported_platform")
    return RuntimeIdentity(
        "CPython", version, cast(SystemName, system), cast(Architecture, architecture)
    )


def _dataset(value: object) -> DatasetIdentity:
    d = _object(
        value,
        "kind descriptor_id descriptor_sha256 generator_source_sha256 dataset_sha256 file_count source_bytes expected_node_count",
    )
    kind: Literal["synthetic_vault", "regression_fixture"] = _choice(
        d["kind"], ("synthetic_vault", "regression_fixture")
    )
    descriptor = _text(d["descriptor_id"])
    count = _count(d["file_count"], positive=True)
    nodes = _count(d["expected_node_count"], positive=True)
    if kind == "synthetic_vault":
        profile = next((p for p in _VAULT_PROFILES if p.profile_id == descriptor), None)
        if profile is None or (count, nodes) != (profile.total_pages, profile.expected_node_count):
            _fail("descriptor_mismatch")
    elif descriptor not in ("m87-pathological-1148-v1", "m113-deep-refresh-v1") or count != 1:
        _fail("descriptor_mismatch")
    return DatasetIdentity(
        kind,
        descriptor,
        _identity(d["descriptor_sha256"]),
        _identity(d["generator_source_sha256"]),
        _identity(d["dataset_sha256"]),
        count,
        _count(d["source_bytes"], positive=True),
        nodes,
    )


def _workload(value: object) -> WorkloadIdentity:
    d = _object(
        value,
        "scenario workload_manifest_sha256 operation_parameters_sha256 parser_options_sha256 semantic_contract_sha256",
    )
    return WorkloadIdentity(
        _choice(d["scenario"], _SCENARIOS),
        _identity(d["workload_manifest_sha256"]),
        _identity(d["operation_parameters_sha256"]),
        _identity(d["parser_options_sha256"]),
        _identity(d["semantic_contract_sha256"]),
    )


def _executor(value: object) -> ExecutorShape:
    d = _object(value, "mode workers start_method")
    mode, method = _text(d["mode"]), _text(d["start_method"])
    workers = _count(d["workers"], positive=True)
    if (
        mode not in _EXECUTORS
        or method != ("spawn" if mode == "processes_spawn" else "none")
        or (mode == "serial" and workers != 1)
        or (mode in ("threads_fixed", "processes_spawn") and workers not in (1, 2, 4, 8))
        or (mode == "threads_current" and workers > 32)
    ):
        _fail("invalid_worker_shape")
    return ExecutorShape(cast(ExecutorMode, mode), workers, cast(StartMethod, method))


def _outcome(value: object) -> Outcome:
    d = _object(value, "availability semantic reason")
    availability: OutcomeAvailability = _choice(
        d["availability"], ("available", "invalid", "unavailable")
    )
    semantic: SemanticStatus = _choice(d["semantic"], ("passed", "failed", "not_run"))
    reason: OutcomeReason = _choice(
        d["reason"],
        (
            "none",
            "semantic_mismatch",
            "worker_launch_failure",
            "timeout",
            "worker_failure",
            "clock_invalid",
            "incomplete_samples",
            "optional_adapter_unavailable",
            "workload_not_admitted",
        ),
    )
    if (
        (availability == "available" and (semantic != "passed" or reason != "none"))
        or (
            availability == "invalid"
            and reason
            not in (
                "semantic_mismatch",
                "worker_launch_failure",
                "timeout",
                "worker_failure",
                "clock_invalid",
                "incomplete_samples",
            )
        )
        or (reason == "semantic_mismatch" and semantic != "failed")
        or (
            availability == "unavailable"
            and (
                semantic != "not_run"
                or reason
                not in (
                    "optional_adapter_unavailable",
                    "workload_not_admitted",
                )
            )
        )
    ):
        _fail("schema_invalid")
    return Outcome(availability, semantic, reason)


def _phase(value: object, expected: PhaseName, outcome: Outcome) -> Phase:
    d = _object(value, "name availability reason samples_ns median_ns p95_ns")
    name = _choice(d["name"], _PHASE_NAMES)
    if name != expected:
        _fail("schema_invalid")
    availability: Availability = _choice(d["availability"], ("available", "unavailable"))
    reason: PhaseReason = _choice(
        d["reason"],
        (
            "none",
            "not_applicable",
            "not_instrumented",
            "invalid_observation",
            "unavailable_observation",
        ),
    )
    raw_samples = _array(d["samples_ns"])
    if availability == "available":
        if outcome.availability != "available" or reason != "none":
            _fail("invalid_statistics")
        if len(raw_samples) != 21:
            _fail("incomplete_samples")
        samples = tuple(_count(x) for x in raw_samples)
        median, p95 = _count(d["median_ns"]), _count(d["p95_ns"])
        ordered = sorted(samples)
        if (median, p95) != (ordered[10], ordered[19]):
            _fail("invalid_statistics")
    else:
        if raw_samples or d["median_ns"] is not None or d["p95_ns"] is not None:
            _fail("invalid_statistics")
        if (
            (outcome.availability == "invalid" and reason != "invalid_observation")
            or (outcome.availability == "unavailable" and reason != "unavailable_observation")
            or (
                outcome.availability == "available"
                and reason
                not in (
                    "not_applicable",
                    "not_instrumented",
                )
            )
        ):
            _fail("schema_invalid")
        samples, median, p95 = (), None, None
    return Phase(name, availability, reason, samples, median, p95)


def _timing(value: object, outcome: Outcome, scenario: ScenarioName) -> Timing:
    d = _object(value, "clock completed_warmups completed_samples phases")
    clock: Literal["perf_counter_ns"] = _choice(d["clock"], ("perf_counter_ns",))
    warmups, samples = _count(d["completed_warmups"]), _count(d["completed_samples"])
    if warmups > 3 or samples > 21:
        _fail("incomplete_samples")
    if (outcome.availability == "available" and (warmups, samples) != (3, 21)) or (
        outcome.availability == "unavailable" and (warmups, samples) != (0, 0)
    ):
        _fail("incomplete_samples")
    raw = _array(d["phases"])
    if len(raw) != 7:
        _fail("schema_invalid")
    phases = tuple(_phase(p, name, outcome) for p, name in zip(raw, _PHASE_NAMES, strict=True))
    primary = 0 if scenario.startswith("full_load_") else 6
    if outcome.availability == "available" and phases[primary].availability != "available":
        _fail("incomplete_samples")
    if not scenario.startswith("full_load_") and phases[0].availability != "unavailable":
        _fail("invalid_statistics")
    return Timing(clock, warmups, samples, phases)


def _memory(value: object, runtime: RuntimeIdentity) -> Memory:
    d = _object(value, "availability coverage method value unit evidence_sha256")
    availability: Availability = _choice(d["availability"], ("available", "unavailable"))
    coverage: MemoryCoverage = _choice(d["coverage"], ("coordinator_only", "process_tree", "none"))
    method: MemoryMethod = _choice(
        d["method"], ("native_self_high_water", "isolated_process_tree_peak_v1", "unavailable")
    )
    unit: MemoryUnit = _choice(d["unit"], ("bytes", "KiB", "none"))
    if availability == "unavailable":
        if (coverage, method, unit, d["value"], d["evidence_sha256"]) != (
            "none",
            "unavailable",
            "none",
            None,
            None,
        ):
            _fail("schema_invalid")
        return Memory(availability, coverage, method, None, unit, None)
    number, evidence = _count(d["value"]), _identity(d["evidence_sha256"])
    if (
        unit == "none"
        or method == "unavailable"
        or coverage == "none"
        or (method == "native_self_high_water" and coverage != "coordinator_only")
        or (method == "isolated_process_tree_peak_v1" and coverage != "process_tree")
        or (
            method == "native_self_high_water"
            and (
                runtime.system == "Windows"
                or unit != ("bytes" if runtime.system == "Darwin" else "KiB")
            )
        )
    ):
        _fail("schema_invalid")
    if number * (1024 if unit == "KiB" else 1) > _MAX_COUNT:
        _fail("invalid_statistics")
    return Memory(availability, coverage, method, number, unit, evidence)


def validate_comparison_receipt(payload: object) -> ReceiptValidation:
    """Check decoded closed JSON; prior decoder duplicate-key handling is unknown."""
    try:
        d = _object(
            payload,
            "schema schema_version observation_id run_plan_sha256 environment_group_id environment_evidence_sha256 source runtime dataset workload executor outcome timing memory",
        )
        schema: Literal["matryca-decision-observation"] = _choice(
            d["schema"], ("matryca-decision-observation",)
        )
        version = _version(d["schema_version"])
        source, runtime = _source(d["source"]), _runtime(d["runtime"])
        dataset, workload = _dataset(d["dataset"]), _workload(d["workload"])
        executor, outcome = _executor(d["executor"]), _outcome(d["outcome"])
        if not workload.scenario.startswith("full_load_") and executor.mode != "serial":
            _fail("invalid_worker_shape")
        receipt = ComparisonReceipt(
            schema,
            version,
            _identity(d["observation_id"], 32),
            _identity(d["run_plan_sha256"]),
            _identity(d["environment_group_id"], 32),
            _identity(d["environment_evidence_sha256"]),
            source,
            runtime,
            dataset,
            workload,
            executor,
            outcome,
            _timing(d["timing"], outcome, workload.scenario),
            _memory(d["memory"], runtime),
        )
        return ReceiptValidation(receipt, ())
    except _ValidationError as error:
        return ReceiptValidation(None, error.reasons)


def _json_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for name, value in pairs:
        if name in result:
            _fail("duplicate_key")
        result[name] = value
    return result


def _json_nonfinite(value: str) -> NoReturn:
    _fail("invalid_type")


def parse_comparison_json(raw: str) -> ReceiptValidation:
    """Decode bounded UTF-8 JSON without losing duplicate-key evidence."""
    try:
        _text(raw)
        if len(raw) > _MAX_JSON or len(raw.encode("utf-8")) > _MAX_JSON:
            _fail("schema_invalid")
        payload = json.loads(raw, object_pairs_hook=_json_pairs, parse_constant=_json_nonfinite)
    except _ValidationError as error:
        return ReceiptValidation(None, error.reasons)
    except (ValueError, RecursionError, UnicodeError):
        return ReceiptValidation(None, ("schema_invalid",))
    return validate_comparison_receipt(payload)


type Purpose = Literal["calibration", "cache_design", "executor_design"]


@dataclass(frozen=True, slots=True)
class ComparisonInvariants:
    source: SourceIdentity
    runtime: RuntimeIdentity
    dataset: DatasetIdentity
    environment_group_id: str
    environment_evidence_sha256: str
    parser_options_sha256: str
    semantic_contract_sha256: str
    clock: Literal["perf_counter_ns"]
    phase_interpretation: Literal["elapsed_wall_v1"]
    instrumentation_sha256: str
    os_cache_condition: Literal["uncontrolled", "warm_observed", "cold_verified"]


@dataclass(frozen=True, slots=True)
class CellRequirement:
    cell_id: str
    scenario: ScenarioName
    executor: ExecutorShape
    workload_manifest_sha256: str
    operation_parameters_sha256: str


@dataclass(frozen=True, slots=True)
class ObservationAssignment:
    observation_id: str
    cell_id: str


@dataclass(frozen=True, slots=True)
class ThresholdAdmission:
    thresholds_sha256: str
    evidence_manifest_sha256: str
    predeclared_before_selected_runs: bool


@dataclass(frozen=True, slots=True)
class ComparisonPolicy:
    policy_version: int
    purpose: Purpose
    run_plan_sha256: str
    selection_manifest_sha256: str
    invariants: ComparisonInvariants
    permitted_variation: Literal["none", "executor_shape", "cache_preconditioning"]
    cells: tuple[CellRequirement, ...]
    assignments: tuple[ObservationAssignment, ...]
    minimum_independent_per_cell: int
    thresholds: ThresholdAdmission | None


@dataclass(frozen=True, slots=True)
class AdmittedComparisonPolicy:
    policy: ComparisonPolicy
    policy_sha256: str
    evidence_manifest_sha256: str
    verified: bool


@dataclass(frozen=True, slots=True)
class ComparisonRequest:
    purpose: Purpose
    policy_sha256: str
    run_plan_sha256: str
    selection_manifest_sha256: str
    expected_observation_ids: tuple[str, ...]
    comparison_key_sha256: str
    thresholds_sha256: str | None


@dataclass(frozen=True, slots=True)
class AdmissionAttestation:
    observation_id: str
    outer_execution_id: str
    receipt_sha256: str
    policy_sha256: str
    evidence_manifest_sha256: str
    source_verified: bool
    environment_verified: bool
    dataset_verified: bool
    workload_verified: bool
    actual_execution_verified: bool
    semantic_verified: bool
    independence_verified: bool
    cleanup_verified: bool
    worker_rule_verified: bool
    phase_interpretation_verified: bool
    os_cache_condition_verified: bool
    full_load_costs_verified: bool
    parse_attribution_verified: bool
    memory_coverage_verified: bool


_RECORD_TYPES = (
    SourceIdentity,
    RuntimeIdentity,
    DatasetIdentity,
    WorkloadIdentity,
    ExecutorShape,
    Outcome,
    Phase,
    Timing,
    Memory,
    ComparisonReceipt,
    ComparisonInvariants,
    CellRequirement,
    ObservationAssignment,
    ThresholdAdmission,
    ComparisonPolicy,
    AdmittedComparisonPolicy,
    ComparisonRequest,
    AdmissionAttestation,
)
_ADMISSION_FLAGS: tuple[tuple[str, ReasonCode], ...] = (
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
    ("parse_attribution_verified", "phase_interpretation_unverified"),
    ("memory_coverage_verified", "memory_coverage_insufficient"),
)
_INCOMPARABLE: frozenset[ReasonCode] = frozenset(
    (
        "insufficient_independent_observations",
        "incompatible_environment",
        "incompatible_source",
        "incompatible_dataset",
        "incompatible_workload",
        "incompatible_timing",
        "thresholds_not_predeclared",
    )
)
_UNAVAILABLE: frozenset[ReasonCode] = frozenset(
    (
        "unsupported_platform",
        "optional_adapter_unavailable",
        "workload_not_admitted",
        "memory_unavailable",
        "memory_coverage_insufficient",
    )
)


def _frozen_payload(value: object, depth: int = 0) -> object:
    """Convert only known immutable records; mutable caller containers are not trusted."""
    if depth > 16:
        _fail("schema_invalid")
    if type(value) in _RECORD_TYPES and is_dataclass(value) and not isinstance(value, type):
        return {f.name: _frozen_payload(getattr(value, f.name), depth + 1) for f in fields(value)}
    if type(value) is tuple:
        items = cast(tuple[object, ...], value)
        if len(items) > 256:
            _fail("schema_invalid")
        return [_frozen_payload(item, depth + 1) for item in items]
    if value is None or type(value) in (str, bool, int):
        return value
    _fail("invalid_type")


def _canonical_hash(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _record_hash(record: object) -> str:
    return _canonical_hash(_frozen_payload(record))


def _checked_receipt(value: object) -> ComparisonReceipt:
    if type(value) is not ComparisonReceipt:
        _fail("invalid_type")
    validated = validate_comparison_receipt(_frozen_payload(value))
    if validated.receipt is None:
        _fail(*validated.reasons)
    return validated.receipt


def _invariants(value: object) -> ComparisonInvariants:
    d = _object(
        value,
        "source runtime dataset environment_group_id environment_evidence_sha256 parser_options_sha256 semantic_contract_sha256 clock phase_interpretation instrumentation_sha256 os_cache_condition",
    )
    return ComparisonInvariants(
        _source(d["source"]),
        _runtime(d["runtime"]),
        _dataset(d["dataset"]),
        _identity(d["environment_group_id"], 32),
        _identity(d["environment_evidence_sha256"]),
        _identity(d["parser_options_sha256"]),
        _identity(d["semantic_contract_sha256"]),
        _choice(d["clock"], ("perf_counter_ns",)),
        _choice(d["phase_interpretation"], ("elapsed_wall_v1",)),
        _identity(d["instrumentation_sha256"]),
        _choice(d["os_cache_condition"], ("uncontrolled", "warm_observed", "cold_verified")),
    )


def _cell(value: object) -> CellRequirement:
    d = _object(
        value, "cell_id scenario executor workload_manifest_sha256 operation_parameters_sha256"
    )
    scenario, executor = _choice(d["scenario"], _SCENARIOS), _executor(d["executor"])
    if not scenario.startswith("full_load_") and executor.mode != "serial":
        _fail("invalid_worker_shape")
    return CellRequirement(
        _identity(d["cell_id"], 32),
        scenario,
        executor,
        _identity(d["workload_manifest_sha256"]),
        _identity(d["operation_parameters_sha256"]),
    )


def _assignment(value: object) -> ObservationAssignment:
    d = _object(value, "observation_id cell_id")
    return ObservationAssignment(_identity(d["observation_id"], 32), _identity(d["cell_id"], 32))


def _threshold(value: object) -> ThresholdAdmission:
    d = _object(
        value, "thresholds_sha256 evidence_manifest_sha256 predeclared_before_selected_runs"
    )
    return ThresholdAdmission(
        _identity(d["thresholds_sha256"]),
        _identity(d["evidence_manifest_sha256"]),
        _boolean(d["predeclared_before_selected_runs"]),
    )


def _selection_hash(
    cells: tuple[CellRequirement, ...],
    assignments: tuple[ObservationAssignment, ...],
) -> str:
    return _canonical_hash(
        {
            "cells": [_frozen_payload(c) for c in cells],
            "assignments": [_frozen_payload(a) for a in assignments],
        }
    )


def _comparison_policy(value: object) -> ComparisonPolicy:
    d = _object(
        value,
        "policy_version purpose run_plan_sha256 selection_manifest_sha256 invariants permitted_variation cells assignments minimum_independent_per_cell thresholds",
    )
    version = _version(d["policy_version"])
    purpose: Purpose = _choice(d["purpose"], ("calibration", "cache_design", "executor_design"))
    variation: Literal["none", "executor_shape", "cache_preconditioning"] = _choice(
        d["permitted_variation"], ("none", "executor_shape", "cache_preconditioning")
    )
    raw_cells, raw_assignments = _array(d["cells"]), _array(d["assignments"])
    if not (1 <= len(raw_cells) <= 10 and 1 <= len(raw_assignments) <= 256):
        _fail("selection_mismatch")
    cells = tuple(_cell(x) for x in raw_cells)
    assignments = tuple(_assignment(x) for x in raw_assignments)
    cell_ids = {c.cell_id for c in cells}
    if len(cell_ids) != len(cells):
        _fail("selection_mismatch")
    if len({a.observation_id for a in assignments}) != len(assignments):
        _fail("duplicate_observation")
    if {a.cell_id for a in assignments} != cell_ids:
        _fail("selection_mismatch")
    minimum = _count(d["minimum_independent_per_cell"], positive=True)
    if minimum != 3:
        _fail("policy_mismatch")
    threshold = None if d["thresholds"] is None else _threshold(d["thresholds"])
    if purpose == "calibration":
        if len(cells) != 1 or variation != "none" or threshold is not None:
            _fail("policy_mismatch")
    elif purpose == "executor_design":
        modes = {c.executor.mode for c in cells}
        if (
            not 2 <= len(cells) <= 10
            or variation != "executor_shape"
            or threshold is None
            or len({c.executor for c in cells}) != len(cells)
            or not modes.intersection(("serial", "threads_current"))
            or "processes_spawn" not in modes
            or not cells[0].scenario.startswith("full_load_")
            or any(
                (c.scenario, c.workload_manifest_sha256, c.operation_parameters_sha256)
                != (
                    cells[0].scenario,
                    cells[0].workload_manifest_sha256,
                    cells[0].operation_parameters_sha256,
                )
                for c in cells
            )
        ):
            _fail("policy_mismatch")
    elif (
        len(cells) != 2
        or variation != "cache_preconditioning"
        or threshold is None
        or {c.scenario for c in cells} != {"full_load_cold_instance", "full_load_unchanged_repeat"}
        or cells[0].executor != cells[1].executor
        or cells[0].executor.mode != "threads_current"
    ):
        _fail("policy_mismatch")
    selection = _identity(d["selection_manifest_sha256"])
    if selection != _selection_hash(cells, assignments):
        _fail("policy_mismatch")
    return ComparisonPolicy(
        version,
        purpose,
        _identity(d["run_plan_sha256"]),
        selection,
        _invariants(d["invariants"]),
        variation,
        cells,
        assignments,
        minimum,
        threshold,
    )


def _admitted_policy(value: object) -> AdmittedComparisonPolicy:
    if type(value) is not AdmittedComparisonPolicy:
        _fail("comparison_policy_unverified")
    d = _object(_frozen_payload(value), "policy policy_sha256 evidence_manifest_sha256 verified")
    verified = _boolean(d["verified"])
    if not verified:
        _fail("comparison_policy_unverified")
    policy = _comparison_policy(d["policy"])
    digest = _identity(d["policy_sha256"])
    if digest != _record_hash(policy):
        _fail("policy_mismatch")
    return AdmittedComparisonPolicy(
        policy, digest, _identity(d["evidence_manifest_sha256"]), verified
    )


def _admission(value: object) -> AdmissionAttestation:
    if value is None:
        _fail("admission_missing")
    if type(value) is not AdmissionAttestation:
        _fail("invalid_type")
    d = _object(
        _frozen_payload(value),
        "observation_id outer_execution_id receipt_sha256 policy_sha256 evidence_manifest_sha256 "
        + " ".join(name for name, _ in _ADMISSION_FLAGS),
    )
    flags = [_boolean(d[name]) for name, _ in _ADMISSION_FLAGS]
    return AdmissionAttestation(
        _identity(d["observation_id"], 32),
        _identity(d["outer_execution_id"], 32),
        _identity(d["receipt_sha256"]),
        _identity(d["policy_sha256"]),
        _identity(d["evidence_manifest_sha256"]),
        *flags,
    )


def _eligibility(reasons: set[ReasonCode]) -> EligibilityResult:
    ordered: tuple[ReasonCode, ...] = tuple(sorted(reasons))
    if reasons - _INCOMPARABLE - _UNAVAILABLE:
        return EligibilityResult("invalid", ordered)
    if reasons & _UNAVAILABLE:
        return EligibilityResult("unavailable", ordered)
    if reasons:
        return EligibilityResult("incomparable", ordered)
    return EligibilityResult("eligible", ())


def _observation_reasons(
    receipt: ComparisonReceipt,
    admission: AdmissionAttestation,
    admitted: AdmittedComparisonPolicy,
) -> set[ReasonCode]:
    policy, invariants = admitted.policy, admitted.policy.invariants
    reasons: set[ReasonCode] = set()
    if (
        admission.observation_id != receipt.observation_id
        or admission.receipt_sha256 != _record_hash(receipt)
        or admission.policy_sha256 != admitted.policy_sha256
    ):
        reasons.add("admission_mismatch")
    if receipt.run_plan_sha256 != policy.run_plan_sha256:
        reasons.add("policy_mismatch")
    if receipt.source != invariants.source:
        reasons.add("incompatible_source")
    if (
        receipt.runtime != invariants.runtime
        or receipt.environment_group_id != invariants.environment_group_id
        or receipt.environment_evidence_sha256 != invariants.environment_evidence_sha256
    ):
        reasons.add("incompatible_environment")
    if receipt.dataset != invariants.dataset:
        reasons.add("incompatible_dataset")
    if (
        receipt.workload.parser_options_sha256 != invariants.parser_options_sha256
        or receipt.workload.semantic_contract_sha256 != invariants.semantic_contract_sha256
    ):
        reasons.add("incompatible_workload")
    assignment = next(
        (a for a in policy.assignments if a.observation_id == receipt.observation_id), None
    )
    if assignment is None:
        reasons.add("selection_mismatch")
    else:
        cell = next(c for c in policy.cells if c.cell_id == assignment.cell_id)
        if receipt.executor != cell.executor or receipt.workload.scenario != cell.scenario:
            reasons.add("policy_mismatch")
        if (
            receipt.workload.workload_manifest_sha256 != cell.workload_manifest_sha256
            or receipt.workload.operation_parameters_sha256 != cell.operation_parameters_sha256
        ):
            reasons.add("incompatible_workload")
    for flag, reason in _ADMISSION_FLAGS[:11]:
        if receipt.outcome.reason == "workload_not_admitted" and flag in (
            "dataset_verified",
            "workload_verified",
        ):
            continue
        # A truthful not-run result has no measurement evidence, but cleanup
        # and independent outer-launch evidence remain lifecycle requirements.
        if receipt.outcome.availability == "unavailable" and flag in (
            "actual_execution_verified",
            "semantic_verified",
            "worker_rule_verified",
            "phase_interpretation_verified",
            "os_cache_condition_verified",
        ):
            continue
        if not getattr(admission, flag):
            reasons.add(reason)
    if receipt.outcome.availability == "unavailable":
        reasons.add(cast(ReasonCode, receipt.outcome.reason))
        return reasons
    if receipt.outcome.availability == "invalid":
        reasons.add(
            "semantic_failure"
            if receipt.outcome.reason == "semantic_mismatch"
            else cast(ReasonCode, receipt.outcome.reason)
        )
        return reasons
    if (
        receipt.workload.scenario.startswith("full_load_")
        and not admission.full_load_costs_verified
    ):
        reasons.add("phase_interpretation_unverified")
    if (
        policy.purpose == "cache_design"
        and receipt.workload.scenario == "full_load_unchanged_repeat"
    ):
        if receipt.timing.phases[3].availability != "available":
            reasons.add("incompatible_timing")
        elif not admission.parse_attribution_verified:
            reasons.add("phase_interpretation_unverified")
    if policy.purpose == "executor_design":
        if receipt.memory.availability != "available":
            reasons.add("memory_unavailable")
        elif receipt.memory.coverage != "process_tree" or not admission.memory_coverage_verified:
            reasons.add("memory_coverage_insufficient")
    return reasons


def assess_observation(
    receipt: ComparisonReceipt,
    admission: AdmissionAttestation,
    policy: AdmittedComparisonPolicy,
) -> EligibilityResult:
    """Check metadata eligibility against explicit trusted review inputs, never files."""
    try:
        admitted = _admitted_policy(policy)
        checked = _checked_receipt(receipt)
        attestation = _admission(admission)
        return _eligibility(_observation_reasons(checked, attestation, admitted))
    except _ValidationError as error:
        return _eligibility(set(error.reasons))
    except (RecursionError, UnicodeError):
        return _eligibility({"schema_invalid"})


def _request(value: object) -> ComparisonRequest:
    if type(value) is not ComparisonRequest:
        _fail("invalid_type")
    d = _object(
        _frozen_payload(value),
        "purpose policy_sha256 run_plan_sha256 selection_manifest_sha256 expected_observation_ids comparison_key_sha256 thresholds_sha256",
    )
    purpose: Purpose = _choice(d["purpose"], ("calibration", "cache_design", "executor_design"))
    raw_ids = _array(d["expected_observation_ids"])
    if not 1 <= len(raw_ids) <= 256:
        _fail("selection_mismatch")
    ids = tuple(_identity(x, 32) for x in raw_ids)
    if len(set(ids)) != len(ids):
        _fail("duplicate_observation")
    threshold = None if d["thresholds_sha256"] is None else _identity(d["thresholds_sha256"])
    if (purpose == "calibration") != (threshold is None):
        _fail("schema_invalid")
    return ComparisonRequest(
        purpose,
        _identity(d["policy_sha256"]),
        _identity(d["run_plan_sha256"]),
        _identity(d["selection_manifest_sha256"]),
        ids,
        _identity(d["comparison_key_sha256"]),
        threshold,
    )


def assess_comparison(
    receipts: tuple[ComparisonReceipt, ...],
    admissions: tuple[AdmissionAttestation, ...],
    request: ComparisonRequest,
    policy: AdmittedComparisonPolicy,
) -> EligibilityResult:
    """Assess the entire predeclared selection; never launch, filter or retry work."""
    try:
        if type(receipts) is not tuple or type(admissions) is not tuple:
            _fail("invalid_type")
        if len(receipts) > 256 or len(admissions) > 256:
            _fail("selection_mismatch")
        admitted, selected = _admitted_policy(policy), _request(request)
        p = admitted.policy
        reasons: set[ReasonCode] = set()
        expected_ids = tuple(a.observation_id for a in p.assignments)
        expected_threshold = None if p.thresholds is None else p.thresholds.thresholds_sha256
        if (
            selected.purpose != p.purpose
            or selected.policy_sha256 != admitted.policy_sha256
            or selected.run_plan_sha256 != p.run_plan_sha256
            or selected.selection_manifest_sha256 != p.selection_manifest_sha256
            or selected.comparison_key_sha256 != _record_hash(p.invariants)
            or selected.thresholds_sha256 != expected_threshold
        ):
            reasons.add("policy_mismatch")
        if selected.expected_observation_ids != expected_ids:
            reasons.add("selection_mismatch")
        if p.thresholds is not None and not p.thresholds.predeclared_before_selected_runs:
            reasons.add("thresholds_not_predeclared")
        checked_receipts: list[ComparisonReceipt] = []
        checked_admissions: list[AdmissionAttestation] = []
        for receipt in receipts:
            try:
                checked_receipts.append(_checked_receipt(receipt))
            except _ValidationError as error:
                reasons.update(error.reasons)
        for admission in admissions:
            try:
                checked_admissions.append(_admission(admission))
            except _ValidationError as error:
                reasons.update(error.reasons)
        receipt_ids = [r.observation_id for r in checked_receipts]
        admission_ids = [a.observation_id for a in checked_admissions]
        outer_ids = [a.outer_execution_id for a in checked_admissions]
        if (
            len(set(receipt_ids)) != len(receipt_ids)
            or len(set(admission_ids)) != len(admission_ids)
            or len(set(outer_ids)) != len(outer_ids)
        ):
            reasons.add("duplicate_observation")
        if (
            set(receipt_ids) != set(expected_ids)
            or len(receipt_ids) != len(expected_ids)
            or set(admission_ids) != set(expected_ids)
            or len(admission_ids) != len(expected_ids)
        ):
            reasons.add("selection_mismatch")
        by_id = {a.observation_id: a for a in checked_admissions}
        assignment_cells = {a.observation_id: a.cell_id for a in p.assignments}
        eligible_outer_ids: dict[str, set[str]] = {cell.cell_id: set() for cell in p.cells}
        for receipt in checked_receipts:
            matching = by_id.get(receipt.observation_id)
            if matching is None:
                reasons.add("admission_missing")
                continue
            observation_reasons = _observation_reasons(receipt, matching, admitted)
            reasons.update(observation_reasons)
            if not observation_reasons:
                cell_id = assignment_cells[receipt.observation_id]
                eligible_outer_ids[cell_id].add(matching.outer_execution_id)
        if any(len(ids) < p.minimum_independent_per_cell for ids in eligible_outer_ids.values()):
            reasons.add("insufficient_independent_observations")
        return _eligibility(reasons)
    except _ValidationError as error:
        return _eligibility(set(error.reasons))
    except (RecursionError, UnicodeError):
        return _eligibility({"schema_invalid"})
