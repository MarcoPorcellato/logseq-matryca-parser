---
type: ArchitectureDecisionRecord
title: ADR-0002 official OKF v0.2 migration gate
description: Decision to defer a repository-wide official OKF v0.2 claim until reserved-index and historical-document contracts are reconciled upstream.
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

# ADR-0002: official OKF v0.2 migration gate

## Status

Accepted — **defer repository-wide official conformance; continue the separate
Matryca quality profile**.

## Context

The current deterministic official-profile audit of `docs/` reports 38
findings:

- 35 documents without official-profile frontmatter;
- two nested reserved `index.md` files whose current Matryca metadata conflicts
  with the official rule that only the bundle-root index may have frontmatter;
- one bundle-root `index.md` without `okf_version: "0.2"`.

Most of the 35 documents are historical roadmaps, blueprints, audits, and
internal records. Rewriting them in bulk would blur their original evidence
context. Removing metadata from `docs/reference/index.md` and
`docs/decisions/index.md` would also break the currently enforced maintained
Matryca profile. Therefore a mechanical zero-finding rewrite would trade one
declared contract for another and is not an acceptable migration.

## Decision

This repository does not claim official OKF v0.2 conformance. It keeps
`okf_profile: matryca_okf_inspired_quality` and `okf_spec_version: null` until
all of these prerequisites are met:

1. Matryca Knowledge publishes a reviewed compatibility rule for nested
   reserved indexes that allows the source bundle to pass both declared
   profiles without contradictory metadata requirements.
2. The source profile defines whether historic, generated, superseded, and
   internal documents are in the official conformance bundle or a separate
   preserved-history class.
3. A dry-run migration lists every changed file and proves that document bodies,
   dates, canonical roles, Logseq links, and historical meaning remain intact.
4. The exact source commit passes both the official and Matryca audits with
   stable, sorted findings.
5. The generated Knowledge projection is refreshed only through its proposal,
   review, apply, and verification workflow.

Adding `okf_version` to the root index alone is not treated as conformance and
is intentionally deferred until the bundle contract is coherent.

## Consequences

- The current 38 findings remain an explicit, measured migration backlog.
- Maintained source documents may continue to improve under the Matryca profile.
- Historical documents are not mass-rewritten for a score.
- The private generated projection is never hand-edited to hide source
  findings.
- Any future migration is a separate source PR with before/after dual-profile
  receipts.

## Rejected alternatives

- **Mass-add generic `type: Document` frontmatter.** Rejected because it erases
  meaningful document types and rewrites historical evidence without review.
- **Remove nested-index frontmatter immediately.** Rejected because it breaks
  the current enforced profile.
- **Narrow the bundle silently.** Rejected because it would inflate a
  conformance claim by excluding findings without a reviewed source policy.
