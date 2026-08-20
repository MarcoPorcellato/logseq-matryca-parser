---
type: DependencyLicensePolicy
title: Dependency, license, SBOM, and provenance policy
description: Release-time evidence contract for dependency scopes, license metadata, VCS sources, SBOMs, checksums, and attestations.
status: stable
classification: canonical
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-08-19
verified: 2026-08-19
stale_after: 2026-11-17
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---

# Dependency, license, SBOM, and provenance policy

## Release evidence contract

Every new release workflow run must generate these files from the exact tagged
checkout and locked environment:

| Evidence | Contract |
|---|---|
| `SBOM.cdx.json` | CycloneDX 1.5 production graph for the base package and all optional extras, exported from `uv.lock`; volatile exporter timestamp and UUID fields are normalized to the source commit and lock hash |
| `DEPENDENCY_LICENSES.json` | Runtime, optional, development, direct/transitive, registry/VCS, version, PURL, license expression, and evidence classification |
| `SHA256SUMS` | SHA-256 for wheel, sdist, SBOM, and dependency/license inventory |
| GitHub attestations | Build provenance for every checksummed artifact plus an SBOM attestation bound to wheel and sdist |
| PyPI attestations | OIDC-backed attestations created by trusted publishing for the distributions uploaded to PyPI |

The GitHub Release must publish the exact same wheel, sdist, SBOM, inventory,
and checksum manifest downloaded from the immutable build bundle. No public
stage may rebuild them. Manifest entries use the flat public asset names rather
than the build bundle's internal `dist/` directory, so standard verification
works after downloading all release assets into one clean directory.

## License evidence rules

1. Prefer the standardized `License-Expression` field from installed Core
   Metadata.
2. Otherwise accept an unambiguous recognized metadata value or license Trove
   classifier.
3. Ambiguous direct-dependency metadata blocks the release unless a maintainer
   records a version-exact override in
   [`.github/dependency-license-overrides.toml`](../../.github/dependency-license-overrides.toml).
4. An override must identify a content-addressed release artifact, its SHA-256,
   the installed license-file path and SHA-256, a review date, and a reason. The
   generator requires the artifact URL and digest to match `uv.lock`, verifies
   the installed file, and expires the override automatically when the resolved
   package version, artifact, or license bytes change.
5. Missing or ambiguous transitive metadata remains visible as review debt; it
   is listed in the inventory summary and never silently converted into a
   license identifier.
6. VCS dependencies must retain their resolved revision in the PURL. A mutable
   branch or unpinned VCS source is a release blocker.

The inventory is evidence, not legal advice and not an automatic compatibility
opinion. A license change, new copyleft obligation, unknown direct license,
vendored source, or intended relicensing requires maintainer review and, when
material, qualified legal review.

## Dependency-review exception path

Pull requests fail when they introduce a vulnerability rated **moderate** or
higher in runtime or development scope. License enforcement is kept separate
from vulnerability enforcement because license compatibility is context- and
distribution-dependent.

An advisory exception must be a dedicated, reviewable change that records the
advisory ID, affected package and scope, exploitability analysis, compensating
control, owner, and expiry date. Do not make the dependency-review job
`warn-only`, use `pull_request_target`, or grant it write permissions.

## Verification

After downloading a release into a clean directory:

```bash
sha256sum --check SHA256SUMS
gh attestation verify logseq_matryca_parser-*.whl -R MarcoPorcellato/logseq-matryca-parser
gh attestation verify logseq_matryca_parser-*.tar.gz -R MarcoPorcellato/logseq-matryca-parser
gh attestation verify SBOM.cdx.json -R MarcoPorcellato/logseq-matryca-parser
gh attestation verify DEPENDENCY_LICENSES.json -R MarcoPorcellato/logseq-matryca-parser
```

Generating source files and passing local tests proves only the release
contract. The provenance and SBOM gates become **verified** only after a real
tag workflow completes and these commands succeed for its exact artifacts.
