"""Private, source-free runtime evidence data model for performance tests."""

from __future__ import annotations

import math
import platform
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Final, Literal

try:  # pragma: no cover - exercised where the Unix-only module is unavailable.
    import resource
except ImportError:  # Windows has no resource module.
    resource = None  # type: ignore[assignment]

from tests.performance.synthetic_vault import SYNTHETIC_VAULT_SCHEMA_VERSION, SyntheticVault

WARMUP_COUNT: Final = 3
SAMPLE_COUNT: Final = 21
RUNTIME_EVIDENCE_SCHEMA_VERSION: Final = 1
RUNTIME_EVIDENCE_HARNESS_VERSION: Final = 1
REPLAY_COMMAND: Final = "uv run python -m tests.performance.runtime_evidence"

ScenarioName = Literal[
    "deep_parse_1024",
    "cold_graph_load",
    "incremental_alias_move_reload",
    "search_content",
    "synapse_context_chunks",
]
ScenarioAvailability = Literal["available", "unavailable", "invalid"]
UnavailableReason = Literal["optional_adapter_unavailable"]


@dataclass(frozen=True)
class ScenarioReceipt:
    """Aggregate, source-free evidence from one named scenario."""

    scenario: ScenarioName
    availability: ScenarioAvailability
    unavailable_reason: UnavailableReason | None
    semantic_gate_passed: bool
    warmup_count: int
    sample_count: int
    median_duration_ns: int | None
    p95_duration_ns: int | None


@dataclass(frozen=True)
class RuntimeEvidenceReceipt:
    """Aggregate-only observation bound to a deterministic synthetic vault."""

    runtime_evidence_schema_version: int
    runtime_evidence_harness_version: int
    synthetic_vault_schema_version: int
    source_sha256: str
    aggregate_counts: dict[str, int]
    python_version: str
    platform_system: str
    platform_machine: str
    replay_command: str
    resident_high_water: dict[str, int | str]
    scenarios: tuple[ScenarioReceipt, ...]

    def to_payload(self) -> dict[str, object]:
        """Return the fixed JSON-ready aggregate receipt payload."""
        return asdict(self)


def percentile_p95_ns(samples: tuple[int, ...]) -> int:
    """Return the declared nearest-rank p95 for a non-empty duration vector."""
    if not samples:
        raise ValueError("p95 requires at least one sample")
    return sorted(samples)[math.ceil(0.95 * len(samples)) - 1]


def median_ns(samples: tuple[int, ...]) -> int:
    """Return the middle duration for the deliberately odd measurement count."""
    if len(samples) % 2 != 1:
        raise ValueError("runtime evidence requires an odd sample count")
    return sorted(samples)[len(samples) // 2]


def _invalid_receipt(scenario: ScenarioName) -> ScenarioReceipt:
    return ScenarioReceipt(
        scenario=scenario,
        availability="invalid",
        unavailable_reason=None,
        semantic_gate_passed=False,
        warmup_count=WARMUP_COUNT,
        sample_count=0,
        median_duration_ns=None,
        p95_duration_ns=None,
    )


def measure_scenario(
    scenario: ScenarioName,
    semantic_action: Callable[[], None],
    *,
    clock_ns: Callable[[], int] = time.perf_counter_ns,
) -> ScenarioReceipt:
    """Measure only semantic-successful actions under the fixed warm-up protocol."""
    try:
        for _ in range(WARMUP_COUNT):
            semantic_action()
        samples: list[int] = []
        for _ in range(SAMPLE_COUNT):
            started = clock_ns()
            semantic_action()
            elapsed = clock_ns() - started
            if elapsed < 0:
                raise ValueError("measurement clock returned a negative elapsed duration")
            samples.append(elapsed)
    except Exception:
        return _invalid_receipt(scenario)

    durations = tuple(samples)
    return ScenarioReceipt(
        scenario=scenario,
        availability="available",
        unavailable_reason=None,
        semantic_gate_passed=True,
        warmup_count=WARMUP_COUNT,
        sample_count=SAMPLE_COUNT,
        median_duration_ns=median_ns(durations),
        p95_duration_ns=percentile_p95_ns(durations),
    )


def resident_high_water_observation() -> dict[str, int | str]:
    """Return a labelled native high-water observation without normalizing it."""
    if resource is None:
        return {"availability": "unavailable"}
    try:
        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except (AttributeError, OSError):
        return {"availability": "unavailable"}
    unit = "bytes" if platform.system() == "Darwin" else "KiB"
    return {"availability": "available", "value": value, "unit": unit}


def build_runtime_receipt(
    vault: SyntheticVault,
    scenarios: tuple[ScenarioReceipt, ...],
) -> RuntimeEvidenceReceipt:
    """Bind aggregate scenario observations to the fixed synthetic-vault identity."""
    return RuntimeEvidenceReceipt(
        runtime_evidence_schema_version=RUNTIME_EVIDENCE_SCHEMA_VERSION,
        runtime_evidence_harness_version=RUNTIME_EVIDENCE_HARNESS_VERSION,
        synthetic_vault_schema_version=SYNTHETIC_VAULT_SCHEMA_VERSION,
        source_sha256=vault.source_sha256,
        aggregate_counts={
            "page_count": vault.page_count,
            "blocks_per_page": vault.blocks_per_page,
            "deep_chain_depth": vault.deep_chain_depth,
            "total_source_bytes": vault.total_source_bytes,
        },
        python_version=platform.python_version(),
        platform_system=platform.system(),
        platform_machine=platform.machine(),
        replay_command=REPLAY_COMMAND,
        resident_high_water=resident_high_water_observation(),
        scenarios=scenarios,
    )
