"""Explicit, unmeasured small-fixture binding; never execution admission."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from os import lstat, scandir
from pathlib import Path, PurePosixPath
from stat import S_ISDIR, S_ISREG
from tempfile import TemporaryDirectory
from threading import Lock, Thread, current_thread
from types import TracebackType
from typing import TYPE_CHECKING, Literal, NoReturn, Protocol, Self
from weakref import ReferenceType, ref

from tests.performance.comparison_contract import ExecutorShape
from tests.performance.decision_semantics import (
    SmallGraphProjection,
    expected_small_graph,
    observe_small_graph,
)
from tests.performance.decision_vault import build_decision_vault
from tests.performance.decision_workload import SmallFullLoadWorkload, workload_payload
from tests.performance.synthetic_vault import SyntheticVault

if TYPE_CHECKING:
    from logseq_matryca_parser.graph import LogseqGraph

type BindingState = Literal["new", "preparing", "ready", "loading", "verifying", "failed", "closed"]
type CleanupStatus = Literal["not_acquired", "pending", "succeeded", "failed"]


class _LoadDirectory(Protocol):
    def __call__(
        self, graph_path: Path, *, strict_refs: bool, strict_title_collisions: bool,
    ) -> LogseqGraph: ...


@dataclass(frozen=True, slots=True)
class _NativeLoader:
    load_directory: _LoadDirectory
    max_workers: int


def _resolve_native() -> _NativeLoader:
    from logseq_matryca_parser import graph

    return _NativeLoader(graph.LogseqGraph.load_directory, graph._DEFAULT_MAX_WORKERS)


def _integrity_failure() -> NoReturn:
    raise RuntimeError("native small-load source integrity failure") from None


def _validate_source(source: SyntheticVault) -> None:
    if type(source) is not SyntheticVault or type(source.files) is not tuple:
        _integrity_failure()
    if any(type(value) is not int for value in (
        source.page_count, source.blocks_per_page, source.deep_chain_depth,
    )) or (source.page_count, source.blocks_per_page, source.deep_chain_depth) != (96, 24, 1024):
        _integrity_failure()
    if len(source.files) != 96:
        _integrity_failure()
    for entry in source.files:
        if (type(entry) is not tuple or len(entry) != 2
                or type(entry[0]) is not PurePosixPath or type(entry[1]) is not bytes):
            _integrity_failure()
    names = tuple(name.as_posix() for name, _ in source.files)
    expected = ("pages/runtime-evidence-deep.md", *(
        f"pages/runtime-evidence-page-{index:04d}.md" for index in range(1, 96)
    ))
    if (names != expected or source.total_source_bytes != 1107557
            or source.source_sha256 != "adcbc2e2085aad2533ad5f9f5961c0525b291ad4fd47a89eb7ac42ab7b77e583"):
        _integrity_failure()


def _check_kind(path: Path, *, directory: bool) -> None:
    metadata = lstat(path)
    if (getattr(metadata, "st_file_attributes", 0) & 0x400
            or not (S_ISDIR(metadata.st_mode) if directory else S_ISREG(metadata.st_mode))):
        _integrity_failure()


def _names(path: Path, maximum: int) -> set[str]:
    names: set[str] = set()
    with scandir(path) as entries:
        for entry in entries:
            names.add(entry.name)
            if len(names) > maximum:
                _integrity_failure()
    return names


def _materialize(source: SyntheticVault, root: Path) -> Path:
    return source.materialize(root)


def _verify_source(root: Path, source: SyntheticVault) -> None:
    try:
        _check_kind(root, directory=True)
        if _names(root, 1) != {"pages"}:
            _integrity_failure()
        pages = root / "pages"
        _check_kind(pages, directory=True)
        if _names(pages, 96) != {name.name for name, _ in source.files}:
            _integrity_failure()
        digest = sha256()
        total = 0
        for relative, expected in source.files:
            target = root / relative
            _check_kind(target, directory=False)
            with open(target, "rb") as stream:
                content = stream.read(len(expected) + 1)
            if content != expected:
                _integrity_failure()
            total += len(content)
            digest.update(relative.as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(content)
            digest.update(b"\0")
        if (total != 1107557 or digest.hexdigest()
                != "adcbc2e2085aad2533ad5f9f5961c0525b291ad4fd47a89eb7ac42ab7b77e583"):
            _integrity_failure()
    except OSError:
        _integrity_failure()


class NativeSmallLoadContext:
    """Private single-use owner; construction validates metadata only."""

    def __init__(self, workload: SmallFullLoadWorkload) -> None:
        workload_payload(workload)
        self._workload = workload
        self._state: BindingState = "new"
        self._cleanup_status: CleanupStatus = "not_acquired"
        self._entry_claim = Lock()
        self._owner_thread: Thread | None = None
        self._native: _NativeLoader | None = None
        self._source: SyntheticVault | None = None
        self._root: Path | None = None
        self._expected: SmallGraphProjection | None = None
        self._owner: TemporaryDirectory[str] | None = None
        self._cleanup_attempted = False
        self._cleanup_error: BaseException | None = None
        self._pending: ReferenceType[LogseqGraph] | None = None

    def __enter__(self) -> Self:
        if not self._entry_claim.acquire(blocking=False):
            raise RuntimeError("native small-load lifecycle violation")
        try:
            if self._state != "new":
                raise RuntimeError("native small-load lifecycle violation")
            try:
                workload_payload(self._workload)
            except BaseException:
                self._state = "failed"
                raise
            self._owner_thread = current_thread()
            self._state = "preparing"
        finally:
            self._entry_claim.release()
        try:
            native = _resolve_native()
            if (not callable(native.load_directory) or type(native.max_workers) is not int
                    or not 1 <= native.max_workers <= 32):
                raise RuntimeError("invalid native small-load executor")
            self._native = native
            source = build_decision_vault("vault-small-96-v1")
            _validate_source(source)
            self._source = source
            self._owner = TemporaryDirectory(
                prefix="matryca-decision-small-", ignore_cleanup_errors=False, delete=True,
            )
            self._cleanup_status = "pending"
            root = Path(self._owner.name).resolve()
            self._root = root
            try:
                _check_kind(root, directory=True)
                if _names(root, 0) or _materialize(source, root) != root:
                    _integrity_failure()
                _verify_source(root, source)
            except OSError:
                _integrity_failure()
            self._expected = expected_small_graph()
            self._state = "ready"
            return self
        except BaseException as primary:
            self._state = "failed"
            self._finalize(primary)
            raise

    def _require_owner(self) -> None:
        if current_thread() is not self._owner_thread:
            raise RuntimeError("native small-load lifecycle violation")

    def load_fresh(self) -> LogseqGraph:
        self._require_owner()
        if (self._state != "ready" or self._pending is not None
                or self._native is None or self._root is None):
            raise RuntimeError("native small-load lifecycle violation")
        self._state = "loading"
        result: LogseqGraph | None = None
        try:
            result = self._native.load_directory(
                self._root, strict_refs=False, strict_title_collisions=False,
            )
            try:
                self._pending = ref(result)
            except TypeError:
                raise RuntimeError("native small-load result is not weak-referenceable") from None
            self._state = "ready"
            return result
        except BaseException:
            self._state = "failed"
            self._pending = None
            raise
        finally:
            result = None

    def verify_graph(self, graph: LogseqGraph) -> None:
        self._require_owner()
        if (self._state != "ready" or self._pending is None
                or self._root is None or self._source is None):
            raise RuntimeError("native small-load lifecycle violation")
        live: LogseqGraph | None = None
        observed: SmallGraphProjection | None = None
        try:
            live = self._pending()
            if live is None or live is not graph:
                raise RuntimeError("native small-load result identity mismatch")
            self._state = "verifying"
            _verify_source(self._root, self._source)
            observed = observe_small_graph(graph, graph_root=self._root)
            if observed != self._expected:
                raise AssertionError("small workload semantic mismatch") from None
            self._pending = None
            self._state = "ready"
        except BaseException:
            self._state = "failed"
            self._pending = None
            raise
        finally:
            live = None
            observed = None
            del graph

    def _finalize(self, primary: BaseException | None) -> None:
        try:
            self._cleanup_once()
        except BaseException as secondary:
            if primary is None:
                raise
            primary.__dict__["_matryca_native_small_cleanup_error"] = secondary
            BaseException.add_note(
                primary, "native small-load cleanup failed; secondary exception retained privately",
            )

    def _complete(self, primary: BaseException | None) -> BaseException | None:
        self._require_owner()
        if self._state not in ("ready", "failed", "closed"):
            raise RuntimeError("native small-load lifecycle violation")
        if primary is None:
            if self._state == "failed":
                primary = RuntimeError("native small-load binding failed")
            elif self._pending is not None:
                primary = RuntimeError("native small-load verification pending")
        if primary is not None:
            self._state = "failed"
        try:
            self._finalize(primary)
        finally:
            self._pending = None
        if primary is None:
            self._state = "closed"
        return primary

    def _cleanup_once(self) -> None:
        if self._owner is None or self._cleanup_attempted:
            return
        self._cleanup_attempted = True
        try:
            self._owner.cleanup()
            try:
                lstat(self._owner.name)
            except FileNotFoundError:
                pass
            else:
                raise RuntimeError("native small-load cleanup unconfirmed")
        except BaseException as error:
            self._cleanup_error = error
            self._cleanup_status = "failed"
            self._state = "failed"
            raise
        self._cleanup_status = "succeeded"

    def __exit__(
        self, exc_type: type[BaseException] | None,
        exc: BaseException | None, tb: TracebackType | None,
    ) -> Literal[False]:
        primary = self._complete(exc)
        if exc is None and primary is not None:
            raise primary
        return False

    def close(self) -> None:
        primary = self._complete(None)
        if primary is not None:
            raise primary

    @property
    def executor(self) -> ExecutorShape:
        self._require_owner()
        if self._state != "ready" or self._native is None:
            raise RuntimeError("native small-load lifecycle violation")
        return ExecutorShape("threads_current", self._native.max_workers, "none")

    @property
    def cleanup_error(self) -> BaseException | None:
        return self._cleanup_error

    @property
    def state(self) -> BindingState:
        return self._state

    @property
    def cleanup_status(self) -> CleanupStatus:
        return self._cleanup_status
