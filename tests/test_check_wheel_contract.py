from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

from scripts.check_wheel_contract import MARKER, check_wheel, main, source_version


def _wheel(
    path: Path,
    *,
    version: str = "1.7.0",
    include_marker: bool = True,
    record_marker: bool = True,
) -> Path:
    metadata = f"Metadata-Version: 2.5\nName: logseq-matryca-parser\nVersion: {version}\n"
    record = io.StringIO()
    writer = csv.writer(record, lineterminator="\n")
    if record_marker:
        writer.writerow([MARKER, "", ""])
    writer.writerow(["logseq_matryca_parser-1.7.0.dist-info/METADATA", "", ""])
    writer.writerow(["logseq_matryca_parser-1.7.0.dist-info/RECORD", "", ""])

    with zipfile.ZipFile(path, "w") as archive:
        if include_marker:
            archive.writestr(MARKER, "")
        archive.writestr("logseq_matryca_parser-1.7.0.dist-info/METADATA", metadata)
        archive.writestr("logseq_matryca_parser-1.7.0.dist-info/RECORD", record.getvalue())
    return path


def test_source_version_reads_lightweight_version_module() -> None:
    assert source_version() == "1.9.0"


def test_valid_wheel_contract(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path / "package.whl")

    assert check_wheel(wheel, "1.7.0") == []


def test_wheel_contract_reports_marker_and_record_failures(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path / "package.whl", include_marker=False, record_marker=False)

    assert check_wheel(wheel, "1.7.0") == [
        f"missing PEP 561 marker: {MARKER}",
        f"PEP 561 marker absent from RECORD: {MARKER}",
    ]


def test_wheel_contract_reports_version_mismatch(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path / "package.whl", version="1.5.0")

    assert check_wheel(wheel, "1.7.0") == [
        "wheel version '1.5.0' does not match source version '1.7.0'"
    ]


def test_main_accepts_valid_wheel(tmp_path: Path, capsys) -> None:
    wheel = _wheel(tmp_path / "package.whl", version=source_version())

    assert main([str(wheel)]) == 0
    assert capsys.readouterr().out == (
        f"wheel-contract: OK ({wheel.name}, version {source_version()})\n"
    )


def test_main_reports_missing_wheel_without_raising(tmp_path: Path, capsys) -> None:
    missing_wheel = tmp_path / "missing.whl"

    assert main([str(missing_wheel)]) == 2
    diagnostic = capsys.readouterr().out
    assert diagnostic.startswith("wheel-contract: ")
    assert str(missing_wheel) in diagnostic


def test_main_reports_malformed_wheel_without_raising(tmp_path: Path, capsys) -> None:
    malformed_wheel = tmp_path / "malformed.whl"
    malformed_wheel.write_text("not a wheel archive", encoding="utf-8")

    assert main([str(malformed_wheel)]) == 2
    assert capsys.readouterr().out == "wheel-contract: File is not a zip file\n"
