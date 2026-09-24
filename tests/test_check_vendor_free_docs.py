from __future__ import annotations

import base64
import subprocess
import sys
from pathlib import Path

CHECKER = Path(__file__).resolve().parents[1] / "scripts" / "check_vendor_free_docs.py"
FORBIDDEN_PATTERN_B64 = "Z2l0bmV4dXN8dXNlci1naXRuZXh1c3xcLmdpdG5leHVzcmN8XC5naXRuZXh1cy8="


def _needle() -> bytes:
    return base64.b64decode(FORBIDDEN_PATTERN_B64).split(b"|")[0]


def _git_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True)


def _check(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), "--root", str(root)],
        capture_output=True,
        check=False,
        text=True,
    )


def test_checker_finds_forbidden_text_in_hidden_tracked_files(tmp_path: Path) -> None:
    _git_repo(tmp_path)
    hidden = tmp_path / ".github" / "policy.md"
    hidden.parent.mkdir()
    hidden.write_bytes(_needle() + b"\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", ".github/policy.md"], check=True)
    (tmp_path / "untracked.txt").write_bytes(_needle() + b"\n")

    result = _check(tmp_path)

    assert result.returncode == 1
    assert ".github/policy.md:1" in result.stdout
    assert "untracked.txt:1" in result.stdout


def test_checker_skips_explicit_exemptions_and_binary_files(tmp_path: Path) -> None:
    _git_repo(tmp_path)
    (tmp_path / "uv.lock").write_bytes(_needle() + b"\n")
    binary = tmp_path / "archive.bin"
    binary.write_bytes(b"header\0" + _needle())
    checker = tmp_path / "scripts" / "check_vendor_free_docs.sh"
    checker.parent.mkdir()
    checker.write_bytes(_needle() + b"\n")
    subprocess.run(
        ["git", "-C", str(tmp_path), "add", "uv.lock", "archive.bin", str(checker.relative_to(tmp_path))],
        check=True,
    )

    result = _check(tmp_path)

    assert result.returncode == 0
    assert "vendor-name-check: OK" in result.stdout


def test_checker_does_not_follow_symlinks_or_scan_ignored_untracked_files(tmp_path: Path) -> None:
    _git_repo(tmp_path)
    (tmp_path / ".gitignore").write_text("ignored-dir/\nignored.txt\n", encoding="utf-8")
    ignored_dir = tmp_path / "ignored-dir"
    ignored_dir.mkdir()
    external = ignored_dir / "external.txt"
    external.write_bytes(_needle() + b"\n")
    link = tmp_path / "linked.txt"
    link.symlink_to(external)
    (tmp_path / "ignored.txt").write_bytes(_needle() + b"\n")

    result = _check(tmp_path)

    assert result.returncode == 0
    assert "vendor-name-check: OK" in result.stdout


def test_checker_fails_closed_when_git_cannot_enumerate_files(tmp_path: Path) -> None:
    result = _check(tmp_path)

    assert result.returncode == 2
    assert "could not enumerate repository files" in result.stderr


def test_checker_fails_closed_when_a_tracked_file_is_missing(tmp_path: Path) -> None:
    _git_repo(tmp_path)
    tracked = tmp_path / "tracked.md"
    tracked.write_text("ordinary content\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "tracked.md"], check=True)
    tracked.unlink()

    result = _check(tmp_path)

    assert result.returncode == 2
    assert "could not read repository file" in result.stderr
