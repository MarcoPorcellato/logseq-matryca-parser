"""Closed, pure identities for two unmeasured small full-load workloads."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Literal, cast

from tests.performance.comparison_contract import _VAULT_PROFILES, WorkloadIdentity
from tests.performance.decision_semantics import _require_source_digest, semantic_contract_payload

type SmallScenario = Literal["full_load_cold_instance", "full_load_unchanged_repeat"]


@dataclass(frozen=True, slots=True)
class SmallFullLoadWorkload:
    """Validated metadata only; digest syntax proves no runtime provenance."""

    schema: Literal["matryca-small-full-load-workload"]
    schema_version: Literal[1]
    profile_id: Literal["vault-small-96-v1"]
    scenario: SmallScenario
    generator_source_sha256: str
    semantic_source_sha256: str

    def __post_init__(self) -> None:
        _validate(self)


def _validate(workload: object) -> None:
    if type(workload) is not SmallFullLoadWorkload:
        raise TypeError("invalid small workload input")
    try:
        values = (workload.schema, workload.schema_version, workload.profile_id,
                  workload.scenario, workload.generator_source_sha256,
                  workload.semantic_source_sha256)
    except AttributeError:
        raise ValueError("invalid small workload input") from None
    if any(type(value) is not str for index, value in enumerate(values) if index != 1):
        raise TypeError("invalid small workload input")
    if type(workload.schema_version) is not int:
        raise TypeError("invalid small workload input")
    if (workload.schema != "matryca-small-full-load-workload" or workload.schema_version != 1
            or workload.profile_id != "vault-small-96-v1"
            or workload.scenario not in ("full_load_cold_instance", "full_load_unchanged_repeat")):
        raise ValueError("invalid small workload input")
    _require_source_digest(workload.generator_source_sha256)
    _require_source_digest(workload.semantic_source_sha256)


def describe_small_full_load_workload(
    profile_id: str, scenario: str, *,
    generator_source_sha256: str, semantic_source_sha256: str,
) -> SmallFullLoadWorkload:
    """Bind explicit caller identities; never discover sources or run a workload."""
    return SmallFullLoadWorkload(
        "matryca-small-full-load-workload", 1, cast(Literal["vault-small-96-v1"], profile_id),
        cast(SmallScenario, scenario), generator_source_sha256, semantic_source_sha256,
    )


def workload_payload(workload: SmallFullLoadWorkload) -> dict[str, object]:
    """Return a fresh complete payload, including preconditioning and semantic meaning."""
    _validate(workload)
    descriptor = _VAULT_PROFILES[0]
    if (descriptor.profile_id != "vault-small-96-v1"
            or (descriptor.total_pages, descriptor.ordinary_pages,
                descriptor.blocks_per_ordinary_page, descriptor.deep_chain_nodes,
                descriptor.expected_node_count) != (96, 95, 24, 1024, 3304)):
        raise ValueError("invalid small workload input")
    repeat = workload.scenario == "full_load_unchanged_repeat"
    return {
        "schema": workload.schema, "schema_version": workload.schema_version,
        "profile_id": workload.profile_id,
        "generator": {"namespace": "decision-vault-generator", "version": 1,
                      "source_sha256": workload.generator_source_sha256},
        "dataset": {
            **asdict(descriptor), "source_bytes": 1107557,
            "dataset_sha256": "adcbc2e2085aad2533ad5f9f5961c0525b291ad4fd47a89eb7ac42ab7b77e583",
        },
        "operation": {
            "scenario": workload.scenario, "api": "LogseqGraph.load_directory",
            "preparation": "materialize_once_outside_timing", "fresh_graph_per_sample": True,
            "fresh_executor_per_sample": True, "source_order": "logical_posix_ascending_v1",
            "primary_phase": "end_to_end", "interval": "complete_load_directory_call",
            "os_cache_condition": "uncontrolled", "priming_loads": 1 if repeat else 0,
            "priming_placement": "once_before_three_warmups" if repeat else "none",
        },
        "parser_options": {"strict_refs": False, "strict_title_collisions": False,
                           "file_tab_policy": "native_per_file"},
        "semantics": semantic_contract_payload(
            semantic_source_sha256=workload.semantic_source_sha256,
        ),
    }


def _digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def workload_identity(workload: SmallFullLoadWorkload) -> WorkloadIdentity:
    """Hash each meaning separately; no hash is included inside its own payload."""
    payload = workload_payload(workload)
    return WorkloadIdentity(
        workload.scenario, _digest(payload), _digest(payload["operation"]),
        _digest(payload["parser_options"]), _digest(payload["semantics"]),
    )
