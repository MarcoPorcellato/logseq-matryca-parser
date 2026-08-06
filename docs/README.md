---
type: DocumentationPortal
title: Logseq Matryca Parser documentation
description: Human-facing navigation for maintained, active, and historical project documentation.
status: stable
classification: canonical
audience: contributors
owner: logseq-matryca-parser
last_verified: 2026-08-06
verified: 2026-08-06
stale_after: 2027-02-02
supersedes: null
superseded_by: null
---

# Documentation index

Use this page to find **active** documentation. Files under [`design-docs/`](design-docs/) are historical blueprints from the Document-Driven Development phase — see [`design-docs/README.md`](design-docs/README.md) before implementing from those specs.

This repository is authoritative for its documentation. Its future projection
into [Matryca Knowledge](https://github.com/MarcoPorcellato/matryca-knowledge)
must remain reproducible from an immutable source commit; generated Logseq views
are navigation layers, not the source of truth. The current target is Matryca
quality level MKQ-4, not a claim of official OKF conformance.

## Active documentation

| Document | Audience | Purpose |
| :--- | :--- | :--- |
| [`index.md`](index.md) | Tools, maintainers | Canonical machine entry point for the maintained knowledge bundle |
| [`CLEAN_CODE_ARCHITECTURE.md`](CLEAN_CODE_ARCHITECTURE.md) | Contributors, maintainers | Uncle Bob rings, SOLID, module maps, layer CI |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Contributors, integrators | LOGOS, SYNAPSE, `LogseqGraph`, agents, data flow |
| [`quality/`](quality/) | Maintainers | Architecture backlog (v1 complete), GitHub roadmap, triage |
| [`internal/LOCAL_CODE_STUDY.md`](internal/LOCAL_CODE_STUDY.md) | Maintainers | Local code audit runbook (graph-based MCP) |
| [`logseq_ast_primer.md`](logseq_ast_primer.md) | Parser contributors | Logseq Spatial Markdown domain rules |
| [`GOOD_FIRST_ISSUES.md`](GOOD_FIRST_ISSUES.md) | New contributors | Curated starter tasks; Clean Architecture v1 shipped in **v1.6.0** ([#78](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/78)) |
| [`COOKBOOK.md`](COOKBOOK.md) | Integrators | Copy-paste recipes (Synapse, graph query, watcher, agents, contributor test patterns) |
| [`RELEASE_PROCESS.md`](RELEASE_PROCESS.md) | Maintainers | Semver, tag, and PyPI publish checklist |
| [`CODEQL.md`](CODEQL.md) | Maintainers | CodeQL default setup notes |
| [`BUG_HUNT_REPORT.md`](BUG_HUNT_REPORT.md) | Maintainers, contributors | Local static analysis bug audit (Clean Architecture lens, runtime evidence) |
| [`REPOSITORY_STELLAR_ROADMAP_2026-08-06.md`](REPOSITORY_STELLAR_ROADMAP_2026-08-06.md) | Maintainers, contributors | Evidence-backed repository audit, confirmed defects, issue map, and sequenced improvement roadmap |
| [`quality/ISSUE_RECONCILIATION_2026-08-06.md`](quality/ISSUE_RECONCILIATION_2026-08-06.md) | Maintainers, contributors | Evidence-backed disposition of every issue open at the audit baseline |
| [`decisions/index.md`](decisions/index.md) | Maintainers | Canonical decision registry and ADR gaps |
| [`reference/index.md`](reference/index.md) | Maintainers, integrators | Provenance and Matryca ecosystem relations |
| [`log.md`](log.md) | Maintainers | Maintained documentation chronology |
| [`rfc/OLLAMA_RAG.md`](rfc/OLLAMA_RAG.md) | Integrators | Draft RFC for local Ollama RAG (issue [#34](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/34)) |
| [`roadmaps/`](roadmaps/) | Historians | Executed architectural contracts (Waves 2–12) |

## Historical / reference only

| Path | Note |
| :--- | :--- |
| [`design-docs/`](design-docs/) | Original DDD scaffolds and mldoc parity research |
| [`error_log.md`](error_log.md) | Informal internal fix log |
| [`REPOSITORY_IMPROVEMENT_STUDY_2026-07-28.md`](REPOSITORY_IMPROVEMENT_STUDY_2026-07-28.md) | Superseded audit baseline; retained for provenance |
| [`quality/ISSUE_TRIAGE_2026-07.md`](quality/ISSUE_TRIAGE_2026-07.md) | Superseded July issue-triage baseline |

## Root-level docs

- [`../README.md`](../README.md) — project overview and quickstart
- [`../CONTRIBUTING.md`](../CONTRIBUTING.md) — setup, `make all`, PR workflow, **Your first PR**
- [`../CHANGELOG.md`](../CHANGELOG.md) — shipped releases and Unreleased changes
- [`../CODE_OF_CONDUCT.md`](../CODE_OF_CONDUCT.md) — community standards
- [`../SECURITY.md`](../SECURITY.md) — private vulnerability reporting

## Examples

- [`../examples/run_demo.py`](../examples/run_demo.py) — parse journal fixture, print FORGE output
- [`../examples/demo_logseq_journal.md`](../examples/demo_logseq_journal.md) — sample Spatial Markdown input
