from __future__ import annotations

import hashlib
import io
import json
import multiprocessing
import os
import select
import shutil
import signal
import stat
import subprocess
import sys
import threading
import time
from contextlib import suppress
from pathlib import Path
from typing import Any

import probe
import pytest
from probe import (
    MAX_CHILD_OUTPUT,
    classify_worker_result,
    load_verified_inputs,
    run_worker,
    validate_destination,
)


class SyntheticDomainError(Exception):
    pass


class _PipeStdout:
    def __init__(self, descriptor: int) -> None:
        self.descriptor = descriptor

    def fileno(self) -> int:
        return self.descriptor


def group_exists(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    return True


def cleanup_group(pgid: int) -> None:
    with suppress(ProcessLookupError):
        os.killpg(pgid, signal.SIGKILL)


def entry(root: Path, source: str, destination: str, data: bytes) -> dict[str, object]:
    return {
        "source_path": source,
        "destination": destination,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "git_blob": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest(),
    }


def test_verified_inputs_preserve_literal_percent_and_send_exact_payload(tmp_path: Path) -> None:
    root = tmp_path / "corpus"
    root.mkdir()
    data = b"- synthetic\n"
    (root / "pages").mkdir()
    path = root / "pages" / "New%3F.md"
    path.write_bytes(data)
    records = load_verified_inputs(
        root, [entry(root, "pages/New%3F.md", "corpus/pages/New%3F.md", data)], expected_count=1
    )
    assert records[0]["source_path"] == "pages/New%3F.md"
    assert records[0]["payload"] == data


@pytest.mark.parametrize(
    "bad_destination",
    ["../escape.md", "/absolute.md", "provenance/README.md", "corpus/../outside.md"],
)
def test_rejects_manifest_destination_escape(tmp_path: Path, bad_destination: str) -> None:
    with pytest.raises(ValueError, match="destination"):
        validate_destination(bad_destination)


def test_rejects_symlinked_input(tmp_path: Path) -> None:
    root = tmp_path / "corpus"
    root.mkdir()
    other = tmp_path / "other.md"
    other.write_bytes(b"- synthetic\n")
    (root / "pages").mkdir()
    (root / "pages" / "link.md").symlink_to(other)
    with pytest.raises(ValueError, match="symlink"):
        load_verified_inputs(
            root,
            [entry(root, "pages/link.md", "corpus/pages/link.md", other.read_bytes())],
            expected_count=1,
        )


def test_rejects_invalid_utf8_and_byte_mismatch(tmp_path: Path) -> None:
    root = tmp_path / "corpus"
    root.mkdir()
    data = b"\xff"
    (root / "bad.md").write_bytes(data)
    with pytest.raises(ValueError, match="UTF-8"):
        load_verified_inputs(root, [entry(root, "bad.md", "corpus/bad.md", data)], expected_count=1)


def test_rejects_symlinked_corpus_subdirectory(tmp_path: Path) -> None:
    root = tmp_path / "corpus"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "x.md").write_bytes(b"- synthetic\n")
    (root / "nested").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        load_verified_inputs(root, [], expected_count=0)


def test_real_worker_parses_synthetic_text_and_checks_input_hash() -> None:
    payload = b"- parent\n  - child\n"
    result = run_worker(
        payload,
        hashlib.sha256(payload).hexdigest(),
        "synthetic%3F",
        timeout=3,
        command=[sys.executable, "-c", "from probe import worker_main; worker_main()"],
    )
    assert result["classification"] == "parsed_invariants_pass"
    assert result["node_count"] == 2


def test_worker_rejects_wrong_hash_without_echoing_input() -> None:
    payload = b"PRIVATE TITLE\n"
    result = run_worker(
        payload,
        "0" * 64,
        "private title",
        timeout=3,
        command=[sys.executable, "-c", "from probe import worker_main; worker_main()"],
    )
    assert result["classification"] == "binding_failure"
    assert "PRIVATE TITLE" not in json.dumps(result)


def test_worker_result_never_echoes_page_title() -> None:
    payload = b"- ordinary\n"
    private_title = "PRIVATE CORPUS TITLE"
    result = run_worker(payload, hashlib.sha256(payload).hexdigest(), private_title, timeout=3)
    assert result["classification"] == "parsed_invariants_pass"
    assert private_title not in json.dumps(result)


def test_worker_timeout_reaps_child() -> None:
    code = "import time; time.sleep(10)"
    result = run_worker(
        b"x",
        hashlib.sha256(b"x").hexdigest(),
        "x",
        timeout=0.1,
        command=[sys.executable, "-c", code],
    )
    assert result["classification"] == "timeout"
    assert result["cleanup_confirmed"] is True


def test_worker_output_overflow_stops_and_reaps() -> None:
    code = f"import sys; sys.stdout.write('x' * {MAX_CHILD_OUTPUT + 1}); sys.stdout.flush()"
    result = run_worker(
        b"x", hashlib.sha256(b"x").hexdigest(), "x", timeout=3, command=[sys.executable, "-c", code]
    )
    assert result["classification"] == "output_overflow"
    assert result["cleanup_confirmed"] is True


def test_nonzero_child_is_invalid_even_with_valid_json() -> None:
    code = "import json,sys; print(json.dumps({'classification':'parsed_invariants_pass','root_count':0,'node_count':0,'invariant_result':'pass'})); sys.exit(7)"
    result = run_worker(
        b"x", hashlib.sha256(b"x").hexdigest(), "x", timeout=3, command=[sys.executable, "-c", code]
    )
    assert result["classification"] == "invalid_child_result"


@pytest.mark.parametrize("packet", [b"not-json", b'{"classification":"parsed_invariants_pass"}'])
def test_malformed_or_incomplete_child_result_is_unexpected(packet: bytes) -> None:
    result = classify_worker_result(packet, 0)
    assert result["classification"] == "invalid_child_result"


def test_bounded_stage_round_trips_exact_verified_payload_bytes() -> None:
    payload = b"synthetic %3F bytes\x00\xff"
    value = probe._bounded_stage(
        "input_read",
        lambda: {"payload": payload, "paths": ["pages/a%3F.md"]},
        deadline=time.monotonic() + 3,
        reserve_final=False,
        max_payload_bytes=len(payload),
    )
    assert value == {"payload": payload, "paths": ["pages/a%3F.md"]}


def test_bounded_stage_enforces_combined_output_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(probe, "_cleanup_stage_process", lambda _process, _deadline: True)
    with pytest.raises(probe.StageFailure, match="^stage_output_overflow$") as failure:
        probe._bounded_stage(
            "noisy",
            lambda: print("x" * (MAX_CHILD_OUTPUT + 1)),
            deadline=time.monotonic() + 3,
            reserve_final=False,
        )
    assert failure.value.cleanup_confirmed is True


@pytest.mark.parametrize(
    "stage", ["preflight", "input_read", "git", "post_bindings", "summary_write", "summary_sync"]
)
def test_bounded_stage_timeout_owns_and_reaps_blocking_stage(
    monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    monkeypatch.setattr(probe, "MAX_STAGE_SECONDS", 0.3)
    monkeypatch.setattr(probe, "STAGE_CLEANUP_SECONDS", 0.1)
    started = time.monotonic()
    with pytest.raises(probe.StageFailure, match=f"^{stage}_timeout$") as failure:
        probe._bounded_stage(
            stage, lambda: time.sleep(10), deadline=started + 2, reserve_final=False
        )
    assert failure.value.cleanup_confirmed is True
    assert time.monotonic() - started < 1.5


def test_bounded_stage_rejects_malformed_frame_after_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        probe, "_write_stage_frame", lambda write_fd, _envelope, _limit: os.write(write_fd, b"\x00")
    )
    with pytest.raises(probe.StageFailure, match="^stage_frame_invalid$") as failure:
        probe._bounded_stage(
            "malformed", lambda: {"ok": True}, deadline=time.monotonic() + 3, reserve_final=False
        )
    assert failure.value.cleanup_confirmed is True


def test_bounded_stage_preserves_sanitized_operation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(probe, "_cleanup_stage_process", lambda _process, _deadline: True)
    with pytest.raises(probe.StageFailure, match="^expected_domain_rejection$") as failure:
        probe._bounded_stage(
            "domain",
            lambda: (_ for _ in ()).throw(probe.ProbeStop("expected_domain_rejection")),
            deadline=time.monotonic() + 3,
            reserve_final=False,
        )
    assert failure.value.cleanup_confirmed is True


def test_bounded_stage_rejects_overflow_after_cleanup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(probe, "_cleanup_stage_process", lambda _process, _deadline: True)
    with pytest.raises(probe.StageFailure, match="^stage_result_too_large$") as failure:
        probe._bounded_stage(
            "oversized",
            lambda: b"x" * probe.MAX_STAGE_FRAME_BYTES,
            deadline=time.monotonic() + 3,
            reserve_final=False,
        )
    assert failure.value.cleanup_confirmed is True


@pytest.mark.parametrize(
    ("max_stage", "reserve_final", "deadline_delta", "final_reserve", "decode_delay", "expected"),
    [
        (0.1, False, 1.0, 10.0, 0.15, "decode_timeout"),
        (1.0, True, 0.3, 0.1, 0.25, "lifecycle_deadline"),
    ],
)
def test_bounded_stage_rejects_result_decoded_after_boundary(
    monkeypatch: pytest.MonkeyPatch,
    max_stage: float,
    reserve_final: bool,
    deadline_delta: float,
    final_reserve: float,
    decode_delay: float,
    expected: str,
) -> None:
    monkeypatch.setattr(probe, "MAX_STAGE_SECONDS", max_stage)
    monkeypatch.setattr(probe, "STAGE_CLEANUP_SECONDS", 0.01)
    monkeypatch.setattr(probe, "FINAL_RESERVE_SECONDS", final_reserve)
    monkeypatch.setattr(probe, "_cleanup_stage_process", lambda _process, _deadline: True)
    original_unpack = probe._stage_unpack

    def delayed_unpack(value: Any) -> Any:
        time.sleep(decode_delay)
        return original_unpack(value)

    monkeypatch.setattr(probe, "_stage_unpack", delayed_unpack)
    with pytest.raises(probe.StageFailure, match=f"^{expected}$") as failure:
        probe._bounded_stage(
            "decode",
            lambda: "finished",
            deadline=time.monotonic() + deadline_delta,
            reserve_final=reserve_final,
        )
    assert failure.value.cleanup_confirmed is True


def test_bounded_stage_partial_start_failure_cleans_retained_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process_type = multiprocessing.get_context("fork").Process
    original_start = process_type.start

    def start_then_raise(process: Any) -> None:
        original_start(process)
        raise OSError("synthetic failure after child creation")

    def uncertain_cleanup(process: Any, _deadline: float) -> bool:
        process.join(1)
        return False

    monkeypatch.setattr(process_type, "start", start_then_raise)
    monkeypatch.setattr(probe, "_cleanup_stage_process", uncertain_cleanup)
    with pytest.raises(probe.StageFailure, match="^stage_start_failure$") as failure:
        probe._bounded_stage(
            "partial_start",
            lambda: time.sleep(0.05),
            deadline=time.monotonic() + 3,
            reserve_final=False,
        )
    assert failure.value.cleanup_confirmed is False


@pytest.mark.parametrize(
    ("startup_error", "expected_reason"),
    [(OSError, "stage_start_failure"), (KeyboardInterrupt, "ambiguous_start_interrupted")],
)
def test_bounded_stage_start_entered_without_pid_is_unconfirmed(
    monkeypatch: pytest.MonkeyPatch, startup_error: type[BaseException], expected_reason: str
) -> None:
    process_type = multiprocessing.get_context("fork").Process

    def fail_after_entering_start(_process: Any) -> None:
        raise startup_error("synthetic ambiguous startup")

    monkeypatch.setattr(process_type, "start", fail_after_entering_start)
    with pytest.raises(probe.StageFailure, match=f"^{expected_reason}$") as failure:
        probe._bounded_stage(
            "ambiguous_start", lambda: "unused", deadline=time.monotonic() + 3, reserve_final=False
        )
    assert failure.value.cleanup_confirmed is False


def test_bounded_stage_setup_failure_before_start_proves_no_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process_type = multiprocessing.get_context("fork").Process

    def fail_before_start(_process: Any) -> None:
        raise AssertionError("Process.start must not be entered")

    monkeypatch.setattr(process_type, "start", fail_before_start)
    monkeypatch.setattr(
        os, "pipe", lambda: (_ for _ in ()).throw(OSError("synthetic pipe setup failure"))
    )
    with pytest.raises(probe.StageFailure, match="^stage_start_failure$") as failure:
        probe._bounded_stage(
            "setup", lambda: "unused", deadline=time.monotonic() + 3, reserve_final=False
        )
    assert failure.value.cleanup_confirmed is True


def test_bounded_stage_interruption_cleans_owned_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(probe, "MAX_STAGE_SECONDS", 1.0)
    monkeypatch.setattr(
        probe.select, "select", lambda *_args: (_ for _ in ()).throw(KeyboardInterrupt)
    )
    with pytest.raises(probe.StageFailure, match="^interrupt_interrupted$") as failure:
        probe._bounded_stage(
            "interrupt", lambda: time.sleep(10), deadline=time.monotonic() + 2, reserve_final=False
        )
    assert failure.value.cleanup_confirmed is True


def test_bounded_stage_reaping_failure_is_not_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(probe, "_cleanup_stage_process", lambda _process, _deadline: False)
    with pytest.raises(probe.StageFailure, match="^stage_cleanup_unconfirmed$") as failure:
        probe._bounded_stage(
            "reaping", lambda: "synthetic", deadline=time.monotonic() + 3, reserve_final=False
        )
    assert failure.value.cleanup_confirmed is False


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            {"classification": "expected_domain_rejection", "exception_type": "LogseqParserError"},
            "expected_domain_rejection",
        ),
        (
            {"classification": "unexpected_exception", "exception_type": "ValueError"},
            "unexpected_exception",
        ),
        ({"classification": "raw_content_mismatch"}, "raw_content_mismatch"),
        ({"classification": "tree_invariants"}, "tree_invariants"),
    ],
)
def test_classifications_remain_distinct(raw: dict[str, object], expected: str) -> None:
    assert classify_worker_result(json.dumps(raw).encode(), 0)["classification"] == expected


def test_optimized_python_is_rejected_before_parser_import() -> None:
    code = "from probe import run_worker; import hashlib; print(run_worker(b'x', hashlib.sha256(b'x').hexdigest(), 'x', timeout=1))"
    env = dict(os.environ)
    from probe import REPO_ROOT

    env["PYTHONPATH"] = os.pathsep.join(
        (str(Path(__file__).parent), str(REPO_ROOT / "src"), str(REPO_ROOT))
    )
    completed = subprocess.run(
        [sys.executable, "-O", "-c", code], capture_output=True, text=True, check=True, env=env
    )
    assert "runner_rejected_optimized_python" in completed.stdout


def test_optimized_worker_refuses_to_claim_parse_result() -> None:
    from probe import REPO_ROOT

    script = Path(__file__).with_name("probe.py")
    packet = json.dumps(
        {"payload": "LXN5bnRoZXRpYwo=", "sha256": "0" * 64, "page_title": "private"}
    )
    completed = subprocess.run(
        [sys.executable, "-O", str(script), "--worker"],
        input=packet,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    assert json.loads(completed.stdout)["classification"] == "binding_failure"


def test_binding_maps_detect_source_change() -> None:
    from probe import _bindings_changed

    before = {"src/parser.py": "a" * 64, "uv.lock": "b" * 64}
    assert not _bindings_changed(before, dict(before))
    assert _bindings_changed(before, {**before, "src/parser.py": "c" * 64})


def test_output_directory_is_exclusive_and_preserves_existing(tmp_path: Path) -> None:
    attempt = tmp_path / "attempt-1"
    attempt.mkdir()
    marker = attempt / "existing"
    marker.write_text("keep", encoding="utf-8")
    with pytest.raises(FileExistsError):
        probe_create_output(attempt)
    assert marker.read_text(encoding="utf-8") == "keep"


def test_new_output_directory_has_private_mode(tmp_path: Path) -> None:
    from probe import create_output_directory

    output = tmp_path / "attempt"
    owned = create_output_directory(output)
    try:
        assert output.stat().st_mode & 0o777 == 0o700
    finally:
        owned.close()


def probe_create_output(path: Path) -> None:
    from probe import create_output_directory

    create_output_directory(path)


def test_lifecycle_git_preflight_uses_remaining_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    observed: dict[str, Any] = {}
    read_fd, write_fd = os.pipe()

    class StalledProcess:
        def __init__(self) -> None:
            self.stdout = os.fdopen(read_fd, "rb", buffering=0)
            self.killed = False

        def poll(self) -> int | None:
            return 0 if self.killed else None

        def kill(self) -> None:
            self.killed = True
            os.close(write_fd)

        def wait(self, timeout: float | None = None) -> int:
            del timeout
            return 0

    def stalled_popen(*args: object, **kwargs: Any) -> StalledProcess:
        observed.update(kwargs)
        observed["args"] = args
        return StalledProcess()

    monkeypatch.setattr(probe.subprocess, "Popen", stalled_popen)
    with pytest.raises(probe.ProbeStop, match="lifecycle_deadline"):
        probe._git("status", deadline=time.monotonic() + probe.FINAL_RESERVE_SECONDS + 0.01)
    assert observed["args"] == (["git", "status"],)
    assert observed["cwd"] == probe.REPO_ROOT
    assert observed["stderr"] == subprocess.STDOUT


def test_final_summary_late_success_becomes_bounded_incomplete() -> None:
    summary, encoded, exit_code = probe._finalize_summary(
        {"status": "pass_diagnostic_only", "completed_count": 1, "results": []},
        deadline=time.monotonic() - 0.01,
        started=time.monotonic() - 2,
    )
    assert summary["status"] == "provisional"
    assert summary["diagnostic_outcome"] == "incomplete"
    assert summary["reason"] == "lifecycle_deadline"
    assert len(encoded) <= probe.MAX_SUMMARY_BYTES
    assert exit_code != 0


def test_summary_metadata_overflow_keeps_accurate_counts_and_fails() -> None:
    rows = [
        {"source_path": f"pages/{index}.md", "classification": "parsed_invariants_pass"}
        for index in range(2000)
    ]
    summary, encoded, exit_code = probe._finalize_summary(
        {
            "status": "pass_diagnostic_only",
            "completed_count": len(rows),
            "results": rows,
            "metadata": "x" * (probe.MAX_SUMMARY_BYTES + 1),
        },
        deadline=time.monotonic() + 5,
        started=time.monotonic(),
    )
    decoded = json.loads(encoded)
    assert len(encoded) <= probe.MAX_SUMMARY_BYTES
    assert decoded["completed_count"] == len(rows)
    assert decoded["recorded_result_count"] == len(decoded["results"])
    assert summary["status"] == "provisional"
    assert summary["diagnostic_outcome"] == "incomplete"
    assert exit_code != 0


def test_completed_worker_with_live_descendant_is_not_success(tmp_path: Path) -> None:
    pid_file = tmp_path / "leader.pid"
    code = (
        "import json,os,subprocess,sys; sys.stdin.buffer.read(); "
        "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'], "
        "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); "
        f"open({str(pid_file)!r},'w').write(str(os.getpid())); "
        "print(json.dumps({'classification':'parsed_invariants_pass','root_count':0,'node_count':0,'invariant_result':'pass'}),flush=True)"
    )
    result: dict[str, object] | None = None
    teardown_problem: str | None = None
    try:
        result = run_worker(
            b"x",
            hashlib.sha256(b"x").hexdigest(),
            "x",
            timeout=2,
            command=[sys.executable, "-c", code],
        )
    finally:
        if pid_file.exists():
            pgid = int(pid_file.read_text(encoding="utf-8"))
            try:
                group_was_left = group_exists(pgid)
                if group_was_left:
                    cleanup_group(pgid)
            except PermissionError as exc:
                teardown_problem = f"process-group cleanup denied: {exc}; probe_result={result!r}"
    if teardown_problem is not None:
        pytest.fail(teardown_problem)
    assert result is not None
    assert result["classification"] == "worker_descendant_detected"
    assert result["cleanup_confirmed"] is True
    assert result["return_code"] == 0


def test_worker_io_interruption_cleans_owned_process_group(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pid_file = tmp_path / "leader.pid"
    code = f"import os,time; open({str(pid_file)!r},'w').write(str(os.getpid())); time.sleep(30)"
    selector_type = probe.selectors.DefaultSelector

    class InterruptingSelector:
        def __init__(self) -> None:
            self.inner = selector_type()

        def register(self, *args: Any, **kwargs: Any) -> Any:
            return self.inner.register(*args, **kwargs)

        def unregister(self, *args: Any, **kwargs: Any) -> Any:
            return self.inner.unregister(*args, **kwargs)

        def get_map(self) -> object:
            return self.inner.get_map()

        def select(self, *args: object, **kwargs: object) -> object:
            raise KeyboardInterrupt

        def close(self) -> None:
            self.inner.close()

    monkeypatch.setattr(probe.selectors, "DefaultSelector", InterruptingSelector)
    try:
        result = run_worker(
            b"x",
            hashlib.sha256(b"x").hexdigest(),
            "x",
            timeout=2,
            command=[sys.executable, "-c", code],
        )
    except KeyboardInterrupt:
        result = {"classification": "worker_interrupted", "cleanup_confirmed": False}
    finally:
        end = time.monotonic() + 1
        while not pid_file.exists() and time.monotonic() < end:
            time.sleep(0.01)
        if pid_file.exists():
            pgid = int(pid_file.read_text(encoding="utf-8"))
            group_was_left = group_exists(pgid)
            if group_was_left:
                cleanup_group(pgid)
    assert result["classification"] == "worker_interrupted"
    assert result["cleanup_confirmed"] is True


def test_descriptor_anchored_input_survives_ancestor_replacement(tmp_path: Path) -> None:
    safe = tmp_path / "safe"
    outside = tmp_path / "outside"
    safe.mkdir()
    outside.mkdir()
    (safe / "doc.md").write_bytes(b"safe bytes")
    (outside / "doc.md").write_bytes(b"outside bytes")
    root_fd = probe.open_directory(safe)
    moved = tmp_path / "safe-original"
    safe.rename(moved)
    safe.symlink_to(outside, target_is_directory=True)
    try:
        data = probe.read_regular_at(root_fd, "doc.md", expected_size=10)
    finally:
        os.close(root_fd)
    assert data == b"safe bytes"


def test_descriptor_anchored_output_never_follows_replaced_parent(tmp_path: Path) -> None:
    parent = tmp_path / "parent"
    outside = tmp_path / "outside"
    parent.mkdir()
    outside.mkdir()
    output = probe.create_output_directory(parent / "attempt")
    moved = tmp_path / "parent-original"
    parent.rename(moved)
    parent.symlink_to(outside, target_is_directory=True)
    try:
        probe.write_private_at(output, "summary.json", b"synthetic")
        assert (moved / "attempt" / "summary.json").read_bytes() == b"synthetic"
        assert not (outside / "summary.json").exists()
    finally:
        output.close()


def test_worker_wrong_package_origin_is_binding_failure(tmp_path: Path) -> None:
    impostor_root = tmp_path / "no-package"
    code = f"import probe; from pathlib import Path; probe.REPO_ROOT=Path({str(impostor_root)!r}); probe.worker_main()"
    payload = b"- synthetic\n"
    result = run_worker(
        payload,
        hashlib.sha256(payload).hexdigest(),
        "synthetic",
        timeout=3,
        command=[sys.executable, "-c", code],
    )
    assert result["classification"] == "binding_failure"


def test_worker_import_exception_is_binding_failure_not_parser_result() -> None:
    code = (
        "import builtins,probe; original=builtins.__import__; "
        "builtins.__import__=lambda name,*a,**k: (_ for _ in ()).throw(ImportError()) "
        "if name.startswith('logseq_matryca_parser') else original(name,*a,**k); probe.worker_main()"
    )
    payload = b"- synthetic\n"
    result = run_worker(
        payload,
        hashlib.sha256(payload).hexdigest(),
        "synthetic",
        timeout=3,
        command=[sys.executable, "-c", code],
    )
    assert result["classification"] == "binding_failure"


@pytest.mark.parametrize(
    ("packet", "classification"),
    [
        ({"payload": "YQ==", "sha256": "0" * 64, "page_title": "x"}, "binding_failure"),
        ({"payload": "YQ==", "sha256": "0" * 64, "page_title": "x", "extra": 1}, "binding_failure"),
        ({"payload": 7, "sha256": "0" * 64, "page_title": "x"}, "binding_failure"),
        (
            {"payload": "/w==", "sha256": hashlib.sha256(b"\xff").hexdigest(), "page_title": "x"},
            "binding_failure",
        ),
    ],
)
def test_exact_worker_input_packet_rejects_invalid_shapes_and_utf8(
    packet: dict[str, object], classification: str
) -> None:
    result = probe.decode_worker_packet(json.dumps(packet).encode())
    assert result["classification"] == classification


def test_worker_import_fault_is_binding_failure_not_parser_exception() -> None:
    result = probe.classify_worker_setup_error(ImportError("synthetic import fault"))
    assert result["classification"] == "binding_failure"


@pytest.mark.parametrize(
    ("parser_error", "invariant_error", "raw_content", "expected"),
    [
        (SyntheticDomainError, None, "x", "expected_domain_rejection"),
        (ValueError, None, "x", "unexpected_exception"),
        (None, None, "different", "raw_content_mismatch"),
        (None, AssertionError, "x", "tree_invariants"),
        (AssertionError, None, "x", "unexpected_exception"),
    ],
)
def test_parser_call_and_invariants_have_separate_classification(
    parser_error: type[BaseException] | None,
    invariant_error: type[BaseException] | None,
    raw_content: str,
    expected: str,
) -> None:
    class FakePage:
        def __init__(self, value: str) -> None:
            self.root_nodes: list[object] = []
            self.raw_content = value

    class FakeParser:
        def __init__(self, *, tab_size: int, strict_refs: bool) -> None:
            assert tab_size == 2 and strict_refs is False

        def parse(self, text: str, page_title: str) -> FakePage:
            if parser_error is not None:
                raise parser_error("synthetic")
            return FakePage(raw_content)

    def check_invariants(page: FakePage) -> None:
        if invariant_error is not None:
            raise invariant_error("synthetic invariant")

    result = probe.classify_parse(
        b"x", "synthetic", FakeParser, SyntheticDomainError, check_invariants
    )
    assert result["classification"] == expected


def test_file_aggregate_is_order_independent_and_observer_is_exactly_bound() -> None:
    hashes = {"b.py": "b" * 64, "a.py": "a" * 64}
    assert probe.aggregate_file_binding(hashes) == probe.aggregate_file_binding(
        dict(reversed(list(hashes.items())))
    )
    observer = {
        "artifacts": {"manifest_sha256": probe.EXPECTED_MANIFEST_SHA256},
        "authorization_id": "official-logseq-docs-text-copy-v2",
        "destination": {"path": probe.EXPECTED_OBSERVER_DESTINATION},
        "outcome": "deadline_qualified",
        "owned_children_reaped": True,
        "repository_head": probe.EXPECTED_HEAD,
        "run_id": "logseq-docs-08f855f-attempt-2-2026-10-05",
        "source": {"commit": probe.EXPECTED_SOURCE_COMMIT, "tree": probe.EXPECTED_SOURCE_TREE},
        "worker_complete": True,
    }
    raw = json.dumps(observer, separators=(",", ":")).encode()
    with pytest.raises(probe.ProbeStop, match="observer_sha256"):
        probe.verify_observer(raw, expected_sha256=probe.EXPECTED_OBSERVER_SHA256)


def _setup_synthetic_controller(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> tuple[Path, Path]:
    source_root = probe.REPO_ROOT
    source_probe = Path(probe.__file__)
    repo = tmp_path / "synthetic-repo"
    repo.mkdir()
    shutil.copytree(source_root / "src/logseq_matryca_parser", repo / "src/logseq_matryca_parser")
    (repo / "tests/parser_assurance").mkdir(parents=True)
    shutil.copy2(
        source_root / "tests/parser_assurance/invariants.py",
        repo / "tests/parser_assurance/invariants.py",
    )
    (repo / ".superpowers/sdd/official-corpus-offline-probe").mkdir(parents=True)
    copied_probe = repo / ".superpowers/sdd/official-corpus-offline-probe/probe.py"
    shutil.copy2(source_probe, copied_probe)
    shutil.copy2(
        Path(__file__), repo / ".superpowers/sdd/official-corpus-offline-probe/test_probe.py"
    )
    (repo / "pyproject.toml").write_text("[project]\nname='synthetic'\n", encoding="utf-8")
    (repo / "uv.lock").write_text("version=1\n", encoding="utf-8")

    attempt = (
        repo
        / ".superpowers/sdd/corpora/logseq-docs-08f855f24d66e4509b7ea808554c13b4649e6ee1/attempt-2"
    )
    corpus = attempt / "corpus/pages"
    corpus.mkdir(parents=True)
    page = b"- synthetic parent\n  - synthetic child\n"
    (corpus / "page.md").write_bytes(page)
    record = entry(repo, "pages/page.md", "corpus/pages/page.md", page)
    manifest = {
        "source": {"commit": "synthetic-commit", "tree": "synthetic-tree"},
        "files": [record],
    }
    manifest_bytes = json.dumps(manifest, separators=(",", ":")).encode()
    (attempt / "manifest.json").write_bytes(manifest_bytes)
    observer = {
        "artifacts": {"manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest()},
        "authorization_id": "official-logseq-docs-text-copy-v2",
        "destination": {"path": str(attempt)},
        "outcome": "deadline_qualified",
        "owned_children_reaped": True,
        "repository_head": "synthetic-head",
        "run_id": "logseq-docs-08f855f-attempt-2-2026-10-05",
        "source": {"commit": "synthetic-commit", "tree": "synthetic-tree"},
        "worker_complete": True,
    }
    observer_path = repo / probe.OBSERVER_RELATIVE_PATH
    observer_path.parent.mkdir(parents=True)
    observer_bytes = json.dumps(observer, separators=(",", ":")).encode()
    observer_path.write_bytes(observer_bytes)

    monkeypatch.setattr(probe, "REPO_ROOT", repo)
    monkeypatch.setattr(probe, "__file__", str(copied_probe))
    monkeypatch.setattr(probe, "EXPECTED_HEAD", "synthetic-head")
    monkeypatch.setattr(
        probe, "EXPECTED_MANIFEST_SHA256", hashlib.sha256(manifest_bytes).hexdigest()
    )
    monkeypatch.setattr(
        probe, "EXPECTED_OBSERVER_SHA256", hashlib.sha256(observer_bytes).hexdigest()
    )
    monkeypatch.setattr(probe, "EXPECTED_OBSERVER_DESTINATION", str(attempt))
    monkeypatch.setattr(probe, "EXPECTED_SOURCE_COMMIT", "synthetic-commit")
    monkeypatch.setattr(probe, "EXPECTED_SOURCE_TREE", "synthetic-tree")
    monkeypatch.setattr(probe, "EXPECTED_COUNT", 1)
    monkeypatch.setattr(
        probe,
        "_git",
        lambda *args, **kwargs: (
            "synthetic-head" if args == ("rev-parse", "HEAD") else "## synthetic"
        ),
    )
    monkeypatch.setattr(
        probe,
        "_runtime_binding",
        lambda deadline, *, phase_cutoff=None: {"python_version": "synthetic"},
    )
    monkeypatch.setattr(probe.sys, "argv", [str(copied_probe), "--run"])
    return repo, attempt


def test_synthetic_controller_runs_full_binding_parse_and_private_finalization(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo, attempt = _setup_synthetic_controller(monkeypatch, tmp_path)
    original_bounded_stage = probe._bounded_stage
    stage_names: list[str] = []

    def record_stage(name: str, operation: Any, **kwargs: Any) -> Any:
        stage_names.append(name)
        return original_bounded_stage(name, operation, **kwargs)

    monkeypatch.setattr(probe, "_bounded_stage", record_stage)
    reader_fd, writer_fd = os.pipe()
    monkeypatch.setattr(probe.sys, "stdout", _PipeStdout(writer_fd))
    try:
        assert probe.main() == 0
        witness_line = os.read(reader_fd, 4096).decode("utf-8").strip()
    finally:
        os.close(writer_fd)
        os.close(reader_fd)
    assert stage_names == [
        "preflight",
        "source_before",
        "runtime_before",
        "manifest",
        "observer",
        "output_create",
        "input_inventory",
        "input_read",
        "source_after",
        "runtime_after",
        "summary_write",
        "summary_verify",
    ]
    witness = json.loads(witness_line)
    output = repo / ".superpowers/sdd/official-corpus-offline-probe/attempt-1"
    summary_bytes = (output / "summary.json").read_bytes()
    summary = json.loads(summary_bytes)
    assert summary["status"] == "provisional"
    assert summary["diagnostic_outcome"] == "complete"
    assert summary["completed_count"] == summary["selection_count"] == 1
    assert summary["results"][0]["source_path"] == "pages/page.md"
    assert summary["results"][0]["node_count"] == 2
    assert "synthetic parent" not in summary_bytes.decode()
    assert output.stat().st_mode & 0o777 == 0o700
    assert (output / "summary.json").stat().st_mode & 0o777 == 0o600
    assert witness["outcome"] == "diagnostic_complete"
    assert witness["summary_sha256"] == hashlib.sha256(summary_bytes).hexdigest()
    assert witness["completed_count"] == witness["selection_count"] == 1
    assert witness["source_aggregate_sha256"] == summary["source_aggregate_sha256_after"]
    assert witness["runtime_sha256"] == probe._canonical_sha256(summary["runtime"])
    assert witness["completed_monotonic"] < witness["deadline_monotonic"]


@pytest.mark.parametrize(
    "failed_stage",
    [
        "preflight",
        "source_before",
        "runtime_before",
        "manifest",
        "observer",
        "output_create",
        "input_inventory",
        "input_read",
        "source_after",
        "runtime_after",
        "summary_write",
        "summary_verify",
    ],
)
def test_synthetic_controller_stage_failure_stops_without_witness(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    failed_stage: str,
) -> None:
    repo, _attempt = _setup_synthetic_controller(monkeypatch, tmp_path)
    original_bounded_stage = probe._bounded_stage
    stage_names: list[str] = []

    def fail_selected_stage(name: str, operation: Any, **kwargs: Any) -> Any:
        stage_names.append(name)
        if name == failed_stage:
            raise probe.StageFailure("synthetic_stage_failure", cleanup_confirmed=True)
        return original_bounded_stage(name, operation, **kwargs)

    monkeypatch.setattr(probe, "_bounded_stage", fail_selected_stage)
    assert probe.main() == 1
    assert stage_names[-1] == failed_stage
    assert failed_stage not in stage_names[stage_names.index(failed_stage) + 1 :]
    assert capsys.readouterr().out == ""
    summary_path = repo / ".superpowers/sdd/official-corpus-offline-probe/attempt-1/summary.json"
    if failed_stage == "summary_verify":
        assert json.loads(summary_path.read_bytes())["status"] == "provisional"
    else:
        assert not summary_path.exists()


def test_synthetic_git_preflight_failure_stops_before_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, _attempt = _setup_synthetic_controller(monkeypatch, tmp_path)
    stage_names: list[str] = []
    original_bounded_stage = probe._bounded_stage

    def fail_git(*_args: Any, **_kwargs: Any) -> str:
        raise OSError("synthetic git failure")

    def record_stage(name: str, operation: Any, **kwargs: Any) -> Any:
        stage_names.append(name)
        return original_bounded_stage(name, operation, **kwargs)

    monkeypatch.setattr(probe, "_git", fail_git)
    monkeypatch.setattr(probe, "_bounded_stage", record_stage)
    assert probe.main() == 1
    assert stage_names == ["preflight"]
    assert capsys.readouterr().out == ""
    assert not (repo / ".superpowers/sdd/official-corpus-offline-probe/attempt-1").exists()


def test_synthetic_interrupted_summary_write_preserves_partial_file_without_witness(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, _attempt = _setup_synthetic_controller(monkeypatch, tmp_path)

    def partial_write(
        output_path: Path, _identity: dict[str, Any], _data: bytes, *, deadline: float
    ) -> Any:
        probe._deadline_check(deadline)
        descriptor = os.open(
            output_path / "summary.json",
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        try:
            os.write(descriptor, b'{"status":"')
        finally:
            os.close(descriptor)
        raise probe.ProbeStop("synthetic_write_interrupted")

    monkeypatch.setattr(probe, "_write_provisional_file", partial_write)
    assert probe.main() == 1
    assert capsys.readouterr().out == ""
    partial = repo / ".superpowers/sdd/official-corpus-offline-probe/attempt-1/summary.json"
    assert partial.read_bytes() == b'{"status":"'
    assert partial.stat().st_mode & 0o777 == 0o600


def test_synthetic_summary_sync_failure_preserves_complete_provisional_bytes_without_witness(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, _attempt = _setup_synthetic_controller(monkeypatch, tmp_path)

    def fail_sync(_descriptor: int) -> None:
        raise OSError("synthetic fsync failure")

    monkeypatch.setattr(probe.os, "fsync", fail_sync)
    assert probe.main() == 1
    assert capsys.readouterr().out == ""
    summary = repo / ".superpowers/sdd/official-corpus-offline-probe/attempt-1/summary.json"
    summary_bytes = summary.read_bytes()
    parsed = json.loads(summary_bytes)
    assert parsed["status"] == "provisional"
    assert parsed["diagnostic_outcome"] == "complete"
    assert summary.stat().st_mode & 0o777 == 0o600


def test_synthetic_summary_identity_verification_failure_denies_witness(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, _attempt = _setup_synthetic_controller(monkeypatch, tmp_path)

    def fail_verification(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise probe.ProbeStop("synthetic_identity_mismatch")

    monkeypatch.setattr(probe, "_verify_provisional_file", fail_verification)
    assert probe.main() == 1
    assert capsys.readouterr().out == ""
    summary = repo / ".superpowers/sdd/official-corpus-offline-probe/attempt-1/summary.json"
    assert json.loads(summary.read_bytes())["status"] == "provisional"


def test_main_rejects_stdout_without_bounded_descriptor(monkeypatch: pytest.MonkeyPatch) -> None:
    deadline = time.monotonic() + 2
    witness = {
        "schema": 1,
        "outcome": "diagnostic_complete",
        "summary_sha256": "a" * 64,
        "source_aggregate_sha256": "b" * 64,
        "runtime_sha256": "c" * 64,
        "completed_count": 1,
        "selection_count": 1,
        "started_monotonic": deadline - 1,
        "completed_monotonic": deadline - 0.5,
        "deadline_monotonic": deadline,
    }
    output = io.StringIO()
    monkeypatch.setattr(probe, "run_probe", lambda: (0, witness))
    monkeypatch.setattr(probe.sys, "stdout", output)
    monkeypatch.setattr(probe.sys, "argv", ["probe.py", "--run"])
    assert probe.main() == 1
    assert output.getvalue() == ""


def test_parser_cleanup_after_deadline_cannot_retain_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_cleanup = probe._cleanup_process_group

    def late_cleanup(process: Any, deadline: float) -> bool:
        confirmed = original_cleanup(process, deadline)
        time.sleep(0.32)
        return confirmed

    monkeypatch.setattr(probe, "_cleanup_process_group", late_cleanup)
    code = (
        "import json,sys; sys.stdin.buffer.read(); "
        "print(json.dumps({'classification':'parsed_invariants_pass','root_count':0,"
        "'node_count':0,'invariant_result':'pass'}))"
    )
    result = run_worker(
        b"synthetic",
        hashlib.sha256(b"synthetic").hexdigest(),
        "synthetic",
        timeout=0.25,
        command=[sys.executable, "-c", code],
    )
    assert result["cleanup_confirmed"] is True
    assert result["classification"] == "timeout"


def _short_controller_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(probe, "RUN_SECONDS", 3.0)
    monkeypatch.setattr(probe, "FINAL_RESERVE_SECONDS", 0.1)
    monkeypatch.setattr(probe, "MAX_STAGE_SECONDS", 0.25)
    monkeypatch.setattr(probe, "STAGE_CLEANUP_SECONDS", 0.05)
    monkeypatch.setattr(probe, "MAX_CHILD_SECONDS", 0.5)


def _record_stage_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[list[str], list[tuple[str, bool]]]:
    original = probe._bounded_stage
    names: list[str] = []
    failures: list[tuple[str, bool]] = []

    def record(name: str, operation: Any, **kwargs: Any) -> Any:
        names.append(name)
        try:
            return original(name, operation, **kwargs)
        except probe.StageFailure as exc:
            failures.append((name, exc.cleanup_confirmed))
            raise

    monkeypatch.setattr(probe, "_bounded_stage", record)
    return names, failures


def _run_main_with_pipe(monkeypatch: pytest.MonkeyPatch) -> tuple[int, bytes]:
    reader_fd, writer_fd = os.pipe()
    writer_open = True
    try:
        monkeypatch.setattr(probe.sys, "stdout", _PipeStdout(writer_fd))
        try:
            exit_code = probe.main()
        finally:
            try:
                os.close(writer_fd)
            finally:
                writer_open = False
        deadline = time.monotonic() + 0.25
        output = bytearray()
        os.set_blocking(reader_fd, False)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("pipe capture deadline exceeded before EOF")
            readable, _, _ = select.select([reader_fd], [], [], remaining)
            if not readable:
                raise TimeoutError("pipe capture deadline exceeded before EOF")
            chunk = os.read(reader_fd, MAX_CHILD_OUTPUT + 1 - len(output))
            if not chunk:
                break
            output.extend(chunk)
            if len(output) > MAX_CHILD_OUTPUT:
                raise ValueError("pipe capture exceeded output limit")
        return exit_code, bytes(output)
    finally:
        if writer_open:
            with suppress(OSError):
                os.close(writer_fd)
        os.close(reader_fd)


def test_pipe_capture_times_out_while_extra_writer_remains_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_pipe = os.pipe
    held_writer_fd: int | None = None
    owned_fds: list[int] = []

    def pipe_with_held_writer() -> tuple[int, int]:
        nonlocal held_writer_fd
        reader_fd, writer_fd = original_pipe()
        owned_fds.extend((reader_fd, writer_fd))
        held_writer_fd = os.dup(writer_fd)
        return reader_fd, writer_fd

    monkeypatch.setattr(os, "pipe", pipe_with_held_writer)
    monkeypatch.setattr(probe, "main", lambda: 1)

    def release_held_writer() -> None:
        if held_writer_fd is not None:
            with suppress(OSError):
                os.close(held_writer_fd)

    release_safety = threading.Timer(0.8, release_held_writer)
    release_safety.daemon = True
    release_safety.start()
    started = time.monotonic()
    try:
        with pytest.raises(TimeoutError, match="pipe capture deadline"):
            _run_main_with_pipe(monkeypatch)
        elapsed = time.monotonic() - started
        assert held_writer_fd is not None
        os.fstat(held_writer_fd)
        assert elapsed < 0.5
        for descriptor in owned_fds:
            with pytest.raises(OSError):
                os.fstat(descriptor)
    finally:
        release_safety.cancel()
        if held_writer_fd is not None:
            with suppress(OSError):
                os.close(held_writer_fd)


def test_controller_reaps_stalled_synthetic_git_descendant(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    real_git = probe._git
    _setup_synthetic_controller(monkeypatch, tmp_path)
    _short_controller_clock(monkeypatch)
    names, failures = _record_stage_cleanup(monkeypatch)
    monkeypatch.setattr(probe, "_git", real_git)
    real_popen = probe.subprocess.Popen

    def stalled_git(_args: Any, **kwargs: Any) -> Any:
        return real_popen([sys.executable, "-c", "import time; time.sleep(10)"], **kwargs)

    monkeypatch.setattr(probe.subprocess, "Popen", stalled_git)
    monkeypatch.setattr(probe.sys, "argv", ["probe.py", "--run"])
    assert probe.main() == 1
    assert names == ["preflight"]
    assert failures == [("preflight", True)]
    assert capsys.readouterr().out == ""


def test_controller_reaps_stalled_selected_input_read(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _setup_synthetic_controller(monkeypatch, tmp_path)
    _short_controller_clock(monkeypatch)
    names, failures = _record_stage_cleanup(monkeypatch)
    original_read = probe.read_regular_at

    def stalled_selected_read(root_fd: int, relative: str, **kwargs: Any) -> bytes:
        if relative == "pages/page.md":
            time.sleep(10)
        return original_read(root_fd, relative, **kwargs)

    monkeypatch.setattr(probe, "read_regular_at", stalled_selected_read)
    monkeypatch.setattr(probe.sys, "argv", ["probe.py", "--run"])
    assert probe.main() == 1
    assert names[-1] == "input_read"
    assert failures == [("input_read", True)]
    assert capsys.readouterr().out == ""


def test_controller_final_bindings_use_original_deadline_reserve(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    real_runtime_binding = probe._runtime_binding
    repo, _attempt = _setup_synthetic_controller(monkeypatch, tmp_path)
    monkeypatch.setattr(probe, "_runtime_binding", real_runtime_binding)
    monkeypatch.setattr(probe, "RUN_SECONDS", 2.5)
    monkeypatch.setattr(probe, "FINAL_RESERVE_SECONDS", 1.5)
    monkeypatch.setattr(probe, "MAX_STAGE_SECONDS", 1.5)
    monkeypatch.setattr(probe, "STAGE_CLEANUP_SECONDS", 0.1)
    monkeypatch.setattr(probe, "MAX_CHILD_SECONDS", 1.5)
    active_stage = {"name": ""}
    original_stage = probe._bounded_stage
    original_read = probe.read_regular_at
    stage_names: list[str] = []
    failures: list[tuple[str, bool]] = []

    def read_after_work_cutoff(root_fd: int, relative: str, **kwargs: Any) -> bytes:
        if active_stage["name"] == "source_after" and relative.endswith(
            "official-corpus-offline-probe/probe.py"
        ):
            time.sleep(1.0)
        return original_read(root_fd, relative, **kwargs)

    def mark_stage(name: str, operation: Any, **kwargs: Any) -> Any:
        active_stage["name"] = name
        stage_names.append(name)
        try:
            return original_stage(name, operation, **kwargs)
        except probe.StageFailure as exc:
            failures.append((name, exc.cleanup_confirmed))
            raise

    monkeypatch.setattr(probe, "read_regular_at", read_after_work_cutoff)
    monkeypatch.setattr(probe, "_bounded_stage", mark_stage)
    monkeypatch.setattr(probe.sys, "argv", ["probe.py", "--run"])
    exit_code, output = _run_main_with_pipe(monkeypatch)
    assert stage_names[-1:] == ["summary_verify"]
    assert failures == []
    assert exit_code == 0
    witness = json.loads(output.decode("utf-8").strip())
    assert witness["completed_monotonic"] < witness["deadline_monotonic"]
    summary = repo / ".superpowers/sdd/official-corpus-offline-probe/attempt-1/summary.json"
    assert json.loads(summary.read_bytes())["diagnostic_outcome"] == "complete"


def test_controller_post_binding_read_timeout_denies_witness_and_publication(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, _attempt = _setup_synthetic_controller(monkeypatch, tmp_path)
    _short_controller_clock(monkeypatch)
    names: list[str] = []
    failures: list[tuple[str, bool]] = []
    active_stage = {"name": ""}
    original_stage = probe._bounded_stage
    original_read = probe.read_regular_at

    def stalled_post_binding_read(root_fd: int, relative: str, **kwargs: Any) -> bytes:
        if active_stage["name"] == "source_after" and relative.endswith(
            "official-corpus-offline-probe/probe.py"
        ):
            time.sleep(10)
        return original_read(root_fd, relative, **kwargs)

    def record_stage(name: str, operation: Any, **kwargs: Any) -> Any:
        active_stage["name"] = name
        names.append(name)
        try:
            return original_stage(name, operation, **kwargs)
        except probe.StageFailure as exc:
            failures.append((name, exc.cleanup_confirmed))
            raise

    monkeypatch.setattr(probe, "read_regular_at", stalled_post_binding_read)
    monkeypatch.setattr(probe, "_bounded_stage", record_stage)
    monkeypatch.setattr(probe.sys, "argv", ["probe.py", "--run"])
    exit_code, output = _run_main_with_pipe(monkeypatch)
    assert exit_code == 1
    assert names[-1] == "source_after"
    assert failures == [("source_after", True)]
    assert output == b""
    assert "summary_write" not in names and "summary_verify" not in names
    assert not (
        repo / ".superpowers/sdd/official-corpus-offline-probe/attempt-1/summary.json"
    ).exists()


def test_controller_low_level_summary_write_timeout_preserves_partial_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, _attempt = _setup_synthetic_controller(monkeypatch, tmp_path)
    _short_controller_clock(monkeypatch)
    names, failures = _record_stage_cleanup(monkeypatch)
    active_stage = {"name": ""}
    original_stage = probe._bounded_stage
    original_write = os.write

    def record_stage(name: str, operation: Any, **kwargs: Any) -> Any:
        active_stage["name"] = name
        return original_stage(name, operation, **kwargs)

    def stalled_summary_write(descriptor: int, data: bytes | memoryview) -> int:
        if active_stage["name"] == "summary_write" and stat.S_ISREG(os.fstat(descriptor).st_mode):
            prefix = bytes(data[: max(1, len(data) // 2)])
            original_write(descriptor, prefix)
            time.sleep(10)
        return original_write(descriptor, data)

    monkeypatch.setattr(probe, "_bounded_stage", record_stage)
    monkeypatch.setattr(probe.os, "write", stalled_summary_write)
    monkeypatch.setattr(probe.sys, "argv", ["probe.py", "--run"])
    exit_code, output = _run_main_with_pipe(monkeypatch)
    assert exit_code == 1
    assert names[-1] == "summary_write"
    assert failures == [("summary_write", True)]
    assert output == b""
    assert "summary_verify" not in names
    summary_path = repo / ".superpowers/sdd/official-corpus-offline-probe/attempt-1/summary.json"
    partial = summary_path.read_bytes()
    assert partial.startswith(b'{"candidate":')
    assert summary_path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(json.JSONDecodeError):
        json.loads(partial)


def test_controller_failure_pipe_read_is_eof_safe_and_bounded(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _setup_synthetic_controller(monkeypatch, tmp_path)
    original_stage = probe._bounded_stage

    def fail_preflight(name: str, operation: Any, **kwargs: Any) -> Any:
        if name == "preflight":
            raise probe.StageFailure("synthetic_preflight_failure", cleanup_confirmed=True)
        return original_stage(name, operation, **kwargs)

    monkeypatch.setattr(probe, "_bounded_stage", fail_preflight)
    monkeypatch.setattr(probe.sys, "argv", ["probe.py", "--run"])
    started = time.monotonic()
    exit_code, output = _run_main_with_pipe(monkeypatch)
    elapsed = time.monotonic() - started
    assert exit_code == 1
    assert output == b""
    assert elapsed < 0.5


def test_controller_sync_stall_preserves_provisional_summary_without_witness(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, _attempt = _setup_synthetic_controller(monkeypatch, tmp_path)
    _short_controller_clock(monkeypatch)
    names, failures = _record_stage_cleanup(monkeypatch)
    original_fsync = os.fsync
    active_stage = {"name": ""}
    original_stage = probe._bounded_stage

    def mark_stage(name: str, operation: Any, **kwargs: Any) -> Any:
        active_stage["name"] = name
        return original_stage(name, operation, **kwargs)

    def stalled_sync(descriptor: int) -> None:
        if active_stage["name"] == "summary_write":
            time.sleep(10)
        original_fsync(descriptor)

    monkeypatch.setattr(probe, "_bounded_stage", mark_stage)
    monkeypatch.setattr(probe.os, "fsync", stalled_sync)
    monkeypatch.setattr(probe.sys, "argv", ["probe.py", "--run"])
    assert probe.main() == 1
    assert names[-1] == "summary_write"
    assert failures == [("summary_write", True)]
    assert capsys.readouterr().out == ""
    summary_path = repo / ".superpowers/sdd/official-corpus-offline-probe/attempt-1/summary.json"
    summary = json.loads(summary_path.read_bytes())
    assert summary["status"] == "provisional"
    assert summary["diagnostic_outcome"] == "complete"


def test_controller_full_pipe_denies_terminal_witness_by_deadline(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, _attempt = _setup_synthetic_controller(monkeypatch, tmp_path)
    monkeypatch.setattr(probe, "RUN_SECONDS", 1.5)
    monkeypatch.setattr(probe, "FINAL_RESERVE_SECONDS", 0.2)
    monkeypatch.setattr(probe, "MAX_STAGE_SECONDS", 1.0)
    monkeypatch.setattr(probe, "STAGE_CLEANUP_SECONDS", 0.1)
    monkeypatch.setattr(probe, "MAX_CHILD_SECONDS", 0.8)
    reader_fd, writer_fd = os.pipe()
    os.set_blocking(writer_fd, False)
    filler_size = 0
    try:
        while True:
            try:
                filler_size += os.write(writer_fd, b"x" * 65536)
            except BlockingIOError:
                break

        class PipeOutput:
            def fileno(self) -> int:
                return writer_fd

        monkeypatch.setattr(probe.sys, "stdout", PipeOutput())
        monkeypatch.setattr(probe.sys, "argv", ["probe.py", "--run"])
        assert probe.main() == 1
    finally:
        os.close(writer_fd)
    try:
        received = bytearray()
        while True:
            chunk = os.read(reader_fd, 65536)
            if not chunk:
                break
            received.extend(chunk)
    finally:
        os.close(reader_fd)
    assert len(received) == filler_size
    assert received == b"x" * filler_size
    summary_path = repo / ".superpowers/sdd/official-corpus-offline-probe/attempt-1/summary.json"
    assert json.loads(summary_path.read_bytes())["diagnostic_outcome"] == "complete"
