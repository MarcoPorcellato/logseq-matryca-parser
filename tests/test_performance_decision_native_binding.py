"""Fake-native lifecycle checks; no native graph call or sampling campaign."""

from __future__ import annotations

import builtins
import importlib
import importlib.util
import os
import sys
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from tests.performance import decision_semantics, decision_vault
from tests.performance.decision_workload import (
    SmallFullLoadWorkload,
    describe_small_full_load_workload,
)


def _binding() -> ModuleType:
    return importlib.import_module("tests.performance.decision_native_binding")


def _workload(scenario: str = "full_load_cold_instance") -> SmallFullLoadWorkload:
    return describe_small_full_load_workload(
        "vault-small-96-v1", scenario,
        generator_source_sha256="1" * 64, semantic_source_sha256="2" * 64,
    )


def _fresh_binding(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    name = "tests.performance._native_binding_fresh"
    path = Path(__file__).parent / "performance/decision_native_binding.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


def test_import_and_collection_are_inert(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        events.append("unexpected effect")
        raise AssertionError("binding performed preparation during import")

    native_import = builtins.__import__

    def guarded_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "logseq_matryca_parser" or name.startswith("logseq_matryca_parser."):
            return forbidden()
        return native_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    monkeypatch.setattr(os, "cpu_count", forbidden)
    monkeypatch.setattr(time, "perf_counter_ns", forbidden)
    monkeypatch.setattr(tempfile, "TemporaryDirectory", forbidden)
    monkeypatch.setattr(decision_vault, "build_decision_vault", forbidden)
    monkeypatch.setattr(decision_semantics, "expected_small_graph", forbidden)
    module = _fresh_binding(monkeypatch)
    context = module.NativeSmallLoadContext(_workload())
    assert context.state == "new"
    assert context.cleanup_status == "not_acquired"
    assert events == []


class _FakeGraph:
    def __init__(self, root: Path) -> None:
        self.graph_path = root


class _Harness:
    """Keep native/semantic effects fake; exercise actual owned synthetic bytes."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, sandbox: Path) -> None:
        self.module = _binding()
        self.monkeypatch = monkeypatch
        self.sandbox = sandbox
        self.counts = dict.fromkeys(("resolve", "build", "owner", "materialize", "expected", "load", "observe", "cleanup"), 0)
        self.events: list[str] = []
        self.roots: list[Path] = []
        self.recovery: list[Any] = []
        self.expectation = object()
        self.cap: Any = 7
        self.load_action: Any = None
        self.observe_action: Any = None
        self.materialize_action: Any = None
        self.build_action: Any = None
        self.expected_error: BaseException | None = None
        self.owner_error: BaseException | None = None
        self.cleanup_error: BaseException | None = None
        self.cleanup_noop = False
        for name, callback in (
            ("_resolve_native", self.resolve), ("build_decision_vault", self.build),
            ("TemporaryDirectory", self.owner), ("_materialize", self.materialize),
            ("expected_small_graph", self.expected), ("observe_small_graph", self.observe),
        ):
            monkeypatch.setattr(self.module, name, callback, raising=False)

    def resolve(self) -> Any:
        self.counts["resolve"] += 1
        return self.module._NativeLoader(self.load, self.cap)

    def build(self, profile: str) -> Any:
        assert profile == "vault-small-96-v1"
        self.counts["build"] += 1
        self.events.append("build")
        source = decision_vault.build_decision_vault(profile)
        return self.build_action(source) if self.build_action else source

    def owner(self, **options: Any) -> Any:
        assert options == {
            "prefix": "matryca-decision-small-", "ignore_cleanup_errors": False, "delete": True,
        }
        self.counts["owner"] += 1
        if self.owner_error is not None:
            raise self.owner_error
        owner = tempfile.TemporaryDirectory(dir=self.sandbox, **options)
        cleanup = owner.cleanup
        self.recovery.append(cleanup)
        self.roots.append(Path(owner.name).resolve())

        def counted_cleanup() -> None:
            self.counts["cleanup"] += 1
            self.events.append("cleanup")
            if not self.cleanup_noop:
                cleanup()
            if self.cleanup_error is not None:
                raise self.cleanup_error

        self.monkeypatch.setattr(owner, "cleanup", counted_cleanup)
        return owner

    def materialize(self, source: Any, root: Path) -> Path:
        self.counts["materialize"] += 1
        self.events.append("materialize")
        result = source.materialize(root)
        if self.materialize_action:
            return self.materialize_action(source, root)
        return result

    def expected(self) -> Any:
        self.counts["expected"] += 1
        self.events.append("expected")
        if self.expected_error is not None:
            raise self.expected_error
        return self.expectation

    def load(self, root: Path, *, strict_refs: bool, strict_title_collisions: bool) -> Any:
        assert (strict_refs, strict_title_collisions) == (False, False)
        assert root == self.roots[-1]
        self.counts["load"] += 1
        self.events.append("load")
        return self.load_action(root) if self.load_action else _FakeGraph(root)

    def observe(self, graph: Any, *, graph_root: Path) -> Any:
        assert graph_root == self.roots[-1]
        self.counts["observe"] += 1
        self.events.append("observe")
        if self.observe_action:
            return self.observe_action(graph, graph_root)
        if graph.graph_path != graph_root:
            raise AssertionError("small workload semantic mismatch")
        return self.expectation

    def context(self, scenario: str = "full_load_cold_instance") -> Any:
        return self.module.NativeSmallLoadContext(_workload(scenario))


@pytest.fixture
def harness(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[_Harness]:
    data = _Harness(monkeypatch, tmp_path)
    try:
        yield data
    finally:
        # Test-owned recovery is separate from the binding's explicit one-attempt policy.
        for cleanup in data.recovery:
            if Path(cleanup.__self__.name).exists():
                cleanup()


def test_fixed_source_prepared_once(harness: _Harness) -> None:
    from tests.performance.comparison_contract import ExecutorShape

    context = harness.context()
    with context:
        assert context.state == "ready"
        assert context.executor == ExecutorShape("threads_current", 7, "none")
        assert harness.counts == {
            "resolve": 1, "build": 1, "owner": 1, "materialize": 1,
            "expected": 1, "load": 0, "observe": 0, "cleanup": 0,
        }
        files = sorted(harness.roots[0].rglob("*.md"))
        assert len(files) == 96
        assert sum(path.stat().st_size for path in files) == 1107557
    assert (context.state, context.cleanup_status) == ("closed", "succeeded")
    assert harness.counts["cleanup"] == 1 and not harness.roots[0].exists()


@pytest.mark.parametrize("cap", [1, 32, True, False, 0, 33, 1.5, "7", None])
def test_imported_cap_is_exact(harness: _Harness, cap: Any) -> None:
    harness.cap = cap
    context = harness.context()
    if type(cap) is int and cap in (1, 32):
        with context:
            assert context.executor.workers == cap
    else:
        with pytest.raises(RuntimeError, match="^invalid native small-load executor$"):
            context.__enter__()
        assert (context.state, context.cleanup_status) == ("failed", "not_acquired")
        assert harness.counts["build"] == harness.counts["owner"] == 0


@pytest.mark.parametrize("case", [
    "missing", "extra", "changed", "truncated", "oversized", "directory-file",
    "extra-directory", "extra-root", "symlink-file", "symlink-pages", "symlink-root",
    "reparse-file", "unreadable-stat", "unreadable-inventory", "unreadable-bytes",
    "wrong-materializer-root",
])
def test_source_integrity_rejects_drift(harness: _Harness, case: str) -> None:
    import stat
    from types import SimpleNamespace

    def mutate(source: Any, root: Path) -> Path:
        target = root / "pages/runtime-evidence-page-0001.md"
        if case == "missing":
            target.unlink()
        elif case == "extra":
            (root / "pages/extra.md").write_bytes(b"unexpected")
        elif case == "changed":
            target.write_bytes(b"x" * target.stat().st_size)
        elif case == "truncated":
            target.write_bytes(b"")
        elif case == "oversized":
            with target.open("ab") as stream:
                stream.write(b"x")
        elif case == "directory-file":
            target.unlink()
            target.mkdir()
        elif case == "extra-directory":
            (root / "pages/extra").mkdir()
        elif case == "extra-root":
            (root / "other").mkdir()
        elif case == "wrong-materializer-root":
            return root.parent
        else:
            lstat = harness.module.lstat
            scandir = harness.module.scandir
            if case.startswith("symlink"):
                selected = root if case == "symlink-root" else root / "pages" if case == "symlink-pages" else target

                def fake_stat(path: Any) -> Any:
                    result = lstat(path)
                    if Path(path) == selected:
                        return SimpleNamespace(st_mode=stat.S_IFLNK | 0o777, st_file_attributes=0)
                    return result

                harness.monkeypatch.setattr(harness.module, "lstat", fake_stat)
            elif case == "reparse-file":
                def reparse(path: Any) -> Any:
                    result = lstat(path)
                    if Path(path) == target:
                        return SimpleNamespace(st_mode=result.st_mode, st_file_attributes=0x400)
                    return result
                harness.monkeypatch.setattr(harness.module, "lstat", reparse)
            elif case == "unreadable-stat":
                def denied_stat(path: Any) -> Any:
                    if Path(path) == target:
                        raise PermissionError("private fake path")
                    return lstat(path)
                harness.monkeypatch.setattr(harness.module, "lstat", denied_stat)
            elif case == "unreadable-inventory":
                def denied_scan(path: Any) -> Any:
                    if Path(path) == root / "pages":
                        raise PermissionError("private fake inventory")
                    return scandir(path)
                harness.monkeypatch.setattr(harness.module, "scandir", denied_scan)
            elif case == "unreadable-bytes":
                def denied_open(*args: Any, **kwargs: Any) -> Any:
                    raise PermissionError("private fake bytes")
                harness.monkeypatch.setattr(harness.module, "open", denied_open, raising=False)
        return root

    harness.materialize_action = mutate
    context = harness.context()
    with pytest.raises(RuntimeError, match="^native small-load source integrity failure$"):
        context.__enter__()
    assert context.state == "failed"
    assert context.cleanup_status == "succeeded"
    assert harness.counts["cleanup"] == 1
    assert harness.counts["load"] == harness.counts["expected"] == 0


@pytest.mark.parametrize("case", ["duplicate", "unsorted", "escape", "wrong-count", "wrong-bytes", "boolean-count"])
def test_in_memory_source_rejected_before_owner(harness: _Harness, case: str) -> None:
    from dataclasses import replace
    from pathlib import PurePosixPath

    def corrupt(source: Any) -> Any:
        if case == "duplicate":
            return replace(source, files=(source.files[0], *source.files[:-1]))
        if case == "unsorted":
            return replace(source, files=tuple(reversed(source.files)))
        if case == "escape":
            return replace(source, files=((PurePosixPath("../escape.md"), source.files[0][1]), *source.files[1:]))
        if case == "wrong-count":
            return replace(source, page_count=95)
        if case == "boolean-count":
            return replace(source, page_count=True)
        return replace(source, files=((source.files[0][0], b"x"), *source.files[1:]))

    harness.build_action = corrupt
    context = harness.context()
    with pytest.raises(RuntimeError, match="^native small-load source integrity failure$"):
        context.__enter__()
    assert (context.state, context.cleanup_status) == ("failed", "not_acquired")
    assert harness.counts["owner"] == harness.counts["cleanup"] == 0



@pytest.mark.parametrize("case", [
    "none", "mapping", "missing", "subclass", "boolean-version", "scale", "scenario",
])
def test_invalid_workload_precedes_all_effects(
    monkeypatch: pytest.MonkeyPatch, case: str,
) -> None:
    module = _binding()
    events: list[str] = []

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        events.append("effect")
        raise AssertionError("invalid workload reached a side effect")

    for name in ("_resolve_native", "build_decision_vault", "TemporaryDirectory", "expected_small_graph"):
        monkeypatch.setattr(module, name, forbidden)
    if case in ("none", "mapping"):
        value: Any = None if case == "none" else {}
    else:
        class Derived(SmallFullLoadWorkload):
            pass

        value = object.__new__(Derived if case == "subclass" else SmallFullLoadWorkload)
        if case != "missing":
            fields = {
                "schema": "matryca-small-full-load-workload", "schema_version": 1,
                "profile_id": "vault-small-96-v1", "scenario": "full_load_cold_instance",
                "generator_source_sha256": "1" * 64, "semantic_source_sha256": "2" * 64,
            }
            if case == "boolean-version":
                fields["schema_version"] = True
            elif case == "scale":
                fields["profile_id"] = "vault-scale-1000-v1"
            elif case == "scenario":
                fields["scenario"] = "arbitrary"
            for name, field in fields.items():
                object.__setattr__(value, name, field)
    with pytest.raises((TypeError, ValueError), match="^invalid small workload input$"):
        module.NativeSmallLoadContext(value)
    assert events == []


def test_load_callback_contains_only_declared_bookkeeping(harness: _Harness) -> None:
    context = harness.context()
    with context:
        verify_source = harness.module._verify_source

        def outside_interval(*args: Any) -> None:
            assert context.state != "loading"
            verify_source(*args)

        harness.monkeypatch.setattr(harness.module, "_verify_source", outside_interval)

        def load(root: Path) -> _FakeGraph:
            assert context.state == "loading"
            assert harness.counts["cleanup"] == 0
            assert harness.counts["observe"] == harness.counts["load"] - 1
            return _FakeGraph(root)

        harness.load_action = load
        first = context.load_fresh()
        assert context.state == "ready"
        with pytest.raises(RuntimeError, match="^native small-load lifecycle violation$"):
            context.load_fresh()
        assert harness.counts["load"] == 1
        assert context.verify_graph(first) is None
        second = context.load_fresh()
        assert first is not second
        assert context.verify_graph(second) is None
        assert harness.events == ["build", "materialize", "expected", "load", "observe", "load", "observe"]
    assert harness.counts["cleanup"] == 1


def test_post_load_disk_drift_precedes_graph_oracle(harness: _Harness) -> None:
    context = harness.context()
    with pytest.raises(RuntimeError, match="^native small-load source integrity failure$"):
        with context:
            graph = context.load_fresh()
            (harness.roots[0] / "pages/runtime-evidence-page-0001.md").write_bytes(b"drift")
            context.verify_graph(graph)
    assert harness.counts["observe"] == 0
    assert (context.state, context.cleanup_status) == ("failed", "succeeded")


@pytest.mark.parametrize("case", ["pass", "different", "oracle-assertion", "foreign-root"])
def test_verifier_uses_precomputed_independent_expectation(harness: _Harness, case: str) -> None:
    context = harness.context()
    failure = AssertionError("small workload semantic mismatch")

    def projection(graph: Any, root: Path) -> Any:
        assert context.state == "verifying"
        if case == "oracle-assertion":
            raise failure
        return object() if case == "different" else harness.expectation

    if case != "foreign-root":
        harness.observe_action = projection
    if case == "foreign-root":
        harness.load_action = lambda root: _FakeGraph(root.parent)
    if case == "pass":
        with context:
            graph = context.load_fresh()
            assert context.verify_graph(graph) is None
    else:
        with pytest.raises(AssertionError, match="^small workload semantic mismatch$") as caught:
            with context:
                context.verify_graph(context.load_fresh())
        if case == "oracle-assertion":
            assert caught.value is failure
    assert harness.counts["expected"] == 1 and harness.counts["observe"] == 1


def _foreign_call(callback: Any) -> BaseException | None:
    from threading import Thread

    errors: list[BaseException] = []

    def run() -> None:
        try:
            callback()
        except BaseException as error:
            errors.append(error)

    thread = Thread(target=run, daemon=True)
    thread.start()
    thread.join(5)
    assert not thread.is_alive()
    return errors[0] if errors else None


@pytest.mark.parametrize("action", ["entry", "load", "verify", "close", "exit", "executor"])
def test_owner_and_state_guards(harness: _Harness, action: str) -> None:
    context = harness.context()
    with context:
        callbacks = {
            "entry": context.__enter__, "load": context.load_fresh,
            "verify": lambda: context.verify_graph(None), "close": context.close,
            "exit": lambda: context.__exit__(None, None, None), "executor": lambda: context.executor,
        }
        error = _foreign_call(callbacks[action])
        assert type(error) is RuntimeError and str(error) == "native small-load lifecycle violation"
        assert context.state == "ready" and harness.counts["cleanup"] == 0
        with pytest.raises(RuntimeError, match="^native small-load lifecycle violation$"):
            context.__enter__()
    assert (context.state, harness.counts["cleanup"]) == ("closed", 1)


@pytest.mark.parametrize("phase", ["loading", "verifying"])
@pytest.mark.parametrize("action", ["load", "close", "exit", "entry"])
def test_busy_callback_rejects_reentry_without_cleanup(
    harness: _Harness, phase: str, action: str,
) -> None:
    context = harness.context()

    def rejected() -> None:
        callbacks = {
            "load": context.load_fresh, "close": context.close,
            "exit": lambda: context.__exit__(None, None, None), "entry": context.__enter__,
        }
        with pytest.raises(RuntimeError, match="^native small-load lifecycle violation$"):
            callbacks[action]()
        assert context.state == phase and harness.counts["cleanup"] == 0

    def load(root: Path) -> _FakeGraph:
        if phase == "loading":
            rejected()
        return _FakeGraph(root)

    def observe(graph: Any, root: Path) -> Any:
        if phase == "verifying":
            rejected()
        return harness.expectation

    harness.load_action, harness.observe_action = load, observe
    with context:
        context.verify_graph(context.load_fresh())
    assert harness.counts["cleanup"] == 1


def test_concurrent_first_entry_claims_one_owner(harness: _Harness) -> None:
    from threading import Barrier, Event, Thread

    context = harness.context()
    barrier, entered, rejected, release = Barrier(2), Event(), Event(), Event()
    outcomes: list[str] = []
    errors: list[BaseException] = []

    def run() -> None:
        try:
            barrier.wait(5)
            with context:
                outcomes.append("owner")
                entered.set()
                assert release.wait(5)
        except RuntimeError as error:
            if str(error) == "native small-load lifecycle violation":
                outcomes.append("rejected")
                rejected.set()
            else:
                errors.append(error)
        except BaseException as error:
            errors.append(error)

    threads = [Thread(target=run, daemon=True) for _ in range(2)]
    for thread in threads:
        thread.start()
    try:
        assert entered.wait(5) and rejected.wait(5)
    finally:
        release.set()
        for thread in threads:
            thread.join(5)
    assert not any(thread.is_alive() for thread in threads)
    assert not errors and sorted(outcomes) == ["owner", "rejected"]
    assert harness.counts["build"] == harness.counts["owner"] == harness.counts["cleanup"] == 1


def test_closed_and_unentered_context_reject_use(harness: _Harness) -> None:
    context = harness.context()
    for callback in (context.load_fresh, lambda: context.verify_graph(None), lambda: context.executor):
        with pytest.raises(RuntimeError, match="^native small-load lifecycle violation$"):
            callback()
    with context:
        pass
    context.close()
    for callback in (context.__enter__, context.load_fresh, lambda: context.verify_graph(None), lambda: context.executor):
        with pytest.raises(RuntimeError, match="^native small-load lifecycle violation$"):
            callback()
    assert context.state == "closed" and harness.counts["cleanup"] == 1


def test_unverified_result_cannot_exit_successfully(harness: _Harness) -> None:
    context = harness.context()
    with pytest.raises(RuntimeError, match="^native small-load verification pending$"):
        with context:
            graph = context.load_fresh()
            assert graph.graph_path == harness.roots[0]
    assert (context.state, context.cleanup_status, harness.counts["cleanup"]) == ("failed", "succeeded", 1)


class _Abort(BaseException):
    pass


@pytest.mark.parametrize("stage", ["preparation", "load", "disk", "oracle", "body"])
@pytest.mark.parametrize("error_type", [ValueError, TypeError, KeyboardInterrupt, SystemExit, _Abort])
@pytest.mark.parametrize("cofailure", [False, True])
def test_failure_and_cleanup_precedence(
    harness: _Harness, stage: str, error_type: type[BaseException], cofailure: bool,
) -> None:
    primary = error_type("controlled primary")
    original_cause, original_context = ValueError("cause"), RuntimeError("context")
    primary.__cause__, primary.__context__ = original_cause, original_context
    secondary = PermissionError("controlled private cleanup")
    context = harness.context()

    def fail(*args: Any) -> Any:
        raise primary

    if stage == "preparation":
        harness.expected_error = primary
    elif stage == "load":
        harness.load_action = fail
    elif stage == "oracle":
        harness.observe_action = fail
    elif stage == "disk":
        real_verify = harness.module._verify_source

        def disk(*args: Any) -> None:
            if context.state == "verifying":
                fail()
            real_verify(*args)

        harness.monkeypatch.setattr(harness.module, "_verify_source", disk)
    if cofailure:
        harness.cleanup_error = secondary
    with pytest.raises(BaseException) as caught:
        with context:
            if stage == "body":
                fail()
            context.verify_graph(context.load_fresh())
    assert caught.value is primary
    assert primary.__cause__ is original_cause and primary.__context__ is original_context
    assert context.state == "failed" and harness.counts["cleanup"] == 1
    assert context.cleanup_status == ("failed" if cofailure else "succeeded")
    if cofailure:
        assert context.cleanup_error is secondary
        assert primary.__dict__["_matryca_native_small_cleanup_error"] is secondary
        assert primary.__notes__.count("native small-load cleanup failed; secondary exception retained privately") == 1
    with pytest.raises(RuntimeError, match="^native small-load binding failed$"):
        context.close()
    assert context.__exit__(type(primary), primary, primary.__traceback__) is False
    assert harness.counts["cleanup"] == 1


@pytest.mark.parametrize("error_type", [PermissionError, KeyboardInterrupt, SystemExit, _Abort])
def test_cleanup_only_failure_remains_original(harness: _Harness, error_type: type[BaseException]) -> None:
    error = error_type("controlled cleanup")
    harness.cleanup_error = error
    context = harness.context()
    with pytest.raises(BaseException) as caught:
        with context:
            pass
    assert caught.value is error and context.cleanup_error is error
    assert (context.state, context.cleanup_status, harness.counts["cleanup"]) == ("failed", "failed", 1)
    with pytest.raises(RuntimeError, match="^native small-load binding failed$"):
        context.close()
    assert harness.counts["cleanup"] == 1


def test_cleanup_requires_positive_absence(harness: _Harness) -> None:
    harness.cleanup_noop = True
    context = harness.context()
    with pytest.raises(RuntimeError, match="^native small-load cleanup unconfirmed$"):
        with context:
            pass
    assert harness.roots[0].exists()
    assert (context.state, context.cleanup_status, harness.counts["cleanup"]) == ("failed", "failed", 1)


def test_caught_operation_error_cannot_restore_success(harness: _Harness) -> None:
    error = ValueError("controlled load")

    def fail(root: Path) -> Any:
        raise error

    harness.load_action = fail
    context = harness.context()
    with pytest.raises(RuntimeError, match="^native small-load binding failed$"):
        with context:
            with pytest.raises(ValueError) as caught:
                context.load_fresh()
            assert caught.value is error and context.state == "failed"
    assert context.cleanup_status == "succeeded" and harness.counts["cleanup"] == 1


@pytest.mark.parametrize("dead", [False, True])
@pytest.mark.parametrize("none_argument", [False, True])
def test_pending_reference_rejects_dead_or_foreign_result(
    harness: _Harness, dead: bool, none_argument: bool,
) -> None:
    from weakref import ref

    harness.monkeypatch.setattr(harness.module, "id", lambda value: 1, raising=False)
    context = harness.context()
    with pytest.raises(RuntimeError, match="^native small-load result identity mismatch$"):
        with context:
            graph = context.load_fresh()
            reference = ref(graph)
            if dead:
                del graph
                assert reference() is None
            with pytest.raises(RuntimeError, match="^native small-load lifecycle violation$"):
                context.load_fresh()
            context.verify_graph(None if none_argument else _FakeGraph(harness.roots[0]))
    assert harness.counts["observe"] == 0 and harness.counts["load"] == 1
    assert (context.state, context.cleanup_status) == ("failed", "succeeded")


def test_non_weak_referenceable_result_fails_closed(harness: _Harness) -> None:
    harness.load_action = lambda root: object()
    context = harness.context()
    with pytest.raises(RuntimeError, match="^native small-load result is not weak-referenceable$"):
        with context:
            context.load_fresh()
    assert context.state == "failed" and harness.counts["observe"] == 0
    assert harness.counts["cleanup"] == 1


@pytest.mark.parametrize("verified", [False, True])
def test_binding_does_not_retain_successful_graphs(harness: _Harness, verified: bool) -> None:
    from weakref import ref

    context = harness.context()
    if verified:
        with context:
            graph = context.load_fresh()
            reference = ref(graph)
            context.verify_graph(graph)
            del graph
            assert reference() is None
            with pytest.raises(RuntimeError, match="^native small-load lifecycle violation$"):
                context.verify_graph(None)
    else:
        with pytest.raises(RuntimeError, match="^native small-load verification pending$"):
            with context:
                graph = context.load_fresh()
                reference = ref(graph)
                del graph
                assert reference() is None
    assert harness.counts["cleanup"] == 1


@pytest.mark.parametrize("scenario", ["full_load_cold_instance", "full_load_unchanged_repeat"])
def test_same_preparation_for_both_scenarios(harness: _Harness, scenario: str) -> None:
    with harness.context(scenario):
        assert harness.counts["build"] == harness.counts["materialize"] == harness.counts["expected"] == 1
        assert harness.counts["load"] == harness.counts["observe"] == 0


def test_resolver_captures_imported_rule_without_cpu_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _binding()
    package: Any = ModuleType("logseq_matryca_parser")
    graph_module: Any = ModuleType("logseq_matryca_parser.graph")

    class FakeNative:
        @classmethod
        def load_directory(cls, root: Path, **options: bool) -> Any:
            raise AssertionError("resolver must not call the loader")

    graph_module.LogseqGraph, graph_module._DEFAULT_MAX_WORKERS = FakeNative, 19
    package.graph, package.__path__ = graph_module, []
    monkeypatch.setitem(sys.modules, "logseq_matryca_parser", package)
    monkeypatch.setitem(sys.modules, "logseq_matryca_parser.graph", graph_module)

    def forbidden() -> Any:
        raise AssertionError("resolver recomputed CPU count")

    monkeypatch.setattr(os, "cpu_count", forbidden)
    resolved = module._resolve_native()
    assert resolved.max_workers == 19
    assert resolved.load_directory.__self__ is FakeNative


def test_cleanup_cofailure_preserves_original_and_secondary(harness: _Harness) -> None:
    primary, secondary = _Abort("entry abort"), PermissionError("cleanup")
    harness.expected_error, harness.cleanup_error = primary, secondary
    context = harness.context()
    with pytest.raises(_Abort) as caught:
        context.__enter__()
    assert caught.value is primary
    assert primary.__dict__["_matryca_native_small_cleanup_error"] is secondary
    assert context.cleanup_error is secondary
    assert (context.state, context.cleanup_status, harness.counts["cleanup"]) == ("failed", "failed", 1)
    assert harness.counts["load"] == 0


def test_entry_revalidates_forged_metadata_before_effects(harness: _Harness) -> None:
    workload = _workload()
    context = harness.module.NativeSmallLoadContext(workload)
    object.__setattr__(workload, "schema_version", True)
    with pytest.raises(TypeError, match="^invalid small workload input$"):
        context.__enter__()
    assert context.state == "failed" and context.cleanup_status == "not_acquired"
    assert not any(harness.counts.values())


def test_noncallable_native_loader_precedes_owner(harness: _Harness) -> None:
    harness.monkeypatch.setattr(
        harness.module, "_resolve_native", lambda: harness.module._NativeLoader(None, 7),
    )
    context = harness.context()
    with pytest.raises(RuntimeError, match="^invalid native small-load executor$"):
        context.__enter__()
    assert harness.counts["owner"] == harness.counts["build"] == 0


def test_binding_releases_observed_projection(harness: _Harness) -> None:
    from weakref import ref

    observations: list[Any] = []

    class EqualProjection:
        def __eq__(self, other: object) -> bool:
            return other is harness.expectation

    def observe(graph: Any, root: Path) -> Any:
        projection = EqualProjection()
        observations.append(ref(projection))
        return projection

    harness.observe_action = observe
    with harness.context() as context:
        graph = context.load_fresh()
        context.verify_graph(graph)
        assert observations[0]() is None


def test_closed_context_body_error_never_cleans_twice(harness: _Harness) -> None:
    primary = _Abort("body after explicit close")
    context = harness.context()
    with pytest.raises(_Abort) as caught:
        with context:
            context.close()
            raise primary
    assert caught.value is primary and context.state == "failed"
    assert context.cleanup_status == "succeeded" and harness.counts["cleanup"] == 1


def _fresh_opt_in(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    name = "tests.performance._native_checks_fresh"
    path = Path(__file__).parent / "performance/decision_native_small_checks.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


def test_opt_in_native_file_is_not_default_collection(request: pytest.FixtureRequest) -> None:
    from fnmatch import fnmatchcase

    name = "decision_native_small_checks.py"
    assert (Path(__file__).parent / "performance" / name).is_file()
    assert not any(fnmatchcase(name, pattern) for pattern in request.config.getini("python_files"))
    assert not any(item.path.name == name for item in request.session.items)


def test_opt_in_collection_does_not_resolve_or_prepare(tmp_path: Path) -> None:
    import json
    import subprocess

    code = r"""
import builtins, json, pytest
from tests.performance import decision_native_binding as binding
events = []
def denied(*args, **kwargs):
    events.append("effect")
    raise AssertionError("native selection executed during collection")
for name in ("_resolve_native", "build_decision_vault", "TemporaryDirectory", "expected_small_graph"):
    setattr(binding, name, denied)
original_import = builtins.__import__
def guarded(name, *args, **kwargs):
    if name == "logseq_matryca_parser" or name.startswith("logseq_matryca_parser."):
        return denied()
    return original_import(name, *args, **kwargs)
builtins.__import__ = guarded
class Probe:
    items = ()
    def pytest_collection_finish(self, session):
        self.items = tuple(item.nodeid for item in session.items)
probe = Probe()
result = pytest.main(["--collect-only", "--noconftest", "-q",
    "tests/performance/decision_native_small_checks.py"], plugins=[probe])
print("COLLECTION_RESULT:" + json.dumps({"exit": int(result), "effects": events, "items": probe.items}))
"""
    child_env = dict(os.environ)
    for name in tuple(child_env):
        if name.startswith("COV_CORE_") or name in ("COVERAGE_PROCESS_START", "PYTHONPATH", "MYPYPATH"):
            child_env.pop(name)
    child_env.update({
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1",
        "PYTEST_ADDOPTS": (
            f'-o cache_dir="{tmp_path / "cache"}" --basetemp="{tmp_path / "pytest"}" '
            f'--junitxml="{tmp_path / "collection.xml"}"'
        ),
        "COVERAGE_FILE": str(tmp_path / "coverage"),
        "TMPDIR": str(tmp_path), "TMP": str(tmp_path), "TEMP": str(tmp_path),
    })
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[1],
        env=child_env, capture_output=True, text=True, timeout=30, check=False,
    )
    lines = [line for line in result.stdout.splitlines() if line.startswith("COLLECTION_RESULT:")]
    assert result.returncode == 0 and len(lines) == 1, result.stderr[-1000:]
    data = json.loads(lines[0].removeprefix("COLLECTION_RESULT:"))
    assert data["exit"] == 0 and data["effects"] == []
    assert len(data["items"]) == len(set(data["items"])) == 3
    assert all("decision_native_small_checks.py::test_" in name for name in data["items"])


@pytest.mark.parametrize("case", [
    "autoload", "worker", "xdist", "xdist.plugin", "repeat", "pytest_repeat",
    "rerunfailures", "pytest_rerunfailures", "second-entry",
])
def test_native_selection_guard_fails_before_preparation(
    monkeypatch: pytest.MonkeyPatch, case: str,
) -> None:
    from types import SimpleNamespace

    module = _fresh_opt_in(monkeypatch)
    events: list[str] = []

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        events.append("effect")
        raise AssertionError("guard reached native preparation")

    binding = _binding()
    for name in ("_resolve_native", "build_decision_vault", "TemporaryDirectory", "expected_small_graph"):
        monkeypatch.setattr(binding, name, forbidden)
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    if case == "autoload":
        monkeypatch.delenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD")
    config = SimpleNamespace(pluginmanager=SimpleNamespace(hasplugin=lambda name: name == case))
    if case == "worker":
        config.workerinput = {}
    if case == "second-entry":
        assert module._claim_native_selection(config) is None
    with pytest.raises(RuntimeError, match="^native small-load correctness selection rejected$"):
        module._claim_native_selection(config)
    assert events == []
