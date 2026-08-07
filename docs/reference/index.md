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
last_verified: 2026-08-07
verified: 2026-08-07
stale_after: 2027-02-02
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

The documentation profile was verified against Matryca Knowledge commit
[`7a3ebd8`](https://github.com/MarcoPorcellato/matryca-knowledge/commit/7a3ebd8).
The official OKF v0.2 baseline recorded there is pinned to commit
`3fcbb9f828c2f23d109c855ee403c3a4c81f3a96` and blob
`a516d50128f5aa1f5746d1464661a39f7143e875`.

This repository currently declares `matryca_okf_inspired_quality`, not official
OKF conformance.

The private `sources.toml` profile at this baseline registers the repository
but does not yet declare its maintained entry points. The source bundle and the
private registry/projection change therefore remain independently reviewed
artifacts.

## Local contracts

- [Python API stability and typing](API_STABILITY.md)
- [Architecture](../CLEAN_CODE_ARCHITECTURE.md)
- [AST primer](../logseq_ast_primer.md)
- [Release process](../RELEASE_PROCESS.md)
- [Security policy](../../SECURITY.md)
- [Current roadmap](../REPOSITORY_STELLAR_ROADMAP_2026-08-06.md)
- [Documentation system](../DOCUMENTATION_SYSTEM.md)
