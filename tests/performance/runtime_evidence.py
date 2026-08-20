"""Private, source-free runtime evidence data model for performance tests."""

from __future__ import annotations

import argparse
import math
import platform
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Final, Literal
from unittest.mock import patch

try:  # pragma: no cover - exercised where the Unix-only module is unavailable.
    import resource
except ImportError:  # Windows has no resource module.
    resource = None  # type: ignore[assignment]

from logseq_matryca_parser import synapse as synapse_module
from logseq_matryca_parser.graph import LogseqGraph, iter_canonical_pages_from_dict
from logseq_matryca_parser.logos_parser import StackMachineParser
from logseq_matryca_parser.synapse import SynapseAdapter
from tests.parser_assurance.invariants import assert_tree_invariants, walk_nodes
from tests.performance.synthetic_vault import (
    SYNTHETIC_VAULT_SCHEMA_VERSION,
    SyntheticVault,
    build_synthetic_vault,
)

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


class HarnessDocument:
    """Small local stand-in that keeps optional chunk evidence dependency-free."""

    def __init__(self, page_content: str, metadata: dict[str, object]) -> None:
        self.page_content = page_content
        self.metadata = metadata


def _with_temporary_graph(
    vault: SyntheticVault, action: Callable[[Path, LogseqGraph], None]
) -> None:
    with TemporaryDirectory() as temporary:
        root = vault.materialize(Path(temporary))
        action(root, LogseqGraph.load_directory(root))


def run_deep_parse_1024(vault: SyntheticVault) -> ScenarioReceipt:
    """Measure parser construction with a real tree-invariant gate."""

    def action() -> None:
        page = StackMachineParser().parse(vault.deep_chain_source, page_title="runtime-deep")
        assert_tree_invariants(page)
        assert len(tuple(walk_nodes(page.root_nodes))) == vault.deep_chain_depth

    return measure_scenario("deep_parse_1024", action)


def run_cold_graph_load(vault: SyntheticVault) -> ScenarioReceipt:
    """Measure loading the complete synthetic vault with canonical-page validation."""

    def action() -> None:
        def assert_graph(_root: Path, graph: LogseqGraph) -> None:
            assert len(list(iter_canonical_pages_from_dict(graph.pages))) == vault.page_count

        _with_temporary_graph(vault, assert_graph)

    return measure_scenario("cold_graph_load", action)


def run_incremental_alias_move_reload(vault: SyntheticVault) -> ScenarioReceipt:
    """Measure the #103 incremental-versus-cold backlink equivalence gate."""

    def action() -> None:
        with TemporaryDirectory() as temporary:
            root = vault.materialize(Path(temporary))
            pages = root / "pages"
            linker_path = pages / "runtime-evidence-page-0001.md"
            linker_path.write_text("- linker [[runtime-evidence-alias-0002]]\n", encoding="utf-8")
            source = pages / "runtime-evidence-page-0002.md"
            moved = pages / "runtime-evidence-page-moved.md"
            incremental = LogseqGraph.load_directory(root)
            source.write_text(
                "title:: runtime-evidence-page-moved\n"
                "alias:: runtime-evidence-alias-0002, runtime-evidence-alias-moved\n\n"
                "- moved target\n",
                encoding="utf-8",
            )
            source.rename(moved)
            incremental.invalidate_and_reload_page(source)
            incremental.invalidate_and_reload_page(moved)
            cold = LogseqGraph.load_directory(root)
            for target in (
                "runtime-evidence-page-0002",
                "runtime-evidence-page-moved",
                "runtime-evidence-alias-0002",
                "runtime-evidence-alias-moved",
            ):
                assert [node.uuid for node in incremental.get_backlinks(target)] == [
                    node.uuid for node in cold.get_backlinks(target)
                ]

    return measure_scenario("incremental_alias_move_reload", action)


def run_search_content(vault: SyntheticVault) -> ScenarioReceipt:
    """Measure a fixed unique-token search over a complete synthetic graph."""

    def action() -> None:
        def assert_search(_root: Path, graph: LogseqGraph) -> None:
            hits = graph.search_content("block-0001-")
            assert len(hits) == vault.blocks_per_page
            assert all(node.uuid for node in hits)

        _with_temporary_graph(vault, assert_search)

    return measure_scenario("search_content", action)


def run_synapse_context_chunks(vault: SyntheticVault | None = None) -> ScenarioReceipt:
    """Measure optional context chunks or report their fixed unavailable state."""
    if synapse_module.Document is None:
        return ScenarioReceipt(
            scenario="synapse_context_chunks",
            availability="unavailable",
            unavailable_reason="optional_adapter_unavailable",
            semantic_gate_passed=False,
            warmup_count=0,
            sample_count=0,
            median_duration_ns=None,
            p95_duration_ns=None,
        )
    selected_vault = vault or build_synthetic_vault()

    def action() -> None:
        def assert_chunks(_root: Path, graph: LogseqGraph) -> None:
            page = graph.pages["runtime-evidence-page-0001"]
            with patch.object(synapse_module, "Document", HarnessDocument):
                chunks = SynapseAdapter.to_context_enriched_chunks(page.root_nodes, graph)
            assert len(chunks) == selected_vault.blocks_per_page
            assert all(chunk.metadata["page_title"] for chunk in chunks)
            assert all(chunk.metadata["source_path"] for chunk in chunks)
            assert all(chunk.metadata["line_start"] for chunk in chunks)

        _with_temporary_graph(selected_vault, assert_chunks)

    return measure_scenario("synapse_context_chunks", action)


def run_runtime_evidence() -> RuntimeEvidenceReceipt:
    """Run all fixed local scenarios and return one aggregate-only receipt."""
    vault = build_synthetic_vault()
    scenarios = (
        run_deep_parse_1024(vault),
        run_cold_graph_load(vault),
        run_incremental_alias_move_reload(vault),
        run_search_content(vault),
        run_synapse_context_chunks(vault),
    )
    return build_runtime_receipt(vault, scenarios)


def main(argv: list[str] | None = None) -> int:
    """Emit one source-free runtime receipt without persisting a result."""
    parser = argparse.ArgumentParser(
        description="Emit a source-free local runtime-evidence receipt."
    )
    parser.parse_args(argv)
    import json

    print(json.dumps(run_runtime_evidence().to_payload(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
