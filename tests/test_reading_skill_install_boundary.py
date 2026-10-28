"""Regression coverage for the reading skill's dependency boundary."""

from __future__ import annotations

import builtins
import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest


def _load_reading_skill() -> ModuleType:
    source = (
        Path(__file__).resolve().parents[1]
        / "claude-skill-logseq-read"
        / "scripts"
        / "parse_logseq.py"
    )
    spec = importlib.util.spec_from_file_location("reading_skill_test_subject", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_missing_parser_stops_before_reading_or_installing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    helper = _load_reading_skill()
    original_import = builtins.__import__

    def import_without_parser(name, *args, **kwargs):
        if name == "logseq_matryca_parser":
            raise ModuleNotFoundError("parser unavailable", name=name)
        return original_import(name, *args, **kwargs)

    def forbid_process(*args, **kwargs):
        pytest.fail("reading skill attempted to start an installer")

    def forbid_read():
        pytest.fail("reading skill accessed the vault before checking its dependency")

    monkeypatch.setattr(builtins, "__import__", import_without_parser)
    monkeypatch.setattr(subprocess, "run", forbid_process)
    monkeypatch.setattr(helper, "cmd_list", forbid_read)
    monkeypatch.setattr(sys, "argv", ["parse_logseq.py", "--list"])

    with pytest.raises(SystemExit) as error:
        helper.main()

    assert error.value.code == 2
    assert "pip install" in capsys.readouterr().err


def test_installed_parser_reads_a_selected_synthetic_page(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    pages = tmp_path / "pages"
    pages.mkdir()
    (pages / "Demo.md").write_text("- Example block\n", encoding="utf-8")
    monkeypatch.setenv("LOGSEQ_GRAPH_PATH", str(tmp_path))
    helper = _load_reading_skill()

    def forbid_process(*args, **kwargs):
        pytest.fail("reading skill attempted to start an installer")

    monkeypatch.setattr(subprocess, "run", forbid_process)
    monkeypatch.setattr(sys, "argv", ["parse_logseq.py", "--page", "Demo"])
    helper.main()

    captured = capsys.readouterr()
    assert "[Line 1] Example block" in captured.out
    assert captured.err == ""


def test_missing_transitive_dependency_is_not_misreported_as_missing_parser(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    helper = _load_reading_skill()
    original_import = builtins.__import__

    def import_with_missing_dependency(name, *args, **kwargs):
        if name == "logseq_matryca_parser":
            raise ModuleNotFoundError("dependency unavailable", name="transitive_dependency")
        return original_import(name, *args, **kwargs)

    def forbid_process(*args, **kwargs):
        pytest.fail("reading skill attempted to start an installer")

    monkeypatch.setattr(builtins, "__import__", import_with_missing_dependency)
    monkeypatch.setattr(subprocess, "run", forbid_process)

    with pytest.raises(ModuleNotFoundError) as error:
        helper.ensure_installed()

    assert error.value.name == "transitive_dependency"
