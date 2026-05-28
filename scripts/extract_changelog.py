#!/usr/bin/env python3
"""Extract a Keep a Changelog version section for GitHub Release notes.

Usage:
    python scripts/extract_changelog.py v1.0.0
    python scripts/extract_changelog.py 1.0.0 --changelog CHANGELOG.md

Prints the matching ``## [X.Y.Z]`` block (heading + body) to stdout.
Exits with code 1 if the version is missing, 2 if [Unreleased] is requested.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_CHANGELOG = _REPO_ROOT / "CHANGELOG.md"

_VERSION_HEADING = re.compile(r"^## \[(?P<label>[^\]]+)\](?:\s+-\s+(?P<date>.+))?\s*$")


def normalize_version(tag_or_version: str) -> str:
    """Strip a leading ``v`` from tags (``v1.0.0`` → ``1.0.0``)."""
    raw = tag_or_version.strip()
    if raw.lower() == "unreleased":
        return "Unreleased"
    if raw.startswith(("v", "V")) and len(raw) > 1 and raw[1].isdigit():
        return raw[1:]
    return raw


def version_heading_pattern(version: str) -> re.Pattern[str]:
    return re.compile(
        rf"^## \[{re.escape(version)}\](?:\s+-\s+.+)?\s*$",
    )


def extract_changelog_section(
    text: str,
    version: str,
    *,
    allow_unreleased: bool = False,
) -> str:
    """Return the changelog section for ``version`` (heading included)."""
    normalized = normalize_version(version)
    if normalized == "Unreleased" and not allow_unreleased:
        raise ValueError(
            "Refusing to extract [Unreleased] for a tagged release. "
            "Finalize CHANGELOG.md with a versioned section first."
        )

    lines = text.splitlines()
    heading_re = version_heading_pattern(normalized)
    start: int | None = None
    for index, line in enumerate(lines):
        if heading_re.match(line):
            start = index
            break

    if start is None:
        known = list(iter_changelog_versions(text))
        hint = f" Known versions: {', '.join(known[:8])}" if known else ""
        if len(known) > 8:
            hint += ", …"
        raise LookupError(f"No changelog section found for version [{normalized}].{hint}")

    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break

    block = "\n".join(lines[start:end]).rstrip()
    return f"{block}\n"


def iter_changelog_versions(text: str) -> list[str]:
    """Return version labels in file order (excludes Unreleased)."""
    versions: list[str] = []
    for line in text.splitlines():
        match = _VERSION_HEADING.match(line)
        if not match:
            continue
        label = match.group("label")
        if label.lower() != "unreleased":
            versions.append(label)
    return versions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Extract a version section from CHANGELOG.md for GitHub Releases.",
    )
    parser.add_argument(
        "version",
        help="Release tag or semver (e.g. v1.0.0 or 1.0.0)",
    )
    parser.add_argument(
        "--changelog",
        type=Path,
        default=_DEFAULT_CHANGELOG,
        help=f"Path to changelog file (default: {_DEFAULT_CHANGELOG.relative_to(_REPO_ROOT)})",
    )
    parser.add_argument(
        "--allow-unreleased",
        action="store_true",
        help="Allow extracting [Unreleased] (for debugging only)",
    )
    args = parser.parse_args(argv)

    changelog_path = args.changelog.expanduser().resolve()
    if not changelog_path.is_file():
        print(f"error: changelog not found: {changelog_path}", file=sys.stderr)
        return 1

    text = changelog_path.read_text(encoding="utf-8")
    try:
        section = extract_changelog_section(
            text,
            args.version,
            allow_unreleased=args.allow_unreleased,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except LookupError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    sys.stdout.write(section)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
