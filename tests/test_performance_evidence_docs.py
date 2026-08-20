"""Registration checks for the maintained runtime-evidence reference."""

from __future__ import annotations

from pathlib import Path


def test_performance_evidence_reference_is_maintained_and_indexed() -> None:
    maintained = Path("docs/maintained.toml").read_text(encoding="utf-8")
    machine_index = Path("docs/index.md").read_text(encoding="utf-8")
    human_index = Path("docs/README.md").read_text(encoding="utf-8")
    reference_index = Path("docs/reference/index.md").read_text(encoding="utf-8")

    assert '"docs/reference/PERFORMANCE_EVIDENCE.md"' in maintained
    assert "[Runtime evidence](reference/PERFORMANCE_EVIDENCE.md)" in machine_index
    assert "[`reference/PERFORMANCE_EVIDENCE.md`](reference/PERFORMANCE_EVIDENCE.md)" in human_index
    assert "[Test-only runtime evidence protocol](PERFORMANCE_EVIDENCE.md)" in reference_index
