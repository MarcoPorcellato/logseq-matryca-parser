from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

from scripts.check_wheel_contract import MARKER, check_wheel, source_version


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
    assert source_version() == "1.7.1"


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
