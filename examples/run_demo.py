"""
Logos Protocol — live demo script.

Parses ``examples/demo_logseq_journal.md`` and prints FORGE clean Markdown.

Run from the repository root after syncing dependencies::

    uv sync --all-extras
    uv run python examples/run_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from logseq_matryca_parser.forge import ForgeExporter
from logseq_matryca_parser.logos_parser import LogosParser

ROOT_DIR = Path(__file__).resolve().parent.parent
EXAMPLE_FILE = ROOT_DIR / "examples" / "demo_logseq_journal.md"


def run_demo() -> None:
    console = Console()
    console.print(Panel("[bold gold1]🔱 Logos Protocol - Live Extraction Demo[/]", expand=False))
    console.print(f"[cyan]Reading file:[/] {EXAMPLE_FILE.name}...")

    parser = LogosParser()
    try:
        ast_nodes = parser.parse_file(EXAMPLE_FILE)
    except ImportError as exc:
        console.print(
            "[bold red]Missing dependencies.[/] Run: [bold]uv sync --all-extras[/]"
        )
        raise SystemExit(1) from exc
    except OSError as exc:
        console.print(f"[bold red]Error reading file:[/] {exc}")
        raise SystemExit(1) from exc

    console.print(f"[green]✅ AST extracted:[/] {len(ast_nodes)} root nodes.\n")
    console.print("[bold]Forge output (clean Markdown for AI):[/]")
    console.print("=" * 40)
    console.print(ForgeExporter.to_clean_markdown(ast_nodes))
    console.print("=" * 40)
    console.print(
        "\n[bold green]Success:[/] Hierarchy preserved — ready for RAG ingestion."
    )


if __name__ == "__main__":
    try:
        run_demo()
    except ImportError as exc:
        print(
            f"Error: install dependencies first (uv sync --all-extras). {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
