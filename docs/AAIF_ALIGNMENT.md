---
type: AAIFAlignmentGuide
title: AAIF alignment and interoperability boundary
description: Evidence-based explanation of the repository's AAIF-aligned practices without membership or conformance claims.
status: stable
classification: active
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

# AAIF alignment and interoperability boundary

Logseq Matryca Parser adopts practices that are useful for agentic and
open-source interoperability: explicit agent guidance, deterministic local
behavior, public contribution rules, bounded writes, and evidence-backed
release and governance plans.

This repository is **not an AAIF project**, does not claim AAIF membership or
certification, and does not claim an official OKF conformance result. This page
describes alignment goals only.

## Relevant current practices

| AAIF-relevant concern | Repository practice | Evidence |
|---|---|---|
| Agent guidance | A concise `AGENTS.md` explains product boundaries and validation | [`AGENTS.md`](../AGENTS.md) |
| Safe agent actions | Reads, dry runs, writes, approvals, and receipts are separated | [Agent action contract](reference/AGENT_ACTION_CONTRACT.md) |
| Open contribution | Public contribution, support, security, governance, and maintainer paths | [`CONTRIBUTING.md`](../CONTRIBUTING.md), [`GOVERNANCE.md`](../GOVERNANCE.md), [`SUPPORT.md`](../SUPPORT.md) |
| Interoperability boundary | Optional adapters remain lazy and protocol-neutral | [Protocol adapter decision](decisions/ADR-0001-PROTOCOL_ADAPTER_BOUNDARY.md) |
| Deterministic quality | Documentation and code checks are reproducible from the source checkout | [`maintained.toml`](maintained.toml), `make all` |
| Public planning | Milestones have owners, dependencies, and exit evidence | [Public roadmap](ROADMAP_2026-2027.md) |

## What still needs independent evidence

The following are not established by source documentation alone:

- current GitHub rulesets, branch protections, Actions settings, security
  features, projects, discussions, and open backlog state;
- supply-chain attestations, SBOMs, dependency-review enforcement, and release
  provenance verification;
- diverse maintainer participation, production adoption, or multi-organization
  governance;
- an AAIF Technical Committee sponsor, legal agreement, charter, or submission
  decision.

Those require fresh remote receipts, release evidence, community evidence, or
explicit legal/maintainer approval. They are deliberately outside this document.

## Interoperability principles

1. Keep Logseq Markdown authoritative and local-first.
2. Keep optional frameworks and future protocols outside the core parser
   dependency path.
3. Require a concrete user workflow, threat model, stable schema, bounded
   permissions, and conformance tests before implementing a protocol endpoint.
4. Treat vault content as untrusted data, never as agent authority.
5. Publish accurate limitations alongside capabilities.

## Path to a future proposal

The project may revisit an AAIF proposal only after the [public roadmap](ROADMAP_2026-2027.md)
has evidence for governance, supply chain, semantic assurance, contributor
durability, and permissioned adoption. Any decision to discuss sponsorship or
submit a project requires a separate legal and maintainer gate.

For the detailed evidence matrix and non-goals, see the
[GitHub and AAIF readiness study](REPOSITORY_GOVERNANCE_AAIF_STUDY_2026-08-19.md).
