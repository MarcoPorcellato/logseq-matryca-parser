---
type: DocumentationLog
title: Documentation evolution log
description: Verifiable chronology for the maintained knowledge bundle.
status: stable
classification: active
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

# Documentation evolution log

## 2026-08-07

- Prepared the issue #101 delivery tranche: verification-only `lint`, explicit
  opt-in `lint-fix`, a non-mutating `make all`, and a final CI
  checkout-integrity assertion guarded by focused contract tests. A global
  Ruff formatter gate was measured but deferred because the existing baseline
  requires a separate 23-file mechanical-formatting change.
- Added a source-owned maintained-document profile in
  [`docs/maintained.toml`](maintained.toml) and implemented
  [`scripts/check_documentation.py`](../scripts/check_documentation.py) with deterministic
  reporting, required frontmatter and link/anchor validation, duplicate canonical
  detection, and non-zero exit on findings.
- Added [`tests/test_check_documentation.py`](../tests/test_check_documentation.py) for valid-bundle checks, failure families,
  deterministic ordering, fenced-code exclusion, duplicate heading anchors, and
  CLI exit codes.
- Added a dedicated `docs-check` target to `Makefile` and a non-mutating CI step
  in `.github/workflows/ci.yml`.
- Replaced two links from the canonical architecture guide to unversioned local
  editor rules with the versioned maintainer audit-code runbook after clean-checkout
  CI exposed the hidden local dependency.
- Activated source-side documentation CI in `make all` and recorded the result in
  this log.
- Did not claim MKQ-4 conformance because private `okf_entry_points` and
  projection activation remain pending.

## 2026-08-06

- Published the canonical
  [documentation system and evolution guide](DOCUMENTATION_SYSTEM.md).
- Reconciled the maintained bundle with Matryca Knowledge `origin/main` at
  commit `7a3ebd8`, including authority, execution mode, lifecycle,
  classification, freshness, and honest conformance boundaries.
- Recorded that the private source registry still requires a separate parser
  entry-point change before projection-level conformance can be claimed.
- Standardized repository documentation and maintainer-facing text in English.
- Added the canonical [knowledge bundle entry point](index.md).
- Published the [stellar repository audit](REPOSITORY_STELLAR_ROADMAP_2026-08-06.md).
- Classified the 2026-07-28 study as a superseded historical baseline.
- Adopted separate OKF lifecycle status and Matryca classification metadata.
- Added decision, reference, quality, and issue-reconciliation entry points.
- Removed volatile test totals from active operational guidance.
- Published draft PR #112, opened parser P0 #113, reconciled the strategic
  backlog and closed nine completed or duplicate issues with evidence.

Earlier release-specific documentation history remains in
[`CHANGELOG.md`](../CHANGELOG.md). Historical counts there are release evidence,
not current quality claims.
