from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _run_python(source: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(source)],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


def test_root_import_and_base_parse_do_not_import_llamaindex_or_nltk() -> None:
    result = _run_python(
        """
        import sys
        import logseq_matryca_parser as parser

        page = parser.LogosParser().parse("- boundary check", page_title="Boundary")
        assert page.root_nodes
        assert not any(
            name.startswith(("llama_index", "nltk")) for name in sys.modules
        )
        """
    )

    assert result.returncode == 0, result.stderr


def test_langchain_and_cli_paths_do_not_import_llamaindex_or_nltk() -> None:
    langchain_result = _run_python(
        """
        import sys
        from logseq_matryca_parser import LogosParser, SynapseAdapter

        page = LogosParser().parse("- boundary check", page_title="Boundary")
        documents = SynapseAdapter.to_langchain_documents(
            page.root_nodes, source_name="Boundary.md"
        )
        assert documents
        assert not any(
            name.startswith(("llama_index", "nltk")) for name in sys.modules
        )
        """
    )
    assert langchain_result.returncode == 0, langchain_result.stderr

    cli_result = _run_python(
        """
        import sys
        from typer.testing import CliRunner
        from logseq_matryca_parser.kinetic import app

        result = CliRunner().invoke(app, ["--help"])
        assert result.exit_code == 0, result.output
        assert not any(
            name.startswith(("llama_index", "nltk")) for name in sys.modules
        )
        """
    )
    assert cli_result.returncode == 0, cli_result.stderr
