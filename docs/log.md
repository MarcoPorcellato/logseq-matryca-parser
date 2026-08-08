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
last_verified: 2026-08-08
verified: 2026-08-08
stale_after: 2027-02-04
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---

# Documentation evolution log

## 2026-08-08

- Merged [PR #123](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/123)
  and published the SemVer-minor v1.7.0 release from
  `main@af45c1b3e75dfc32f42cfede5083f90aec8b96ce`.
- Verified the complete ordered release run: Python 3.12/3.13 pre-flight,
  dependency audit, non-mutating quality gate, one wheel/sdist build, wheel and
  Twine contracts, SHA-256 manifest, PyPI trusted publication with OIDC
  attestations, and GitHub Release creation from the same bundle.
- Reconciled GitHub, PyPI, and local verification. Wheel SHA-256 is
  `6624b59742206ad9c4cf68dd00686f0995861ebc304f9241d05b5a3d047cf354`;
  sdist SHA-256 is
  `57e44dd90cbc7aa43b7fb47462fdddfe4d8759a45fd6c268250cfa1356a36f62`.
  PyPI provenance exists for both files; direct installation, runtime metadata,
  package import, and CLI help report v1.7.0 successfully.
- Closed #105 with public evidence and opened
  [#124](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/124)
  for the upstream Node.js 20 artifact-action annotations. Current official
  releases still declare `node20`, so no unreviewed workaround was introduced.
- Corrected a factual release-note error: `examples/run_synapse_rag.py` is not
  present in v1.7.0, so #90 remains open. Added a dated changelog erratum and a
  post-publication correction procedure; tag, artifacts, attestations, and
  digests remain unchanged.

## 2026-08-07

- Prepared [PR #122](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/122)
  directly against `main` as the final documentation record for the live issue
  ledger, source-gate evolution, and completed delivery sequence.
- Squash merged PRs #117-#121 in dependency order after tranche-only rebases,
  full local qualification, and fresh required GitHub checks. Recorded each
  resulting default-branch commit in the stellar roadmap.
- Reconciled the live 23-issue backlog after the sequence. Closed #106 manually
  with implementation and validation evidence because #121 satisfied its
  acceptance criteria but GitHub did not apply the PR closing keyword.
- Synchronized the new delivery evidence to GitHub issues #102, #106, #107,
  #109, #110, and #113; #109 now distinguishes the merged source gate from its
  still-open snippet, private-profile, and projection acceptance criteria.
- Updated the documentation evolution record to distinguish the source gate
  merged in #115 from the still-pending private profile and projection work.
- Published [draft PR #121](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/121),
  stacked on #120, as the fifth tranche for issue #106: fail-closed vault
  containment, pre-read and pre-replace target validation, identity checks,
  permission/owner preservation, mutation-free unified patches, configurable
  limits, typed diagnostics, and confined symlink and `file://` asset reads.
- Published [draft PR #120](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/120),
  stacked on #119, as the fourth tranche for issue #102: stable structured
  diagnostics for derived-title, frontmatter-title, and alias collisions;
  documented deterministic winner policy; typed opt-in strict rejection;
  human and JSON CLI rendering; and no-ghost regression coverage.
- Published [draft PR #119](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/119),
  stacked on #118, as the third tranche for issue #110: a stable immutable
  diagnostic schema and code enum, deterministic broken-reference collection,
  vault-relative path enforcement, human and JSON CLI rendering, opt-in
  escalation, and a canonical compatibility contract. Title-collision and
  recoverable-parser producers remain subsequent stacked tranches.
- Published [draft PR #118](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/118),
  stacked on #117, for the confirmed parser P0 #113. The surgical iterative
  rebuild propagates immutable leaf updates to the root at depths through 32
  and is covered across soft breaks, properties, fences, queries, list values,
  ordering, identity, parent/left pointers, and round trips.
- Published [draft PR #117](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/117)
  for issue #107: PEP 561 wheel metadata, a single derived version source,
  stable/experimental/internal API policy, root export and signature contracts,
  and a clean downstream Mypy qualification. The CI trigger now also covers
  pull requests stacked on feature branches.
- Published the issue #101 delivery tranche as
  [draft PR #116](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/116):
  verification-only `lint`, explicit opt-in `lint-fix`, a non-mutating `make all`, and a final CI
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
