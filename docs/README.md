---
type: DocumentationPortal
title: Logseq Matryca Parser documentation
description: Human-facing navigation for maintained, active, and historical project documentation.
status: stable
classification: canonical
audience: contributors
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

# Documentation index

Use this page to find **active** documentation. Files under [`design-docs/`](design-docs/) are historical blueprints from the Document-Driven Development phase — see [`design-docs/README.md`](design-docs/README.md) before implementing from those specs.

This repository is authoritative for its documentation. Its projection
into [Matryca Knowledge](https://github.com/MarcoPorcellato/matryca-knowledge)
must remain reproducible from an immutable source commit; generated Logseq views
are navigation layers, not the source of truth. The current target is Matryca
quality level MKQ-4, not a claim of official OKF conformance.

Read the [documentation system and evolution guide](DOCUMENTATION_SYSTEM.md)
before changing canonical roles, metadata, lifecycle, paths, or federation
entry points.

## Active documentation

| Document | Audience | Purpose |
| :--- | :--- | :--- |
| [`index.md`](index.md) | Tools, maintainers | Canonical machine entry point for the maintained knowledge bundle |
| [`DOCUMENTATION_SYSTEM.md`](DOCUMENTATION_SYSTEM.md) | Contributors, maintainers | Canonical documentation governance, metadata, lifecycle, validation, and federation workflow |
| [`AI_CONTRIBUTION_POLICY.md`](AI_CONTRIBUTION_POLICY.md) | Contributors, maintainers | AI assistance disclosure, privacy, human accountability, and review rules |
| [`ISSUE_TRIAGE_POLICY.md`](ISSUE_TRIAGE_POLICY.md) | Contributors, maintainers | Labels, priorities, good-first issue lifecycle, stale work, and closure policy |
| [`ROADMAP_2026-2027.md`](ROADMAP_2026-2027.md) | Contributors, maintainers | Current milestones, dependencies, owners, and evidence gates |
| [`AAIF_ALIGNMENT.md`](AAIF_ALIGNMENT.md) | Maintainers, integrators | AAIF-aligned practices and explicit non-membership boundary |
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
| [`REPOSITORY_GOVERNANCE_AAIF_STUDY_2026-08-19.md`](REPOSITORY_GOVERNANCE_AAIF_STUDY_2026-08-19.md) | Maintainers | GitHub governance, supply-chain, agent interoperability, and AAIF-readiness study |
| [`LSDOC_REFERENCE_STUDY_AND_EXECUTION_PLAN_2026-08-16.md`](LSDOC_REFERENCE_STUDY_AND_EXECUTION_PLAN_2026-08-16.md) | Maintainers, parser contributors | License-safe comparative study and execution plan for semantic, complexity, and source-location assurance |
| [`README_READABILITY_REPORT_2026-08-08.md`](README_READABILITY_REPORT_2026-08-08.md) | Maintainers | Measured human and AI README assessment with a phased simplification proposal |
| [`quality/ISSUE_RECONCILIATION_2026-08-06.md`](quality/ISSUE_RECONCILIATION_2026-08-06.md) | Maintainers, contributors | Evidence-backed disposition of every issue open at the audit baseline |
| [`decisions/index.md`](decisions/index.md) | Maintainers | Canonical decision registry, including the external-oracle boundary |
| [`reference/index.md`](reference/index.md) | Maintainers, integrators | Provenance and Matryca ecosystem relations |
| [`reference/DIAGNOSTICS.md`](reference/DIAGNOSTICS.md) | Integrators, contributors | Stable diagnostic codes, payload schema, path safety, CLI rendering, and escalation |
| [`reference/FILESYSTEM_SAFETY.md`](reference/FILESYSTEM_SAFETY.md) | Integrators, contributors | Vault containment, atomic replacement, dry-run, metadata, limits, and asset-read policy |
| [`reference/AGENT_ACTION_CONTRACT.md`](reference/AGENT_ACTION_CONTRACT.md) | Integrators, contributors | Agent authority, approvals, provenance, and prompt-injection boundary |
| [`reference/CONFORMANCE_SUPPORT_MATRIX.md`](reference/CONFORMANCE_SUPPORT_MATRIX.md) | Integrators, contributors | Supported runtimes, public contract tiers, optional adapters, and deprecation rules |
| [`reference/DEPENDENCY_LICENSE_POLICY.md`](reference/DEPENDENCY_LICENSE_POLICY.md) | Maintainers, release reviewers | Release SBOM, dependency/license inventory, checksum, override, and attestation contract |
| [`security/DAILY_METRICS_THREAT_MODEL.md`](security/DAILY_METRICS_THREAT_MODEL.md) | Maintainers, security reviewers | Trust boundaries and fail-closed controls for the self-mutating metrics archive |
| [`decisions/ADR-0001-PROTOCOL_ADAPTER_BOUNDARY.md`](decisions/ADR-0001-PROTOCOL_ADAPTER_BOUNDARY.md) | Maintainers, integrators | Decision to defer protocol endpoints until explicit safety and compatibility gates are met |
| [`decisions/ADR-0002-OFFICIAL-OKF-V02-MIGRATION-GATE.md`](decisions/ADR-0002-OFFICIAL-OKF-V02-MIGRATION-GATE.md) | Maintainers, documentation reviewers | Decision to preserve the measured official OKF backlog until profile conflicts are resolved |
| [`decisions/ADR-0003-AAIF-SUBMISSION-GATE.md`](decisions/ADR-0003-AAIF-SUBMISSION-GATE.md) | Maintainers, legal reviewers | Evidence-based NO-GO and reconsideration gate for any AAIF submission |
| [`reference/LOCAL_GRAPH_ASSURANCE.md`](reference/LOCAL_GRAPH_ASSURANCE.md) | Integrators, maintainers | Bounded aggregate-only local vault assurance, report schema, and privacy boundary |
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
- [`../RELEASE_HIGHLIGHTS.md`](../RELEASE_HIGHLIGHTS.md) — reader-focused release history
- [`../AGENTS.md`](../AGENTS.md) — product map, execution contract, and safety rules for AI agents
- [`../llms.txt`](../llms.txt) — concise standard-format LLM discovery and capability index
- [`../.github/copilot-instructions.md`](../.github/copilot-instructions.md) — thin GitHub-specific adapter to the canonical agent guidance
- [`../CONTRIBUTING.md`](../CONTRIBUTING.md) — setup, `make all`, PR workflow, **Your first PR**
- [`../GOVERNANCE.md`](../GOVERNANCE.md) — decision classes, review authority, and succession
- [`../MAINTAINERS.md`](../MAINTAINERS.md) — current ownership and maintainer path
- [`../SUPPORT.md`](../SUPPORT.md) — support scope and safe issue-reporting boundary
- [`../CITATION.cff`](../CITATION.cff) — machine-readable citation metadata
- [`../CHANGELOG.md`](../CHANGELOG.md) — shipped releases and Unreleased changes
- [`../CODE_OF_CONDUCT.md`](../CODE_OF_CONDUCT.md) — community standards
- [`../SECURITY.md`](../SECURITY.md) — private vulnerability reporting

## Examples

- [`../examples/run_demo.py`](../examples/run_demo.py) — parse journal fixture, print FORGE output
- [`../examples/demo_logseq_journal.md`](../examples/demo_logseq_journal.md) — sample Spatial Markdown input
