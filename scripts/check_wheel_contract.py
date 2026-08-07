#!/usr/bin/env python3
"""Verify the version and PEP 561 contract of a built wheel."""

from __future__ import annotations

import argparse
import csv
import re
import zipfile
from email.parser import BytesParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "src" / "logseq_matryca_parser" / "_version.py"
MARKER = "logseq_matryca_parser/py.typed"
VERSION_PATTERN = re.compile(r'^__version__\s*=\s*["\']([^"\']+)["\']$', re.MULTILINE)


def source_version(path: Path = VERSION_FILE) -> str:
    """Read the single source version without importing the package."""
    match = VERSION_PATTERN.search(path.read_text(encoding="utf-8"))
    if match is None:
        raise ValueError(f"version assignment not found in {path}")
    return match.group(1)


def check_wheel(path: Path, expected_version: str) -> list[str]:
    """Return deterministic contract failures for one wheel archive."""
    failures: list[str] = []
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        metadata_files = sorted(name for name in names if name.endswith(".dist-info/METADATA"))
        record_files = sorted(name for name in names if name.endswith(".dist-info/RECORD"))

        if MARKER not in names:
            failures.append(f"missing PEP 561 marker: {MARKER}")

        if len(metadata_files) != 1:
            failures.append(f"expected one METADATA file, found {len(metadata_files)}")
        else:
            metadata = BytesParser().parsebytes(archive.read(metadata_files[0]))
            wheel_version = metadata.get("Version")
            if wheel_version != expected_version:
                failures.append(
                    f"wheel version {wheel_version!r} does not match source version {expected_version!r}"
                )

        if len(record_files) != 1:
            failures.append(f"expected one RECORD file, found {len(record_files)}")
        else:
            rows = csv.reader(archive.read(record_files[0]).decode("utf-8").splitlines())
            recorded = {row[0] for row in rows if row}
            if MARKER not in recorded:
                failures.append(f"PEP 561 marker absent from RECORD: {MARKER}")

    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args(argv)

    try:
        version = source_version()
        failures = check_wheel(args.wheel, version)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"wheel-contract: {exc}")
        return 2

    for failure in failures:
        print(f"wheel-contract: {failure}")
    if failures:
        return 1
    print(f"wheel-contract: OK ({args.wheel.name}, version {version})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
