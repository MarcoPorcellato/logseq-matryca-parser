#!/usr/bin/env python3
"""Enrich a release SBOM and emit a scoped dependency/license inventory.

The input SBOMs are generated from ``uv.lock`` by ``uv export --format
cyclonedx1.5``. This script normalizes their volatile identity fields. Installed
wheel metadata supplies license evidence; narrowly reviewed overrides are
version-exact and fail closed after a dependency update.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.metadata
import json
import re
import subprocess
import tomllib
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import parse_qs, urlsplit

_SCHEMA_VERSION = 1
_NAME_PATTERN = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
_SIMPLE_LICENSES = {
    "Apache License, Version 2.0": "Apache-2.0",
    "Apache-2.0": "Apache-2.0",
    "MIT": "MIT",
    "MIT License": "MIT",
}
_CLASSIFIER_LICENSES = {
    "License :: OSI Approved :: MIT License": "MIT",
    "License :: OSI Approved :: Python Software Foundation License": "PSF-2.0",
}


@dataclass(frozen=True)
class DistributionEvidence:
    """Relevant installed Core Metadata for one distribution."""

    version: str
    license_expression: str | None
    license_text: str | None
    license_classifiers: tuple[str, ...]
    home_page: str | None
    license_files: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class LicenseOverride:
    """Version-exact maintainer review for ambiguous package metadata."""

    version: str
    license_expression: str
    evidence_url: str
    artifact_sha256: str
    license_file: str
    license_file_sha256: str
    reviewed_on: str
    reason: str


def canonical_name(value: str) -> str:
    """Return the normalized Python distribution name."""
    return re.sub(r"[-_.]+", "-", value).lower()


def requirement_name(requirement: str) -> str:
    """Extract a distribution name from a PEP 508-style requirement string."""
    match = _NAME_PATTERN.match(requirement)
    if match is None:
        raise ValueError(f"cannot determine dependency name from {requirement!r}")
    return canonical_name(match.group(1))


def vcs_revision_from_purl(purl: str) -> str | None:
    """Return the immutable commit encoded by a uv VCS package URL."""
    vcs_urls = parse_qs(urlsplit(purl).query).get("vcs_url", [])
    if len(vcs_urls) != 1:
        return None
    revision = urlsplit(vcs_urls[0]).fragment
    if not re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", revision):
        return None
    return revision.lower()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_sbom(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"SBOM must be a JSON object: {path}")
    if loaded.get("bomFormat") != "CycloneDX" or loaded.get("specVersion") != "1.5":
        raise ValueError(f"expected CycloneDX 1.5 SBOM: {path}")
    if not isinstance(loaded.get("components"), list):
        raise ValueError(f"SBOM components must be a list: {path}")
    return loaded


def component_map(sbom: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    components: dict[str, dict[str, Any]] = {}
    for raw in sbom.get("components", []):
        if not isinstance(raw, dict) or not isinstance(raw.get("name"), str):
            continue
        components[canonical_name(raw["name"])] = raw
    return components


def load_project_declarations(path: Path) -> tuple[str, dict[str, set[str]]]:
    project = tomllib.loads(path.read_text(encoding="utf-8"))
    project_table = project["project"]
    project_name = canonical_name(str(project_table["name"]))
    declarations: dict[str, set[str]] = {}

    for requirement in project_table.get("dependencies", []):
        declarations.setdefault(requirement_name(str(requirement)), set()).add("runtime")

    for group, requirements in project_table.get("optional-dependencies", {}).items():
        for requirement in requirements:
            declarations.setdefault(requirement_name(str(requirement)), set()).add(
                f"optional:{group}"
            )

    for group, requirements in project.get("dependency-groups", {}).items():
        for requirement in requirements:
            name = requirement_name(str(requirement))
            if name != project_name:
                declarations.setdefault(name, set()).add(f"development:{group}")
    return project_name, declarations


def load_overrides(path: Path) -> dict[str, LicenseOverride]:
    loaded = tomllib.loads(path.read_text(encoding="utf-8"))
    if loaded.get("schema_version") != _SCHEMA_VERSION:
        raise ValueError("unsupported dependency license override schema")
    overrides: dict[str, LicenseOverride] = {}
    for item in loaded.get("overrides", []):
        name = canonical_name(str(item["name"]))
        if name in overrides:
            raise ValueError(f"duplicate dependency license override: {name}")
        evidence_url = str(item["evidence_url"])
        version = str(item["version"])
        license_expression = str(item["license_expression"])
        artifact_sha256 = str(item["artifact_sha256"])
        license_file = str(item["license_file"])
        license_file_sha256 = str(item["license_file_sha256"])
        reviewed_on = str(item["reviewed_on"])
        reason = str(item["reason"])
        license_path = PurePosixPath(license_file)
        if not name or not version or not license_expression or not reason:
            raise ValueError("dependency license override fields must not be empty")
        try:
            dt.date.fromisoformat(reviewed_on)
        except ValueError as error:
            raise ValueError(f"override review date must be ISO YYYY-MM-DD: {name}") from error
        if not evidence_url.startswith("https://"):
            raise ValueError(f"override evidence URL must use HTTPS: {name}")
        if not re.fullmatch(r"[0-9a-f]{64}", artifact_sha256):
            raise ValueError(f"override artifact hash must be lowercase SHA-256: {name}")
        if not re.fullmatch(r"[0-9a-f]{64}", license_file_sha256):
            raise ValueError(f"override license-file hash must be lowercase SHA-256: {name}")
        if license_path.is_absolute() or ".." in license_path.parts:
            raise ValueError(f"override license file must be a safe relative path: {name}")
        overrides[name] = LicenseOverride(
            version=version,
            license_expression=license_expression,
            evidence_url=evidence_url,
            artifact_sha256=artifact_sha256,
            license_file=license_file,
            license_file_sha256=license_file_sha256,
            reviewed_on=reviewed_on,
            reason=reason,
        )
    return overrides


def validate_override_artifacts(
    overrides: Mapping[str, LicenseOverride],
    lock_path: Path,
) -> None:
    """Require every override artifact URL and digest to match ``uv.lock``."""
    lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    packages = lock.get("package", [])
    for name, override in overrides.items():
        package = next(
            (
                item
                for item in packages
                if isinstance(item, dict)
                and canonical_name(str(item.get("name", ""))) == name
                and str(item.get("version", "")) == override.version
            ),
            None,
        )
        if package is None:
            raise ValueError(f"override package/version is absent from uv.lock: {name}")
        artifacts = list(package.get("wheels", []))
        if isinstance(package.get("sdist"), dict):
            artifacts.append(package["sdist"])
        expected_hash = f"sha256:{override.artifact_sha256}"
        if not any(
            isinstance(artifact, dict)
            and artifact.get("url") == override.evidence_url
            and artifact.get("hash") == expected_hash
            for artifact in artifacts
        ):
            raise ValueError(f"override artifact evidence does not match uv.lock: {name}")


def installed_distributions() -> dict[str, DistributionEvidence]:
    result: dict[str, DistributionEvidence] = {}
    for distribution in importlib.metadata.distributions():
        metadata = distribution.metadata
        name = metadata.get("Name")
        if not name:
            continue
        classifiers = tuple(
            classifier
            for classifier in metadata.get_all("Classifier", [])
            if classifier.startswith("License ::")
        )
        declared_license_files = set(metadata.get_all("License-File", []))
        for package_path in distribution.files or ():
            relative_path = PurePosixPath(str(package_path))
            if (
                not relative_path.is_absolute()
                and ".." not in relative_path.parts
                and any(part.endswith(".dist-info") for part in relative_path.parts[:-1])
                and relative_path.name.upper().startswith(("LICENSE", "COPYING", "NOTICE"))
            ):
                declared_license_files.add(relative_path.as_posix())
        license_files: list[tuple[str, str]] = []
        distribution_root = Path(str(distribution.locate_file(""))).resolve()
        for relative in sorted(declared_license_files):
            relative_path = PurePosixPath(relative)
            if relative_path.is_absolute() or ".." in relative_path.parts:
                continue
            candidate = Path(str(distribution.locate_file(relative))).resolve()
            try:
                candidate.relative_to(distribution_root)
            except ValueError:
                continue
            if candidate.is_file():
                license_files.append((relative, sha256_file(candidate)))
        result[canonical_name(name)] = DistributionEvidence(
            version=distribution.version,
            license_expression=metadata.get("License-Expression"),
            license_text=metadata.get("License"),
            license_classifiers=classifiers,
            home_page=metadata.get("Home-page"),
            license_files=tuple(sorted(license_files)),
        )
    return result


def resolve_license(
    name: str,
    version: str,
    distribution: DistributionEvidence | None,
    overrides: Mapping[str, LicenseOverride],
) -> tuple[str | None, dict[str, str]]:
    override = overrides.get(name)
    if override is not None:
        if override.version != version:
            return None, {
                "kind": "expired_override",
                "observed_version": version,
                "reviewed_version": override.version,
            }
        if distribution is None or distribution.version != version:
            return None, {"kind": "override_installed_metadata_unavailable"}
        observed_license_hash = dict(distribution.license_files).get(override.license_file)
        if observed_license_hash != override.license_file_sha256:
            return None, {
                "kind": "override_license_evidence_mismatch",
                "license_file": override.license_file,
                "expected_sha256": override.license_file_sha256,
                "observed_sha256": observed_license_hash or "missing",
            }
        return override.license_expression, {
            "kind": "maintainer_override",
            "evidence_url": override.evidence_url,
            "artifact_sha256": override.artifact_sha256,
            "license_file": override.license_file,
            "license_file_sha256": override.license_file_sha256,
            "reviewed_on": override.reviewed_on,
            "reason": override.reason,
        }

    if distribution is None or distribution.version != version:
        return None, {"kind": "installed_metadata_unavailable"}

    expression = (distribution.license_expression or "").strip()
    if expression:
        return expression, {"kind": "core_metadata_license_expression"}

    raw_license = (distribution.license_text or "").strip()
    if raw_license in _SIMPLE_LICENSES:
        return _SIMPLE_LICENSES[raw_license], {
            "kind": "core_metadata_license",
            "raw_value": raw_license,
        }

    mapped = {
        _CLASSIFIER_LICENSES[classifier]
        for classifier in distribution.license_classifiers
        if classifier in _CLASSIFIER_LICENSES
    }
    if len(mapped) == 1:
        expression = next(iter(mapped))
        return expression, {"kind": "core_metadata_classifier"}

    evidence = {"kind": "ambiguous_or_missing_metadata"}
    if raw_license:
        evidence["raw_value"] = raw_license[:200]
    return None, evidence


def git_value(project_root: Path, format_value: str) -> str:
    completed = subprocess.run(
        ["git", "show", "-s", f"--format={format_value}", "HEAD"],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def build_evidence(
    *,
    runtime_sbom: dict[str, Any],
    production_sbom: dict[str, Any],
    development_sbom: dict[str, Any],
    project_name: str,
    declarations: Mapping[str, set[str]],
    distributions: Mapping[str, DistributionEvidence],
    overrides: Mapping[str, LicenseOverride],
    source_revision: str,
    source_date: str,
    lock_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    runtime = component_map(runtime_sbom)
    production = component_map(production_sbom)
    development = component_map(development_sbom)
    universe = {**development, **production, **runtime}

    components: list[dict[str, Any]] = []
    unresolved_direct: list[str] = []
    for name in sorted(universe):
        raw = universe[name]
        version = str(raw.get("version", ""))
        scopes: list[str] = []
        if name in runtime:
            scopes.append("runtime")
        if name in production and name not in runtime:
            scopes.append("optional")
        if name in development and name not in production:
            scopes.append("development")

        declared_in = sorted(declarations.get(name, set()))
        expression, evidence = resolve_license(name, version, distributions.get(name), overrides)
        direct = bool(declared_in)
        if direct and expression is None:
            unresolved_direct.append(name)
        purl = str(raw.get("purl", ""))
        source_type = "vcs" if "vcs_url=" in purl else "registry" if purl else "unknown"
        vcs_revision = vcs_revision_from_purl(purl) if source_type == "vcs" else None
        if source_type == "vcs" and vcs_revision is None:
            raise ValueError(f"VCS dependency lacks an immutable commit revision: {name}")
        item: dict[str, Any] = {
            "name": name,
            "version": version,
            "purl": purl or None,
            "scopes": scopes,
            "direct": direct,
            "declared_in": declared_in,
            "source_type": source_type,
            "license_expression": expression,
            "license_evidence": evidence,
        }
        if vcs_revision is not None:
            item["vcs_revision"] = vcs_revision
        installed = distributions.get(name)
        if installed is not None and installed.home_page:
            item["home_page"] = installed.home_page
        components.append(item)

    inventory = {
        "schema_version": _SCHEMA_VERSION,
        "kind": "dependency_license_inventory",
        "project": project_name,
        "source_revision": source_revision,
        "source_date": source_date,
        "uv_lock_sha256": lock_sha256,
        "scope_definition": {
            "runtime": "required by the base package",
            "optional": "required only when one or more package extras are installed",
            "development": "required only by repository development groups",
        },
        "summary": {
            "component_count": len(components),
            "direct_component_count": sum(item["direct"] for item in components),
            "vcs_component_count": sum(item["source_type"] == "vcs" for item in components),
            "unresolved_direct_licenses": unresolved_direct,
            "unresolved_transitive_licenses": [
                item["name"]
                for item in components
                if not item["direct"] and item["license_expression"] is None
            ],
        },
        "components": components,
    }

    enriched = json.loads(json.dumps(production_sbom))
    enriched["serialNumber"] = "urn:uuid:" + str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"{project_name}:{source_revision}:{lock_sha256}",
        )
    )
    metadata = enriched.setdefault("metadata", {})
    metadata["timestamp"] = source_date
    root = metadata.setdefault("component", {})
    project_distribution = distributions.get(project_name)
    if project_distribution is not None:
        root["version"] = project_distribution.version
        root["purl"] = f"pkg:pypi/{project_name}@{project_distribution.version}"

    inventory_by_name = {item["name"]: item for item in components}
    for component in enriched.get("components", []):
        if not isinstance(component, dict) or not isinstance(component.get("name"), str):
            continue
        inventory_item = inventory_by_name.get(canonical_name(component["name"]))
        if inventory_item is None:
            continue
        expression = inventory_item["license_expression"]
        if expression:
            component["licenses"] = [{"expression": expression}]
        properties = component.setdefault("properties", [])
        properties.append(
            {
                "name": "matryca:dependency:scopes",
                "value": ",".join(inventory_item["scopes"]),
            }
        )
        properties.append(
            {
                "name": "matryca:dependency:direct",
                "value": str(inventory_item["direct"]).lower(),
            }
        )
    return enriched, inventory


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-sbom", type=Path, required=True)
    parser.add_argument("--production-sbom", type=Path, required=True)
    parser.add_argument("--development-sbom", type=Path, required=True)
    parser.add_argument("--inventory-out", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--overrides",
        type=Path,
        default=Path(".github/dependency-license-overrides.toml"),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    project_root = args.project_root.resolve()
    project_name, declarations = load_project_declarations(project_root / "pyproject.toml")
    overrides = load_overrides(project_root / args.overrides)
    validate_override_artifacts(overrides, project_root / "uv.lock")
    enriched, inventory = build_evidence(
        runtime_sbom=load_sbom(args.runtime_sbom),
        production_sbom=load_sbom(args.production_sbom),
        development_sbom=load_sbom(args.development_sbom),
        project_name=project_name,
        declarations=declarations,
        distributions=installed_distributions(),
        overrides=overrides,
        source_revision=git_value(project_root, "%H"),
        source_date=git_value(project_root, "%cI"),
        lock_sha256=sha256_file(project_root / "uv.lock"),
    )

    args.production_sbom.write_text(
        json.dumps(enriched, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    args.inventory_out.parent.mkdir(parents=True, exist_ok=True)
    args.inventory_out.write_text(
        json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    unresolved = inventory["summary"]["unresolved_direct_licenses"]
    if unresolved:
        print("Unresolved direct dependency licenses: " + ", ".join(unresolved))
        return 1
    print(
        "Generated supply-chain evidence for "
        f"{inventory['summary']['component_count']} components; direct licenses resolved."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
