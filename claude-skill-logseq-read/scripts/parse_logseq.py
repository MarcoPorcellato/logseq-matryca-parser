#!/usr/bin/env python3
"""
Parse Logseq notes and return structured content for Claude.
Part of the logseq-read skill.

Usage:
  parse_logseq.py --page "Progetto Alpha"
  parse_logseq.py --journal today
  parse_logseq.py --journal 2026-05-15
  parse_logseq.py --todos
  parse_logseq.py --search "MarkeTRIZ"
  parse_logseq.py --list
"""

import argparse
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

LOGSEQ_PATH = Path(os.environ.get("LOGSEQ_GRAPH_PATH", "/path/to/your/logseq/graph"))
PAGES_PATH = LOGSEQ_PATH / "pages"
JOURNALS_PATH = LOGSEQ_PATH / "journals"

TASK_ICONS = {"TODO": "☐", "DOING": "🔄", "DONE": "✓", "LATER": "⏳"}


def ensure_installed():
    try:
        from logseq_matryca_parser import LogosParser  # noqa: F401
    except ImportError:
        print("[setup] Installing logseq-matryca-parser...", file=sys.stderr)
        subprocess.run(
            [sys.executable, "-m", "pip", "install",
             "git+https://github.com/MarcoPorcellato/logseq-matryca-parser.git"],
            check=True, capture_output=True,
        )


def format_node(node, depth=0) -> list[str]:
    """Recursively format a LogseqNode using clean_text to preserve hierarchy."""
    text = (getattr(node, "clean_text", None) or "").strip()
    if not text:
        return []

    indent = "  " * depth
    task = getattr(node, "task_status", None)
    if task:
        icon = TASK_ICONS.get(task, task)
        text = f"{icon} {text}"

    # Wikilink e tag estratti dal parser ma omessi dal prompt predefinito per
    # risparmiare token nel contesto; si possono concatenare a `text` se servono.
    _wikilinks = getattr(node, "wikilinks", []) or []
    _tags = getattr(node, "tags", []) or []

    # Numero di riga 1-based nel file sorgente (logseq-matryca-parser v0.2.2+):
    # consente citazioni precise nei riferimenti LLM, es. "[Riga 42] ...".
    line_start = getattr(node, "line_start", None)
    line_prefix = f"[Riga {line_start}] " if line_start is not None else ""

    lines = [f"{indent}- {line_prefix}{text}"]

    for child in (getattr(node, "children", None) or []):
        lines.extend(format_node(child, depth + 1))

    return lines


def format_page(file_path: Path) -> str:
    """Parse and format a Logseq page file into clean structured markdown."""
    from logseq_matryca_parser import LogosParser

    parser = LogosParser()
    try:
        page = parser.parse_page_file(file_path)
    except Exception as e:
        print(f"[warn] Parser error on {file_path.name}: {e}", file=sys.stderr)
        return file_path.read_text(encoding="utf-8")

    sections = []

    # Properties block
    props = getattr(page, "properties", None) or {}
    if props:
        for k, v in props.items():
            sections.append(f"{k}:: {v}")
        sections.append("")

    # Content — recursive clean traversal
    root_nodes = getattr(page, "root_nodes", None) or []
    if root_nodes:
        for node in root_nodes:
            sections.extend(format_node(node))
    else:
        sections.append(file_path.read_text(encoding="utf-8"))

    return "\n".join(sections)


# ─── Query functions ──────────────────────────────────────────────────────────


def cmd_page(name: str) -> str:
    name_lower = name.lower()
    matches = []
    for f in PAGES_PATH.glob("*.md"):
        stem_norm = f.stem.lower().replace("___", "/").replace("_", " ")
        if name_lower in stem_norm or stem_norm in name_lower:
            matches.append(f)
    matches.sort()

    if not matches:
        all_pages = sorted(
            f.stem.replace("___", "/").replace("_", " ")
            for f in PAGES_PATH.glob("*.md")
        )
        return (
            f"Nessuna pagina trovata per '{name}'.\n\n"
            f"Pagine disponibili: {', '.join(all_pages)}"
        )

    parts = []
    for i, match in enumerate(matches):
        title = match.stem.replace("___", "/").replace("_", " ")
        parts.append(f"# {title}\n")
        parts.append(format_page(match))
        if i < len(matches) - 1:
            parts.append("\n---\n")

    return "\n".join(parts)


def cmd_journal(date_arg: str) -> str:
    if date_arg.lower() == "today":
        target = date.today()
    else:
        try:
            target = date.fromisoformat(date_arg)
        except ValueError:
            return f"Formato data non valido: '{date_arg}'. Usa YYYY-MM-DD o 'today'."

    path = JOURNALS_PATH / f"{target.year}_{target.month:02d}_{target.day:02d}.md"
    if not path.exists():
        available = sorted(JOURNALS_PATH.glob("*.md"), reverse=True)[:5]
        nearby = [f.stem.replace("_", "-") for f in available]
        return (
            f"Nessun journal per {target}.\n\n"
            f"Journal recenti: {', '.join(nearby)}"
        )

    return f"# Journal {target}\n\n{format_page(path)}"


def cmd_todos() -> str:
    todo_re = re.compile(r"\b(TODO|DOING|LATER)\b\s*(.*)")
    results: dict[str, list[str]] = {}

    all_files = sorted(PAGES_PATH.glob("*.md")) + sorted(JOURNALS_PATH.glob("*.md"))

    for f in all_files:
        file_todos = []
        for line in f.read_text(encoding="utf-8").splitlines():
            m = todo_re.search(line)
            if m:
                status = m.group(1)
                task = m.group(2).strip()
                task = re.sub(r"\[d:[^\]]+\]", "", task).strip()
                task = re.sub(r"SCHEDULED:.*", "", task).strip()
                task = re.sub(r"\[#[A-Z]\]\s*", "", task).strip()  # priority markers like [#A]
                if task:
                    icon = TASK_ICONS.get(status, status)
                    file_todos.append(f"  {icon} {task}")

        if file_todos:
            stem = f.stem
            if re.match(r"\d{4}_\d{2}_\d{2}", stem):
                section = f"📅 {stem.replace('_', '-')}"
            else:
                section = stem.replace("___", "/").replace("_", " ")
            results[section] = file_todos

    if not results:
        return "Nessun task aperto trovato."

    lines = ["# Task aperti\n"]
    for section, todos in results.items():
        lines.append(f"### {section}")
        lines.extend(todos)
        lines.append("")

    return "\n".join(lines)


def cmd_search(query: str) -> str:
    query_lower = query.lower()
    results = []

    all_files = sorted(PAGES_PATH.glob("*.md")) + sorted(JOURNALS_PATH.glob("*.md"))

    for f in all_files:
        content = f.read_text(encoding="utf-8")
        if query_lower not in content.lower():
            continue

        matches = []
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if query_lower in line.lower():
                start = max(0, i - 1)
                end = min(len(lines), i + 3)
                snippet = "\n".join(
                    f"  {line_str}" for line_str in lines[start:end] if line_str.strip()
                )
                matches.append(snippet)
                if len(matches) >= 4:
                    break

        if matches:
            stem = f.stem.replace("___", "/").replace("_", " ")
            results.append(f"\n### {stem}")
            results.extend(matches)

    if not results:
        return f"Nessun risultato per '{query}'."

    return f"# Ricerca: '{query}'\n" + "\n".join(results)


def cmd_list() -> str:
    pages = sorted(PAGES_PATH.glob("*.md"))
    journals = sorted(JOURNALS_PATH.glob("*.md"), reverse=True)[:15]

    lines = ["# Logseq Graph\n"]
    lines.append("## Pages")
    for p in pages:
        lines.append(f"- {p.stem.replace('___', '/').replace('_', ' ')}")
    lines.append("\n## Journal (ultimi 15)")
    for j in journals:
        lines.append(f"- {j.stem.replace('_', '-')}")

    return "\n".join(lines)


# ─── Entry point ─────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Parse Logseq notes for Claude.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--page", metavar="NAME", help="Leggi una pagina per nome")
    group.add_argument("--journal", metavar="DATE", help="Leggi journal: 'today' o YYYY-MM-DD")
    group.add_argument("--todos", action="store_true", help="Lista tutti i task aperti")
    group.add_argument("--search", metavar="QUERY", help="Ricerca full-text")
    group.add_argument("--list", action="store_true", help="Lista tutte le pagine")

    args = parser.parse_args()
    ensure_installed()

    if args.list:
        print(cmd_list())
    elif args.todos:
        print(cmd_todos())
    elif args.search:
        print(cmd_search(args.search))
    elif args.journal:
        print(cmd_journal(args.journal))
    elif args.page:
        print(cmd_page(args.page))


if __name__ == "__main__":
    main()
