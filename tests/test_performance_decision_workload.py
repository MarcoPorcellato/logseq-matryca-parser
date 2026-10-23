"""Closed workload metadata must stay pure, independently hashed and non-admitting."""

from __future__ import annotations

import builtins
import importlib
import json
import os
import subprocess
import sys
import time
import uuid
from dataclasses import FrozenInstanceError, asdict
from hashlib import sha256
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

SCENARIOS = ("full_load_cold_instance", "full_load_unchanged_repeat")
PAGE_FIELDS = (
    "title", "logical_source", "raw_content_sha256", "properties", "properties_order",
    "refs", "namespace_chain", "root_uuids", "created_at", "updated_at", "tab_size",
)
NODE_FIELDS = (
    "key", "logical_source", "uuid", "source_uuid", "synthetic_id", "content", "clean_text",
    "indent_level", "line_start", "line_end", "properties", "properties_order", "wikilinks",
    "tags", "assets", "block_refs", "refs", "task_status", "task_priority", "repeater",
    "scheduled_at", "deadline_at", "created_at", "updated_at", "parent_id", "left_id",
    "path", "outline_path", "child_uuids",
)


def _module() -> ModuleType:
    return importlib.import_module("tests.performance.decision_workload")


def _describe(module: ModuleType, scenario: str = SCENARIOS[0]) -> Any:
    return module.describe_small_full_load_workload(
        "vault-small-96-v1", scenario,
        generator_source_sha256="1" * 64, semantic_source_sha256="2" * 64,
    )


def _expected_payload(scenario: str) -> dict[str, Any]:
    """Hand-specified manifest: never read the module's constants or output."""
    return {
        "schema": "matryca-small-full-load-workload", "schema_version": 1,
        "profile_id": "vault-small-96-v1",
        "generator": {"namespace": "decision-vault-generator", "version": 1,
                      "source_sha256": "1" * 64},
        "dataset": {
            "profile_id": "vault-small-96-v1", "total_pages": 96, "ordinary_pages": 95,
            "blocks_per_ordinary_page": 24, "deep_chain_nodes": 1024,
            "expected_node_count": 3304, "source_bytes": 1107557,
            "dataset_sha256": "adcbc2e2085aad2533ad5f9f5961c0525b291ad4fd47a89eb7ac42ab7b77e583",
        },
        "operation": {
            "scenario": scenario, "api": "LogseqGraph.load_directory",
            "preparation": "materialize_once_outside_timing", "fresh_graph_per_sample": True,
            "fresh_executor_per_sample": True, "source_order": "logical_posix_ascending_v1",
            "primary_phase": "end_to_end", "interval": "complete_load_directory_call",
            "os_cache_condition": "uncontrolled",
            "priming_loads": 0 if scenario == SCENARIOS[0] else 1,
            "priming_placement": "none" if scenario == SCENARIOS[0] else "once_before_three_warmups",
        },
        "parser_options": {"strict_refs": False, "strict_title_collisions": False,
                           "file_tab_policy": "native_per_file"},
        "semantics": {
            "schema": "matryca-small-full-load-semantics", "schema_version": 1,
            "source_sha256": "2" * 64, "profile": "semantic_roundtrip_v1",
            "identity_policy": {"synthetic_uuid": "stable", "source_uuid": "absent",
                                "relations": "direct_ids"},
            "page_fields": list(PAGE_FIELDS), "node_fields": list(NODE_FIELDS),
            "supplemental_policy": "exact_ranges_and_owned_logical_sources_v1",
            "identity_formula": "source_uuid5_dns_sha256_v1",
            "container_policy": "closed_small_fixture_v1",
        },
    }


def _literal_digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_workload_payloads_match_independent_literals(scenario: str) -> None:
    # Break caught: omitted/changed executed meaning or incorrect hash framing.
    module = _module()
    workload = _describe(module, scenario)
    expected = _expected_payload(scenario)
    assert module.workload_payload(workload) == expected
    assert asdict(module.workload_identity(workload)) == {
        "scenario": scenario, "workload_manifest_sha256": _literal_digest(expected),
        "operation_parameters_sha256": _literal_digest(expected["operation"]),
        "parser_options_sha256": _literal_digest(expected["parser_options"]),
        "semantic_contract_sha256": _literal_digest(expected["semantics"]),
    }


def test_workload_pair_differs_only_in_scenario_and_priming() -> None:
    module = _module()
    cold, repeat = (_describe(module, scenario) for scenario in SCENARIOS)
    first, second = (module.workload_payload(item) for item in (cold, repeat))
    assert {key for key in first if first[key] != second[key]} == {"operation"}
    assert {key for key in first["operation"]
            if first["operation"][key] != second["operation"][key]} == {
                "scenario", "priming_loads", "priming_placement",
            }
    a, b = module.workload_identity(cold), module.workload_identity(repeat)
    assert a.parser_options_sha256 == b.parser_options_sha256
    assert a.semantic_contract_sha256 == b.semantic_contract_sha256
    assert a.operation_parameters_sha256 != b.operation_parameters_sha256
    assert a.workload_manifest_sha256 != b.workload_manifest_sha256


def test_explicit_source_bindings_change_their_dependent_identities() -> None:
    module = _module()
    original = _describe(module)
    for parameter in ("generator_source_sha256", "semantic_source_sha256"):
        arguments = {"generator_source_sha256": "1" * 64, "semantic_source_sha256": "2" * 64}
        arguments[parameter] = "3" * 64
        changed = module.describe_small_full_load_workload("vault-small-96-v1", SCENARIOS[0],
                                                         **arguments)
        a, b = module.workload_identity(original), module.workload_identity(changed)
        assert a.workload_manifest_sha256 != b.workload_manifest_sha256
        assert a.operation_parameters_sha256 == b.operation_parameters_sha256
        assert a.parser_options_sha256 == b.parser_options_sha256
        assert (a.semantic_contract_sha256 != b.semantic_contract_sha256) == (
            parameter == "semantic_source_sha256"
        )


class _Hostile:
    def __str__(self) -> str:
        raise AssertionError("rejected input was coerced")

    def __eq__(self, other: object) -> bool:
        raise AssertionError("rejected input was compared")


class _StringSubclass(str):
    def __eq__(self, other: object) -> bool:
        raise AssertionError("rejected subclass was compared")


@pytest.mark.parametrize(("value", "error"), [
    (None, TypeError), (False, TypeError), (7, TypeError), (b"x", TypeError),
    (_Hostile(), TypeError), ("", ValueError), ("A" * 64, ValueError),
    ("0" * 64, ValueError), ("1" * 63, ValueError), ("g" * 64, ValueError),
], ids=["none", "bool", "int", "bytes", "hostile", "empty", "uppercase", "zero", "short", "nonhex"])
def test_standalone_semantic_descriptor_rejects_invalid_source_bindings(
    value: object, error: type[Exception],
) -> None:
    # The standalone consumer must not rely on the workload factory's validation.
    semantics = importlib.import_module("tests.performance.decision_semantics")
    with pytest.raises(error, match="^invalid small workload input$"):
        semantics.semantic_contract_payload(semantic_source_sha256=value)


@pytest.mark.parametrize("field", ("profile_id", "scenario", "generator_source_sha256",
                                  "semantic_source_sha256"))
@pytest.mark.parametrize("bad", [None, False, 1, 1.5, b"private-sentinel",
                                Path("private-sentinel"), _Hostile(),
                                _StringSubclass("vault-small-96-v1")],
                         ids=["none", "bool", "int", "float", "bytes", "path", "hostile", "subclass"])
def test_metadata_rejects_wrong_types_without_coercion(field: str, bad: object) -> None:
    module = _module()
    arguments: dict[str, object] = {
        "profile_id": "vault-small-96-v1", "scenario": SCENARIOS[0],
        "generator_source_sha256": "1" * 64, "semantic_source_sha256": "2" * 64,
    }
    arguments[field] = bad
    with pytest.raises(TypeError, match="^invalid small workload input$"):
        module.describe_small_full_load_workload(**arguments)


@pytest.mark.parametrize(("field", "bad"), [
    ("profile_id", ""), ("profile_id", "vault-scale-1000-v1"),
    ("profile_id", "vault-scale-10000-v1"), ("profile_id", "private-sentinel"),
    ("scenario", "incremental_single_page_reload"), ("scenario", "private-sentinel"),
    *[(field, value) for field in ("generator_source_sha256", "semantic_source_sha256")
      for value in ("", "0" * 64, "A" * 64, "g" * 64, "1" * 63, "1" * 65, "private-sentinel")],
])
def test_metadata_rejects_unsupported_values_without_echo(field: str, bad: str) -> None:
    arguments = {"profile_id": "vault-small-96-v1", "scenario": SCENARIOS[0],
                 "generator_source_sha256": "1" * 64, "semantic_source_sha256": "2" * 64}
    arguments[field] = bad
    with pytest.raises(ValueError, match="^invalid small workload input$"):
        _module().describe_small_full_load_workload(**arguments)


@pytest.mark.parametrize("consumer", ("workload_payload", "workload_identity"))
@pytest.mark.parametrize(("field", "bad", "error"), [
    ("schema", "other", ValueError), ("schema_version", 2, ValueError),
    ("schema_version", True, TypeError), ("profile_id", "vault-scale-1000-v1", ValueError),
    ("scenario", "other", ValueError), ("generator_source_sha256", "0" * 64, ValueError),
    ("semantic_source_sha256", None, TypeError),
])
def test_constructor_and_consumers_revalidate_records(
    consumer: str, field: str, bad: object, error: type[Exception],
) -> None:
    module = _module()
    record = _describe(module)
    arguments = asdict(record)
    arguments[field] = bad
    with pytest.raises(error, match="^invalid small workload input$"):
        module.SmallFullLoadWorkload(**arguments)
    object.__setattr__(record, field, bad)
    with pytest.raises(error, match="^invalid small workload input$"):
        getattr(module, consumer)(record)


@pytest.mark.parametrize("consumer", ("workload_payload", "workload_identity"))
def test_consumers_reject_incomplete_foreign_and_subclass_records(consumer: str) -> None:
    module = _module()
    function = getattr(module, consumer)
    with pytest.raises(ValueError, match="^invalid small workload input$"):
        function(object.__new__(module.SmallFullLoadWorkload))
    foreign = type("Foreign", (module.SmallFullLoadWorkload,), {})
    foreign_values: tuple[object, ...] = (None, {}, _Hostile(), object.__new__(foreign))
    for value in foreign_values:
        with pytest.raises(TypeError, match="^invalid small workload input$"):
            function(value)


def test_records_are_frozen_and_payload_mutation_cannot_change_identity() -> None:
    module = _module()
    record = _describe(module)
    before = module.workload_identity(record)
    with pytest.raises(FrozenInstanceError):
        record.scenario = "other"
    payload = module.workload_payload(record)
    payload["parser_options"]["strict_refs"] = True
    payload["semantics"]["page_fields"].clear()
    assert module.workload_payload(record) == _expected_payload(SCENARIOS[0])
    assert module.workload_identity(record) == before


def test_closed_signature_rejects_binding_errors_without_value_echo() -> None:
    function = _module().describe_small_full_load_workload
    with pytest.raises(TypeError):
        function()
    with pytest.raises(TypeError) as caught:
        function("vault-small-96-v1", SCENARIOS[0], generator_source_sha256="1" * 64,
                 semantic_source_sha256="2" * 64, unexpected_option="private-sentinel")
    assert "private-sentinel" not in str(caught.value)


def test_metadata_import_and_construction_are_inert(monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.performance import decision_vault, synthetic_vault
    names = ("tests.performance.decision_workload", "tests.performance.decision_semantics")
    package = sys.modules["tests.performance"]
    missing = object()
    parent_attributes = {name.rpartition(".")[2]: package.__dict__.get(name.rpartition(".")[2], missing)
                         for name in names}
    originals = {name: sys.modules.pop(name, None) for name in names}
    original_import = builtins.__import__
    original_profile = sys.getprofile()
    calls: list[str] = []

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        calls.append("forbidden")
        raise AssertionError("metadata performed runtime work")

    def checked_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name.startswith(("logseq_matryca_parser", "tests.parser_assurance")):
            return forbidden()
        return original_import(name, *args, **kwargs)

    def check_profile(frame: Any, event: str, argument: Any) -> None:
        if event == "call" and frame.f_code.co_name == "expected_small_graph":
            forbidden()

    try:
        with monkeypatch.context() as scoped:
            for owner, attribute in (
                (builtins, "open"), (Path, "open"), (Path, "read_bytes"), (Path, "read_text"),
                (Path, "glob"), (Path, "rglob"), (os, "cpu_count"), (os, "getenv"),
                (time, "perf_counter"), (time, "process_time"), (subprocess, "run"),
                (subprocess, "Popen"), (uuid, "uuid5"),
                (decision_vault, "build_decision_vault"),
                (synthetic_vault, "build_synthetic_vault"), (synthetic_vault.SyntheticVault, "materialize"),
            ):
                scoped.setattr(owner, attribute, forbidden)
            scoped.setattr(builtins, "__import__", checked_import)
            sys.setprofile(check_profile)
            semantics = importlib.import_module(names[1])
            scoped.setattr(semantics, "expected_small_graph", forbidden, raising=False)
            module = importlib.import_module(names[0])
            for scenario in SCENARIOS:
                record = _describe(module, scenario)
                assert module.workload_payload(record) == _expected_payload(scenario)
                module.workload_identity(record)
    finally:
        sys.setprofile(original_profile)
        for name, old in originals.items():
            sys.modules.pop(name, None)
            if old is not None:
                sys.modules[name] = old
        for name, original in parent_attributes.items():
            if original is missing:
                package.__dict__.pop(name, None)
            else:
                package.__dict__[name] = original
    assert calls == []
    for name, original in parent_attributes.items():
        assert package.__dict__.get(name, missing) is original, "fresh imports did not restore package state"
