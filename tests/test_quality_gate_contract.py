"""Regression tests for the non-mutating Makefile and CI quality contract."""

from __future__ import annotations

import re
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


def test_check_type_checks_compatibility_snapshot_generator() -> None:
    commands = _dry_run("check")

    mypy_command = next(command for command in commands if command.startswith("uv run mypy "))
    assert "scripts/update_compat_snapshots.py" in mypy_command


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


def test_all_external_actions_are_immutable_sha_pins() -> None:
    workflows = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
    uses_pattern = re.compile(r"^\s*uses:\s*([^\s#]+)", re.MULTILINE)

    for workflow in workflows:
        for action in uses_pattern.findall(workflow.read_text(encoding="utf-8")):
            if action.startswith("./"):
                continue
            assert re.fullmatch(r"[^@]+@[0-9a-f]{40}", action), (
                f"{workflow.name} has a mutable action reference: {action}"
            )


def test_release_builds_once_and_orders_publication() -> None:
    workflow = (ROOT / ".github" / "workflows" / "pypi_publish.yml").read_text(
        encoding="utf-8"
    )

    assert workflow.count("uv build --out-dir release-bundle/dist") == 1
    assert "needs: pre-flight" in workflow
    assert "needs: build" in workflow
    assert "needs: publish" in workflow
    assert workflow.count("sha256sum --check SHA256SUMS") == 3
    assert "packages-dir: release-bundle/dist/" in workflow
    assert "release-bundle/dist/*" in workflow
