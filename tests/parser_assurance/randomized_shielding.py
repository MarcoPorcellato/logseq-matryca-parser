"""Finite, parser-independent source recipes and projection oracle."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import selectors
import signal
import stat
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, distribution, version
from pathlib import Path
from typing import IO, Any, Literal, cast

from hypothesis import Phase, given, settings
from hypothesis import seed as hypothesis_seed
from hypothesis import strategies as st

from logseq_matryca_parser.logos_core import LogseqPage
from logseq_matryca_parser.logos_parser import StackMachineParser
from tests.parser_assurance.invariants import assert_tree_invariants

_PRIMARY = ("Beta", "Cedar", "Éclair")
_SECONDARY = ("Alpha", "Maple", "Orchid")
_CATEGORIES = ("Topic", "delta", "Étiquette")
_SPAN_KINDS = ("comment", "fence-backtick-3", "fence-backtick-4", "fence-tilde-3", "fence-tilde-4")
_MAX_RECIPES = 8
_MAX_EXAMPLES = 16
_MAX_LINES = 12
_MAX_SOURCE_BYTES = 1024
_VISIBLE_TEXT = re.compile(r"[\w ]+", re.UNICODE)
PROTOCOL = "randomized-shielding-v1"
MAX_CHILD_OUTPUT = 16 * 1024
MAX_ATTEMPT_EVIDENCE = 256 * 1024
MAX_CAMPAIGN_TRANSFER = MAX_ATTEMPT_EVIDENCE
MAX_CLI_SUMMARY = 1024
PARENT_DEADLINE = 60.0
GENERATION_LIMIT = 5.0
PARSE_STOP_SECOND = 53.0
FINAL_RESERVE = 7.0
CASE_TIMEOUT = 3.0
CLEANUP_RESERVE = 1.0
CAMPAIGN_RECEIPT_ACK = "randomized-shielding-receipt-ack-v1"
_CAMPAIGN_PROCESS_GROUP: int | None = None


@dataclass(frozen=True)
class SpanRecipe:
    """Bounded deterministic choices for one multiline shielding case."""

    seed: int
    span_kinds: tuple[str, ...]
    payload_counts: tuple[int, ...]
    primary: str
    secondary: str
    category: str
    unicode_text: str
    fence_length: int


@dataclass(frozen=True)
class ShieldingObservation:
    """Small copied projection used by the independent expected-facts oracle."""

    root_count: int
    child_counts: tuple[int, ...]
    root_properties: tuple[tuple[str, Any], ...]
    page_properties: tuple[tuple[str, Any], ...]
    content: str
    raw_content: str
    line_start: int | None
    line_end: int | None
    wikilinks: tuple[str, ...]
    tags: tuple[str, ...]
    node_refs: tuple[str, ...]
    page_refs: tuple[str, ...]
    parent_ids: tuple[str | None, ...]
    left_ids: tuple[str | None, ...]
    paths: tuple[tuple[int, bool], ...]


@dataclass(frozen=True)
class ShieldingCase:
    """Source plus facts derived solely from finite recipe choices."""

    recipe: SpanRecipe
    source: str
    content: str
    wikilinks: tuple[str, ...]
    tags: tuple[str, ...]
    refs: tuple[str, ...]
    sha256: str
    source_bytes: int
    line_start: int
    line_end: int
    expected: ShieldingObservation


@dataclass(frozen=True)
class SourceContext:
    """Path-free revision and runtime binding carried by every worker result."""

    head: str
    manifest_sha256: str
    dirty: bool
    python_version: str
    package_version: str
    hypothesis_version: str = "unknown"
    dependency_manifest_sha256: str = "unknown"
    dependency_versions: tuple[tuple[str, str], ...] = ()

    @property
    def digest(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "head": self.head,
            "manifest_sha256": self.manifest_sha256,
            "dirty": self.dirty,
            "python_version": self.python_version,
            "package_version": self.package_version,
            "hypothesis_version": self.hypothesis_version,
            "dependency_manifest_sha256": self.dependency_manifest_sha256,
            "dependency_versions": self.dependency_versions,
        }


@dataclass(frozen=True)
class WorkerResult:
    """Strictly source- and context-bound single-parse outcome."""

    source_sha256: str
    context_digest: str
    classification: Literal[
        "parsed", "expected_parser_error", "unexpected_exception", "invariant_failure",
        "timeout", "runner_failure",
    ]
    parse_attempts: int
    observation: ShieldingObservation | None
    output_bytes: int = 0
    detail: str | None = None


@dataclass(frozen=True)
class CampaignResult:
    """Durable campaign outcome; incomplete evidence never qualifies."""

    classification: Literal["pass", "fail", "incomplete"]
    attempted_count: int
    completed_count: int
    elapsed_seconds: float
    receipt: dict[str, Any]
    cleanup: str
    receipt_sha256: str | None = None
    supervisor_status: str = "unverified"


@dataclass(frozen=True)
class SupervisorOutcome:
    """Outer-process observation; child receipt remains provisional until checked."""

    packet: dict[str, Any] | None
    classification: Literal["completed", "incomplete"]
    returncode: int | None
    output_bytes: int
    elapsed_seconds: float
    cleanup: Literal["reaped", "unconfirmed"]
    stdout: bytes


class _ChildError(RuntimeError):
    def __init__(
        self,
        classification: Literal[
            "parsed", "expected_parser_error", "unexpected_exception",
            "invariant_failure", "timeout", "runner_failure",
        ],
        output_bytes: int = 0,
        cleanup: str = "reaped",
    ):
        super().__init__(classification)
        self.classification = classification
        self.output_bytes = output_bytes
        self.cleanup = cleanup


def _process_group_exists(process_group: int) -> bool:
    try:
        os.killpg(process_group, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _signal_process_group(process_group: int, signum: int) -> None:
    with suppress(ProcessLookupError):
        os.killpg(process_group, signum)


def _supervise_process(
    arguments: Sequence[str],
    input_bytes: bytes,
    *,
    deadline: float,
    cleanup_reserve: float,
    output_limit: int,
) -> SupervisorOutcome:
    """Bound child IPC, exit and process-group cleanup by one absolute deadline."""
    started = time.monotonic()
    empty_packet: dict[str, Any] | None = None
    if deadline <= started or cleanup_reserve <= 0 or output_limit < 0:
        return SupervisorOutcome(empty_packet, "incomplete", None, 0, 0.0, "unconfirmed", b"")
    try:
        process = subprocess.Popen(
            list(arguments), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, start_new_session=True,
        )
    except OSError:
        return SupervisorOutcome(empty_packet, "incomplete", None, 0, 0.0, "reaped", b"")
    assert process.stdin is not None and process.stdout is not None and process.stderr is not None
    process_group = process.pid
    selector: selectors.BaseSelector | None = None
    stdout_bytes = bytearray()
    stderr_bytes = bytearray()
    input_offset = 0
    forced_stop = False
    completed_before_cutoff = False
    output_overflow = False
    return_code: int | None = None
    cleanup: Literal["reaped", "unconfirmed"] = "unconfirmed"
    try:
        selector = selectors.DefaultSelector()
        for stream, label in ((process.stdout, "stdout"), (process.stderr, "stderr")):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, label)
        os.set_blocking(process.stdin.fileno(), False)
        if input_bytes:
            selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")
        else:
            process.stdin.close()
        work_cutoff = deadline - cleanup_reserve
        while True:
            now = time.monotonic()
            if now >= work_cutoff:
                forced_stop = True
                break
            if process.poll() is not None and not selector.get_map():
                completed_before_cutoff = True
                break
            if not selector.get_map() and process.poll() is None:
                time.sleep(min(0.01, max(0.0, work_cutoff - time.monotonic())))
                continue
            for key, _ in selector.select(min(0.05, work_cutoff - now)):
                if key.data == "stdin":
                    try:
                        input_offset += os.write(key.fd, input_bytes[input_offset:])
                    except BlockingIOError:
                        continue
                    except BrokenPipeError:
                        selector.unregister(key.fileobj)
                        process.stdin.close()
                        forced_stop = True
                        break
                    if input_offset == len(input_bytes):
                        selector.unregister(key.fileobj)
                        process.stdin.close()
                    continue
                buffer = stdout_bytes if key.data == "stdout" else stderr_bytes
                combined_size = len(stdout_bytes) + len(stderr_bytes)
                chunk = os.read(key.fd, min(4096, output_limit + 1 - combined_size))
                if not chunk:
                    selector.unregister(key.fileobj)
                    cast(IO[bytes], key.fileobj).close()
                    continue
                buffer.extend(chunk)
                if len(stdout_bytes) + len(stderr_bytes) > output_limit:
                    output_overflow = True
                    forced_stop = True
                    break
            if forced_stop:
                break

        if not completed_before_cutoff:
            _signal_process_group(process_group, signal.SIGTERM)
            grace_until = min(deadline, time.monotonic() + 0.1)
            while process.poll() is None and time.monotonic() < grace_until:
                time.sleep(min(0.01, grace_until - time.monotonic()))
            if process.poll() is None or _process_group_exists(process_group):
                _signal_process_group(process_group, signal.SIGKILL)
        remaining = max(0.0, deadline - time.monotonic())
        try:
            return_code = process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            _signal_process_group(process_group, signal.SIGKILL)
            return_code = None
        while _process_group_exists(process_group) and time.monotonic() < deadline:
            _signal_process_group(process_group, signal.SIGKILL)
            time.sleep(min(0.01, max(0.0, deadline - time.monotonic())))
        cleanup = "reaped" if not _process_group_exists(process_group) else "unconfirmed"
        completed_before_cutoff = (
            completed_before_cutoff
            and not forced_stop
            and not output_overflow
            and return_code == 0
            and cleanup == "reaped"
            and time.monotonic() < deadline
        )
        packet: dict[str, Any] | None = None
        try:
            decoded = json.loads(bytes(stdout_bytes))
            if isinstance(decoded, dict):
                packet = decoded
            else:
                completed_before_cutoff = False
        except (UnicodeDecodeError, json.JSONDecodeError):
            completed_before_cutoff = False
        return SupervisorOutcome(
            packet,
            "completed" if completed_before_cutoff else "incomplete",
            return_code,
            len(stdout_bytes) + len(stderr_bytes),
            max(0.0, time.monotonic() - started),
            cleanup,
            bytes(stdout_bytes),
        )
    except BaseException:
        forced_stop = True
        completed_before_cutoff = False
        try:
            _signal_process_group(process_group, signal.SIGTERM)
            grace_until = min(deadline, time.monotonic() + 0.1)
            while process.poll() is None and time.monotonic() < grace_until:
                time.sleep(min(0.01, max(0.0, grace_until - time.monotonic())))
        except BaseException:
            pass
        with suppress(BaseException):
            _signal_process_group(process_group, signal.SIGKILL)
        try:
            wait_budget = max(0.0, deadline - time.monotonic())
            return_code = process.wait(timeout=wait_budget) if wait_budget else process.poll()
        except BaseException:
            return_code = None
            with suppress(BaseException):
                _signal_process_group(process_group, signal.SIGKILL)
        try:
            while time.monotonic() < deadline:
                if not _process_group_exists(process_group):
                    cleanup = "reaped"
                    break
                _signal_process_group(process_group, signal.SIGKILL)
                time.sleep(min(0.01, max(0.0, deadline - time.monotonic())))
            else:
                cleanup = "unconfirmed"
        except BaseException:
            cleanup = "unconfirmed"
        if cleanup != "reaped":
            try:
                cleanup = "reaped" if not _process_group_exists(process_group) else "unconfirmed"
            except BaseException:
                cleanup = "unconfirmed"
        packet = None
        try:
            decoded = json.loads(bytes(stdout_bytes))
            if isinstance(decoded, dict):
                packet = decoded
        except BaseException:
            pass
        return SupervisorOutcome(
            packet,
            "incomplete",
            return_code,
            len(stdout_bytes) + len(stderr_bytes),
            max(0.0, time.monotonic() - started),
            cleanup,
            bytes(stdout_bytes),
        )
    finally:
        if selector is not None:
            with suppress(BaseException):
                selector.close()
        for stream in (process.stdin, process.stdout, process.stderr):
            with suppress(BaseException):
                stream.close()


def _write_all(fd: int, payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        written = os.write(fd, view)
        if written <= 0:
            raise OSError("short write to attempt evidence")
        view = view[written:]


def _candidate_receipt_passes(receipt: dict[str, Any]) -> bool:
    try:
        results = receipt["results"]
        cases = receipt["cases"]
        seed_value = receipt["seed"]
        context = _context_from_dict(receipt["source_context"])
        if (
            receipt.get("protocol") != PROTOCOL
            or receipt.get("classification") != "provisional-pass"
            or type(seed_value) is not int
            or type(receipt.get("attempted_count")) is not int
            or receipt["attempted_count"] != 16
            or type(receipt.get("completed_count")) is not int
            or receipt["completed_count"] != 16
            or not isinstance(results, list) or len(results) != 16
            or not isinstance(cases, list) or len(cases) != 16
        ):
            return False
        recipes: dict[str, SpanRecipe] = {}
        for index, case_record in enumerate(cases):
            if not isinstance(case_record, dict) or set(case_record) != {
                "recipe", "newline", "source", "source_sha256", "worker",
            }:
                return False
            recipe = _recipe_from_dict(case_record["recipe"])
            if recipe.seed != seed_value:
                return False
            key = hashlib.sha256(
                json.dumps(_recipe_dict(recipe), sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            prior = recipes.setdefault(key, recipe)
            if prior != recipe:
                return False
            newline = case_record["newline"]
            if newline not in ("\n", "\r\n"):
                return False
            expected_case = build_case(recipe, newline)
            expected_observation = json.loads(
                json.dumps(_observation_dict(expected_case.expected), sort_keys=True)
            )
            worker = case_record["worker"]
            result = results[index]
            if (
                case_record["source"] != expected_case.source
                or case_record["source_sha256"] != expected_case.sha256
                or not isinstance(worker, dict)
                or worker.get("source_sha256") != expected_case.sha256
                or worker.get("context_digest") != context.digest
                or worker.get("classification") != "parsed"
                or type(worker.get("parse_attempts")) is not int
                or worker["parse_attempts"] != 1
                or worker.get("observation") != expected_observation
                or result.get("source_sha256") != expected_case.sha256
                or result.get("worker") != worker
            ):
                return False
        pair_recipes: set[str] = set()
        for index in range(0, _MAX_EXAMPLES, 2):
            first, second = cases[index], cases[index + 1]
            if (
                first["recipe"] != second["recipe"]
                or first["newline"] != "\n"
                or second["newline"] != "\r\n"
            ):
                return False
            pair_key = json.dumps(first["recipe"], sort_keys=True, separators=(",", ":"))
            if pair_key in pair_recipes:
                return False
            pair_recipes.add(pair_key)
        return len(recipes) == _MAX_RECIPES == len(pair_recipes)
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


def _campaign_result_from_supervisor(
    outcome: SupervisorOutcome, *, started: float, deadline: float
) -> CampaignResult:
    elapsed = max(0.0, time.monotonic() - started)
    packet = outcome.packet
    attempted = _MAX_EXAMPLES
    completed = 0
    receipt: dict[str, Any] = {}
    digest: str | None = None
    bound_packet = False
    if (
        packet is not None
        and set(packet) == {"ack", "receipt_sha256", "receipt", "durable"}
        and packet.get("ack") == CAMPAIGN_RECEIPT_ACK
        and packet.get("durable") is True
        and isinstance(packet.get("receipt"), dict)
    ):
        candidate = cast(dict[str, Any], packet["receipt"])
        try:
            serialized = (json.dumps(candidate, sort_keys=True, separators=(",", ":")) + "\n").encode()
        except (TypeError, ValueError):
            serialized = b""
        candidate_digest = hashlib.sha256(serialized).hexdigest()
        candidate_attempted = candidate.get("attempted_count")
        candidate_completed = candidate.get("completed_count")
        if (
            serialized
            and len(serialized) <= MAX_ATTEMPT_EVIDENCE
            and packet.get("receipt_sha256") == candidate_digest
            and candidate.get("protocol") == PROTOCOL
            and type(candidate_attempted) is int
            and type(candidate_completed) is int
            and 0 <= candidate_attempted <= _MAX_EXAMPLES
            and 0 <= candidate_completed <= candidate_attempted
        ):
            attempted = candidate_attempted
            completed = candidate_completed
            receipt = candidate
            digest = candidate_digest
            bound_packet = True
    incomplete = CampaignResult(
        "incomplete", attempted, completed, elapsed, receipt, outcome.cleanup,
        digest, "unconfirmed",
    )
    if (
        outcome.classification != "completed"
        or outcome.returncode != 0
        or outcome.cleanup != "reaped"
        or not bound_packet
        or time.monotonic() >= deadline
        or outcome.elapsed_seconds >= PARENT_DEADLINE
    ):
        return incomplete
    status = receipt.get("classification")
    if status == "provisional-pass":
        if not _candidate_receipt_passes(receipt):
            return incomplete
        validation_finished = time.monotonic()
        elapsed = max(0.0, validation_finished - started)
        if validation_finished >= deadline or elapsed >= PARENT_DEADLINE:
            return CampaignResult(
                "incomplete", attempted, completed, elapsed, receipt, outcome.cleanup,
                digest, "deadline-expired-during-validation",
            )
        return CampaignResult(
            "pass", attempted, completed, elapsed, receipt, "reaped", digest,
            "outer-verified",
        )
    if status == "provisional-fail":
        elapsed = max(0.0, time.monotonic() - started)
        return CampaignResult(
            "fail", attempted, completed, elapsed, receipt, "reaped", digest,
            "outer-verified",
        )
    elapsed = max(0.0, time.monotonic() - started)
    return CampaignResult(
        "incomplete", attempted, completed, elapsed, receipt, "reaped", digest,
        "outer-verified",
    )


@dataclass
class _OwnedAttemptDirectory:
    """Exclusive directory capability; evidence writes never follow pathnames."""

    path: Path
    parent_fd: int
    directory_fd: int
    name: str
    device: int
    inode: int
    file_descriptors: dict[str, int]

    @classmethod
    def create(cls, path: Path) -> _OwnedAttemptDirectory:
        if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
            raise OSError("safe directory descriptors unavailable on this platform")
        absolute = Path(os.path.abspath(path))
        if absolute.name in ("", ".", ".."):
            raise ValueError("attempt destination must be a directory leaf")
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        parent_fd = os.open(absolute.anchor, flags)
        try:
            for part in absolute.parent.parts[1:]:
                next_fd = os.open(part, flags, dir_fd=parent_fd)
                os.close(parent_fd)
                parent_fd = next_fd
            os.mkdir(absolute.name, mode=0o700, dir_fd=parent_fd)
            directory_fd = os.open(absolute.name, flags, dir_fd=parent_fd)
            identity = os.fstat(directory_fd)
            return cls(
                absolute, parent_fd, directory_fd, absolute.name,
                identity.st_dev, identity.st_ino, {},
            )
        except BaseException:
            os.close(parent_fd)
            raise

    def write_new(self, name: str, payload: bytes) -> None:
        if name not in {"plan.jsonl", "results.jsonl", "receipt.json"}:
            raise ValueError("unexpected evidence filename")
        if name not in self.file_descriptors:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
            if name == "results.jsonl":
                flags |= os.O_APPEND
            fd = os.open(name, flags, mode=0o600, dir_fd=self.directory_fd)
            self.file_descriptors[name] = fd
        elif name != "results.jsonl":
            raise FileExistsError("evidence file is append-only after exclusive creation")
        fd = self.file_descriptors[name]
        _write_all(fd, payload)
        os.fsync(fd)

    def read_file(self, name: str, limit: int) -> bytes:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=self.directory_fd)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
                raise OSError("attempt evidence type or size is invalid")
            chunks: list[bytes] = []
            remaining = limit + 1
            while remaining:
                chunk = os.read(fd, min(4096, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            result = b"".join(chunks)
            if len(result) > limit:
                raise OSError("attempt evidence exceeds bound")
            return result
        finally:
            os.close(fd)

    def flush_directory(self) -> None:
        os.fsync(self.directory_fd)

    def current_size(self) -> int:
        return sum(os.fstat(fd).st_size for fd in self.file_descriptors.values())

    def verify_path(self) -> None:
        info = os.stat(self.name, dir_fd=self.parent_fd, follow_symlinks=False)
        if (
            not stat.S_ISDIR(info.st_mode)
            or (info.st_dev, info.st_ino) != (self.device, self.inode)
        ):
            raise OSError("attempt destination no longer names owned directory")

    def close(self) -> None:
        for fd in self.file_descriptors.values():
            with suppress(OSError):
                os.close(fd)
        self.file_descriptors.clear()
        for fd in (self.directory_fd, self.parent_fd):
            with suppress(OSError):
                os.close(fd)


def _validate_recipe(recipe: SpanRecipe, newline: str) -> None:
    if not isinstance(recipe.seed, int) or isinstance(recipe.seed, bool) or not 0 <= recipe.seed < 2**32:
        raise ValueError("seed must be an unsigned 32-bit integer")
    if newline not in ("\n", "\r\n"):
        raise ValueError("newline must be LF or CRLF")
    if not 1 <= len(recipe.span_kinds) <= 2 or len(recipe.span_kinds) != len(recipe.payload_counts):
        raise ValueError("recipe must contain one or two aligned spans")
    if recipe.primary not in _PRIMARY or recipe.secondary not in _SECONDARY or recipe.category not in _CATEGORIES:
        raise ValueError("recipe values must use the finite disjoint vocabularies")
    if not isinstance(recipe.fence_length, int) or isinstance(recipe.fence_length, bool) or recipe.fence_length not in (3, 4):
        raise ValueError("fence length must be three or four")
    if not recipe.unicode_text or _VISIBLE_TEXT.fullmatch(recipe.unicode_text) is None:
        raise ValueError("payload text must contain only visible Unicode letters, numbers, and spaces")
    for kind, count in zip(recipe.span_kinds, recipe.payload_counts, strict=True):
        if kind not in _SPAN_KINDS:
            raise ValueError("unknown shielding span kind")
        if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 3:
            raise ValueError("each span must have one to three payload lines")
        if kind.endswith("-3") and recipe.fence_length != 3:
            raise ValueError("three-character fence kind requires fence_length=3")
        if kind.endswith("-4") and recipe.fence_length != 4:
            raise ValueError("four-character fence kind requires fence_length=4")


def _render_span(kind: str, payload_count: int, recipe: SpanRecipe, newline: str) -> list[str]:
    if kind == "comment":
        opening, closing = "  <!--", "  -->"
    else:
        fence_char = "`" if "backtick" in kind else "~"
        delimiter = fence_char * recipe.fence_length
        opening, closing = f"  {delimiter}", f"  {delimiter}"
    payload = (
        f"  [[{recipe.primary}]] [[{recipe.secondary}]] [[{recipe.primary}]] "
        f"#{recipe.category} #{recipe.secondary} #{recipe.category} "
        f"[[HiddenOnly]] #hiddenOnly {recipe.unicode_text}"
    )
    return [opening, *([payload] * payload_count), closing]


def build_case(recipe: SpanRecipe, newline: str) -> ShieldingCase:
    """Render one grammar-valid source and derive all expected facts independently."""
    _validate_recipe(recipe, newline)
    root = f"- lead #{recipe.category} [[{recipe.primary}]] [[{recipe.secondary}]] [[{recipe.primary}]]"
    source_lines = [root]
    for kind, count in zip(recipe.span_kinds, recipe.payload_counts, strict=True):
        source_lines.extend(_render_span(kind, count, recipe, newline))
    source_lines.append(f"  #{recipe.secondary} #{recipe.category}")
    source = newline.join(source_lines) + newline
    content = "\n".join((source_lines[0][2:], *source_lines[1:]))
    source_bytes = len(source.encode("utf-8"))
    if len(source_lines) > _MAX_LINES:
        raise ValueError("source exceeds twelve lines")
    if source_bytes > _MAX_SOURCE_BYTES:
        raise ValueError("source exceeds 1,024 UTF-8 bytes")

    wikilinks = (recipe.primary, recipe.secondary, recipe.primary)
    tags = (recipe.category, recipe.secondary, recipe.category)
    refs = (recipe.primary, recipe.secondary, recipe.category)
    line_end = len(source_lines)
    expected = ShieldingObservation(
        root_count=1,
        child_counts=(0,),
        root_properties=(),
        page_properties=(),
        content=content,
        raw_content=source,
        line_start=1,
        line_end=line_end,
        wikilinks=wikilinks,
        tags=tags,
        node_refs=refs,
        page_refs=refs,
        parent_ids=(None,),
        left_ids=(None,),
        paths=((1, True),),
    )
    return ShieldingCase(
        recipe=recipe,
        source=source,
        content=content,
        wikilinks=wikilinks,
        tags=tags,
        refs=refs,
        sha256=hashlib.sha256(source.encode("utf-8")).hexdigest(),
        source_bytes=source_bytes,
        line_start=1,
        line_end=line_end,
        expected=expected,
    )


def _generate_recipes(seed: int, strategy: st.SearchStrategy[SpanRecipe]) -> tuple[SpanRecipe, ...]:
    """Draw exactly the bounded generated sample; never refill rejected or duplicate cases."""
    generated: list[SpanRecipe] = []

    @hypothesis_seed(seed)
    @settings(max_examples=_MAX_EXAMPLES, deadline=None, database=None, phases=(Phase.generate,))
    @given(recipe=strategy)
    def collect_only(recipe: SpanRecipe) -> None:
        generated.append(recipe)

    collect_only()
    return tuple(generated)


def _select_recipes(candidates: tuple[SpanRecipe, ...]) -> tuple[SpanRecipe, ...]:
    """Retain unique valid cases from an already bounded sample, with no refill."""
    selected: list[SpanRecipe] = []
    seen: set[SpanRecipe] = set()
    for recipe in candidates:
        if recipe in seen:
            continue
        try:
            build_case(recipe, "\n")
        except ValueError:
            continue
        seen.add(recipe)
        selected.append(recipe)
        if len(selected) == _MAX_RECIPES:
            break
    return tuple(selected)


def collect_recipes(seed: int) -> tuple[SpanRecipe, ...]:
    """Collect at most eight unique recipes from at most sixteen Hypothesis examples."""
    if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed < 2**32:
        raise ValueError("seed must be an unsigned 32-bit integer")

    @st.composite
    def recipe_strategy(draw: st.DrawFn) -> SpanRecipe:
        span_count = draw(st.integers(min_value=1, max_value=2))
        kinds = draw(st.lists(st.sampled_from(_SPAN_KINDS), min_size=span_count, max_size=span_count))
        counts = draw(st.lists(st.integers(min_value=1, max_value=3), min_size=span_count, max_size=span_count))
        fence_length = draw(st.sampled_from((3, 4)))
        return SpanRecipe(
            seed=seed,
            span_kinds=tuple(kinds),
            payload_counts=tuple(counts),
            primary=draw(st.sampled_from(_PRIMARY)),
            secondary=draw(st.sampled_from(_SECONDARY)),
            category=draw(st.sampled_from(_CATEGORIES)),
            unicode_text=draw(st.sampled_from(("Éclair", "λambda", "naïve"))),
            fence_length=fence_length,
        )

    candidates = _generate_recipes(seed, recipe_strategy())
    return _select_recipes(candidates)


def observe(page: LogseqPage) -> ShieldingObservation:
    """Copy visible page/root projection without parser extraction helpers."""
    roots = page.root_nodes
    root = roots[0] if roots else None
    return ShieldingObservation(
        root_count=len(roots),
        child_counts=tuple(len(node.children) for node in roots),
        root_properties=tuple(sorted(root.properties.items())) if root is not None else (),
        page_properties=tuple(sorted(page.properties.items())),
        content=root.content if root is not None else "",
        raw_content=page.raw_content,
        line_start=root.line_start if root is not None else None,
        line_end=root.line_end if root is not None else None,
        wikilinks=tuple(root.wikilinks) if root is not None else (),
        tags=tuple(root.tags) if root is not None else (),
        node_refs=tuple(root.refs) if root is not None else (),
        page_refs=tuple(page.refs),
        parent_ids=tuple(node.parent_id for node in roots),
        left_ids=tuple(node.left_id for node in roots),
        paths=tuple((len(node.path), bool(node.path and node.path[-1] == node.uuid)) for node in roots),
    )


def assert_observation(actual: ShieldingObservation, expected: ShieldingObservation) -> None:
    """Fail on any copied projection difference."""
    assert actual == expected


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _ensure_assertions_enabled() -> None:
    if not __debug__:
        raise RuntimeError("optimized Python disables required parser-assurance assertions")


def _source_manifest_digest(root: Path, relative_paths: Sequence[str]) -> str:
    digest = hashlib.sha256()
    for relative in sorted(set(relative_paths)):
        path = root / relative
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("source manifest contains a non-regular file")
        content_digest = hashlib.sha256(path.read_bytes()).digest()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content_digest)
    return digest.hexdigest()


def _dependency_manifest_digest(distributions: Mapping[str, Sequence[Path]]) -> str:
    digest = hashlib.sha256()
    for name in sorted(distributions):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        for index, path in enumerate(distributions[name]):
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode):
                raise ValueError("dependency manifest contains a non-regular file")
            digest.update(str(index).encode("ascii"))
            digest.update(path.name.encode("utf-8"))
            digest.update(b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def _executed_source_paths(root: Path) -> tuple[str, ...]:
    package_root = root / "src" / "logseq_matryca_parser"
    package_sources = tuple(
        path.relative_to(root).as_posix()
        for path in sorted(package_root.rglob("*.py"))
        if not path.is_symlink()
    )
    return (
        "tests/parser_assurance/randomized_shielding.py",
        "tests/parser_assurance/invariants.py",
        "tests/test_parser_shielding_properties.py",
        "pyproject.toml",
        "uv.lock",
        *package_sources,
    )


def _installed_dependencies() -> tuple[dict[str, str], dict[str, tuple[Path, ...]]]:
    names = (
        "annotated-types", "hypothesis", "pydantic", "pydantic-core",
        "sortedcontainers", "typing-extensions",
    )
    versions: dict[str, str] = {}
    files_by_distribution: dict[str, tuple[Path, ...]] = {}
    for name in names:
        try:
            installed = distribution(name)
        except PackageNotFoundError as error:
            raise ValueError(f"required dependency unavailable: {name}") from error
        versions[name] = installed.version
        package_files = installed.files
        if package_files is None:
            raise ValueError(f"dependency file manifest unavailable: {name}")
        paths = tuple(Path(str(installed.locate_file(item))) for item in sorted(package_files))
        if not paths or any(not path.is_file() or path.is_symlink() for path in paths):
            raise ValueError(f"dependency bytes unavailable: {name}")
        files_by_distribution[name] = paths
    return versions, files_by_distribution


def capture_source_context() -> SourceContext:
    """Hash executed parser sources, lock and installed dependency bytes."""
    _ensure_assertions_enabled()
    root = _repository_root()
    manifest_digest = _source_manifest_digest(root, _executed_source_paths(root))
    dependency_versions, dependencies = _installed_dependencies()
    dependency_manifest = _dependency_manifest_digest(dependencies)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True,
        check=True, timeout=2.0,
    ).stdout.strip()
    dirty = bool(subprocess.run(
        ["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True,
        check=True, timeout=2.0,
    ).stdout)
    try:
        package_version = version("logseq-matryca-parser")
    except PackageNotFoundError:
        package_version = "uninstalled"
    try:
        hypothesis_version = version("hypothesis")
    except PackageNotFoundError:
        hypothesis_version = "uninstalled"
    if len(head) != 40 or any(character not in "0123456789abcdef" for character in head):
        raise ValueError("source HEAD is not a full Git object id")
    return SourceContext(
        head, manifest_digest, dirty, platform.python_version(), package_version,
        hypothesis_version, dependency_manifest,
        tuple(sorted(dependency_versions.items())),
    )


def _recipe_dict(recipe: SpanRecipe) -> dict[str, Any]:
    return {
        "seed": recipe.seed,
        "span_kinds": list(recipe.span_kinds),
        "payload_counts": list(recipe.payload_counts),
        "primary": recipe.primary,
        "secondary": recipe.secondary,
        "category": recipe.category,
        "unicode_text": recipe.unicode_text,
        "fence_length": recipe.fence_length,
    }


def _recipe_from_dict(payload: dict[str, Any]) -> SpanRecipe:
    if set(payload) != {
        "seed", "span_kinds", "payload_counts", "primary", "secondary", "category",
        "unicode_text", "fence_length",
    }:
        raise ValueError("worker recipe envelope has unexpected fields")
    return SpanRecipe(
        payload["seed"], tuple(payload["span_kinds"]), tuple(payload["payload_counts"]),
        payload["primary"], payload["secondary"], payload["category"],
        payload["unicode_text"], payload["fence_length"],
    )


def _context_from_dict(payload: dict[str, Any]) -> SourceContext:
    if set(payload) != {
        "head", "manifest_sha256", "dirty", "python_version", "package_version",
        "hypothesis_version", "dependency_manifest_sha256", "dependency_versions",
    } or type(payload["dirty"]) is not bool:
        raise ValueError("worker context envelope has unexpected fields")
    versions = payload["dependency_versions"]
    if not isinstance(versions, list) or any(
        not isinstance(item, list) or len(item) != 2
        or not all(isinstance(part, str) and part for part in item)
        for item in versions
    ):
        raise ValueError("worker dependency versions are malformed")
    context = SourceContext(
        payload["head"], payload["manifest_sha256"], payload["dirty"],
        payload["python_version"], payload["package_version"],
        payload["hypothesis_version"], payload["dependency_manifest_sha256"],
        tuple((item[0], item[1]) for item in versions),
    )
    if (
        len(context.head) != 40
        or any(character not in "0123456789abcdef" for character in context.head)
        or len(context.manifest_sha256) != 64
        or any(character not in "0123456789abcdef" for character in context.manifest_sha256)
        or len(context.dependency_manifest_sha256) != 64
        or any(character not in "0123456789abcdef" for character in context.dependency_manifest_sha256)
        or not all(isinstance(value, str) and value for value in (
            context.python_version, context.package_version, context.hypothesis_version
        ))
    ):
        raise ValueError("worker manifest digest is invalid")
    return context


def _observation_dict(observation: ShieldingObservation | None) -> dict[str, Any] | None:
    if observation is None:
        return None
    return {
        name: getattr(observation, name)
        for name in observation.__dataclass_fields__
    }


def _observation_from_dict(payload: dict[str, Any] | None) -> ShieldingObservation | None:
    if payload is None:
        return None
    tuple_fields = {
        "child_counts", "root_properties", "page_properties", "wikilinks", "tags",
        "node_refs", "page_refs", "parent_ids", "left_ids", "paths",
    }
    values = dict(payload)
    for field in tuple_fields:
        values[field] = tuple(tuple(value) if isinstance(value, list) else value for value in values[field])
    values["root_properties"] = tuple((key, value) for key, value in values["root_properties"])
    values["page_properties"] = tuple((key, value) for key, value in values["page_properties"])
    values["paths"] = tuple(tuple(value) for value in values["paths"])
    return ShieldingObservation(**values)


def run_worker(case: ShieldingCase, context: SourceContext) -> WorkerResult:
    """Validate finite source/context identity, parse once, then check oracle and tree."""
    if not isinstance(case, ShieldingCase) or not isinstance(context, SourceContext):
        raise ValueError("worker requires a shielding case and source context")
    newline = "\r\n" if "\r\n" in case.source else "\n"
    rebuilt = build_case(case.recipe, newline)
    if rebuilt != case:
        raise ValueError("worker source does not match finite recipe identity")
    if capture_source_context() != context:
        raise ValueError("worker source context drifted")
    source_hash = hashlib.sha256(case.source.encode("utf-8")).hexdigest()
    try:
        parser = StackMachineParser()
    except Exception as error:
        return WorkerResult(
            source_hash, context.digest, "unexpected_exception", 0, None,
            detail=type(error).__name__,
        )
    try:
        page = parser.parse(case.source, page_title="randomized-shielding")
    except Exception as error:
        return WorkerResult(
            source_hash, context.digest, "expected_parser_error", 1, None,
            detail=type(error).__name__,
        )
    try:
        assert_observation(observe(page), case.expected)
        assert_tree_invariants(page)
    except AssertionError as error:
        return WorkerResult(
            source_hash, context.digest, "invariant_failure", 1, None,
            detail=type(error).__name__,
        )
    return WorkerResult(source_hash, context.digest, "parsed", 1, observe(page))


def _terminate_and_reap(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        if _CAMPAIGN_PROCESS_GROUP is not None:
            _signal_process_group(_CAMPAIGN_PROCESS_GROUP, signal.SIGKILL)
        else:
            with suppress(ProcessLookupError):
                process.kill()
    try:
        process.wait(timeout=1.0)
    except subprocess.TimeoutExpired as error:
        raise _ChildError("runner_failure", cleanup="incomplete") from error


def _run_bounded_child(
    arguments: list[str],
    payload: dict[str, Any],
    timeout: float,
    *,
    kind: Literal["generation", "parser"] = "parser",
) -> tuple[bytes, int]:
    """Run one child with a deadline and a receive-time combined output cap."""
    maximum_timeout = GENERATION_LIMIT if kind == "generation" else CASE_TIMEOUT
    if timeout <= 0 or timeout > maximum_timeout:
        raise _ChildError("runner_failure")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    started = time.monotonic()
    try:
        process = subprocess.Popen(
            arguments, cwd=_repository_root(), stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            start_new_session=_CAMPAIGN_PROCESS_GROUP is None,
        )
    except OSError as error:
        raise _ChildError("runner_failure") from error
    assert process.stdin is not None and process.stdout is not None and process.stderr is not None
    selector: selectors.BaseSelector | None = None
    try:
        process.stdin.write(encoded)
        process.stdin.close()
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        selector.register(process.stderr, selectors.EVENT_READ)
        output = bytearray()
        open_streams = 2
        while open_streams:
            remaining = timeout - (time.monotonic() - started)
            if remaining <= 0:
                raise _ChildError("timeout", len(output))
            for key, _ in selector.select(min(0.05, remaining)):
                stream = cast(IO[bytes], key.fileobj)
                chunk = os.read(stream.fileno(), min(4096, MAX_CHILD_OUTPUT + 1 - len(output)))
                if not chunk:
                    selector.unregister(key.fileobj)
                    open_streams -= 1
                    continue
                output.extend(chunk)
                if len(output) > MAX_CHILD_OUTPUT:
                    raise _ChildError("runner_failure", len(output))
        remaining = timeout - (time.monotonic() - started)
        if remaining <= 0:
            raise _ChildError("timeout", len(output))
        return_code = process.wait(timeout=remaining)
        if return_code != 0:
            raise _ChildError("runner_failure", len(output))
        return bytes(output), len(output)
    except (BrokenPipeError, OSError, subprocess.TimeoutExpired) as error:
        raise _ChildError("runner_failure") from error
    except _ChildError:
        raise
    finally:
        if selector is not None:
            with suppress(OSError):
                selector.close()
        try:
            _terminate_and_reap(process)
        finally:
            for stream in (process.stdin, process.stdout, process.stderr):
                with suppress(OSError):
                    stream.close()


def _decode_child(output: bytes) -> dict[str, Any]:
    try:
        value = json.loads(output)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _ChildError("runner_failure", len(output)) from error
    if not isinstance(value, dict):
        raise _ChildError("runner_failure", len(output))
    return value


def _generate_supervised(seed: int, timeout: float) -> tuple[SpanRecipe, ...]:
    output, _ = _run_bounded_child(
        [sys.executable, "-m", "tests.parser_assurance.randomized_shielding", "--worker-generate"],
        {"seed": seed}, timeout, kind="generation",
    )
    payload = _decode_child(output)
    if set(payload) != {"protocol", "recipes"} or payload["protocol"] != PROTOCOL:
        raise _ChildError("runner_failure", len(output))
    return tuple(_recipe_from_dict(item) for item in payload["recipes"])


def _worker_supervised(case: ShieldingCase, context: SourceContext, *, timeout: float) -> WorkerResult:
    newline = "\r\n" if "\r\n" in case.source else "\n"
    output, output_bytes = _run_bounded_child(
        [sys.executable, "-m", "tests.parser_assurance.randomized_shielding", "--worker-parse"],
        {
            "protocol": PROTOCOL,
            "recipe": _recipe_dict(case.recipe),
            "newline": newline,
            "context": context.to_dict(),
        }, timeout,
    )
    payload = _decode_child(output)
    try:
        result = WorkerResult(
            payload["source_sha256"], payload["context_digest"], payload["classification"],
            payload["parse_attempts"], _observation_from_dict(payload["observation"]),
            output_bytes=output_bytes, detail=payload.get("detail"),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise _ChildError("runner_failure", output_bytes) from error
    if result.classification not in {
        "parsed", "expected_parser_error", "unexpected_exception", "invariant_failure",
        "timeout", "runner_failure",
    } or type(result.parse_attempts) is not int or result.parse_attempts < 0:
        raise _ChildError("runner_failure", output_bytes)
    if result.source_sha256 != case.sha256 or result.context_digest != context.digest:
        raise _ChildError("runner_failure", output_bytes)
    if result.parse_attempts != 1 or output_bytes > MAX_CHILD_OUTPUT:
        raise _ChildError("runner_failure", output_bytes)
    return result


def _campaign_work(
    seed: int, owned: _OwnedAttemptDirectory, started: float, deadline: float
) -> CampaignResult:
    """Run bounded campaign work inside the outer supervisor's process group."""
    if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed < 2**32:
        raise ValueError("seed must be an unsigned 32-bit integer")
    context = capture_source_context()
    attempted = 0
    completed = 0
    evidence_size = 0
    results: list[dict[str, Any]] = []
    receipt_cases: list[dict[str, Any]] = []
    classification: Literal["pass", "fail", "incomplete"] = "incomplete"
    cleanup = "reaped"
    try:
        generation_timeout = min(GENERATION_LIMIT, max(0.0, deadline - time.monotonic()))
        if generation_timeout <= 0:
            raise _ChildError("timeout")
        recipes = _generate_supervised(seed, generation_timeout)
        if time.monotonic() >= deadline - FINAL_RESERVE:
            raise _ChildError("timeout")
        recipes_valid = len(recipes) == _MAX_RECIPES and len(set(recipes)) == _MAX_RECIPES
        if recipes_valid:
            recipes_valid = all(recipe.seed == seed for recipe in recipes)
            if recipes_valid:
                try:
                    for recipe in recipes:
                        build_case(recipe, "\n")
                except (TypeError, ValueError):
                    recipes_valid = False
        if not recipes_valid:
            plan_cases: list[dict[str, Any]] = []
            if recipes:
                plan_cases = [
                    {
                        "recipe": _recipe_dict(recipe),
                        "sources": [
                            {
                                "newline": newline,
                                "source": (case := build_case(recipe, newline)).source,
                                "source_sha256": case.sha256,
                            }
                            for newline in ("\n", "\r\n")
                        ],
                    }
                    for recipe in recipes
                ]
            receipt_cases = plan_cases
            plan = {
                "protocol": PROTOCOL, "seed": seed, "source_context": context.to_dict(),
                "cases": plan_cases, "classification": "incomplete",
            }
            plan_bytes = (json.dumps(plan, sort_keys=True, separators=(",", ":")) + "\n").encode()
            if evidence_size + len(plan_bytes) > MAX_ATTEMPT_EVIDENCE:
                raise _ChildError("runner_failure")
            owned.write_new("plan.jsonl", plan_bytes)
            evidence_size += len(plan_bytes)
            raise _ChildError("runner_failure")
        cases = [
            build_case(recipe, newline)
            for recipe in recipes
            for newline in ("\n", "\r\n")
        ]
        receipt_cases = [
            {
                "recipe": _recipe_dict(case.recipe),
                "newline": "\r\n" if "\r\n" in case.source else "\n",
                "source": case.source,
                "source_sha256": case.sha256,
            }
            for case in cases
        ]
        plan = {
            "protocol": PROTOCOL, "seed": seed, "source_context": context.to_dict(),
            "cases": receipt_cases,
        }
        plan_bytes = (json.dumps(plan, sort_keys=True, separators=(",", ":")) + "\n").encode()
        if evidence_size + len(plan_bytes) > MAX_ATTEMPT_EVIDENCE:
            raise _ChildError("runner_failure")
        owned.write_new("plan.jsonl", plan_bytes)
        evidence_size += len(plan_bytes)
        if capture_source_context() != context:
            raise _ChildError("runner_failure")
        semantic_failure = False
        for case in cases:
            remaining = min(PARSE_STOP_SECOND - (time.monotonic() - started), deadline - time.monotonic() - FINAL_RESERVE)
            timeout = min(CASE_TIMEOUT, remaining - 0.25)
            if timeout <= 0:
                raise _ChildError("timeout")
            attempted += 1
            try:
                result = _worker_supervised(case, context, timeout=timeout)
                child_completed = True
            except _ChildError as error:
                child_completed = False
                if error.cleanup != "reaped":
                    cleanup = error.cleanup
                result = WorkerResult(case.sha256, context.digest, error.classification, 1, None, error.output_bytes)
            if (
                result.source_sha256 != case.sha256
                or result.context_digest != context.digest
                or result.output_bytes > MAX_CHILD_OUTPUT
            ):
                result = WorkerResult(case.sha256, context.digest, "runner_failure", max(1, result.parse_attempts), None, result.output_bytes)
            record = {
                "source_sha256": case.sha256,
                "source_bytes": case.source_bytes,
                "newline": "\r\n" if "\r\n" in case.source else "\n",
                "worker": {
                    "source_sha256": result.source_sha256,
                    "context_digest": result.context_digest,
                    "classification": result.classification,
                    "parse_attempts": result.parse_attempts,
                    "output_bytes": result.output_bytes,
                    "observation": _observation_dict(result.observation),
                    "detail": result.detail,
                },
            }
            line = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
            if evidence_size + len(line) > MAX_ATTEMPT_EVIDENCE:
                raise _ChildError("runner_failure")
            owned.write_new("results.jsonl", line)
            evidence_size += len(line)
            results.append(record)
            receipt_cases[attempted - 1]["worker"] = record["worker"]
            if child_completed:
                completed += 1
            if result.classification != "parsed" or result.parse_attempts != 1:
                semantic_failure = result.classification in ("expected_parser_error", "invariant_failure")
                classification = "fail" if semantic_failure else "incomplete"
                break
            if result.observation != case.expected:
                classification = "fail"
                break
        else:
            classification = "pass" if attempted == completed == 16 and len(recipes) == 8 else "incomplete"
        if capture_source_context() != context or time.monotonic() > deadline:
            classification = "incomplete"
    except _ChildError as error:
        cleanup = error.cleanup
        classification = "incomplete"
    except (OSError, ValueError, FileExistsError):
        classification = "incomplete"
    elapsed = max(0.0, time.monotonic() - started)
    receipt = {
        "protocol": PROTOCOL,
        "seed": seed,
        "source_context": context.to_dict(),
        "cases": receipt_cases,
        "attempted_count": attempted,
        "completed_count": completed,
        "elapsed_seconds": elapsed,
        "classification": classification,
        "cleanup": cleanup,
        "results": results,
    }
    rendered = (json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if evidence_size + len(rendered) > MAX_ATTEMPT_EVIDENCE:
        receipt["classification"] = "provisional-incomplete"
    elif classification == "pass":
        receipt["classification"] = "provisional-pass"
    elif classification == "fail":
        receipt["classification"] = "provisional-fail"
    else:
        receipt["classification"] = "provisional-incomplete"
    return CampaignResult("incomplete", attempted, completed, elapsed, receipt, cleanup)


def _campaign_child(payload: dict[str, Any]) -> int:
    global _CAMPAIGN_PROCESS_GROUP
    if set(payload) != {"seed", "output_dir", "started", "deadline"}:
        return 2
    seed_value = payload["seed"]
    started = payload["started"]
    deadline = payload["deadline"]
    if (
        type(seed_value) is not int or not 0 <= seed_value < 2**32
        or not isinstance(payload["output_dir"], str)
        or not isinstance(started, (int, float))
        or not isinstance(deadline, (int, float))
        or deadline <= started or deadline - started > PARENT_DEADLINE
    ):
        return 2
    _CAMPAIGN_PROCESS_GROUP = os.getpgrp()
    owned: _OwnedAttemptDirectory | None = None
    try:
        owned = _OwnedAttemptDirectory.create(Path(payload["output_dir"]))
        provisional = _campaign_work(seed_value, owned, float(started), float(deadline))
        receipt_bytes = (
            json.dumps(provisional.receipt, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode()
        if (
            len(receipt_bytes) > MAX_ATTEMPT_EVIDENCE
            or owned.current_size() + len(receipt_bytes) > MAX_ATTEMPT_EVIDENCE
        ):
            return 3
        packet = {
            "ack": CAMPAIGN_RECEIPT_ACK,
            "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
            "receipt": provisional.receipt,
            "durable": True,
        }
        packet_bytes = json.dumps(packet, sort_keys=True, separators=(",", ":")).encode()
        if len(packet_bytes) > MAX_CAMPAIGN_TRANSFER:
            return 3
        owned.write_new("receipt.json", receipt_bytes)
        owned.flush_directory()
        owned.verify_path()
        if time.monotonic() >= deadline - CLEANUP_RESERVE:
            return 4
        durable = owned.read_file("receipt.json", MAX_ATTEMPT_EVIDENCE)
        if (
            durable != receipt_bytes
            or hashlib.sha256(durable).hexdigest() != packet["receipt_sha256"]
        ):
            return 5
        sys.stdout.write(packet_bytes.decode("utf-8"))
        sys.stdout.flush()
        return 0
    finally:
        if owned is not None:
            owned.close()
        _CAMPAIGN_PROCESS_GROUP = None


def run_pilot(seed: int, output_dir: Path) -> CampaignResult:
    """Run one explicit opt-in campaign under an absolute outer deadline."""
    if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed < 2**32:
        raise ValueError("seed must be an unsigned 32-bit integer")
    started = time.monotonic()
    deadline = started + PARENT_DEADLINE
    payload = json.dumps(
        {
            "seed": seed,
            "output_dir": str(Path(os.path.abspath(output_dir))),
            "started": started,
            "deadline": deadline,
        }, sort_keys=True, separators=(",", ":"),
    ).encode()
    outcome = _supervise_process(
        [sys.executable, "-m", "tests.parser_assurance.randomized_shielding", "--campaign-child"],
        payload,
        deadline=deadline,
        cleanup_reserve=CLEANUP_RESERVE,
        output_limit=MAX_CAMPAIGN_TRANSFER,
    )
    return _campaign_result_from_supervisor(outcome, started=started, deadline=deadline)


def _worker_main(argv: list[str]) -> int:
    try:
        payload = json.loads(sys.stdin.buffer.read(MAX_CHILD_OUTPUT + 1))
        if len(json.dumps(payload).encode("utf-8")) > MAX_CHILD_OUTPUT:
            return 2
        result: dict[str, Any]
        if argv == ["--campaign-child"]:
            return _campaign_child(payload)
        if argv == ["--worker-generate"]:
            seed_value = payload["seed"]
            recipes = collect_recipes(seed_value)
            result = {"protocol": PROTOCOL, "recipes": [_recipe_dict(recipe) for recipe in recipes]}
        elif argv == ["--worker-parse"]:
            if payload.get("protocol") != PROTOCOL:
                return 2
            recipe = _recipe_from_dict(payload["recipe"])
            context = _context_from_dict(payload["context"])
            case = build_case(recipe, payload["newline"])
            worker = run_worker(case, context)
            result = {
                "source_sha256": worker.source_sha256,
                "context_digest": worker.context_digest,
                "classification": worker.classification,
                "parse_attempts": worker.parse_attempts,
                "observation": _observation_dict(worker.observation),
                "detail": worker.detail,
            }
        else:
            return 2
        sys.stdout.write(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    except Exception as error:
        sys.stdout.write(json.dumps({"error": type(error).__name__}))
        return 1


def main(argv: list[str] | None = None) -> int:
    """Expose campaign only through its explicit protocol and opt-in switches."""
    import argparse

    args = list(sys.argv[1:] if argv is None else argv)
    if args and (args[0].startswith("--worker-") or args[0] == "--campaign-child"):
        return _worker_main(args)
    parser = argparse.ArgumentParser(description="Bounded randomized shielding pilot.")
    parser.add_argument("--protocol", choices=(PROTOCOL,), required=True)
    parser.add_argument("--opt-in", action="store_true", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parsed = parser.parse_args(args)
    result = run_pilot(parsed.seed, parsed.output_dir)
    receipt_digest = result.receipt_sha256
    valid_digest = (
        isinstance(receipt_digest, str)
        and re.fullmatch(r"[0-9a-f]{64}", receipt_digest) is not None
    )
    attempted_count = result.attempted_count
    completed_count = result.completed_count
    receipt = result.receipt
    receipt_bound_counts = False
    if (
        valid_digest
        and isinstance(receipt, dict)
        and receipt.get("protocol") == PROTOCOL
        and receipt.get("classification") in {
            "provisional-pass", "provisional-fail", "provisional-incomplete",
        }
        and type(attempted_count) is int
        and type(completed_count) is int
        and 0 <= attempted_count <= _MAX_EXAMPLES
        and 0 <= completed_count <= attempted_count
        and receipt.get("attempted_count") == attempted_count
        and receipt.get("completed_count") == completed_count
    ):
        try:
            receipt_bytes = (
                json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n"
            ).encode()
        except (TypeError, ValueError):
            receipt_bytes = b""
        receipt_bound_counts = (
            bool(receipt_bytes)
            and len(receipt_bytes) <= MAX_ATTEMPT_EVIDENCE
            and hashlib.sha256(receipt_bytes).hexdigest() == receipt_digest
        )
    if receipt_bound_counts:
        count_basis = "receipt-bound"
    else:
        attempted_count = _MAX_EXAMPLES
        completed_count = 0
        count_basis = "conservative-upper-bound"
        receipt_digest = None
        valid_digest = False
    elapsed_value = result.elapsed_seconds
    valid_elapsed = (
        isinstance(elapsed_value, (int, float))
        and not isinstance(elapsed_value, bool)
        and 0 <= elapsed_value <= PARENT_DEADLINE
    )
    valid_cleanup = result.cleanup in {"reaped", "unconfirmed"}
    valid_status = result.supervisor_status in {
        "outer-verified", "unconfirmed", "deadline-expired-during-validation",
    }
    summary_classification = (
        result.classification
        if result.classification in {"pass", "fail", "incomplete"}
        else "incomplete"
    )
    if summary_classification in {"pass", "fail"} and not receipt_bound_counts:
        summary_classification = "incomplete"
    if summary_classification == "pass" and not (
        valid_digest and valid_elapsed and result.supervisor_status == "outer-verified"
        and result.cleanup == "reaped" and attempted_count == completed_count == _MAX_EXAMPLES
        and receipt.get("classification") == "provisional-pass"
    ):
        summary_classification = "incomplete"
    if summary_classification == "fail" and not (
        result.supervisor_status == "outer-verified" and result.cleanup == "reaped"
        and receipt.get("classification") == "provisional-fail"
    ):
        summary_classification = "incomplete"
    summary = {
        "classification": summary_classification,
        "receipt_sha256": receipt_digest if valid_digest else None,
        "supervisor_status": result.supervisor_status if valid_status else "unverified",
        "elapsed_seconds": elapsed_value if valid_elapsed else None,
        "cleanup": result.cleanup if valid_cleanup else "unconfirmed",
        "attempted_count": attempted_count,
        "completed_count": completed_count,
        "count_basis": count_basis,
    }
    rendered = json.dumps(summary, sort_keys=True, separators=(",", ":"))
    if len(rendered.encode("utf-8")) > MAX_CLI_SUMMARY:
        summary_classification = "incomplete"
        rendered = json.dumps({
            "classification": "incomplete",
            "receipt_sha256": None,
            "supervisor_status": "summary-overflow",
            "elapsed_seconds": None,
            "cleanup": "unconfirmed",
            "attempted_count": _MAX_EXAMPLES,
            "completed_count": 0,
            "count_basis": "conservative-upper-bound",
        }, sort_keys=True, separators=(",", ":"))
    print(rendered)
    return 0 if summary_classification == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
