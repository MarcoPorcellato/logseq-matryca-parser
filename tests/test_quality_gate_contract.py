"""Regression tests for the non-mutating Makefile and CI quality contract."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _dry_run(target: str) -> list[str]:
    result = subprocess.run(
        ["make", "--no-print-directory", "--dry-run", target],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def test_lint_targets_separate_verification_from_rewrites() -> None:
    assert _dry_run("lint") == ["uv run ruff check ."]
    assert _dry_run("lint-fix") == ["uv run ruff check . --fix"]


def test_all_uses_only_non_mutating_ruff_targets() -> None:
    commands = _dry_run("all")

    assert "uv run ruff check ." in commands
    assert "uv run ruff check . --fix" not in commands


def test_ci_finishes_with_clean_checkout_assertion() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    lint = workflow.index("run: make lint")
    verify_clean = workflow.index("run: make verify-clean")

    assert lint < verify_clean
    assert verify_clean > workflow.index("run: make docs-check")


def test_verify_clean_reports_any_dirty_checkout() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert 'status="$$(git status --porcelain)"' in makefile
    assert "printf '%s\\n' \"$$status\"" in makefile
