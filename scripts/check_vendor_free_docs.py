#!/usr/bin/env python3
"""Fail closed when encoded forbidden patterns appear in repository files."""

from __future__ import annotations

import argparse
import base64
import re
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERN_B64 = "Z2l0bmV4dXN8dXNlci1naXRuZXh1c3xcLmdpdG5leHVzcmN8XC5naXRuZXh1cy8="
PATTERN = re.compile(base64.b64decode(PATTERN_B64), re.IGNORECASE)
EXEMPT_PATHS = {"uv.lock", "scripts/check_vendor_free_docs.sh", "scripts/check_vendor_free_docs.py"}


@dataclass(frozen=True)
class Finding:
    """A match without exposing matched text in output."""

    path: str
    line: int

    def render(self) -> str:
        return f"{self.path}:{self.line}"


class ScanError(RuntimeError):
    """Repository contents could not be enumerated or read completely."""


def _repository_paths(root: Path) -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=root,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ScanError("could not enumerate repository files with Git") from exc
    return [Path(path.decode("utf-8", errors="surrogateescape")) for path in result.stdout.split(b"\0") if path]


def _contents(path: Path) -> bytes | None:
    """Read regular files without traversing symlink targets."""
    try:
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            return None
        if stat.S_ISREG(mode):
            return path.read_bytes()
    except OSError as exc:
        raise ScanError(f"could not read repository file: {path}") from exc
    return None


def scan_repository(root: Path) -> list[Finding]:
    """Scan Git-tracked and non-ignored untracked files, including dotfiles."""
    root = root.resolve()
    findings: list[Finding] = []
    for relative in _repository_paths(root):
        relative_text = relative.as_posix()
        if relative_text in EXEMPT_PATHS:
            continue
        if relative.is_absolute() or ".." in relative.parts:
            raise ScanError("Git returned a path outside the repository root")
        path = root / relative
        content = _contents(path)
        if content is None or b"\0" in content:
            continue
        for line_number, line in enumerate(content.splitlines(), start=1):
            if PATTERN.search(line):
                findings.append(Finding(relative_text, line_number))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root to scan")
    args = parser.parse_args(argv)
    try:
        findings = scan_repository(args.root)
    except ScanError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if findings:
        for finding in findings:
            print(finding.render())
        print("ERROR: forbidden vendor tool name found in repository files", file=sys.stderr)
        return 1
    print("vendor-name-check: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
