from __future__ import annotations

import json
import math
import queue
import socket
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from logseq_matryca_parser import local_graph_assurance
from logseq_matryca_parser.kinetic import app
from logseq_matryca_parser.local_graph_assurance import (
    AssuranceLimits,
    _network_denied,
    _safe_report,
    run_local_graph_assurance,
    run_local_graph_assurance_self_test,
)
from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage

runner = CliRunner()


def _vault(tmp_path: Path) -> Path:
    root = tmp_path / "vault"
    (root / "pages").mkdir(parents=True)
    (root / "journals").mkdir()
    return root


def _finding_codes(report: dict[str, object]) -> set[str]:
    findings = report["findings"]
    assert isinstance(findings, list)
    return {str(item["code"]) for item in findings if isinstance(item, dict)}


def test_self_test_uses_the_isolated_worker_and_returns_only_safe_aggregates() -> None:
    report = run_local_graph_assurance_self_test()
    encoded = json.dumps(report, sort_keys=True)

    assert report["status"] == "passed"
    assert set(report) == {"schema_version", "status", "limits", "observed", "findings", "runtime"}
    assert "Alpha" not in encoded
    assert "11111111-1111-1111-1111-111111111111" not in encoded
    assert "matryca-assurance-" not in encoded


def test_assurance_reports_an_aggregate_broken_reference_without_content_or_paths(
    tmp_path: Path,
) -> None:
    root = _vault(tmp_path)
    secret = "do-not-disclose-this-private-markdown"
    missing = "00000000-0000-0000-0000-000000000099"
    (root / "pages" / "Private title.md").write_text(
        f"- {secret} (({missing}))\n", encoding="utf-8"
    )

    report = run_local_graph_assurance(root)
    encoded = json.dumps(report, sort_keys=True)

    assert report["status"] == "findings"
    assert "graph.unresolved_block_reference" in _finding_codes(report)
    assert secret not in encoded
    assert missing not in encoded
    assert "Private title" not in encoded
    assert str(root) not in encoded


def test_assurance_rejects_a_symlink_before_reading_target(tmp_path: Path) -> None:
    root = _vault(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("- outside secret\n", encoding="utf-8")
    (root / "pages" / "Escape.md").symlink_to(outside)

    report = run_local_graph_assurance(root)

    assert report["status"] == "findings"
    assert _finding_codes(report) == {"vault.symlink_rejected"}


def test_assurance_rejects_a_dangling_root_directory_symlink(tmp_path: Path) -> None:
    root = tmp_path / "vault"
    root.mkdir()
    (root / "pages").symlink_to(root / "missing-pages", target_is_directory=True)

    report = run_local_graph_assurance(root)

    assert report["status"] == "findings"
    assert _finding_codes(report) == {"vault.root_directory_rejected"}


def test_assurance_fails_closed_on_declared_file_limits(tmp_path: Path) -> None:
    root = _vault(tmp_path)
    (root / "pages" / "One.md").write_text("- one\n", encoding="utf-8")
    (root / "pages" / "Two.md").write_text("- two\n", encoding="utf-8")

    report = run_local_graph_assurance(root, AssuranceLimits(max_files=1))

    assert report["status"] == "limit_exceeded"
    assert _finding_codes(report) == {"vault.max_files_exceeded"}


def test_assurance_detects_page_title_collisions_without_disclosing_titles(tmp_path: Path) -> None:
    root = _vault(tmp_path)
    (root / "pages" / "Private Daily.md").write_text("- page entry\n", encoding="utf-8")
    (root / "journals" / "Private Daily.md").write_text("- journal entry\n", encoding="utf-8")

    report = run_local_graph_assurance(root)
    encoded = json.dumps(report, sort_keys=True)

    assert report["status"] == "findings"
    assert "graph.page_title_collision" in _finding_codes(report)
    assert "Private Daily" not in encoded


def test_assurance_rechecks_total_bytes_while_reading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _vault(tmp_path)
    (root / "pages" / "One.md").write_text("- x\n", encoding="utf-8")
    monkeypatch.setattr(
        local_graph_assurance,
        "_read_regular_file",
        lambda *_args: b"- larger replacement\n",
    )

    report = local_graph_assurance._assure(str(root), AssuranceLimits(max_total_bytes=4))

    assert report["status"] == "limit_exceeded"
    assert _finding_codes(report) == {"vault.max_total_bytes_exceeded"}


@pytest.mark.parametrize("kind", ["symlink", "non_regular", "outside", "open_failure"])
def test_guarded_read_rejects_unsafe_or_unreadable_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    root = _vault(tmp_path)
    path = root / "pages" / "entry.md"
    path.write_text("- safe\n", encoding="utf-8")
    if kind == "symlink":
        target = tmp_path / "outside.md"
        target.write_text("- outside\n", encoding="utf-8")
        path.unlink()
        path.symlink_to(target)
    elif kind == "non_regular":
        path.unlink()
        path.mkdir()
    elif kind == "outside":
        path = tmp_path / "outside.md"
        path.write_text("- outside\n", encoding="utf-8")

        def reject_outside_open(*_args: object, **_kwargs: object) -> int:
            raise AssertionError("outside-root file must not be opened")

        monkeypatch.setattr(local_graph_assurance.os, "open", reject_outside_open)
    elif kind == "open_failure":
        monkeypatch.setattr(local_graph_assurance.os, "open", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError()))

    assert local_graph_assurance._read_regular_file(root, path, 100) is None


def test_guarded_read_rejects_descriptor_identity_change(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _vault(tmp_path)
    path = root / "pages" / "entry.md"
    path.write_text("- safe\n", encoding="utf-8")
    original_fstat = local_graph_assurance.os.fstat
    calls = 0

    def changed_identity(descriptor: int):
        nonlocal calls
        calls += 1
        result = original_fstat(descriptor)
        return result if calls == 1 else SimpleNamespace(
            st_mode=result.st_mode, st_ino=result.st_ino + 1, st_dev=result.st_dev
        )

    monkeypatch.setattr(local_graph_assurance.os, "fstat", changed_identity)
    assert local_graph_assurance._read_regular_file(root, path, 100) is None


def test_guarded_read_rejects_post_read_size_change(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _vault(tmp_path)
    path = root / "pages" / "entry.md"
    path.write_text("- safe\n", encoding="utf-8")
    calls = 0

    def changed_size(_descriptor: int, _size: int) -> bytes:
        nonlocal calls
        calls += 1
        return b"- safe\nx\n" if calls == 1 else b""

    monkeypatch.setattr(local_graph_assurance.os, "read", changed_size)
    assert local_graph_assurance._read_regular_file(root, path, 100) is None


def test_parser_findings_are_aggregated_without_exception_or_source_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _vault(tmp_path)
    secret = "private-parser-content"
    (root / "pages" / "one.md").write_text(f"- {secret}\n", encoding="utf-8")
    (root / "pages" / "two.md").write_bytes(b"\xff\xfe")
    (root / "pages" / "three.md").write_text("- third\n", encoding="utf-8")
    parsed = LogseqPage(
        title="controlled",
        raw_content="",
        root_nodes=[LogseqNode(uuid="synthetic", content="", indent_level=0)],
    )
    parser_calls = 0

    def parse(*_args: object, **_kwargs: object) -> LogseqPage:
        nonlocal parser_calls
        parser_calls += 1
        if parser_calls == 1:
            return parsed
        raise RuntimeError(secret)

    monkeypatch.setattr(local_graph_assurance.StackMachineParser, "parse", parse)
    report = local_graph_assurance._assure(str(root), AssuranceLimits())
    encoded = json.dumps(report, sort_keys=True)
    findings = report["findings"]
    assert isinstance(findings, list)
    assert report["status"] == "findings"
    assert "parse.invalid_utf8" in _finding_codes(report)
    assert "parse.unclassified_failure" in _finding_codes(report)
    assert secret not in encoded
    assert report["observed"]["parsed_pages"] == 1  # type: ignore[index]


def test_parser_aggregates_structure_duplicate_and_unresolved_findings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _vault(tmp_path)
    (root / "pages" / "one.md").write_text("- one\n", encoding="utf-8")
    (root / "pages" / "two.md").write_text("- two\n", encoding="utf-8")
    node = LogseqNode(
        uuid="same",
        source_uuid="source",
        content="",
        indent_level=0,
        properties={"id": "source-id"},
        parent_id="wrong",
        block_refs=["missing-a", "missing-b"],
        path=["wrong"],
    )
    page = LogseqPage(title="same-title", raw_content="", root_nodes=[node])
    monkeypatch.setattr(local_graph_assurance.StackMachineParser, "parse", lambda *_args, **_kwargs: page)
    report = local_graph_assurance._assure(str(root), AssuranceLimits())
    findings = report["findings"]
    assert isinstance(findings, list)
    counts = {item["code"]: item["count"] for item in findings if isinstance(item, dict)}
    assert counts["graph.page_title_collision"] == 1
    assert counts["graph.structure_invariant_violation"] == 2
    assert counts["graph.duplicate_synthetic_identity"] == 1
    assert counts["graph.duplicate_source_identity"] == 2
    assert counts["graph.unresolved_block_reference"] == 4


def test_assurance_reports_only_directory_read_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _vault(tmp_path)
    (root / "pages" / "Visible.md").write_text("- visible\n", encoding="utf-8")
    original_iterdir = Path.iterdir

    def fail_pages(directory: Path):
        if directory == root / "pages":
            raise OSError("unavailable")
        return original_iterdir(directory)

    monkeypatch.setattr(Path, "iterdir", fail_pages)

    report = local_graph_assurance._assure(str(root), AssuranceLimits())

    assert report["status"] == "error"
    assert _finding_codes(report) == {"vault.directory_read_error"}
    assert report["observed"] == {
        "markdown_files": 0,
        "total_bytes": 0,
        "parsed_pages": 0,
        "parsed_nodes": 0,
        "root_nodes": 0,
        "block_references": 0,
    }


def test_assurance_reports_only_entry_stat_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _vault(tmp_path)
    entry = root / "pages" / "Visible.md"
    entry.write_text("- visible\n", encoding="utf-8")
    original_lstat = Path.lstat

    def fail_entry(path: Path):
        if path == entry:
            raise OSError("unavailable")
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", fail_entry)

    report = local_graph_assurance._assure(str(root), AssuranceLimits())

    assert report["status"] == "error"
    assert _finding_codes(report) == {"vault.entry_stat_error"}
    assert report["observed"] == {
        "markdown_files": 0,
        "total_bytes": 0,
        "parsed_pages": 0,
        "parsed_nodes": 0,
        "root_nodes": 0,
        "block_references": 0,
    }


def test_assurance_ignores_excluded_directories_and_non_markdown_entries(tmp_path: Path) -> None:
    root = _vault(tmp_path)
    for directory in (".git", ".recycle", "logseq"):
        (root / "pages" / directory).mkdir()
        (root / "pages" / directory / "Hidden.md").write_text("- hidden\n", encoding="utf-8")
    (root / "pages" / "Visible.md").write_text("- visible\n", encoding="utf-8")
    (root / "pages" / "notes.txt").write_text("not markdown\n", encoding="utf-8")

    report = run_local_graph_assurance(root)

    assert report["status"] == "passed"
    observed = report["observed"]
    assert isinstance(observed, dict)
    assert observed["markdown_files"] == 1
    assert observed["parsed_pages"] == 1


@pytest.mark.parametrize("root_name", ["pages", "journals"])
def test_assurance_rejects_non_directory_roots(tmp_path: Path, root_name: str) -> None:
    root = tmp_path / "vault"
    root.mkdir()
    (root / root_name).write_text("not a directory\n", encoding="utf-8")

    report = run_local_graph_assurance(root)

    assert report["status"] == "findings"
    assert _finding_codes(report) == {"vault.root_directory_rejected"}


def test_assurance_enforces_max_file_bytes_during_traversal(tmp_path: Path) -> None:
    root = _vault(tmp_path)
    (root / "pages" / "Too large.md").write_text("- too large\n", encoding="utf-8")

    report = run_local_graph_assurance(root, AssuranceLimits(max_file_bytes=1))

    assert report["status"] == "limit_exceeded"
    assert _finding_codes(report) == {"vault.max_file_bytes_exceeded"}


def test_assurance_enforces_max_total_bytes_during_traversal(tmp_path: Path) -> None:
    root = _vault(tmp_path)
    (root / "pages" / "One.md").write_text("- one\n", encoding="utf-8")
    (root / "pages" / "Two.md").write_text("- two\n", encoding="utf-8")

    report = run_local_graph_assurance(root, AssuranceLimits(max_total_bytes=7, max_file_bytes=6))

    assert report["status"] == "limit_exceeded"
    assert _finding_codes(report) == {"vault.max_total_bytes_exceeded"}


@pytest.mark.parametrize(
    "limits",
    [
        {"max_files": True},
        {"max_total_bytes": "1024"},
        {"max_file_bytes": 0},
        {"timeout_seconds": True},
        {"timeout_seconds": math.inf},
        {"timeout_seconds": math.nan},
    ],
)
def test_limits_reject_invalid_runtime_values(limits: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        AssuranceLimits(**limits)  # type: ignore[arg-type]


def test_network_guard_rejects_socket_entry_points() -> None:
    originals = socket.socket, socket.create_connection, socket.getaddrinfo
    with pytest.raises(RuntimeError, match="exit through exception"):
        with _network_denied():
            for operation in (socket.socket, socket.create_connection, socket.getaddrinfo):
                with pytest.raises(RuntimeError, match="network disabled"):
                    operation()  # type: ignore[call-arg]
            raise RuntimeError("exit through exception")
    assert (socket.socket, socket.create_connection, socket.getaddrinfo) == originals


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("schema_version", "1"),
        ("status", object()),
        ("limits", []),
        ("observed", "counts"),
        ("findings", {}),
        ("runtime", []),
    ],
)
def test_safe_report_rejects_top_level_schema_and_type_failures(
    field: str, replacement: object
) -> None:
    report = run_local_graph_assurance_self_test()
    report[field] = replacement
    assert not _safe_report(report)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("status", "unknown"),
        ("schema_version", 2),
        ("limits", {"max_files": 1, "max_total_bytes": 1, "max_file_bytes": 1, "timeout_seconds": math.inf}),
    ],
)
def test_safe_report_rejects_invalid_status_schema_and_numeric_values(
    field: str, replacement: object
) -> None:
    report = run_local_graph_assurance_self_test()
    report[field] = replacement
    assert not _safe_report(report)


def test_safe_report_requires_findings_to_match_status_and_json_safety() -> None:
    report = run_local_graph_assurance_self_test()
    report["status"] = "findings"
    assert not _safe_report(report)

    report = run_local_graph_assurance_self_test()
    report["findings"] = [{"code": "runner.no_report", "count": 1}]
    assert not _safe_report(report)

    report = run_local_graph_assurance_self_test()
    report["runtime"] = {"python": "3.12", "platform": float("nan")}
    assert not _safe_report(report)


class _FakeQueue:
    def __init__(self, result: object = None, error: BaseException | None = None) -> None:
        self.result = result
        self.error = error
        self.closed = False
        self.joined = False

    def put(self, value: object) -> None:
        self.result = value

    def get(self, timeout: float) -> object:
        del timeout
        if self.error:
            raise self.error
        return self.result

    def close(self) -> None:
        self.closed = True

    def join_thread(self) -> None:
        self.joined = True


class _FakeProcess:
    def __init__(self, alive: bool = False, result: object = None) -> None:
        self.alive = alive
        self.terminated = False
        self.joined: list[float | None] = []
        self.result = result

    def start(self) -> None:
        return None

    def join(self, timeout: float | None = None) -> None:
        self.joined.append(timeout)

    def is_alive(self) -> bool:
        return self.alive

    def terminate(self) -> None:
        self.terminated = True
        self.alive = False


class _FakeContext:
    def __init__(self, process: _FakeProcess, result_queue: _FakeQueue) -> None:
        self.process = process
        self.result_queue = result_queue

    def Queue(self, maxsize: int) -> _FakeQueue:
        assert maxsize == 1
        return self.result_queue

    def Process(self, target: object, args: tuple[object, ...]) -> _FakeProcess:
        del target, args
        return self.process


@pytest.mark.parametrize(
    ("queue_error", "expected_code"),
    [
        (queue.Empty(), "runner.no_report"),
        (None, "runner.invalid_report"),
    ],
)
def test_runner_handles_no_report_and_invalid_report_with_cleanup(
    monkeypatch: pytest.MonkeyPatch, queue_error: BaseException | None, expected_code: str
) -> None:
    process = _FakeProcess(result=None)
    result_queue = _FakeQueue(error=queue_error)
    monkeypatch.setattr(
        local_graph_assurance.multiprocessing,
        "get_context",
        lambda _name: _FakeContext(process, result_queue),
    )
    report = run_local_graph_assurance(Path("/vault"))
    assert _finding_codes(report) == {expected_code}
    assert result_queue.closed and result_queue.joined


def test_runner_timeout_terminates_and_cleans_up(monkeypatch: pytest.MonkeyPatch) -> None:
    process = _FakeProcess(alive=True)
    result_queue = _FakeQueue()
    monkeypatch.setattr(
        local_graph_assurance.multiprocessing,
        "get_context",
        lambda _name: _FakeContext(process, result_queue),
    )
    report = run_local_graph_assurance(Path("/vault"), AssuranceLimits(timeout_seconds=1))
    assert _finding_codes(report) == {"runner.timeout"}
    assert process.terminated and process.joined == [1, None]
    assert result_queue.closed and result_queue.joined


def test_worker_converts_unexpected_failure_to_safe_report() -> None:
    result_queue = _FakeQueue()
    original_assure = local_graph_assurance._assure
    local_graph_assurance._assure = lambda *_args: (_ for _ in ()).throw(RuntimeError("worker failed"))
    try:
        local_graph_assurance._worker("/vault", AssuranceLimits(), result_queue)
    finally:
        local_graph_assurance._assure = original_assure
    assert isinstance(result_queue.result, dict)
    assert _finding_codes(result_queue.result) == {"runner.unexpected_failure"}


def test_safe_report_rejects_nested_extra_fields_and_unknown_codes() -> None:
    report = run_local_graph_assurance_self_test()
    limits = report["limits"]
    assert isinstance(limits, dict)
    limits["private_markdown"] = "do-not-disclose"
    assert not _safe_report(report)

    report = run_local_graph_assurance_self_test()
    findings = report["findings"]
    assert isinstance(findings, list)
    findings.append({"code": "do-not-disclose", "count": 1})
    assert not _safe_report(report)

    report = run_local_graph_assurance_self_test()
    runtime = report["runtime"]
    assert isinstance(runtime, dict)
    runtime["platform"] = "private-vault-content"
    assert not _safe_report(report)

    report = run_local_graph_assurance_self_test()
    limits = report["limits"]
    assert isinstance(limits, dict)
    limits["max_files"] = 1
    assert not _safe_report(report, expected_limits=AssuranceLimits())

    report = run_local_graph_assurance_self_test()
    findings = report["findings"]
    assert isinstance(findings, list)
    findings.append({"code": "runner.no_report", "count": 1})
    assert not _safe_report(report)


def test_assure_cli_emits_safe_json_for_self_test() -> None:
    result = runner.invoke(app, ["assure", "--self-test"])

    assert result.exit_code == 0
    report = json.loads(result.output)
    assert report["status"] == "passed"
    assert "Alpha" not in result.output


def test_assure_cli_rejects_graph_path_with_self_test(tmp_path: Path) -> None:
    root = _vault(tmp_path)
    result = runner.invoke(app, ["assure", str(root), "--self-test"])

    assert result.exit_code == 1
    assert "Do not pass a graph path" in result.output

    result = runner.invoke(app, ["--graph", str(root), "assure", "--self-test"])

    assert result.exit_code == 1
    assert "Do not pass a graph path" in result.output


@pytest.mark.parametrize("arguments", [["assure"], ["--graph", "/private/vault", "assure"]])
def test_assure_cli_invalid_input_returns_safe_json_without_a_path(arguments: list[str]) -> None:
    result = runner.invoke(app, arguments)

    assert result.exit_code == 1
    report = json.loads(result.output)
    assert report["status"] == "error"
    assert _finding_codes(report) == {"vault.invalid_root"}
    assert "/private/vault" not in result.output


@pytest.mark.parametrize("use_global_option", [False, True])
def test_assure_cli_symlink_loop_returns_safe_json(
    tmp_path: Path, use_global_option: bool
) -> None:
    loop = tmp_path / "private-vault-loop"
    loop.symlink_to(loop, target_is_directory=True)
    arguments = ["--graph", str(loop), "assure"] if use_global_option else ["assure", str(loop)]

    result = runner.invoke(app, arguments)

    assert result.exit_code == 1
    report = json.loads(result.output)
    assert report["status"] == "error"
    assert _finding_codes(report) == {"vault.invalid_root"}
    assert str(loop) not in result.output
