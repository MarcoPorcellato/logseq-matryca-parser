from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest
from typer.testing import CliRunner

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


def test_assurance_fails_closed_on_declared_file_limits(tmp_path: Path) -> None:
    root = _vault(tmp_path)
    (root / "pages" / "One.md").write_text("- one\n", encoding="utf-8")
    (root / "pages" / "Two.md").write_text("- two\n", encoding="utf-8")

    report = run_local_graph_assurance(root, AssuranceLimits(max_files=1))

    assert report["status"] == "limit_exceeded"
    assert _finding_codes(report) == {"vault.max_files_exceeded"}


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


def test_assure_cli_emits_safe_json_for_self_test() -> None:
    result = runner.invoke(app, ["assure", "--self-test"])

    assert result.exit_code == 0
    report = json.loads(result.output)
    assert report["status"] == "passed"
    assert "Alpha" not in result.output


def test_assure_cli_rejects_graph_path_with_self_test(tmp_path: Path) -> None:
    result = runner.invoke(app, ["assure", str(_vault(tmp_path)), "--self-test"])

    assert result.exit_code == 1
    assert "Do not pass a graph path" in result.output
