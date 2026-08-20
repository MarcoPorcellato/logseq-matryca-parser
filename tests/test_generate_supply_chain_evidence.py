from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from scripts.generate_supply_chain_evidence import (
    DistributionEvidence,
    LicenseOverride,
    build_evidence,
    load_overrides,
    load_project_declarations,
    resolve_license,
    validate_override_artifacts,
    vcs_revision_from_purl,
)


def _sbom(*components: dict[str, Any]) -> dict[str, Any]:
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "metadata": {"component": {"name": "logseq-matryca-parser"}},
        "components": list(components),
        "dependencies": [],
    }


def _component(name: str, version: str, *, vcs: bool = False) -> dict[str, Any]:
    suffix = (
        "?vcs_url=https://example.invalid/repo%3Frev%3Dv1%23" + "a" * 40
        if vcs
        else ""
    )
    return {
        "type": "library",
        "name": name,
        "version": version,
        "purl": f"pkg:pypi/{name}@{version}{suffix}",
    }


def _metadata(version: str, license_expression: str | None) -> DistributionEvidence:
    return DistributionEvidence(
        version=version,
        license_expression=license_expression,
        license_text=None,
        license_classifiers=(),
        home_page=None,
    )


def test_build_evidence_classifies_scopes_and_enriches_production_sbom() -> None:
    base = _component("base-lib", "1.0")
    optional = _component("optional-lib", "2.0", vcs=True)
    development = _component("dev-lib", "3.0")
    project = _metadata("1.7.1", "Apache-2.0")

    enriched, inventory = build_evidence(
        runtime_sbom=_sbom(base),
        production_sbom=_sbom(base, optional),
        development_sbom=_sbom(base, optional, development),
        project_name="logseq-matryca-parser",
        declarations={
            "base-lib": {"runtime"},
            "optional-lib": {"optional:ai"},
            "dev-lib": {"development:dev"},
        },
        distributions={
            "logseq-matryca-parser": project,
            "base-lib": _metadata("1.0", "MIT"),
            "optional-lib": _metadata("2.0", "Apache-2.0"),
            "dev-lib": _metadata("3.0", "BSD-3-Clause"),
        },
        overrides={},
        source_revision="a" * 40,
        source_date="2026-08-19T00:00:00+00:00",
        lock_sha256="b" * 64,
    )

    by_name = {item["name"]: item for item in inventory["components"]}
    assert by_name["base-lib"]["scopes"] == ["runtime"]
    assert by_name["optional-lib"]["scopes"] == ["optional"]
    assert by_name["optional-lib"]["source_type"] == "vcs"
    assert by_name["optional-lib"]["vcs_revision"] == "a" * 40
    assert by_name["dev-lib"]["scopes"] == ["development"]
    assert inventory["summary"]["unresolved_direct_licenses"] == []
    assert inventory["summary"]["unresolved_transitive_licenses"] == []
    assert enriched["metadata"]["component"]["version"] == "1.7.1"
    assert enriched["metadata"]["timestamp"] == "2026-08-19T00:00:00+00:00"
    assert enriched["serialNumber"].startswith("urn:uuid:")
    enriched_by_name = {item["name"]: item for item in enriched["components"]}
    assert enriched_by_name["base-lib"]["licenses"] == [{"expression": "MIT"}]


def test_build_evidence_normalizes_nondeterministic_sbom_identity() -> None:
    component = _component("base-lib", "1.0")
    first = _sbom(component)
    first["serialNumber"] = "urn:uuid:11111111-1111-1111-1111-111111111111"
    first["metadata"]["timestamp"] = "2026-08-19T00:00:01Z"
    second = _sbom(component)
    second["serialNumber"] = "urn:uuid:22222222-2222-2222-2222-222222222222"
    second["metadata"]["timestamp"] = "2026-08-19T00:00:02Z"
    def normalize(production_sbom: dict[str, Any]) -> dict[str, Any]:
        enriched, _inventory = build_evidence(
            runtime_sbom=_sbom(component),
            production_sbom=production_sbom,
            development_sbom=_sbom(component),
            project_name="logseq-matryca-parser",
            declarations={"base-lib": {"runtime"}},
            distributions={"base-lib": _metadata("1.0", "MIT")},
            overrides={},
            source_revision="a" * 40,
            source_date="2026-08-19T00:00:00+00:00",
            lock_sha256="b" * 64,
        )
        return enriched

    enriched_first = normalize(first)
    enriched_second = normalize(second)

    assert enriched_first == enriched_second


def test_version_exact_override_expires_after_dependency_update() -> None:
    override = LicenseOverride(
        version="1.0",
        license_expression="BSD-3-Clause",
        evidence_url="https://example.invalid/license",
        artifact_sha256="a" * 64,
        license_file="example-1.0.dist-info/LICENSE",
        license_file_sha256="b" * 64,
        reviewed_on="2026-08-19",
        reason="reviewed",
    )

    expression, evidence = resolve_license(
        "example", "2.0", _metadata("2.0", None), {"example": override}
    )

    assert expression is None
    assert evidence["kind"] == "expired_override"


def test_override_requires_the_reviewed_installed_license_file_hash() -> None:
    override = LicenseOverride(
        version="1.0",
        license_expression="BSD-3-Clause",
        evidence_url="https://example.invalid/example.whl",
        artifact_sha256="a" * 64,
        license_file="example-1.0.dist-info/LICENSE",
        license_file_sha256="b" * 64,
        reviewed_on="2026-08-19",
        reason="reviewed",
    )
    metadata = DistributionEvidence(
        version="1.0",
        license_expression=None,
        license_text="BSD",
        license_classifiers=(),
        home_page=None,
        license_files=(("example-1.0.dist-info/LICENSE", "c" * 64),),
    )

    expression, evidence = resolve_license("example", "1.0", metadata, {"example": override})

    assert expression is None
    assert evidence["kind"] == "override_license_evidence_mismatch"


def test_generic_bsd_classifier_is_not_misreported_as_a_specific_license() -> None:
    metadata = DistributionEvidence(
        version="1.0",
        license_expression=None,
        license_text=None,
        license_classifiers=("License :: OSI Approved :: BSD License",),
        home_page=None,
    )

    expression, evidence = resolve_license("example", "1.0", metadata, {})

    assert expression is None
    assert evidence["kind"] == "ambiguous_or_missing_metadata"


def test_generic_apache_classifier_is_not_misreported_as_a_specific_license() -> None:
    metadata = DistributionEvidence(
        version="1.0",
        license_expression=None,
        license_text=None,
        license_classifiers=("License :: OSI Approved :: Apache Software License",),
        home_page=None,
    )

    expression, evidence = resolve_license("example", "1.0", metadata, {})

    assert expression is None
    assert evidence["kind"] == "ambiguous_or_missing_metadata"


def test_current_project_declarations_cover_runtime_optional_and_development() -> None:
    root = Path(__file__).resolve().parents[1]

    project_name, declarations = load_project_declarations(root / "pyproject.toml")

    assert project_name == "logseq-matryca-parser"
    assert declarations["pydantic"] == {"runtime"}
    assert "optional:ai" in declarations["langchain-core"]
    assert "development:dev" in declarations["pytest"]


def test_current_license_overrides_match_locked_artifacts() -> None:
    root = Path(__file__).resolve().parents[1]

    overrides = load_overrides(root / ".github" / "dependency-license-overrides.toml")

    validate_override_artifacts(overrides, root / "uv.lock")
    assert overrides["pyvis"].artifact_sha256 == (
        "5720c4ca8161dc5d9ab352015723abb7a8bb8fb443edeb07f7a322db34a97555"
    )
    assert overrides["pip-audit"].license_file_sha256 == (
        "0d542e0c8804e39aa7f37eb00da5a762149dc682d7829451287e11b938e94594"
    )


def test_vcs_purl_requires_an_immutable_commit_fragment() -> None:
    immutable = (
        "pkg:pypi/example@1.0?"
        "vcs_url=https://example.invalid/repo%3Frev%3Dv1%23" + "b" * 40
    )
    mutable = "pkg:pypi/example@1.0?vcs_url=https://example.invalid/repo%3Frev%3Dmain"

    assert vcs_revision_from_purl(immutable) == "b" * 40
    assert vcs_revision_from_purl(mutable) is None


def test_build_evidence_rejects_a_mutable_vcs_dependency() -> None:
    mutable = _component("mutable-lib", "1.0")
    mutable["purl"] += "?vcs_url=https://example.invalid/repo%3Frev%3Dmain"

    with pytest.raises(ValueError, match="lacks an immutable commit revision"):
        build_evidence(
            runtime_sbom=_sbom(mutable),
            production_sbom=_sbom(mutable),
            development_sbom=_sbom(mutable),
            project_name="logseq-matryca-parser",
            declarations={"mutable-lib": {"runtime"}},
            distributions={"mutable-lib": _metadata("1.0", "MIT")},
            overrides={},
            source_revision="a" * 40,
            source_date="2026-08-19T00:00:00+00:00",
            lock_sha256="b" * 64,
        )
