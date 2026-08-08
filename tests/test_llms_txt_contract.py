"""Contract tests for the root llms.txt discovery surface."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LLMS_TXT = ROOT / "llms.txt"
RAW_PREFIX = "https://raw.githubusercontent.com/MarcoPorcellato/logseq-matryca-parser/main/"
MARKDOWN_LINK = re.compile(r"\[[^]]+\]\(([^)]+)\)")


def test_llms_txt_format_and_repository_targets() -> None:
    text = LLMS_TXT.read_text(encoding="utf-8")
    nonempty = [line for line in text.splitlines() if line.strip()]

    assert nonempty[0] == "# Logseq Matryca Parser"
    assert nonempty[1].startswith("> ")
    assert sum(line.startswith("# ") for line in nonempty) == 1
    assert "## Optional" in nonempty

    links = MARKDOWN_LINK.findall(text)
    assert links
    for target in links:
        assert target.startswith(RAW_PREFIX), target
        repository_path = ROOT / target.removeprefix(RAW_PREFIX)
        assert repository_path.is_file(), repository_path
