---
type: ArchitectureDecisionRecord
title: ADR-0003 AAIF submission gate
description: Evidence-based NO-GO decision for AAIF submission while governance, adoption, legal, and externally verified assurance prerequisites remain incomplete.
status: stable
classification: active
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-08-19
verified: 2026-08-19
stale_after: 2026-11-17
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---

# ADR-0003: AAIF submission gate

## Status and decision

Accepted — **NO-GO for submission; continue AAIF-aligned repository hardening
without claiming membership, certification, sponsorship, or official OKF
conformance**.

## Evidence behind the decision

The repository has a credible technical foundation, a public permissive
license, automated tests and releases, contributor guidance, a roadmap, and an
agent-facing contract. Submission is still premature because current evidence
does not prove:

- a second active maintainer or independent security/release reviewer;
- multi-organization maintainership or broad production adoption;
- a Technical Committee sponsor or completed proposal discussion;
- a completed legal review of contribution, trademark, charter, sponsorship,
  and infrastructure commitments;
- live GitHub security/ruleset settings from an authenticated current receipt;
- a successful real release carrying the new GitHub attestations, SBOM, and
  license inventory;
- official OKF v0.2 conformance—the current source audit has 38 findings.

## Reconsideration gate

The maintainer may move from **defer** to **discuss sponsor** only when a dated
dossier contains:

1. current public `main`, ruleset, Actions-permission, security-feature,
   issue/PR/project, and release receipts;
2. six months of privacy-preserving community-health evidence;
3. at least one independent maintainer with accepted responsibilities and a
   demonstrated review path;
4. permissioned integration/adoption evidence with versions and limitations;
5. a completed dependency/license inventory and successful release artifact
   verification;
6. a legal review outcome for the exact AAIF lifecycle and submission terms;
7. a completed requirement matrix with links to evidence, not aspirations.

Moving from **discuss sponsor** to **submit** requires a new explicit maintainer
authorization after sponsor and legal review. No agent, workflow, roadmap item,
or repository document may submit a project or accept external terms.

## Consequences

- AAIF alignment remains a useful engineering lens, not a marketing badge.
- Protocol adapters remain optional and gated by their own threat model and
  conformance tests.
- Missing adoption, reviewer, and legal evidence stays visible rather than
  being inferred from stars, downloads, or local files.
- This decision is revisited by evidence, not by a calendar deadline alone.
