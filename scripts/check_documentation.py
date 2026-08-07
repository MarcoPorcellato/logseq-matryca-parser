#!/usr/bin/env python3
"""Deterministically validate the maintained documentation bundle."""

from __future__ import annotations

import argparse
import re
import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
STATUSES = {"draft", "stable", "deprecated"}
CLASSIFICATIONS = {"canonical", "active", "historical", "generated"}
DATE_FIELDS = ("last_verified", "verified", "stale_after")
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^]]*\]\(([^)]+)\)")


class ProfileError(ValueError):
    """A fatal maintained-profile configuration error."""


@dataclass(frozen=True, order=True)
class Finding:
    """One stable, machine-readable validation finding."""

    source: str
    line: int
    code: str
    message: str

    def render(self) -> str:
        return f"{self.source}:{self.line}: {self.code}: {self.message}"


def _relative(path: Path, root: Path) -> str:
    """Return a checkout-independent path for diagnostics."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _fenced_lines(lines: list[str]) -> set[int]:
    skipped: set[int] = set()
    fence: str | None = None
    for number, line in enumerate(lines, start=1):
        stripped = line.lstrip()
        marker = stripped[:3]
        if marker in {"```", "~~~"}:
            if fence is None:
                fence = marker
            elif marker == fence:
                fence = None
            skipped.add(number)
        elif fence is not None:
            skipped.add(number)
    return skipped


def _heading_anchors(text: str) -> set[str]:
    """Match the current Matryca Knowledge anchor algorithm."""
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    lines = text.splitlines()
    skipped = _fenced_lines(lines)
    for number, line in enumerate(lines, start=1):
        if number in skipped or not (match := HEADING.match(line)):
            continue
        heading = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", match.group(1))
        slug = re.sub(r"[^\w\- ]", "", heading.lower(), flags=re.UNICODE)
        slug = slug.strip().replace(" ", "-")
        occurrence = counts.get(slug, 0)
        counts[slug] = occurrence + 1
        anchors.add(slug if occurrence == 0 else f"{slug}-{occurrence}")
    return anchors


def _frontmatter(path: Path, root: Path, findings: list[Finding]) -> dict[str, str] | None:
    source = _relative(path, root)
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        findings.append(Finding(source, 1, "DOC_FRONTMATTER_MISSING", "missing opening ---"))
        return None
    try:
        end = next(index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration:
        findings.append(Finding(source, 1, "DOC_FRONTMATTER_UNCLOSED", "missing closing ---"))
        return None

    metadata: dict[str, str] = {}
    for line_number, raw in enumerate(lines[1:end], start=2):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith((" ", "\t")) or ":" not in raw:
            findings.append(
                Finding(source, line_number, "DOC_FRONTMATTER_NON_SCALAR", "expected a flat key: value field")
            )
            continue
        key, value = (part.strip() for part in raw.split(":", 1))
        if not key or value.startswith(("[", "{")):
            findings.append(
                Finding(source, line_number, "DOC_FRONTMATTER_NON_SCALAR", "expected a flat scalar field")
            )
            continue
        if key in metadata:
            findings.append(Finding(source, line_number, "DOC_FRONTMATTER_DUPLICATE", f"duplicate field: {key}"))
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        metadata[key] = value
    return metadata


def _profile(path: Path) -> tuple[list[str], list[str]]:
    if not path.is_file():
        raise ProfileError(f"profile not found: {path}")
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ProfileError(f"invalid TOML profile: {exc}") from exc
    documents = data.get("maintained_documents")
    fields = data.get("required_frontmatter_fields")
    if not isinstance(documents, list) or not documents or not all(isinstance(item, str) for item in documents):
        raise ProfileError("maintained_documents must be a non-empty string array")
    if len(documents) != len(set(documents)):
        raise ProfileError("maintained_documents contains duplicate paths")
    if not isinstance(fields, list) or not fields or not all(isinstance(item, str) for item in fields):
        raise ProfileError("required_frontmatter_fields must be a non-empty string array")
    if len(fields) != len(set(fields)):
        raise ProfileError("required_frontmatter_fields contains duplicates")
    return documents, fields


def _validate_metadata(
    metadata: dict[str, str], source: str, required: list[str], as_of: date, findings: list[Finding]
) -> None:
    for field in required:
        if not metadata.get(field):
            findings.append(Finding(source, 1, "DOC_FIELD_MISSING", f"required field missing or empty: {field}"))

    status = metadata.get("status")
    if status not in STATUSES:
        findings.append(Finding(source, 1, "DOC_STATUS_INVALID", f"invalid lifecycle status: {status!r}"))
    classification = metadata.get("classification")
    if classification not in CLASSIFICATIONS:
        findings.append(
            Finding(source, 1, "DOC_CLASSIFICATION_INVALID", f"invalid Matryca classification: {classification!r}")
        )

    parsed: dict[str, date] = {}
    for field in DATE_FIELDS:
        raw = metadata.get(field)
        if not raw:
            continue
        try:
            parsed[field] = date.fromisoformat(raw)
        except ValueError:
            findings.append(Finding(source, 1, "DOC_DATE_INVALID", f"{field} is not YYYY-MM-DD: {raw!r}"))
    if parsed.get("last_verified") != parsed.get("verified") and {"last_verified", "verified"} <= parsed.keys():
        findings.append(Finding(source, 1, "DOC_DATE_MISMATCH", "last_verified must equal verified"))
    verified = parsed.get("verified")
    stale_after = parsed.get("stale_after")
    if verified is not None and verified > as_of:
        findings.append(Finding(source, 1, "DOC_VERIFIED_FUTURE", f"verified {verified} is after {as_of}"))
    if verified is not None and stale_after is not None and stale_after < verified:
        findings.append(Finding(source, 1, "DOC_STALE_ORDER", "stale_after must not precede verified"))
    if stale_after is not None and stale_after < as_of:
        findings.append(Finding(source, 1, "DOC_STALE", f"stale_after {stale_after} is before {as_of}"))


def _markdown_links(text: str) -> list[tuple[int, str]]:
    links: list[tuple[int, str]] = []
    lines = text.splitlines()
    skipped = _fenced_lines(lines)
    for line_number, line in enumerate(lines, start=1):
        if line_number not in skipped:
            links.extend((line_number, match.group(1).strip()) for match in MARKDOWN_LINK.finditer(line))
    return links


def _validate_links(path: Path, root: Path, text: str, findings: list[Finding], cache: dict[Path, set[str]]) -> None:
    source = _relative(path, root)
    for line_number, raw in _markdown_links(text):
        target = raw[1:-1] if raw.startswith("<") and raw.endswith(">") else raw
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc:
            continue
        relative = unquote(parsed.path)
        destination = (path.parent / relative if relative else path).resolve()
        try:
            destination.relative_to(root)
        except ValueError:
            findings.append(Finding(source, line_number, "DOC_LINK_ESCAPE", f"local link escapes root: {raw}"))
            continue
        if not destination.exists():
            findings.append(Finding(source, line_number, "DOC_LINK_MISSING", f"local target does not exist: {raw}"))
            continue
        anchor = unquote(parsed.fragment)
        if anchor and destination.is_file():
            anchors = cache.setdefault(destination, _heading_anchors(destination.read_text(encoding="utf-8")))
            if anchor not in anchors:
                findings.append(Finding(source, line_number, "DOC_ANCHOR_MISSING", f"local anchor does not exist: {raw}"))


def check(root: Path, profile: Path, as_of: date) -> list[Finding]:
    root = root.resolve()
    documents, required = _profile(profile)
    findings: list[Finding] = []
    canonical: dict[str, list[str]] = {}
    anchor_cache: dict[Path, set[str]] = {}
    for relative in documents:
        path = (root / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            findings.append(Finding(relative, 1, "DOC_PATH_ESCAPE", "maintained path escapes repository root"))
            continue
        if not path.is_file():
            findings.append(Finding(relative, 1, "DOC_PATH_MISSING", "maintained document is not a file"))
            continue
        metadata = _frontmatter(path, root, findings)
        if metadata is None:
            continue
        source = _relative(path, root)
        _validate_metadata(metadata, source, required, as_of, findings)
        text = path.read_text(encoding="utf-8")
        _validate_links(path, root, text, findings, anchor_cache)
        if metadata.get("classification") == "canonical" and (doc_type := metadata.get("type")):
            canonical.setdefault(doc_type, []).append(source)
    for doc_type, sources in canonical.items():
        if len(sources) > 1:
            findings.append(
                Finding(sources[0], 1, "DOC_CANONICAL_DUPLICATE", f"type {doc_type!r} is canonical in: {', '.join(sources)}")
            )
    return sorted(findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--profile", type=Path, default=ROOT / "docs" / "maintained.toml")
    parser.add_argument("--as-of-date", required=True, help="deterministic audit date (YYYY-MM-DD)")
    args = parser.parse_args(argv)
    try:
        as_of = date.fromisoformat(args.as_of_date)
        findings = check(args.root, args.profile, as_of)
    except (ValueError, ProfileError) as exc:
        print(f"configuration error: {exc}")
        return 2
    for finding in findings:
        print(finding.render())
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
