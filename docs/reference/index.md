---
type: ReferenceIndex
title: Reference and provenance index
description: Canonical external relations and immutable provenance for maintained documentation.
status: stable
classification: canonical
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-08-19
verified: 2026-08-19
stale_after: 2027-02-19
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---
# Reference and provenance index

## Matryca relations

| Repository | Relationship |
|---|---|
| [Matryca Knowledge](https://github.com/MarcoPorcellato/matryca-knowledge) | Federated knowledge projection and MKQ governance; never the source authority for this repository |
| [Matryca Plumber](https://github.com/MarcoPorcellato/matryca-plumber) | Downstream consumer of parser, graph and CLI contracts |

## Governance baseline

The current local coordination evidence was checked on 2026-08-19 against the
Matryca Knowledge checkout at
`f0318a04f1ad30a87f8d55727f96a759d9e2aa90` on
`feat/okf-v02-migration-tool`; its local `main` ref was `805f02b`. The parser
source profile now declares these maintained entry points:

- `docs/index.md`
- `docs/README.md`
- `docs/log.md`
- `docs/reference/index.md`
- `docs/decisions/index.md`

The dated federation audit records the Matryca-v1 profile as conformant with
zero findings for the parser, while the separate official OKF v0.2 migration
profile remains nonconformant with 38 parser findings. These are distinct
quality profiles and must not be merged into one conformance claim.

This repository currently declares `matryca_okf_inspired_quality`, not official
OKF conformance.

The source repository remains authoritative for parser documentation. The
private registry and any generated projection remain independently reviewed
artifacts; this local source update does not claim that a public projection has
already been refreshed.

## Comparative prior art

| Repository | Reviewed revision | Relationship and boundary |
|---|---|---|
| [`martinkoutecky/lsdoc`](https://github.com/martinkoutecky/lsdoc) | [`c79cb059`](https://github.com/martinkoutecky/lsdoc/commit/c79cb059da5b4360ebde2e5fd953fa1f43ddabc3), AGPL-3.0-only | Public comparative prior art for parser assurance. This repository does not include or adapt lsdoc code, tests, corpora, schemas, module structure, or documentation. See the [study and execution plan](../LSDOC_REFERENCE_STUDY_AND_EXECUTION_PLAN_2026-08-16.md). |

## Local contracts

- [Python API stability and typing](API_STABILITY.md)
- [Structured diagnostics](DIAGNOSTICS.md)
- [Vault-bound filesystem safety](FILESYSTEM_SAFETY.md)
- [Agent action, authority, and provenance](AGENT_ACTION_CONTRACT.md)
- [Support and compatibility matrix](CONFORMANCE_SUPPORT_MATRIX.md)
- [Dependency, license, SBOM, and provenance policy](DEPENDENCY_LICENSE_POLICY.md)
- [Daily metrics threat model](../security/DAILY_METRICS_THREAT_MODEL.md)
- [Architecture](../CLEAN_CODE_ARCHITECTURE.md)
- [AST primer](../logseq_ast_primer.md)
- [Release process](../RELEASE_PROCESS.md)
- [Security policy](../../SECURITY.md)
- [Public roadmap](../ROADMAP_2026-2027.md)
- [Current roadmap](../REPOSITORY_STELLAR_ROADMAP_2026-08-06.md)
- [Parser assurance extension](../LSDOC_REFERENCE_STUDY_AND_EXECUTION_PLAN_2026-08-16.md)
- [Documentation system](../DOCUMENTATION_SYSTEM.md)
