---
type: QualityIndex
title: Quality and architecture audits
description: Canonical navigation for current quality plans, triage, and historical audits.
status: stable
classification: canonical
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-08-26
verified: 2026-08-26
stale_after: 2027-02-22
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---

# Quality & architecture audits

Maintainer-facing triage and backlog for Clean Architecture / Clean Code work.

| Document | Purpose |
|----------|---------|
| [`ISSUE_RECONCILIATION_2026-08-06.md`](ISSUE_RECONCILIATION_2026-08-06.md) | Current disposition of every open GitHub issue and stellar-roadmap integration |
| [`STATIC_ANALYSIS_EVALUATION_2026-08-25.md`](STATIC_ANALYSIS_EVALUATION_2026-08-25.md) | Current static-analysis coverage, candidate comparison, adoption protocol, and maintainer decision gates |
| [`STATIC_ANALYSIS_PILOT_RESULTS_2026-08-26.md`](STATIC_ANALYSIS_PILOT_RESULTS_2026-08-26.md) | Exact-revision results, finding classifications, limitations, and integration gates for the first three pilots |
| [`STATIC_ANALYSIS_AND_CCP_INTEGRATION_2026-08-26.md`](STATIC_ANALYSIS_AND_CCP_INTEGRATION_2026-08-26.md) | Implemented analyzer tiers, workflow hardening, CCP matrix bootstrap, savings boundary, and next activation gate |
| [`../REPOSITORY_STELLAR_ROADMAP_2026-08-06.md`](../REPOSITORY_STELLAR_ROADMAP_2026-08-06.md) | Current repository-wide evidence, priorities and MKQ-4 plan |
| [`../DOCUMENTATION_SYSTEM.md`](../DOCUMENTATION_SYSTEM.md) | Canonical documentation authority, metadata, lifecycle, and federation contract |
| [`GITHUB_CLEAN_ARCH_ROADMAP.md`](GITHUB_CLEAN_ARCH_ROADMAP.md) | Milestone, project board, epic + phase issues (v1.6) |
| [`ISSUE_TRIAGE_2026-07.md`](ISSUE_TRIAGE_2026-07.md) | Superseded July 2026 backlog baseline |
| [`CLEAN_ARCH_BACKLOG.md`](CLEAN_ARCH_BACKLOG.md) | v1 structural debt **complete** — v2 epic (`logos_parser` split) |
| [`../BUG_HUNT_REPORT.md`](../BUG_HUNT_REPORT.md) | Full bug-hunt report (2026-06) with runtime evidence |
| [`../CLEAN_CODE_ARCHITECTURE.md`](../CLEAN_CODE_ARCHITECTURE.md) | **SSOT** — rings, module maps, contributor checklist |
| [`../internal/LOCAL_CODE_STUDY.md`](../internal/LOCAL_CODE_STUDY.md) | Maintainer local code audit runbook |

## Triage verdicts (summary)

| Verdict | Meaning |
|---------|---------|
| **Shipped** | Fixed in v1.4.x–v1.6.0 (see CHANGELOG) |
| **Tracked** | Open GitHub issue or GFI entry |
| **By design** | Documented v1 trade-off — do not "fix" without epic |
| **Rejected** | Audit claim obsolete vs current `src/` |

## Filing new findings

Use the six-section template in [`CLEAN_CODE_ARCHITECTURE.md`](../CLEAN_CODE_ARCHITECTURE.md#filing-github-issues-audit-template). Public issues must **not** name vendor AST tools — cite "local code study wave N" instead.
