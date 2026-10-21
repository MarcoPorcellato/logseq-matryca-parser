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
last_verified: 2026-10-21
verified: 2026-10-21
stale_after: 2027-02-26
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---

# Quality & architecture audits

Maintainer-facing triage and backlog for Clean Architecture / Clean Code work.

| Document | Purpose |
|----------|---------|
| [`PARSER_ASSURANCE_ACCEPTANCE_2026-10-18.md`](PARSER_ASSURANCE_ACCEPTANCE_2026-10-18.md) | Current #104 crosswalk, approved scalar policy, selected depth coverage and remaining acceptance gates; issue remains open |
| [`COMPOSITE_MARKDOWN_ASSURANCE_2026-10-03.md`](COMPOSITE_MARKDOWN_ASSURANCE_2026-10-03.md#current-delivery-and-release-status) | Merged delivery, v1.11.1 boundary and local depth-matrix follow-up; historical checkpoints retained |
| [`GRAPH_PROPERTY_ASSURANCE_2026-10-03.md`](GRAPH_PROPERTY_ASSURANCE_2026-10-03.md) | Separate bounded graph-construction model and its dated qualification |
| [`OFFICIAL_LOGSEQ_MARKDOWN_COMPATIBILITY_2026-10-10.md`](OFFICIAL_LOGSEQ_MARKDOWN_COMPATIBILITY_2026-10-10.md) | Public evidence for all 313 selected official Logseq documents, page metadata semantics and precise compatibility claims |
| [`LOGSEQ_MARKDOWN_DATASET_CANDIDATES_2026-10-10.md`](LOGSEQ_MARKDOWN_DATASET_CANDIDATES_2026-10-10.md) | Research-backed candidates for broader Markdown corpus coverage, with provenance and licensing limits |
| [`official_logseq_corpus_2026-10-10.json`](official_logseq_corpus_2026-10-10.json) | Sanitized per-document results and integrity bindings for the official corpus campaign |
| [`OPEN_ISSUE_RECONCILIATION_2026-09-24.md`](OPEN_ISSUE_RECONCILIATION_2026-09-24.md) | Dated September 24 disposition of 33 open issues and four PRs, not a live counter; recheck GitHub before acting |
| [`ISSUE_RECONCILIATION_2026-08-06.md`](ISSUE_RECONCILIATION_2026-08-06.md) | Historical issue snapshot superseded by the September 24 reconciliation |
| [`../REPOSITORY_STELLAR_ROADMAP_2026-08-06.md`](../REPOSITORY_STELLAR_ROADMAP_2026-08-06.md) | Current repository-wide evidence, priorities and MKQ-4 plan |
| [`../DOCUMENTATION_SYSTEM.md`](../DOCUMENTATION_SYSTEM.md) | Canonical documentation authority, metadata, lifecycle, and federation contract |
| [`../CI_ASSURANCE.md`](../CI_ASSURANCE.md) | Canonical GitHub Actions and repository-settings assurance map |
| [`GITHUB_CLEAN_ARCH_ROADMAP.md`](GITHUB_CLEAN_ARCH_ROADMAP.md) | Milestone, project board, epic + phase issues (v1.6) |
| [`ISSUE_TRIAGE_2026-07.md`](ISSUE_TRIAGE_2026-07.md) | Superseded July 2026 backlog baseline |
| [`CLEAN_ARCH_BACKLOG.md`](CLEAN_ARCH_BACKLOG.md) | Delivered v1.6 slices and residual private #108 scope after #104/#111 gates; no broad parser split |
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
