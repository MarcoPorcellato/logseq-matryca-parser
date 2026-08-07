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
last_verified: 2026-08-07
verified: 2026-08-07
stale_after: 2027-02-02
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
| Documentation lifecycle and MKQ | [`DOCUMENTATION_SYSTEM.md`](../DOCUMENTATION_SYSTEM.md) | Source contract recorded; MKQ-4 enforcement and private profile activation pending under issue #109 |

Every future ADR must identify owner, status, decision date, supersession links,
compatibility impact, verification evidence, and rollback.
