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
last_verified: 2026-11-14
verified: 2026-11-14
stale_after: 2026-12-14
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---

# ADR-0002: official OKF v0.2 migration gate

The 2026-11-14 source review retains this decision and its dated evidence;
no current dual-profile audit or external conformance was established.

## Status

Accepted — **defer repository-wide official conformance; continue the separate
Matryca quality profile**.

## Context

The 2026-08-19 deterministic official-profile audit of `docs/` reported 38
findings. The following list is that historical snapshot, not a current count:

- 35 documents without official-profile frontmatter;
- two nested reserved `index.md` files whose current Matryca metadata conflicts
  with the official rule that only the bundle-root index may have frontmatter;
- one bundle-root `index.md` without `okf_version: "0.2"`.

Most of the 35 documents are historical roadmaps, blueprints, audits, and
internal records. Rewriting them in bulk would blur their original evidence
context. The original audit rationale treated nested-index metadata as a
conflict between profiles. A mechanical zero-finding rewrite is not a
substitute for a coherent, reviewed bundle contract.

### Current source-profile state (2026-11-14)

`docs/reference/index.md` and `docs/decisions/index.md` now have no frontmatter.
The source checker deliberately accepts that reserved nested-index form and
validates its links without applying metadata/freshness checks. It remains in
the maintained path list; removing its metadata does not currently break that
checker. The bundle root `docs/index.md` already contains `okf_version: "0.2"`
while retaining `okf_spec_version: null`. These observations reconcile source
state only: they do not renew the historical audit or prove that the whole
bundle passes both profiles. See the [documentation system](../DOCUMENTATION_SYSTEM.md#31-maintained-bundle).

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

The existing root `okf_version` field alone is not treated as conformance.
Repository-wide official migration remains deferred until the complete bundle
contract and the separate qualification gates above are satisfied.

## Consequences

- The 38 findings are a historical measured migration backlog; a current count
  requires a fresh exact-source audit.
- Maintained source documents may continue to improve under the Matryca profile.
- Historical documents are not mass-rewritten for a score.
- The private generated projection is never hand-edited to hide source
  findings.
- Any future migration is a separate source PR with before/after dual-profile
  receipts.

## Rejected alternatives

- **Mass-add generic `type: Document` frontmatter.** Rejected because it erases
  meaningful document types and rewrites historical evidence without review.
- **Treat a nested-index metadata change as conformance.** Rejected: the source
  checker already accepts the frontmatter-free reserved-index form, but that
  exception does not establish a successful dual-profile migration.
- **Narrow the bundle silently.** Rejected because it would inflate a
  conformance claim by excluding findings without a reviewed source policy.
