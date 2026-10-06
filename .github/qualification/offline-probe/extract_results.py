"""Identity gate and bounded, privacy-safe report for hosted synthetic qualification."""

from __future__ import annotations

import argparse
import contextlib
import ctypes
import errno
import hashlib
import importlib.metadata
import importlib.util
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
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
QUAL = ROOT / ".github/qualification/offline-probe"
WORKFLOW = ROOT / ".github/workflows/parser-adversarial.yml"
FROZEN = {
    ".github/qualification/offline-probe/probe.py": "f0aa711cbb93937f05ea09d8ed42d33f9c97e11bdcf2709ee34e3f64ba658337",
    ".github/qualification/offline-probe/test_probe.py": "b42b34089df7275b726db744b3b4d7472d023db9da32921d78942854cf0df6e3",
    "tests/__init__.py": "2f7f2fea2e8766faaf8557de487d9b5e268c14c3c542f70dd3884992662d11f8",
    "tests/parser_assurance/__init__.py": "8016eeffd400b5d2312d188a01400bb98b2b80dfd6666757a31fa47f0c3dcc19",
    "uv.lock": "b7dd6aaccd39382737dd85fe0470f87fd0f856c748bf6761920e581fc9556cb4",
}
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
SAFE_PACKAGE = re.compile(r"[A-Za-z0-9._+!-]{1,128}\Z")
SAFE_RUNNER = re.compile(r"[A-Za-z0-9._-]{1,128}\Z")
SAFE_IMAGE_OS = re.compile(r"[A-Za-z0-9._-]{1,64}\Z")
PHASES = ("identity", "install", "sync", "verify", "strict", "remaining", "extract")
MAX_XML = 1024 * 1024
MAX_CAPTURE = 256 * 1024
MAX_JSON = 16 * 1024
PR_SET_CHILD_SUBREAPER = 36
PR_GET_CHILD_SUBREAPER = 37
LINUX_WALL = 0x40000000
SUPERVISOR_LEAK = 154
SUPERVISOR_TIMEOUT = 124
SUPERVISOR_OVERFLOW = 153
SUPERVISOR_INCOMPLETE = 125
STRICT_TEST = "test_completed_worker_with_live_descendant_is_not_success"
TEST_CLASSNAME = ".github.qualification.offline-probe.test_probe"
EXPECTED_TEST_NAMES = frozenset(
    """test_binding_maps_detect_source_change
test_bounded_stage_enforces_combined_output_limit
test_bounded_stage_interruption_cleans_owned_worker
test_bounded_stage_partial_start_failure_cleans_retained_process
test_bounded_stage_preserves_sanitized_operation_error
test_bounded_stage_reaping_failure_is_not_success
test_bounded_stage_rejects_malformed_frame_after_cleanup
test_bounded_stage_rejects_overflow_after_cleanup
test_bounded_stage_rejects_result_decoded_after_boundary[0.1-False-1.0-10.0-0.15-decode_timeout]
test_bounded_stage_rejects_result_decoded_after_boundary[1.0-True-0.3-0.1-0.25-lifecycle_deadline]
test_bounded_stage_round_trips_exact_verified_payload_bytes
test_bounded_stage_setup_failure_before_start_proves_no_child
test_bounded_stage_start_entered_without_pid_is_unconfirmed[KeyboardInterrupt-ambiguous_start_interrupted]
test_bounded_stage_start_entered_without_pid_is_unconfirmed[OSError-stage_start_failure]
test_bounded_stage_timeout_owns_and_reaps_blocking_stage[git]
test_bounded_stage_timeout_owns_and_reaps_blocking_stage[input_read]
test_bounded_stage_timeout_owns_and_reaps_blocking_stage[post_bindings]
test_bounded_stage_timeout_owns_and_reaps_blocking_stage[preflight]
test_bounded_stage_timeout_owns_and_reaps_blocking_stage[summary_sync]
test_bounded_stage_timeout_owns_and_reaps_blocking_stage[summary_write]
test_classifications_remain_distinct[raw0-expected_domain_rejection]
test_classifications_remain_distinct[raw1-unexpected_exception]
test_classifications_remain_distinct[raw2-raw_content_mismatch]
test_classifications_remain_distinct[raw3-tree_invariants]
test_completed_worker_with_live_descendant_is_not_success
test_controller_failure_pipe_read_is_eof_safe_and_bounded
test_controller_final_bindings_use_original_deadline_reserve
test_controller_full_pipe_denies_terminal_witness_by_deadline
test_controller_low_level_summary_write_timeout_preserves_partial_file
test_controller_post_binding_read_timeout_denies_witness_and_publication
test_controller_reaps_stalled_selected_input_read
test_controller_reaps_stalled_synthetic_git_descendant
test_controller_sync_stall_preserves_provisional_summary_without_witness
test_descriptor_anchored_input_survives_ancestor_replacement
test_descriptor_anchored_output_never_follows_replaced_parent
test_exact_worker_input_packet_rejects_invalid_shapes_and_utf8[packet0-binding_failure]
test_exact_worker_input_packet_rejects_invalid_shapes_and_utf8[packet1-binding_failure]
test_exact_worker_input_packet_rejects_invalid_shapes_and_utf8[packet2-binding_failure]
test_exact_worker_input_packet_rejects_invalid_shapes_and_utf8[packet3-binding_failure]
test_file_aggregate_is_order_independent_and_observer_is_exactly_bound
test_final_summary_late_success_becomes_bounded_incomplete
test_lifecycle_git_preflight_uses_remaining_deadline
test_main_rejects_stdout_without_bounded_descriptor
test_malformed_or_incomplete_child_result_is_unexpected[not-json]
test_malformed_or_incomplete_child_result_is_unexpected[{"classification":"parsed_invariants_pass"}]
test_new_output_directory_has_private_mode
test_nonzero_child_is_invalid_even_with_valid_json
test_optimized_python_is_rejected_before_parser_import
test_optimized_worker_refuses_to_claim_parse_result
test_output_directory_is_exclusive_and_preserves_existing
test_parser_call_and_invariants_have_separate_classification[AssertionError-None-x-unexpected_exception]
test_parser_call_and_invariants_have_separate_classification[None-AssertionError-x-tree_invariants]
test_parser_call_and_invariants_have_separate_classification[None-None-different-raw_content_mismatch]
test_parser_call_and_invariants_have_separate_classification[SyntheticDomainError-None-x-expected_domain_rejection]
test_parser_call_and_invariants_have_separate_classification[ValueError-None-x-unexpected_exception]
test_parser_cleanup_after_deadline_cannot_retain_success
test_pipe_capture_times_out_while_extra_writer_remains_open
test_real_worker_parses_synthetic_text_and_checks_input_hash
test_rejects_invalid_utf8_and_byte_mismatch
test_rejects_manifest_destination_escape[../escape.md]
test_rejects_manifest_destination_escape[/absolute.md]
test_rejects_manifest_destination_escape[corpus/../outside.md]
test_rejects_manifest_destination_escape[provenance/README.md]
test_rejects_symlinked_corpus_subdirectory
test_rejects_symlinked_input
test_summary_metadata_overflow_keeps_accurate_counts_and_fails
test_synthetic_controller_runs_full_binding_parse_and_private_finalization
test_synthetic_controller_stage_failure_stops_without_witness[input_inventory]
test_synthetic_controller_stage_failure_stops_without_witness[input_read]
test_synthetic_controller_stage_failure_stops_without_witness[manifest]
test_synthetic_controller_stage_failure_stops_without_witness[observer]
test_synthetic_controller_stage_failure_stops_without_witness[output_create]
test_synthetic_controller_stage_failure_stops_without_witness[preflight]
test_synthetic_controller_stage_failure_stops_without_witness[runtime_after]
test_synthetic_controller_stage_failure_stops_without_witness[runtime_before]
test_synthetic_controller_stage_failure_stops_without_witness[source_after]
test_synthetic_controller_stage_failure_stops_without_witness[source_before]
test_synthetic_controller_stage_failure_stops_without_witness[summary_verify]
test_synthetic_controller_stage_failure_stops_without_witness[summary_write]
test_synthetic_git_preflight_failure_stops_before_output
test_synthetic_interrupted_summary_write_preserves_partial_file_without_witness
test_synthetic_summary_identity_verification_failure_denies_witness
test_synthetic_summary_sync_failure_preserves_complete_provisional_bytes_without_witness
test_verified_inputs_preserve_literal_percent_and_send_exact_payload
test_worker_import_exception_is_binding_failure_not_parser_result
test_worker_import_fault_is_binding_failure_not_parser_exception
test_worker_io_interruption_cleans_owned_process_group
test_worker_output_overflow_stops_and_reaps
test_worker_rejects_wrong_hash_without_echoing_input
test_worker_result_never_echoes_page_title
test_worker_timeout_reaps_child
test_worker_wrong_package_origin_is_binding_failure""".splitlines()
)
STRICT_TEST_IDS = frozenset({(TEST_CLASSNAME, STRICT_TEST)})
REMAINING_TEST_IDS = frozenset(
    (TEST_CLASSNAME, name) for name in EXPECTED_TEST_NAMES if name != STRICT_TEST
)


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fail() -> None:
    raise ValueError("qualification evidence invalid")


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            fail()
        result[key] = value
    return result


def load_json(path: Path, maximum: int) -> Any:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
        fail()
    raw = path.read_bytes()
    if len(raw) > maximum:
        fail()
    return json.loads(raw, object_pairs_hook=reject_duplicate_keys)


def _wait_options(*, nohang: bool, nowait: bool = False) -> int:
    options = os.WEXITED | LINUX_WALL
    if nohang:
        options |= os.WNOHANG
    if nowait:
        options |= os.WNOWAIT
    return options


def _enable_subreaper() -> None:
    if not sys.platform.startswith("linux") or not all(
        (
            hasattr(os, "pidfd_open"),
            hasattr(os, "P_PIDFD"),
            hasattr(signal, "pidfd_send_signal"),
            hasattr(os, "waitid"),
            hasattr(os, "WNOWAIT"),
        )
    ):
        fail()
    task_root = Path(f"/proc/{os.getpid()}/task")
    if not task_root.is_dir() or len(tuple(task_root.iterdir())) != 1:
        fail()
    if signal.getsignal(signal.SIGCHLD) != signal.SIG_DFL:
        fail()
    libc = ctypes.CDLL(None, use_errno=True)
    prctl = libc.prctl
    prctl.restype = ctypes.c_int
    prctl.argtypes = (ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong)
    if prctl(PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0) != 0:
        fail()
    observed = ctypes.c_int()
    if (
        prctl(PR_GET_CHILD_SUBREAPER, ctypes.addressof(observed), 0, 0, 0) != 0
        or observed.value != 1
    ):
        fail()
    try:
        existing = os.waitid(os.P_ALL, 0, _wait_options(nohang=True, nowait=True))
    except ChildProcessError as error:
        if error.errno != errno.ECHILD:
            raise
    else:
        # A live existing child yields None with WNOHANG; either state means
        # the dedicated supervisor did not begin with an empty child set.
        del existing
        fail()


def _direct_children(deadline: float) -> list[int]:
    if time.monotonic() >= deadline:
        fail()
    path = Path(f"/proc/{os.getpid()}/task/{os.getpid()}/children")
    with path.open("rb") as stream:
        data = stream.read(64 * 1024 + 1)
    if len(data) > 64 * 1024 or time.monotonic() >= deadline:
        fail()
    try:
        text = data.decode("ascii")
        values = [int(item) for item in text.split()]
    except (UnicodeDecodeError, ValueError):
        fail()
    if any(pid <= 0 for pid in values) or len(values) != len(set(values)) or len(values) > 1024:
        fail()
    return values


def _open_child_pidfd(pid: int) -> tuple[int, bool] | None:
    try:
        descriptor = os.pidfd_open(pid, 0)
    except ProcessLookupError:
        return None
    try:
        info = os.waitid(os.P_PIDFD, descriptor, _wait_options(nohang=True, nowait=True))
    except ChildProcessError as error:
        os.close(descriptor)
        if error.errno == errno.ECHILD:
            return None
        raise
    if info is not None and info.si_pid != pid:
        os.close(descriptor)
        fail()
    return descriptor, info is not None


def _reap_child_pidfd(descriptor: int, pid: int) -> None:
    info = os.waitid(os.P_PIDFD, descriptor, _wait_options(nohang=False))
    if info is None or info.si_pid != pid:
        fail()


def _signal_pidfd(descriptor: int, pid: int, sig: signal.Signals) -> None:
    try:
        signal.pidfd_send_signal(descriptor, sig)
    except ProcessLookupError:
        return
    info = os.waitid(os.P_PIDFD, descriptor, _wait_options(nohang=True, nowait=True))
    if info is not None:
        _reap_child_pidfd(descriptor, pid)


def _observe_adoptees(
    leader_pid: int, *, deadline: float, terminate_live: bool, sig: signal.Signals
) -> bool:
    live_found = False
    for pid in _direct_children(deadline):
        if time.monotonic() >= deadline:
            fail()
        if pid == leader_pid:
            continue
        opened = _open_child_pidfd(pid)
        if opened is None:
            continue
        descriptor, exited = opened
        try:
            if exited:
                _reap_child_pidfd(descriptor, pid)
            elif terminate_live:
                live_found = True
                _signal_pidfd(descriptor, pid, sig)
            else:
                # Healthy-phase observation is intentionally passive for live children.
                continue
        finally:
            os.close(descriptor)
    return live_found


def _all_children_gone(deadline: float) -> bool:
    if time.monotonic() >= deadline:
        fail()
    try:
        info = os.waitid(os.P_ALL, 0, _wait_options(nohang=True, nowait=True))
    except ChildProcessError as error:
        if error.errno == errno.ECHILD:
            return True
        raise
    if info is None:
        return False
    if time.monotonic() >= deadline:
        fail()
    opened = _open_child_pidfd(info.si_pid)
    if opened is None:
        return False
    descriptor, exited = opened
    try:
        if exited:
            _reap_child_pidfd(descriptor, info.si_pid)
    finally:
        os.close(descriptor)
    return False


def _write_private_json(path: Path, value: dict[str, Any]) -> None:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("ascii")
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600
    )
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(payload)


def run_supervised(
    capture_path: Path,
    result_path: Path,
    seconds: int,
    command: list[str],
    xml_path: Path | None = None,
) -> int:
    """Supervise one Linux phase, continuously capping output and reaping owned children."""
    if not 1 <= seconds <= 300 or not command or command[0] not in {"uv", "python3"}:
        fail()
    _enable_subreaper()
    started = time.monotonic()
    deadline = started + seconds
    work_deadline = deadline - min(5.0, seconds / 4)
    output_fd = os.open(
        capture_path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    fifo_path: Path | None = None
    fifo_fd = -1
    xml_fd = -1
    try:
        if xml_path is not None:
            if not xml_path.parent.is_dir() or xml_path.exists() or xml_path.is_symlink():
                fail()
            fifo_path = xml_path.with_name(f"{xml_path.name}.fifo")
            os.mkfifo(fifo_path, 0o600)
            fifo_fd = os.open(fifo_path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))
            xml_fd = os.open(
                xml_path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
            option = f"--junitxml={xml_path}"
            if command.count(option) != 1:
                fail()
            command = [f"--junitxml={fifo_path}" if arg == option else arg for arg in command]
    except BaseException:
        if xml_fd >= 0:
            os.close(xml_fd)
        if fifo_fd >= 0:
            os.close(fifo_fd)
        if fifo_path is not None:
            with contextlib.suppress(FileNotFoundError):
                fifo_path.unlink()
        os.close(output_fd)
        raise

    process: subprocess.Popen[bytes] | None = None
    selector = selectors.DefaultSelector()
    child_status: int | None = None
    stdout_bytes = 0
    xml_bytes = 0
    stdout_eof = False
    xml_eof = xml_path is None
    overflow = False
    timed_out = False
    descendant_after_exit = False
    observer_failed = False
    cleanup_confirmed = False
    terminate_at = deadline
    reason = "supervisor_error"

    def read_stdout(output: Any) -> None:
        nonlocal stdout_bytes, stdout_eof, overflow
        if process is None or process.stdout is None or stdout_eof or time.monotonic() >= deadline:
            return
        try:
            chunk = os.read(process.stdout.fileno(), 65536)
        except BlockingIOError:
            return
        if not chunk:
            stdout_eof = True
            selector.unregister(process.stdout)
            return
        room = max(0, MAX_CAPTURE - stdout_bytes)
        kept = chunk[:room]
        if kept:
            output.write(kept)
            output.flush()
            stdout_bytes += len(kept)
        if len(chunk) > room:
            overflow = True

    def read_xml(*, final: bool = False) -> None:
        nonlocal xml_bytes, xml_eof, overflow
        if fifo_fd < 0 or xml_eof or overflow or time.monotonic() >= deadline:
            return
        try:
            chunk = os.read(fifo_fd, 65536)
        except BlockingIOError:
            return
        if not chunk:
            # Only the final ownership check can turn FIFO EOF into completion.
            if final:
                xml_eof = True
            return
        room = max(0, MAX_XML - xml_bytes)
        kept = memoryview(chunk[:room])
        while kept:
            if time.monotonic() >= deadline:
                fail()
            written = os.write(xml_fd, kept)
            if written <= 0:
                fail()
            kept = kept[written:]
        xml_bytes += min(len(chunk), room)
        if len(chunk) > room:
            overflow = True

    def poll_leader() -> int | None:
        nonlocal child_status
        if process is None:
            return None
        code = process.poll()
        if code is not None:
            child_status = code
        return code

    def signal_leader(sig: signal.Signals) -> None:
        if process is None or process.poll() is not None:
            return
        descriptor = os.pidfd_open(process.pid, 0)
        try:
            info = os.waitid(os.P_PIDFD, descriptor, _wait_options(nohang=True, nowait=True))
            if info is None:
                signal.pidfd_send_signal(descriptor, sig)
            else:
                process.poll()
        finally:
            os.close(descriptor)

    try:
        if xml_path is not None:
            os.fchmod(xml_fd, 0o600)
        with os.fdopen(output_fd, "wb") as output:
            output_fd = -1
            process = subprocess.Popen(
                command,
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                close_fds=True,
            )
            if process.stdout is None:
                fail()
            os.set_blocking(process.stdout.fileno(), False)
            selector.register(process.stdout, selectors.EVENT_READ)
            while True:
                now = time.monotonic()
                if now >= deadline:
                    reason = "timeout" if timed_out else "supervisor_error"
                    break
                leader_code = poll_leader()
                if overflow and reason != "capture_overflow":
                    reason = "capture_overflow"
                    if leader_code is None:
                        signal_leader(signal.SIGTERM)
                        terminate_at = min(terminate_at, now + 0.5)
                if leader_code is None:
                    _observe_adoptees(
                        process.pid, deadline=deadline, terminate_live=False, sig=signal.SIGTERM
                    )
                if leader_code is None and now >= work_deadline and not timed_out:
                    timed_out = True
                    reason = "timeout"
                    signal_leader(signal.SIGTERM)
                    terminate_at = min(deadline, now + 0.5)
                now = time.monotonic()
                if now >= deadline:
                    reason = "timeout" if timed_out else "supervisor_error"
                    break
                events = selector.select(min(0.05, max(0.0, deadline - now)))
                if events:
                    read_stdout(output)
                read_xml()
                if overflow and reason != "capture_overflow":
                    reason = "capture_overflow"
                    if process.poll() is None:
                        signal_leader(signal.SIGTERM)
                        terminate_at = min(terminate_at, time.monotonic() + 0.5)
                if time.monotonic() >= deadline:
                    reason = "timeout" if timed_out else "supervisor_error"
                    break
                leader_code = poll_leader()
                if (
                    leader_code is None
                    and (timed_out or overflow)
                    and time.monotonic() >= terminate_at
                ):
                    signal_leader(signal.SIGKILL)
                    terminate_at = deadline
                if leader_code is not None:
                    try:
                        live = _observe_adoptees(
                            process.pid if process.returncode is None else -1,
                            deadline=deadline,
                            terminate_live=True,
                            sig=signal.SIGTERM,
                        )
                    except BaseException:
                        reason = "supervisor_error"
                        observer_failed = True
                        live = True
                    if live and not timed_out and not overflow and not observer_failed:
                        descendant_after_exit = True
                        reason = "descendant_after_exit"
                    if live and time.monotonic() < deadline:
                        # Normal-exit descendants are terminated only after the leader exits.
                        time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
                        _observe_adoptees(
                            process.pid,
                            deadline=deadline,
                            terminate_live=True,
                            sig=signal.SIGKILL,
                        )
                    if not stdout_eof:
                        read_stdout(output)
                    read_xml()
                    if (
                        not observer_failed
                        and not live
                        and _all_children_gone(deadline)
                        and stdout_eof
                    ):
                        if xml_path is not None:
                            read_xml(final=True)
                        if xml_eof:
                            cleanup_confirmed = True
                            break
                if time.monotonic() >= deadline:
                    reason = "timeout" if timed_out else "supervisor_error"
                    break
            if process.poll() is None:
                try:
                    signal_leader(signal.SIGKILL)
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        reason = "supervisor_error"
                    else:
                        process.wait(timeout=remaining)
                except (OSError, subprocess.TimeoutExpired):
                    reason = "supervisor_error"
            child_status = process.returncode
            if reason == "supervisor_error" and cleanup_confirmed:
                reason = "complete"
            if overflow:
                reason = "capture_overflow"
            if timed_out:
                reason = "timeout"
            if descendant_after_exit and cleanup_confirmed and not timed_out and not overflow:
                reason = "descendant_after_exit"
    except BaseException:
        reason = "supervisor_error"
        if process is not None:
            try:
                signal_leader(signal.SIGKILL)
                while time.monotonic() < deadline:
                    if process.poll() is None:
                        time.sleep(min(0.02, max(0.0, deadline - time.monotonic())))
                        continue
                    _observe_adoptees(
                        -1, deadline=deadline, terminate_live=True, sig=signal.SIGKILL
                    )
                    if _all_children_gone(deadline):
                        process.wait()
                        cleanup_confirmed = True
                        break
                    time.sleep(min(0.02, max(0.0, deadline - time.monotonic())))
            except BaseException:
                cleanup_confirmed = False
    finally:
        selector.close()
        if process is not None and process.stdout is not None:
            process.stdout.close()
        if xml_fd >= 0:
            os.close(xml_fd)
        if fifo_fd >= 0:
            os.close(fifo_fd)
        if fifo_path is not None:
            with contextlib.suppress(FileNotFoundError):
                fifo_path.unlink()
        if output_fd >= 0:
            os.close(output_fd)

    if not cleanup_confirmed:
        reason = "supervisor_error" if reason not in {"timeout", "capture_overflow"} else reason
    result = {
        "child_exit_status": child_status,
        "reason": reason,
        "leader_reaped": process is not None and process.returncode is not None,
        "cleanup_confirmed": cleanup_confirmed,
        "live_descendant_after_normal_exit": descendant_after_exit,
        "stdout_bytes": stdout_bytes,
        "xml_bytes": xml_bytes,
        "xml_drained": xml_eof if xml_path is not None else None,
    }
    try:
        _write_private_json(result_path, result)
    except BaseException:
        return SUPERVISOR_INCOMPLETE
    if not cleanup_confirmed:
        return (
            SUPERVISOR_TIMEOUT
            if timed_out
            else SUPERVISOR_OVERFLOW
            if overflow
            else SUPERVISOR_INCOMPLETE
        )
    if timed_out:
        return SUPERVISOR_TIMEOUT
    if overflow:
        return SUPERVISOR_OVERFLOW
    if descendant_after_exit:
        return SUPERVISOR_LEAK
    if child_status is None:
        return SUPERVISOR_INCOMPLETE
    return child_status if child_status >= 0 else min(255, 128 - child_status)


def expected_inputs() -> dict[str, Any]:
    values = {
        "repository": os.environ.get("GITHUB_REPOSITORY", ""),
        "event": os.environ.get("GITHUB_EVENT_NAME", ""),
        "ref": os.environ.get("EXPECTED_REF", ""),
        "commit": os.environ.get("EXPECTED_COMMIT", ""),
        "workflow_sha256": os.environ.get("EXPECTED_WORKFLOW_SHA256", ""),
    }
    if values["repository"] != "MarcoPorcellato/logseq-matryca-parser":
        fail()
    if values["event"] != "workflow_dispatch" or os.environ.get("QUALIFICATION_ENABLED") != "true":
        fail()
    if not values["ref"].startswith("refs/heads/") or not 1 <= len(values["ref"]) <= 255:
        fail()
    if any(not 0x21 <= ord(char) <= 0x7E for char in values["ref"]):
        fail()
    if not HEX40.fullmatch(values["commit"]) or not HEX64.fullmatch(values["workflow_sha256"]):
        fail()
    if values["ref"] != os.environ.get("GITHUB_REF", ""):
        fail()
    if values["commit"] != os.environ.get("GITHUB_SHA", ""):
        fail()
    if os.environ.get("GITHUB_WORKFLOW_REF", "") != (
        f"{values['repository']}/.github/workflows/parser-adversarial.yml@{values['ref']}"
    ):
        fail()
    if os.environ.get("GITHUB_RUN_ATTEMPT", "") != "1":
        fail()
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    if not run_id.isascii() or not run_id.isdecimal() or not 1 <= int(run_id) <= 9007199254740991:
        fail()
    values["run_id"] = int(run_id)
    return values


def manifest_rows() -> tuple[list[dict[str, str]], str]:
    manifest_path = QUAL / "source-manifest.json"
    manifest = load_json(manifest_path, 256 * 1024)
    if not isinstance(manifest, dict) or set(manifest) != {"files", "source_aggregate_sha256"}:
        fail()
    if not isinstance(manifest["source_aggregate_sha256"], str) or not HEX64.fullmatch(
        manifest["source_aggregate_sha256"]
    ):
        fail()
    rows = manifest["files"]
    if not isinstance(rows, list) or len(rows) != 36:
        fail()
    names: list[str] = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"path", "sha256"}:
            fail()
        name, digest = row["path"], row["sha256"]
        if not isinstance(name, str) or not isinstance(digest, str) or not HEX64.fullmatch(digest):
            fail()
        if (
            name.startswith("/")
            or ".." in Path(name).parts
            or "\\" in name
            or Path(name).as_posix() != name
            or not name
        ):
            fail()
        names.append(name)
    if names != sorted(set(names)):
        fail()
    discovered = {
        p.relative_to(ROOT).as_posix() for p in (ROOT / "src/logseq_matryca_parser").rglob("*.py")
    }
    required = discovered | {
        "tests/parser_assurance/invariants.py",
        "pyproject.toml",
        "uv.lock",
        *FROZEN.keys(),
        ".github/workflows/parser-adversarial.yml",
        ".github/qualification/offline-probe/run_hosted_qualification.sh",
        ".github/qualification/offline-probe/extract_results.py",
    }
    if set(names) != required or len(required) != 36:
        fail()
    aggregate = hashlib.sha256()
    for row in rows:
        path = ROOT / row["path"]
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or sha(path) != row["sha256"]:
            fail()
        aggregate.update(row["path"].encode("utf-8") + b"\0")
        aggregate.update(row["sha256"].encode("ascii") + b"\n")
    result = aggregate.hexdigest()
    if manifest["source_aggregate_sha256"] != result:
        fail()
    for name, expected in FROZEN.items():
        row = next((item for item in rows if item["path"] == name), None)
        if row is None or row["sha256"] != expected:
            fail()
    if any("corpus" in path.parts for path in QUAL.rglob("*")):
        fail()
    return rows, result


def identity_gate() -> dict[str, Any]:
    inputs = expected_inputs()
    if not WORKFLOW.is_file() or sha(WORKFLOW) != inputs["workflow_sha256"]:
        fail()
    head = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        timeout=5,
        check=False,
    )
    if len(head.stdout) > 128 or len(head.stderr) > 4096 or head.returncode != 0:
        fail()
    if head.stdout.decode("ascii", "strict").strip() != inputs["commit"]:
        fail()
    rows, aggregate = manifest_rows()
    helper_hashes = {
        "launcher_sha256": sha(QUAL / "run_hosted_qualification.sh"),
        "extractor_sha256": sha(Path(__file__)),
    }
    envelope = {
        **inputs,
        "run_attempt": 1,
        "source_aggregate_sha256": aggregate,
        "hashes": helper_hashes,
    }
    validate_envelope(envelope)
    temp = Path(os.environ["RUNNER_TEMP"])
    if not temp.is_dir() or temp.is_symlink():
        fail()
    private = temp / "hosted-cleanup-qualification"
    private.mkdir(mode=0o700)
    os.chmod(private, 0o700)
    payload = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(payload) > 4096:
        fail()
    fd = os.open(private / "envelope.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(payload)
    return {"rows": rows, "aggregate": aggregate, "private": private, "envelope": envelope}


def validate_envelope(envelope: Any) -> dict[str, Any]:
    expected_keys = {
        "repository",
        "event",
        "ref",
        "commit",
        "workflow_sha256",
        "run_id",
        "run_attempt",
        "source_aggregate_sha256",
        "hashes",
    }
    if not isinstance(envelope, dict) or set(envelope) != expected_keys:
        fail()
    for key in (
        "repository",
        "event",
        "ref",
        "commit",
        "workflow_sha256",
        "source_aggregate_sha256",
    ):
        if not isinstance(envelope[key], str):
            fail()
    if not HEX40.fullmatch(envelope["commit"]) or any(
        not HEX64.fullmatch(envelope[key]) for key in ("workflow_sha256", "source_aggregate_sha256")
    ):
        fail()
    if (
        type(envelope["run_id"]) is not int
        or not 1 <= envelope["run_id"] <= 9007199254740991
        or type(envelope["run_attempt"]) is not int
        or envelope["run_attempt"] != 1
    ):
        fail()
    hashes = envelope["hashes"]
    if not isinstance(hashes, dict) or set(hashes) != {"launcher_sha256", "extractor_sha256"}:
        fail()
    if any(not isinstance(value, str) or not HEX64.fullmatch(value) for value in hashes.values()):
        fail()
    return envelope


def validate_execution_bindings(envelope: dict[str, Any]) -> tuple[list[dict[str, str]], str]:
    validate_envelope(envelope)
    inputs = expected_inputs()
    if any(envelope[key] != inputs[key] for key in inputs):
        fail()
    if sha(WORKFLOW) != envelope["workflow_sha256"]:
        fail()
    head = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        timeout=5,
        check=False,
    )
    if (
        head.returncode != 0
        or len(head.stdout) > 128
        or len(head.stderr) > 4096
        or head.stdout.decode("ascii", "strict").strip() != envelope["commit"]
    ):
        fail()
    rows, aggregate = manifest_rows()
    if aggregate != envelope["source_aggregate_sha256"]:
        fail()
    current_hashes = {
        "launcher_sha256": sha(QUAL / "run_hosted_qualification.sh"),
        "extractor_sha256": sha(Path(__file__)),
    }
    if current_hashes != envelope["hashes"]:
        fail()
    return rows, aggregate


def verify_runtime() -> dict[str, Any]:
    if sys.version_info[:3] != (3, 12, 13) or not __debug__:
        fail()
    os.environ["PYTHONPATH"] = ""
    if (
        os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD") != "1"
        or os.environ.get("PYTEST_ADDOPTS") != ""
        or os.environ.get("PYTEST_PLUGINS", "") != ""
    ):
        fail()
    temp = Path(os.environ["RUNNER_TEMP"])
    envelope = validate_envelope(
        load_json(temp / "hosted-cleanup-qualification/envelope.json", 4096)
    )
    validate_execution_bindings(envelope)
    expected = {
        "probe": QUAL / "probe.py",
        "tests": ROOT / "tests/__init__.py",
        "tests.parser_assurance": ROOT / "tests/parser_assurance/__init__.py",
        "tests.parser_assurance.invariants": ROOT / "tests/parser_assurance/invariants.py",
        "logseq_matryca_parser": ROOT / "src/logseq_matryca_parser/__init__.py",
    }
    for name, path in expected.items():
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        spec = importlib.util.find_spec(name)
        if spec is None or spec.origin is None or Path(spec.origin).resolve() != path.resolve():
            fail()
    for name in ("pytest", "_pytest"):
        spec = importlib.util.find_spec(name)
        if spec is None or spec.origin is None:
            fail()
        origin = Path(spec.origin).resolve()
        venv = (ROOT / ".venv").resolve()
        if Path(sys.prefix).resolve() != venv:
            fail()
        site_packages = (venv / "lib/python3.12/site-packages").resolve()
        if site_packages not in origin.parents:
            fail()
    config = temp / "pytest.ini"
    config_bytes = b"[pytest]\npythonpath = .\naddopts =\n"
    if config.exists():
        if (
            config.is_symlink()
            or not config.is_file()
            or config.stat().st_mode & 0o777 != 0o600
            or config.read_bytes() != config_bytes
        ):
            fail()
    else:
        fd = os.open(config, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(config_bytes)
    resolved_executable = Path(sys.executable).resolve(strict=True)
    return {
        "version": "3.12.13",
        "binary_sha256": sha(resolved_executable),
        "path_sha256": hashlib.sha256(os.fsencode(resolved_executable)).hexdigest(),
    }


def locked_packages() -> list[dict[str, str]]:
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    allowed: set[tuple[str, str]] = set()
    for item in lock["package"]:
        name = item.get("name")
        version = item.get("version")
        if not isinstance(name, str):
            fail()
        if version is None:
            if name.lower().replace("_", "-") != "logseq-matryca-parser":
                fail()
            continue
        if (
            not isinstance(version, str)
            or not SAFE_PACKAGE.fullmatch(name)
            or not SAFE_PACKAGE.fullmatch(version)
        ):
            fail()
        allowed.add((name.lower().replace("_", "-"), version))
    installed: dict[str, str] = {}
    for dist in importlib.metadata.distributions():
        name = dist.metadata.get("Name", "")
        version = dist.version
        normalized = name.lower().replace("_", "-")
        if (normalized, version) in allowed:
            if not SAFE_PACKAGE.fullmatch(name) or not SAFE_PACKAGE.fullmatch(version):
                fail()
            normalized_name = name.lower().replace("_", "-")
            if any(existing.lower().replace("_", "-") == normalized_name for existing in installed):
                fail()
            installed[name] = version
    return [{"name": name, "version": version} for name, version in sorted(installed.items())]


def parse_xml(path: Path, expected_ids: frozenset[tuple[str, str]]) -> dict[str, Any]:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_XML:
        fail()
    raw = path.read_bytes()
    if len(raw) > MAX_XML or b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        fail()
    root = ET.fromstring(raw)
    if root.tag != "testsuites" or len(root.findall("testsuite")) != 1:
        fail()
    suites = root.findall("testsuite")
    cases = suites[0].findall("testcase")
    if not cases or len(cases) > 91:
        fail()
    passed = skipped = failed = errors = 0
    identities: set[tuple[str, str]] = set()
    for case in cases:
        classname = case.attrib.get("classname", "")
        name = case.attrib.get("name", "")
        if not isinstance(classname, str) or not isinstance(name, str):
            fail()
        if (classname, name) in identities:
            fail()
        identities.add((classname, name))
        if (classname, name) not in expected_ids or classname != TEST_CLASSNAME:
            fail()
        outcomes = sum(case.find(tag) is not None for tag in ("failure", "error", "skipped"))
        if outcomes > 1:
            fail()
        if case.find("failure") is not None:
            failed += 1
        elif case.find("error") is not None:
            errors += 1
        elif case.find("skipped") is not None:
            skipped += 1
        else:
            passed += 1
    summary = suites[0]
    observed = {"tests": len(cases), "failures": failed, "errors": errors, "skipped": skipped}
    if any(
        not summary.attrib.get(key, "").isdecimal() or int(summary.attrib[key]) != value
        for key, value in observed.items()
    ):
        fail()
    return {
        "selected": len(cases),
        "passed": passed,
        "skipped": skipped,
        "failed": failed,
        "errors": errors,
        "_ids": identities,
    }


def strict_gate() -> None:
    private = Path(os.environ["RUNNER_TEMP"]) / "hosted-cleanup-qualification"
    counts = parse_xml(private / "strict.xml", STRICT_TEST_IDS)
    result = load_json(private / "strict.result", 4096)
    validate_run_result(result)
    if (
        counts["_ids"] != STRICT_TEST_IDS
        or counts["selected"] != 1
        or counts["passed"] != 1
        or counts["skipped"] != 0
        or counts["failed"] != 0
        or counts["errors"] != 0
        or result["reason"] != "complete"
        or result["child_exit_status"] != 0
        or not result["leader_reaped"]
        or not result["cleanup_confirmed"]
        or not result["xml_drained"]
    ):
        fail()


def validate_run_result(result: Any) -> dict[str, Any]:
    keys = {
        "child_exit_status",
        "reason",
        "leader_reaped",
        "cleanup_confirmed",
        "live_descendant_after_normal_exit",
        "stdout_bytes",
        "xml_bytes",
        "xml_drained",
    }
    if not isinstance(result, dict) or set(result) != keys:
        fail()
    status = result["child_exit_status"]
    if status is not None and (type(status) is not int or not -255 <= status <= 255):
        fail()
    if result["reason"] not in {
        "complete",
        "descendant_after_exit",
        "timeout",
        "capture_overflow",
        "supervisor_error",
    }:
        fail()
    for key in ("leader_reaped", "cleanup_confirmed", "live_descendant_after_normal_exit"):
        if type(result[key]) is not bool:
            fail()
    for key, maximum in (("stdout_bytes", MAX_CAPTURE), ("xml_bytes", MAX_XML)):
        if type(result[key]) is not int or not 0 <= result[key] <= maximum:
            fail()
    if result["xml_drained"] is not None and type(result["xml_drained"]) is not bool:
        fail()
    if result["cleanup_confirmed"] and not result["leader_reaped"]:
        fail()
    if (
        result["reason"] == "descendant_after_exit"
        and not result["live_descendant_after_normal_exit"]
    ):
        fail()
    return result


def phase_statuses(private: Path) -> dict[str, int | None]:
    path = private / "statuses.txt"
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o777 != 0o600 or info.st_size > 1024:
        fail()
    rows: list[tuple[str, int | None]] = []
    for line in path.read_text(encoding="ascii").splitlines():
        parts = line.split("\t")
        if len(parts) != 2:
            fail()
        name, raw = parts
        if raw == "null":
            value = None
        elif raw.isdecimal() and len(raw) <= 3:
            value = int(raw)
            if value > 255:
                fail()
        else:
            fail()
        rows.append((name, value))
    if tuple(name for name, _ in rows) != PHASES[:6]:
        fail()
    return dict(rows)


def phase_result(private: Path, phase: str, status: int | None) -> dict[str, Any] | None:
    path = private / f"{phase}.result"
    if status is None:
        if path.exists() or path.is_symlink():
            fail()
        return None
    return validate_run_result(load_json(path, 4096))


def test_outcome_consistent(
    counts: dict[str, Any], status: int, *, expected: frozenset[tuple[str, str]], allow_subset: bool
) -> bool:
    identities = counts["_ids"]
    if not identities or not identities.issubset(expected):
        fail()
    if not allow_subset and identities != expected:
        fail()
    test_failures = counts["failed"] + counts["errors"]
    if test_failures and status != 1:
        fail()
    if not test_failures and status not in (0,):
        fail()
    if status == 1 and not test_failures:
        fail()
    return test_failures > 0 or counts["skipped"] > 0


def validate_output(result: Any) -> dict[str, Any]:
    if not isinstance(result, dict) or set(result) != {
        "outcome",
        "phases",
        "hashes",
        "python",
        "packages",
        "runner",
        "binding",
    }:
        fail()
    if result["outcome"] not in {"PASS", "FAIL", "INCOMPLETE"}:
        fail()
    hashes = result["hashes"]
    hash_keys = {
        "probe_sha256",
        "tests_sha256",
        "lock_sha256",
        "tests_init_sha256",
        "assurance_init_sha256",
        "launcher_sha256",
        "extractor_sha256",
        "source_aggregate_sha256",
    }
    if (
        not isinstance(hashes, dict)
        or set(hashes) != hash_keys
        or any(
            not isinstance(value, str) or not HEX64.fullmatch(value) for value in hashes.values()
        )
    ):
        fail()
    python = result["python"]
    if (
        not isinstance(python, dict)
        or set(python) != {"version", "binary_sha256", "path_sha256"}
        or python["version"] != "3.12.13"
        or any(
            not isinstance(python[key], str) or not HEX64.fullmatch(python[key])
            for key in ("binary_sha256", "path_sha256")
        )
    ):
        fail()
    if not isinstance(result["packages"], list):
        fail()
    package_names: set[str] = set()
    for package in result["packages"]:
        if (
            not isinstance(package, dict)
            or set(package) != {"name", "version"}
            or not all(
                isinstance(package[key], str) and SAFE_PACKAGE.fullmatch(package[key])
                for key in ("name", "version")
            )
        ):
            fail()
        normalized = package["name"].lower().replace("_", "-")
        if normalized in package_names:
            fail()
        package_names.add(normalized)
    runner = result["runner"]
    if (
        not isinstance(runner, dict)
        or set(runner) != {"ImageOS", "ImageVersion", "kernel_release"}
        or not isinstance(runner["ImageOS"], str)
        or not SAFE_IMAGE_OS.fullmatch(runner["ImageOS"])
        or any(
            not isinstance(runner[key], str) or not SAFE_RUNNER.fullmatch(runner[key])
            for key in ("ImageVersion", "kernel_release")
        )
    ):
        fail()
    binding = result["binding"]
    if not isinstance(binding, dict) or set(binding) != {
        "repository",
        "event",
        "ref",
        "commit",
        "workflow_sha256",
        "run_id",
        "run_attempt",
    }:
        fail()
    if (
        binding["repository"] != "MarcoPorcellato/logseq-matryca-parser"
        or binding["event"] != "workflow_dispatch"
        or not isinstance(binding["ref"], str)
        or not binding["ref"].startswith("refs/heads/")
        or not 1 <= len(binding["ref"]) <= 255
        or any(not 0x21 <= ord(char) <= 0x7E for char in binding["ref"])
        or not isinstance(binding["commit"], str)
        or not HEX40.fullmatch(binding["commit"])
        or not isinstance(binding["workflow_sha256"], str)
        or not HEX64.fullmatch(binding["workflow_sha256"])
        or type(binding["run_id"]) is not int
        or not 1 <= binding["run_id"] <= 9007199254740991
        or type(binding["run_attempt"]) is not int
        or binding["run_attempt"] != 1
    ):
        fail()
    if not isinstance(result["phases"], list) or len(result["phases"]) != len(PHASES):
        fail()
    expected_phase_keys = {
        "phase",
        "exit_status",
        "selected",
        "passed",
        "skipped",
        "failed",
        "errors",
    }
    for index, phase in enumerate(result["phases"]):
        if (
            not isinstance(phase, dict)
            or set(phase) != expected_phase_keys
            or phase["phase"] != PHASES[index]
        ):
            fail()
        status = phase["exit_status"]
        if status is not None and (type(status) is not int or not 0 <= status <= 255):
            fail()
        for key in ("selected", "passed", "skipped", "failed", "errors"):
            count = phase[key]
            if count is not None and (type(count) is not int or not 0 <= count <= 91):
                fail()
        if status is None and any(
            phase[key] is not None
            for key in (
                "selected",
                "passed",
                "skipped",
                "failed",
                "errors",
            )
        ):
            fail()
        if status is not None and any(
            phase[key] is None for key in ("selected", "passed", "skipped", "failed", "errors")
        ):
            fail()
        if phase["phase"] not in ("strict", "remaining"):
            expected_counts = (0, 0, 0, 0, 0) if status is not None else (None,) * 5
            actual_counts = tuple(
                phase[key] for key in ("selected", "passed", "skipped", "failed", "errors")
            )
            if actual_counts != expected_counts:
                fail()
    return result


def report() -> tuple[dict[str, Any], int]:
    private = Path(os.environ["RUNNER_TEMP"]) / "hosted-cleanup-qualification"
    envelope = validate_envelope(load_json(private / "envelope.json", 4096))
    _rows, aggregate = validate_execution_bindings(envelope)
    statuses = phase_statuses(private)
    results = {
        phase: phase_result(private, phase, statuses[phase])
        for phase in PHASES[:6]
        if phase != "identity"
    }
    strict = None
    remaining = None
    if statuses["strict"] is not None:
        strict = parse_xml(private / "strict.xml", STRICT_TEST_IDS)
    if statuses["remaining"] is not None:
        remaining = parse_xml(private / "remaining.xml", REMAINING_TEST_IDS)

    if statuses["identity"] != 0:
        fail()
    if statuses["sync"] is not None and statuses["install"] != 0:
        fail()
    if statuses["verify"] is not None and statuses["sync"] != 0:
        fail()
    if statuses["strict"] is not None and statuses["verify"] != 0:
        fail()
    if statuses["remaining"] is not None and statuses["strict"] != 0:
        fail()

    for phase, run_result in results.items():
        status = statuses[phase]
        if run_result is None:
            continue
        expected_xml_drained = (
            run_result["reason"] in ("complete", "descendant_after_exit")
            and run_result["cleanup_confirmed"]
            if phase in ("strict", "remaining")
            else None
        )
        if (
            run_result["stdout_bytes"] > MAX_CAPTURE
            or run_result["xml_bytes"] > MAX_XML
            or run_result["xml_drained"] is not expected_xml_drained
        ):
            fail()
        if status in (SUPERVISOR_TIMEOUT, SUPERVISOR_OVERFLOW, SUPERVISOR_INCOMPLETE):
            continue
        if not run_result["leader_reaped"] or not run_result["cleanup_confirmed"]:
            fail()
        if run_result["reason"] == "descendant_after_exit":
            if status != SUPERVISOR_LEAK or not run_result["live_descendant_after_normal_exit"]:
                fail()
        elif run_result["reason"] != "complete":
            fail()
        else:
            child_status = run_result["child_exit_status"]
            expected_status = (
                min(255, 128 - child_status)
                if child_status is not None and child_status < 0
                else child_status
            )
            if status != expected_status:
                fail()

    strict_fail = False
    strict_pass = False
    strict_result = results.get("strict")
    if strict is not None and strict_result is not None:
        raw_status = strict_result["child_exit_status"]
        if strict_result["reason"] == "descendant_after_exit":
            strict_fail = True
        elif strict_result["reason"] == "complete" and raw_status is not None:
            strict_fail = test_outcome_consistent(
                strict,
                min(255, 128 - raw_status) if raw_status < 0 else raw_status,
                expected=STRICT_TEST_IDS,
                allow_subset=False,
            )
            strict_pass = (
                strict_fail is False
                and statuses["strict"] == 0
                and strict["_ids"] == STRICT_TEST_IDS
                and strict["passed"] == 1
                and strict["skipped"] == strict["failed"] == strict["errors"] == 0
            )
    remaining_fail = False
    remaining_pass = False
    remaining_result = results.get("remaining")
    if remaining is not None and remaining_result is not None:
        raw_status = remaining_result["child_exit_status"]
        if remaining_result["reason"] == "descendant_after_exit":
            remaining_fail = True
        elif remaining_result["reason"] == "complete" and raw_status is not None:
            remaining_fail = test_outcome_consistent(
                remaining,
                min(255, 128 - raw_status) if raw_status < 0 else raw_status,
                expected=REMAINING_TEST_IDS,
                allow_subset=True,
            )
            remaining_pass = (
                remaining_fail is False
                and statuses["remaining"] == 0
                and remaining["_ids"] == REMAINING_TEST_IDS
                and remaining["selected"] == 91
                and remaining["passed"] == 91
                and remaining["skipped"] == remaining["failed"] == remaining["errors"] == 0
            )

    prerequisite_pass = all(
        statuses[name] == 0 for name in ("identity", "install", "sync", "verify")
    )
    phase_incomplete = any(
        value in (SUPERVISOR_TIMEOUT, SUPERVISOR_OVERFLOW, SUPERVISOR_INCOMPLETE, 137, 143)
        for value in statuses.values()
    ) or any(
        status not in (0, None)
        for name, status in statuses.items()
        if name in ("install", "sync", "verify")
    )
    outcome = (
        "PASS"
        if prerequisite_pass and strict_pass and remaining_pass
        else "FAIL"
        if strict_fail or remaining_fail
        else "INCOMPLETE"
    )
    if phase_incomplete:
        outcome = "INCOMPLETE"

    phase_rows: list[dict[str, Any]] = []
    for phase in PHASES:
        status = 0 if phase == "extract" else statuses.get(phase)
        counts = strict if phase == "strict" else remaining if phase == "remaining" else None
        if phase in ("strict", "remaining") and status is None:
            counts = None
        elif phase not in ("strict", "remaining"):
            counts = (
                {"selected": 0, "passed": 0, "skipped": 0, "failed": 0, "errors": 0}
                if status is not None
                else None
            )
        phase_rows.append(
            {
                "phase": phase,
                "exit_status": status,
                "selected": counts["selected"] if counts else None,
                "passed": counts["passed"] if counts else None,
                "skipped": counts["skipped"] if counts else None,
                "failed": counts["failed"] if counts else None,
                "errors": counts["errors"] if counts else None,
            }
        )

    hashes = {
        "probe_sha256": FROZEN[".github/qualification/offline-probe/probe.py"],
        "tests_sha256": FROZEN[".github/qualification/offline-probe/test_probe.py"],
        "lock_sha256": FROZEN["uv.lock"],
        "tests_init_sha256": FROZEN["tests/__init__.py"],
        "assurance_init_sha256": FROZEN["tests/parser_assurance/__init__.py"],
        **envelope["hashes"],
        "source_aggregate_sha256": aggregate,
    }
    python = verify_runtime()
    image_os = os.environ.get("ImageOS", "")  # noqa: SIM112
    image_version = os.environ.get("ImageVersion", "")  # noqa: SIM112
    kernel = platform.release()
    if (
        not SAFE_IMAGE_OS.fullmatch(image_os)
        or not SAFE_RUNNER.fullmatch(image_version)
        or not SAFE_RUNNER.fullmatch(kernel)
    ):
        fail()
    result = {
        "outcome": outcome,
        "phases": phase_rows,
        "hashes": hashes,
        "python": python,
        "packages": locked_packages(),
        "runner": {"ImageOS": image_os, "ImageVersion": image_version, "kernel_release": kernel},
        "binding": {
            "repository": envelope["repository"],
            "event": envelope["event"],
            "ref": envelope["ref"],
            "commit": envelope["commit"],
            "workflow_sha256": envelope["workflow_sha256"],
            "run_id": envelope["run_id"],
            "run_attempt": envelope["run_attempt"],
        },
    }
    validate_output(result)
    blob = json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    if len(blob) > MAX_JSON:
        fail()
    return result, len(blob)


def validate_run_cli(argv: list[str]) -> None:
    if not argv or argv[0] != "run":
        return
    try:
        separator = argv.index("--")
    except ValueError:
        fail()
    if separator == len(argv) - 1:
        fail()
    required = {"--capture", "--result", "--timeout"}
    allowed = required | {"--xml-capture"}
    seen: set[str] = set()
    index = 1
    while index < separator:
        option = argv[index]
        if option not in allowed or option in seen or index + 1 >= separator:
            fail()
        value = argv[index + 1]
        if not value or value.startswith("--"):
            fail()
        seen.add(option)
        index += 2
    if not required.issubset(seen):
        fail()


def main() -> int:
    raw_args = sys.argv[1:]
    validate_run_cli(raw_args)
    parser = argparse.ArgumentParser(add_help=False)
    subparsers = parser.add_subparsers(dest="mode", required=True)
    for name in ("identity", "verify", "strict", "report"):
        subparsers.add_parser(name, add_help=False)
    run_parser = subparsers.add_parser("run", add_help=False)
    run_parser.add_argument("--capture", required=True)
    run_parser.add_argument("--result", required=True)
    run_parser.add_argument("--timeout", required=True, type=int)
    run_parser.add_argument("--xml-capture")
    run_parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(raw_args)
    try:
        if args.mode == "identity":
            identity_gate()
        elif args.mode == "verify":
            verify_runtime()
        elif args.mode == "strict":
            strict_gate()
        elif args.mode == "run":
            command = args.command[1:] if args.command[:1] == ["--"] else args.command
            if not command:
                fail()
            sys.stdout.write(
                str(
                    run_supervised(
                        Path(args.capture),
                        Path(args.result),
                        args.timeout,
                        command,
                        Path(args.xml_capture) if args.xml_capture else None,
                    )
                )
            )
            sys.stdout.write("\n")
        else:
            result, _ = report()
            sys.stdout.write(
                json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            )
            sys.stdout.write("\n")
        return 0
    except BaseException:
        if args.mode == "report":
            sys.stdout.write('{"outcome":"INCOMPLETE"}\n')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
