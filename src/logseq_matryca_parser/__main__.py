"""Allow running the CLI via ``python -m logseq_matryca_parser``."""

from __future__ import annotations

from logseq_matryca_parser.kinetic import app

if __name__ == "__main__":
    app(prog_name="matryca-parse")
