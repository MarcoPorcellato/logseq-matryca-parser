#!/usr/bin/env python3
"""Check or explicitly regenerate exact parser compatibility snapshots."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from logseq_matryca_parser.logos_core import LogseqPage  # noqa: E402
from logseq_matryca_parser.logos_parser import StackMachineParser  # noqa: E402
from tests.parser_assurance.corpus import CORPUS_ROOT, load_corpus_entries  # noqa: E402
from tests.parser_assurance.projection import project_page  # noqa: E402


def _parse_entry(entry: dict[str, Any]) -> LogseqPage:
    source_path = CORPUS_ROOT / entry["source"]["path"]
    source = source_path.read_text(encoding="utf-8")
    parse = entry["parse"]
    parser = StackMachineParser(tab_size=parse["tab_size"])
    if parse["entrypoint"] == "file":
        return parser.parse_page_file(source_path)
    return parser.parse(source, page_title=parse["page_title"])


def _render_snapshot(entry: dict[str, Any]) -> str:
    projection = project_page(_parse_entry(entry), profile="exact_parse_v1")
    return json.dumps(projection, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="replace snapshots explicitly; the default only checks them",
    )
    args = parser.parse_args(argv)

    stale: list[Path] = []
    for entry in load_corpus_entries():
        snapshot_path = CORPUS_ROOT / entry["profiles"]["exact_parse"]
        expected = _render_snapshot(entry)
        actual = snapshot_path.read_text(encoding="utf-8") if snapshot_path.is_file() else None
        if actual == expected:
            continue
        stale.append(snapshot_path)
        if args.write:
            _atomic_write_text(snapshot_path, expected)

    if stale and not args.write:
        for path in stale:
            print(f"stale compatibility snapshot: {path.relative_to(CORPUS_ROOT)}")
        return 1
    if args.write:
        print(f"updated {len(stale)} compatibility snapshot(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
