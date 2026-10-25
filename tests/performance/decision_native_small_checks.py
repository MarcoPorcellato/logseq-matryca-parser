"""Opt-in two-load correctness; importing or collecting this file does not run it."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from hashlib import sha256
from os import lstat
from pathlib import Path
from tempfile import TemporaryDirectory
from types import MappingProxyType
from typing import TYPE_CHECKING, Literal, cast

import pytest

from tests.performance import decision_native_binding as binding
from tests.performance import decision_semantics, decision_vault
from tests.performance.decision_semantics import NodeKey, SmallGraphProjection
from tests.performance.decision_workload import describe_small_full_load_workload
from tests.performance.synthetic_vault import SyntheticVault

if TYPE_CHECKING:
    from logseq_matryca_parser.graph import LogseqGraph

_selection_started = False


def _claim_native_selection(config: pytest.Config) -> None:
    global _selection_started
    forbidden_plugins = (
        "xdist", "xdist.plugin", "repeat", "pytest_repeat",
        "rerunfailures", "pytest_rerunfailures",
    )
    if (_selection_started or os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD") != "1"
            or hasattr(config, "workerinput")
            or any(config.pluginmanager.hasplugin(name) for name in forbidden_plugins)):
        raise RuntimeError("native small-load correctness selection rejected")
    _selection_started = True


@dataclass(frozen=True, slots=True)
class _NativePair:
    first: LogseqGraph
    second: LogseqGraph
    first_uuid_rows: tuple[tuple[NodeKey, str], ...]
    second_uuid_rows: tuple[tuple[NodeKey, str], ...]
    counts: Mapping[str, int]
    final_state: Literal["closed"]
    cleanup_status: Literal["succeeded"]


@pytest.fixture(scope="module")
def native_binding_pair(
    request: pytest.FixtureRequest,
    record_testsuite_property: Callable[[str, object], None],
) -> _NativePair:
    """An execution envelope, not this fixture, must authorize the two real calls."""
    counts = dict.fromkeys(("build", "materialize", "expected", "native_load", "verify", "cleanup"), 0)
    context: binding.NativeSmallLoadContext | None = None
    first: LogseqGraph | None = None
    second: LogseqGraph | None = None
    root: Path | None = None
    first_rows: tuple[tuple[NodeKey, str], ...] = ()
    second_rows: tuple[tuple[NodeKey, str], ...] = ()
    observations: list[SmallGraphProjection] = []
    try:
        _claim_native_selection(request.config)
        workload = describe_small_full_load_workload(
            "vault-small-96-v1", "full_load_cold_instance",
            generator_source_sha256=sha256(Path(decision_vault.__file__).read_bytes()).hexdigest(),
            semantic_source_sha256=sha256(Path(decision_semantics.__file__).read_bytes()).hexdigest(),
        )
        resolve = binding._resolve_native
        build = binding.build_decision_vault
        materialize = binding._materialize
        expected = binding.expected_small_graph
        observe = binding.observe_small_graph
        create_owner = binding.TemporaryDirectory
        native_source = Path(__file__).resolve().parents[2] / "src/logseq_matryca_parser/graph.py"

        def counted_resolve() -> binding._NativeLoader:
            native = resolve()
            graph_class = getattr(native.load_directory, "__self__", None)
            function = getattr(native.load_directory, "__func__", None)
            assert graph_class is not None and function is not None
            assert vars(graph_class)["load_directory"].__func__ is function
            assert Path(function.__code__.co_filename).resolve() == native_source

            def counted_load(
                graph_path: Path, *, strict_refs: bool, strict_title_collisions: bool,
            ) -> LogseqGraph:
                assert (strict_refs, strict_title_collisions) == (False, False)
                if counts["native_load"] >= 2:
                    raise RuntimeError("native small-load call limit exceeded")
                counts["native_load"] += 1
                return native.load_directory(
                    graph_path, strict_refs=strict_refs, strict_title_collisions=strict_title_collisions,
                )

            return binding._NativeLoader(counted_load, native.max_workers)

        def counted_build(profile: str) -> SyntheticVault:
            counts["build"] += 1
            return build(profile)

        def counted_materialize(source: SyntheticVault, destination: Path) -> Path:
            counts["materialize"] += 1
            return materialize(source, destination)

        def counted_expected() -> SmallGraphProjection:
            counts["expected"] += 1
            return expected()

        def counted_observe(graph: LogseqGraph, *, graph_root: Path) -> SmallGraphProjection:
            counts["verify"] += 1
            projection = observe(graph, graph_root=graph_root)
            observations.append(projection)
            return projection

        with pytest.MonkeyPatch.context() as scoped:
            def counted_owner(
                *, prefix: str, ignore_cleanup_errors: bool, delete: bool,
            ) -> TemporaryDirectory[str]:
                owner = create_owner(
                    prefix=prefix, ignore_cleanup_errors=ignore_cleanup_errors, delete=delete,
                )
                cleanup = owner.cleanup

                def counted_cleanup() -> None:
                    counts["cleanup"] += 1
                    cleanup()

                scoped.setattr(owner, "cleanup", counted_cleanup)
                return owner

            scoped.setattr(binding, "_resolve_native", counted_resolve)
            scoped.setattr(binding, "build_decision_vault", counted_build)
            scoped.setattr(binding, "_materialize", counted_materialize)
            scoped.setattr(binding, "expected_small_graph", counted_expected)
            scoped.setattr(binding, "observe_small_graph", counted_observe)
            scoped.setattr(binding, "TemporaryDirectory", counted_owner)
            context = binding.NativeSmallLoadContext(workload)
            with context:
                first = context.load_fresh()
                context.verify_graph(first)
                second = context.load_fresh()
                context.verify_graph(second)
                first_rows = tuple((node.key, node.uuid) for node in observations[0].nodes)
                second_rows = tuple((node.key, node.uuid) for node in observations[1].nodes)
                root = first.graph_path
    finally:
        for name, count in counts.items():
            record_testsuite_property("decision_native_binding_" + name + "_calls", count)

    assert first is not None and second is not None and root is not None and context is not None
    assert context.state == "closed" and context.cleanup_status == "succeeded"
    try:
        lstat(root)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("native small-load owned cleanup unconfirmed")
    assert counts == {"build": 1, "materialize": 1, "expected": 1, "native_load": 2, "verify": 2, "cleanup": 1}
    return _NativePair(
        first, second, first_rows, second_rows, MappingProxyType(dict(counts)),
        cast(Literal["closed"], context.state), cast(Literal["succeeded"], context.cleanup_status),
    )


def test_two_native_binding_graphs_pass_oracle(native_binding_pair: _NativePair) -> None:
    assert native_binding_pair.counts["native_load"] == native_binding_pair.counts["verify"] == 2
    assert native_binding_pair.first is not native_binding_pair.second


def test_native_binding_same_source_uuid_relations(native_binding_pair: _NativePair) -> None:
    assert len(native_binding_pair.first_uuid_rows) == len(native_binding_pair.second_uuid_rows) == 3304
    assert native_binding_pair.first_uuid_rows == native_binding_pair.second_uuid_rows


def test_native_binding_owned_cleanup_counts(native_binding_pair: _NativePair) -> None:
    assert native_binding_pair.counts == {
        "build": 1, "materialize": 1, "expected": 1, "native_load": 2, "verify": 2, "cleanup": 1,
    }
    assert (native_binding_pair.final_state, native_binding_pair.cleanup_status) == ("closed", "succeeded")
