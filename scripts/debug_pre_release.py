#!/usr/bin/env python3
"""Pre-release stress harness: round-trip, corpus, and structural invariants."""
from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from logseq_matryca_parser.logos_parser import StackMachineParser  # noqa: E402
from logseq_matryca_parser.logseq_markdown import serialize_logseq_page  # noqa: E402

LOG_PATH = ROOT / ".cursor" / "debug-ee1f8a.log"
SESSION_ID = "ee1f8a"


def _agent_log(
    *,
    hypothesis_id: str,
    location: str,
    message: str,
    data: dict[str, Any],
    run_id: str = "stress",
) -> None:
    # #region agent log
    payload = {
        "sessionId": SESSION_ID,
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    # #endregion


def _flatten_uuids(page) -> list[str]:
    out: list[str] = []

    def walk(nodes):
        for n in nodes:
            out.append(n.uuid)
            walk(n.children)

    walk(page.root_nodes)
    return out


def _struct_snapshot(page) -> dict[str, Any]:
    def node_snap(n):
        return {
            "content": n.content,
            "clean_text": n.clean_text,
            "properties": n.properties,
            "properties_order": n.properties_order,
            "wikilinks": n.wikilinks,
            "tags": n.tags,
            "task_status": n.task_status,
            "children": [node_snap(c) for c in n.children],
        }

    return {
        "title": page.title,
        "properties": page.properties,
        "properties_order": page.properties_order,
        "roots": [node_snap(r) for r in page.root_nodes],
    }


CORPUS: list[tuple[str, str]] = [
    ("H-A roundtrip soft-break", "- Line one\n  continuation\n  - child"),
    ("H-A tab indent", "- root\n\t- tab child"),
    ("H-B fence then property", "- block\n  ```py\n  x=1\n  ```\n  id:: aaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
    ("H-B property after soft break", "- block\n  soft line\n  later:: not-a-prop"),
    ("H-C duplicate text siblings", "- same\n- same\n- same"),
    ("H-C nested duplicate", "- parent\n  - dup\n  - dup"),
    ("H-D empty logbook scheduled", "- TODO x SCHEDULED: <2022-01-08 Sat.+2d>\n  :LOGBOOK:\n  :END:"),
    ("H-D drawer mid tree", "- A\n  :LOGBOOK:\n  CLOCK: [2026-01-01 Wed 10:00]--[2026-01-01 Wed 10:30]\n  :END:\n  - B"),
    ("H-E query macro", "- {{query (and [[Page]] #tag)}}"),
    ("H-E embed macro", "- {{embed [[Hidden Page]]}}"),
    ("H-E escaped tokens", "- \\#notag and \\[\\[NotLink\\]\\]"),
    ("H-E page-tags", "page-tags:: [[A]], [[B]]\n\n- root"),
    ("H-E yaml frontmatter", "---\ntitle: Y\n---\n\n- bullet"),
    ("H-E list property bullets", "- root\n  tags::\n    - one\n    - two"),
    ("H-E zero bullet", "-\n- real"),
    ("H-E numbered list", "1. first\n2. second"),
    ("H-E plus bullet", "+ item"),
    ("H-E hybrid alias", "- [Alias]([[Page]])"),
    ("H-E block ref alias", "- [Vis](((01234567-89ab-cdef-0123-456789abcdef)))"),
]


def check_roundtrip(name: str, text: str, parser: StackMachineParser) -> str | None:
    """Return error message or None if OK."""
    p1 = parser.parse(text, page_title=name)
    serialized = serialize_logseq_page(p1)
    p2 = parser.parse(serialized, page_title=name)
    s1 = _struct_snapshot(p1)
    s2 = _struct_snapshot(p2)
    if s1 != s2:
        return f"structural mismatch after round-trip\n--- input ---\n{text}\n--- serialized ---\n{serialized}"
    uuids1 = _flatten_uuids(p1)
    uuids2 = _flatten_uuids(p2)
    if uuids1 != uuids2:
        return f"uuid drift: {uuids1} -> {uuids2}"
    if len(uuids1) != len(set(uuids1)):
        return f"duplicate uuids in first parse: {uuids1}"
    return None


def main() -> int:
    if LOG_PATH.exists():
        LOG_PATH.unlink()
    parser = StackMachineParser()
    failures: list[str] = []
    _agent_log(
        hypothesis_id="INIT",
        location="debug_pre_release.py:main",
        message="stress harness start",
        data={"corpus_size": len(CORPUS)},
    )
    for name, text in CORPUS:
        hid = name.split()[0] if name.startswith("H-") else "GEN"
        try:
            err = check_roundtrip(name, text, parser)
            _agent_log(
                hypothesis_id=hid,
                location="debug_pre_release.py:check_roundtrip",
                message="corpus case",
                data={"name": name, "ok": err is None, "error": err[:200] if err else None},
            )
            if err:
                failures.append(f"[{name}]\n{err}")
        except Exception as exc:
            tb = traceback.format_exc()
            _agent_log(
                hypothesis_id=hid,
                location="debug_pre_release.py:check_roundtrip",
                message="exception",
                data={"name": name, "exc": str(exc)},
            )
            failures.append(f"[{name}] EXCEPTION: {exc}\n{tb}")

    _agent_log(
        hypothesis_id="SUMMARY",
        location="debug_pre_release.py:main",
        message="stress harness done",
        data={"failures": len(failures)},
    )
    if failures:
        print(f"FAILURES: {len(failures)}")
        for f in failures:
            print("=" * 60)
            print(f)
        return 1
    print(f"OK: {len(CORPUS)} corpus cases passed round-trip invariants")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
