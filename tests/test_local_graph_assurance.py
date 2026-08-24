from __future__ import annotations

import json
import math
import socket
from pathlib import Path

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
    observed = report["observed"]
    assert isinstance(observed, dict)
    assert observed["markdown_files"] == 0


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

    report = run_local_graph_assurance(root, AssuranceLimits(max_total_bytes=1))

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
    with _network_denied(), pytest.raises(RuntimeError, match="network disabled"):
        socket.create_connection(("127.0.0.1", 1))


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
