from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROHIBITED_APIS = (
    "TransitionParser",
    "AveragedPerceptron",
    "PerceptronTagger",
    "save_maxent_params",
)


def test_parser_audits_have_no_nltk_waiver() -> None:
    workflows = (
        ROOT / ".github" / "workflows" / "ci.yml",
        ROOT / ".github" / "workflows" / "pypi_publish.yml",
    )

    for path in workflows:
        workflow = path.read_text(encoding="utf-8")
        assert "uv run pip-audit --no-deps --disable-pip" in workflow
        assert "--ignore-vuln" not in workflow
        assert "--all-extras" in workflow
        assert "--no-dev" in workflow
        assert "--no-emit-workspace" in workflow
        assert "requirements-audit.txt" in workflow


def test_parser_does_not_import_nltk_or_reach_its_vulnerable_apis() -> None:
    production_text = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted((ROOT / "src").rglob("*.py"))
    )

    assert "nltk" not in production_text.casefold()
    for api_name in PROHIBITED_APIS:
        assert api_name not in production_text
