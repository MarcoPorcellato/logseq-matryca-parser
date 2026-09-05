from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADVISORY_ID = "PYSEC-2026-3740"
GHSA_ID = "GHSA-8mgp-746c-j5xp"
PROHIBITED_APIS = (
    "TransitionParser",
    "AveragedPerceptron",
    "PerceptronTagger",
    "save_maxent_params",
)


def test_nltk_advisory_exception_is_exact_and_release_consistent() -> None:
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    release = (ROOT / ".github" / "workflows" / "pypi_publish.yml").read_text(
        encoding="utf-8"
    )

    exact_exception = f"--ignore-vuln {ADVISORY_ID}"
    assert ci.count(exact_exception) == 1
    assert release.count(exact_exception) == 1
    assert "--ignore-vuln CVE-2026-71492" not in ci + release
    assert (ci + release).count("--ignore-vuln") == 2


def test_nltk_advisory_exception_records_required_governance() -> None:
    policy = (
        ROOT / "docs" / "security" / "DEPENDENCY_ADVISORY_EXCEPTIONS.md"
    ).read_text(encoding="utf-8")

    for required in (
        ADVISORY_ID,
        GHSA_ID,
        "nltk 3.10.3",
        "optional AI",
        "@MarcoPorcellato",
        "2026-10-05",
        "https://github.com/nltk/nltk/security/advisories/GHSA-8mgp-746c-j5xp",
    ):
        assert required in policy


def test_parser_does_not_reach_the_waived_nltk_apis() -> None:
    production_text = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted((ROOT / "src").rglob("*.py"))
    )

    assert "nltk" not in production_text.casefold()
    for api_name in PROHIBITED_APIS:
        assert api_name not in production_text
