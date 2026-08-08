#!/usr/bin/env python3
"""Verify the tag, runtime version, and changelog contract for a release."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_wheel_contract import source_version  # noqa: E402
from scripts.extract_changelog import extract_changelog_section, normalize_version  # noqa: E402

CHANGELOG = ROOT / "CHANGELOG.md"
SEMVER_TAG = re.compile(
    r"^v(?P<version>0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)


def runtime_version() -> str:
    """Read the public runtime version in a fresh interpreter."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import logseq_matryca_parser as package; print(package.__version__)",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def missing_repository_links(release_notes: str, repository_root: Path) -> list[str]:
    """Return deterministic failures for missing or escaping local Markdown links."""
    resolved_root = repository_root.resolve()
    failures: set[str] = set()
    destinations = re.findall(r"(?<!!)\[[^]]+\]\(([^)\s]+)", release_notes)

    for raw_target in destinations:
        target = raw_target.strip("<>")
        if (
            not target
            or target.startswith(("#", "/"))
            or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target)
        ):
            continue

        path_text = target.split("#", 1)[0].split("?", 1)[0]
        if not path_text:
            continue

        candidate = (resolved_root / path_text).resolve()
        if candidate != resolved_root and resolved_root not in candidate.parents:
            failures.add(f"release notes link escapes repository: {target!r}")
        elif not candidate.exists():
            failures.add(f"release notes link target does not exist: {path_text!r}")

    return sorted(failures)


def validate_release(
    *,
    tag: str,
    source: str,
    runtime: str,
    changelog_text: str,
    repository_root: Path | None = None,
) -> tuple[list[str], str | None]:
    """Return deterministic release-contract failures and release notes."""
    failures: list[str] = []
    match = SEMVER_TAG.fullmatch(tag)
    if match is None:
        failures.append(f"tag {tag!r} is not a stable vX.Y.Z SemVer tag")
        return failures, None

    tag_version = normalize_version(tag)
    if source != tag_version:
        failures.append(f"tag version {tag_version!r} does not match source version {source!r}")
    if runtime != source:
        failures.append(f"runtime version {runtime!r} does not match source version {source!r}")

    notes: str | None = None
    try:
        notes = extract_changelog_section(changelog_text, tag_version)
    except (LookupError, ValueError) as exc:
        failures.append(str(exc))
    else:
        body = "\n".join(notes.splitlines()[1:]).strip()
        if not body or not any(line.lstrip().startswith("- ") for line in body.splitlines()):
            failures.append(f"changelog section [{tag_version}] has no release-note bullets")
        if repository_root is not None:
            failures.extend(missing_repository_links(notes, repository_root))

    try:
        unreleased = extract_changelog_section(
            changelog_text,
            "Unreleased",
            allow_unreleased=True,
        )
    except LookupError as exc:
        failures.append(str(exc))
    else:
        unreleased_body = "\n".join(unreleased.splitlines()[1:]).strip()
        if unreleased_body:
            failures.append("[Unreleased] must be empty before tagging")

    return failures, notes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default=os.environ.get("GITHUB_REF_NAME"))
    parser.add_argument("--changelog", type=Path, default=CHANGELOG)
    parser.add_argument("--notes-out", type=Path)
    args = parser.parse_args(argv)

    if not args.tag:
        print("release-contract: --tag or GITHUB_REF_NAME is required")
        return 2

    try:
        changelog_text = args.changelog.read_text(encoding="utf-8")
        source = source_version()
        runtime = runtime_version()
    except (OSError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"release-contract: {exc}")
        return 2

    failures, notes = validate_release(
        tag=args.tag,
        source=source,
        runtime=runtime,
        changelog_text=changelog_text,
        repository_root=ROOT,
    )
    for failure in failures:
        print(f"release-contract: {failure}")
    if failures:
        return 1

    if args.notes_out is not None and notes is not None:
        args.notes_out.parent.mkdir(parents=True, exist_ok=True)
        args.notes_out.write_text(notes, encoding="utf-8")

    print(f"release-contract: OK ({args.tag}, source/runtime {source})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
