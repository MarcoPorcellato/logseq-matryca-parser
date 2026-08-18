---
type: DecisionIndex
title: Architecture decision index
description: Canonical registry of architectural decisions and required ADRs.
status: draft
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
# Architecture decision index

The existing architecture guides remain authoritative while formal ADRs are
introduced incrementally. Do not rewrite historical roadmaps into ADRs.

| Decision area | Current authority | ADR status |
|---|---|---|
| Clean Architecture rings and graph API | [`CLEAN_CODE_ARCHITECTURE.md`](../CLEAN_CODE_ARCHITECTURE.md) | Recorded in guide; ADR pending |
| Logseq AST and synthetic identity | [`logseq_ast_primer.md`](../logseq_ast_primer.md) | ADR pending |
| Title and alias collision policy | [Issue #102](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/102) | Proposed |
| Writer/watcher concurrency | [Issue #103](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/103) | Proposed |
| Filesystem confinement | [Issue #106](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/106) | Proposed |
| Public API stability | [`reference/API_STABILITY.md`](../reference/API_STABILITY.md) | Contract recorded; wheel enforcement published in [PR #117](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/117) |
| Parser assurance and external oracle boundary | [`ADR-001-external-oracle-boundary.md`](ADR-001-external-oracle-boundary.md) | Accepted negative M2 decision; no external oracle under the current boundary |
| Privacy-safe local graph assurance | [`ADR-002-local-graph-assurance-boundary.md`](ADR-002-local-graph-assurance-boundary.md) | Accepted M5 aggregate-only local CLI boundary; no content retention or network operation |
| Documentation lifecycle and MKQ | [`DOCUMENTATION_SYSTEM.md`](../DOCUMENTATION_SYSTEM.md) | Source contract recorded; MKQ-4 enforcement and private profile activation pending under issue #109 |
| Protocol adapter boundary | [`ADR-0001-PROTOCOL_ADAPTER_BOUNDARY.md`](ADR-0001-PROTOCOL_ADAPTER_BOUNDARY.md) | Accepted: keep the core protocol-neutral until explicit schema, safety, permissions, and conformance gates are met |
| Official OKF v0.2 migration | [`ADR-0002-OFFICIAL-OKF-V02-MIGRATION-GATE.md`](ADR-0002-OFFICIAL-OKF-V02-MIGRATION-GATE.md) | Accepted: defer conformance while the measured 38-finding backlog and nested-index profile conflict remain |
| AAIF submission | [`ADR-0003-AAIF-SUBMISSION-GATE.md`](ADR-0003-AAIF-SUBMISSION-GATE.md) | Accepted: NO-GO until governance, adoption, legal, live security, and release-evidence gates pass |

Every future ADR must identify owner, status, decision date, supersession links,
compatibility impact, verification evidence, and rollback.
