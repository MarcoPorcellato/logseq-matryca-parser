---
type: KnowledgeBundle
title: Logseq Matryca Parser knowledge bundle
description: Canonical machine entry point for maintained project knowledge.
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
okf_version: "0.2"
---

# Logseq Matryca Parser knowledge bundle

This is the stable entry point for tools that consume maintained repository
knowledge. The source repository is authoritative; generated projections are
navigation layers only.

## Maintained entry points

| Resource | Role |
|---|---|
| [Documentation portal](README.md) | Human navigation by audience |
| [AI agent guide](../AGENTS.md) | Product map, execution contract, safety boundaries, and repository gates |
| [LLM discovery index](../llms.txt) | Concise standard-format project and capability map for inference-time discovery |
| [Documentation system](DOCUMENTATION_SYSTEM.md) | Canonical governance, lifecycle, metadata, and federation guide |
| [AI contribution policy](AI_CONTRIBUTION_POLICY.md) | Human accountability, privacy, disclosure, and review rules for AI-assisted work |
| [Agent action contract](reference/AGENT_ACTION_CONTRACT.md) | Read/write authority, provenance, prompt-injection boundary, and approval matrix |
| [Support and compatibility matrix](reference/CONFORMANCE_SUPPORT_MATRIX.md) | Supported runtimes, public API tiers, optional adapters, and explicit limits |
| [Dependency, license, SBOM, and provenance policy](reference/DEPENDENCY_LICENSE_POLICY.md) | Release evidence, override, checksum, and attestation contract |
| [Daily metrics threat model](security/DAILY_METRICS_THREAT_MODEL.md) | Security boundary for the self-mutating repository traffic archive |
| [Architecture](CLEAN_CODE_ARCHITECTURE.md) | Canonical architecture and public graph API |
| [Repository roadmap](REPOSITORY_STELLAR_ROADMAP_2026-08-06.md) | Current evidence-backed improvement plan |
| [GitHub and AAIF readiness study](REPOSITORY_GOVERNANCE_AAIF_STUDY_2026-08-19.md) | Governance, supply-chain, agent, and AAIF-readiness study |
| [Public roadmap](ROADMAP_2026-2027.md) | Current milestones, dependencies, owners, and exit evidence |
| [Issue triage policy](ISSUE_TRIAGE_POLICY.md) | Labels, priorities, contributor handoff, stale work, and closure policy |
| [AAIF alignment](AAIF_ALIGNMENT.md) | Interoperability alignment without AAIF membership or conformance claims |
| [Protocol adapter decision](decisions/ADR-0001-PROTOCOL_ADAPTER_BOUNDARY.md) | Conditions for any future networked agent protocol adapter |
| [Official OKF migration gate](decisions/ADR-0002-OFFICIAL-OKF-V02-MIGRATION-GATE.md) | Decision to keep official v0.2 conformance deferred while measured profile conflicts remain |
| [AAIF submission gate](decisions/ADR-0003-AAIF-SUBMISSION-GATE.md) | Current NO-GO and evidence required before sponsor or submission discussion |
| [Parser assurance extension](LSDOC_REFERENCE_STUDY_AND_EXECUTION_PLAN_2026-08-16.md) | License-safe comparative study and dependency-ordered semantic and complexity plan |
| [README readability report](README_READABILITY_REPORT_2026-08-08.md) | Measured human and AI readability assessment and phased proposal |
| [Issue reconciliation](quality/ISSUE_RECONCILIATION_2026-08-06.md) | Current GitHub backlog decisions |
| [Decision index](decisions/index.md) | Architectural decisions, including the external-oracle boundary |
| [Reference index](reference/index.md) | Provenance and external relations |
| [Structured diagnostics](reference/DIAGNOSTICS.md) | Stable diagnostic schema, codes, path safety, rendering, and escalation |
| [Filesystem safety](reference/FILESYSTEM_SAFETY.md) | Vault containment, atomic write, dry-run, metadata, and asset-read policy |
| [Local graph assurance](reference/LOCAL_GRAPH_ASSURANCE.md) | Bounded aggregate-only vault checks with no report persistence or network operation |
| [Documentation log](log.md) | Chronology of maintained knowledge changes |

## Root governance and support

| Resource | Role |
|---|---|
| [Governance](../GOVERNANCE.md) | Decision classes, review authority, conflicts, and succession |
| [Maintainers](../MAINTAINERS.md) | Current ownership and maintainer path |
| [Support](../SUPPORT.md) | Public support scope, safe issue reports, and boundaries |
| [Citation metadata](../CITATION.cff) | Machine-readable software citation record |

## Quality claim

The current target is Matryca quality level **MKQ-4**. This bundle does not
claim official OKF conformance. Validation must remain offline, deterministic,
non-mutating, and reproducible from a clean source commit. The private source
profile declares this repository's maintained entry points. An exact-source
audit and reviewed projection refresh remain separate gates; their status must
not be inferred from this source bundle alone.
