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
last_verified: 2026-08-25
verified: 2026-08-25
stale_after: 2027-02-17
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---

# Documentation evolution log

## 2026-08-25

- Published v1.8.1 at
  `bb8ec6b758e0e7b3429de49ca252ae8b62f97689` after the coherent graph,
  bounded parser, local-assurance, runtime-evidence, stable NLTK, package,
  supply-chain, and release gates completed.
- Reconciled the active roadmap after release: #103, #186, and the bounded #87
  work are complete; #104 is the next semantic-assurance tranche, followed by
  #111; #108 retains only reducer, semantic-enrichment, equivalence, and
  benchmark work; #185 remains research-only.
- Added the internal
  [post-v1.8.1 backlog execution record](internal/POST_V1_8_1_BACKLOG_EXECUTION_2026-08-25.md)
  with exact source, baseline, authority boundaries, issue and PR gates,
  cost-aware delegation, branch-cleanup proof requirements, and restart
  instructions.
- Reconciled the five strategic issue checklists and the seven-PR starting
  portfolio, published the programme record in PR #191, and deleted 36
  explicitly enumerated merged or superseded remote branches. GitHub readback
  retained only `main`, `gh-pages`, the #191 branch, and the three open
  Dependabot branches. Synchronized Project #5 and both active milestone
  descriptions with the `#104 -> #111 -> #108` sequence, corrected stale
  completed gates, and added #92, #109, #110, and #191 with explicit status,
  evidence, risk, and next-gate fields.

## 2026-08-24

- Prepared the v1.8.1 release candidate from
  `main@2c919fcdef1cb187c30b70b9dd130fa571738b72`, reconciled the changelog
  with the merged parser, graph-coherence, local-assurance, and NLTK work, and
  restored reader-focused v1.8.0 highlights that were missing from the release
  archive. Historical receipts remain bound to their original versions and
  commits.
- Reconciled the public roadmap with live GitHub state and established an
  evidence-gated sequence: finish #103/#180, qualify the mutable NLTK
  declaration in #186, extend existing semantic assurance through #104, make
  cache/executor choices only from #111 comparative evidence, and run the
  synthetic read-only Logseq DB export-conformance study in #185.
- Closed the obsolete v1.0 GUI and completed v1.6 Clean Architecture GitHub
  milestones. Issue #3 remains an adoption-gated RFC; the new
  **Evidence-gated improvements** milestone contains #185 and #186.
- Expanded public GitHub Project #5 into the operational Evidence-Gated Roadmap
  board, added #185, #186, and PR #187, and retained this versioned roadmap as
  the canonical programme contract.
- Preserved the existing generated-document classification and compact
  one-line release-history conventions while clarifying that FORGE exports
  derived artifacts and source-vault writes remain explicit and opt-in.
- Replaced absolute DB lock-in language with a precise boundary: Logseq DB has
  official export paths, Matryca does not currently read DB graphs, and future
  interoperability claims require synthetic conformance evidence.
- Added the declaration-versus-lock immutability rule to the dependency policy;
  a resolved commit in `uv.lock` does not make a mutable top-level VCS tag an
  acceptable release declaration.

## 2026-08-21

- Recorded distinct post-v1.8.0 deliveries: PR #174 merged as
  `8801498a31251dc9b8b6f0e1106835d87e083e16`, PR #175 merged as
  `b56c0c6a6f9f2bc4766c07736c6c566da8c77c3e`, and PR #176 published M9 from
  source head `a8558aca305c43bbadb66b884b9def945f8af36c` as squash merge
  `2a3679e176772bfcc57ed49b2c7c63d9d7d72346`.
- PR #176's [CodeQL run 32434564524](https://github.com/MarcoPorcellato/logseq-matryca-parser/actions/runs/32434564524), [Dependency Review run 32434567688](https://github.com/MarcoPorcellato/logseq-matryca-parser/actions/runs/32434567688),
  and [Logos Protocol CI run 32434567730](https://github.com/MarcoPorcellato/logseq-matryca-parser/actions/runs/32434567730) completed successfully.
- Reconciled maintained status through [PR #177](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/177): source head
  `02bd6f293276faa5001aab05be5c4c19e99364fa` was squash-merged as
  `60082bb725b80904572a43ac01c3849766a242a0`; all eight hosted checks passed.
  Issue #108 is now open with residual reducer, semantic-enrichment, final
  equivalence, and benchmark gates.
- Locally qualified the bounded #87 soft-break correction as code commit
  `c188556`. Derived metadata is finalized once per node, strict-reference state
  is page-local, and parser registries contain the exact returned nodes across
  direct and file entry points. `make all` passed 691 tests at 89.82% coverage;
  the focused parser suite passed 33 tests; deterministic helper-call growth,
  1024-level traversal, semantic snapshots, registry identity, Ruff, mypy,
  documentation, and vendor gates passed. The 1,148-line privacy-clean seed had
  a local 3-warm-up/21-sample median of 0.02702 seconds and p95 of 0.02739
  seconds. This is diagnostic local evidence only: no v1.8.1, hosted #87
  validation, universal speedup, or completion of #103, #104, or #111 is
  claimed.

## 2026-08-20

- Added the maintained [runtime evidence reference](reference/PERFORMANCE_EVIDENCE.md)
  for M8 / #111. It documents the test-only deterministic synthetic-vault
  harness, source-free stdout receipt, semantic gates, optional SYNAPSE
  classification, and local-noise policy. It adds no CI timing threshold,
  cross-machine comparison, release qualification, or public performance claim.
- Prepared v1.8.0 in [PR #171](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/171), merged it as `06a1d6cb3dcbb215c6aa108ce82d37da530d52a5`, and published tag `v1.8.0` through [release workflow run #32324328464](https://github.com/MarcoPorcellato/logseq-matryca-parser/actions/runs/32324328464).
- The exact-tag run passed Python 3.12/3.13 pre-flight, package contract, one-time wheel/sdist build, Twine metadata checks, CycloneDX SBOM generation, dependency/license evidence, checksum verification, GitHub provenance and SBOM attestations, PyPI trusted publication, and GitHub Release creation.
- Verified the public [GitHub Release](https://github.com/MarcoPorcellato/logseq-matryca-parser/releases/tag/v1.8.0) assets after download: SHA-256 checks passed for the wheel, sdist, SBOM, and dependency/license inventory, and GitHub attestation verification passed for all four attestable artifacts. PyPI exposes version `1.8.0` with the published wheel and sdist digests.
- Updated the maintained assurance goal and execution ledger to distinguish completed v1.8.0 publication from the broader #104, #103, #87, #111, and #108 work that remains open.

## 2026-08-19

- Published the evidence-backed [GitHub and AAIF repository readiness study](REPOSITORY_GOVERNANCE_AAIF_STUDY_2026-08-19.md), covering governance, security, documentation, agent interoperability, AAIF alignment, and a cost-aware implementation roadmap. The study records current local evidence, separates verified facts from unknown remote settings, and leaves GitHub mutation for a later execution phase.
- Added the first lightweight governance, maintainer, support, citation, and
  AI-assisted contribution surfaces. These documents describe the current
  single-maintainer model and human accountability without claiming unverified
  GitHub settings, AAIF membership, or multi-organization governance.
- Added the Terra-owned cross-file policy tranche: an agent action and
  provenance contract, compatibility matrix, public roadmap, current triage
  policy, staged ownership map, AAIF alignment page, and protocol-adapter ADR.
  Security, release, legal, official OKF migration, and external GitHub-setting
  decisions remain separate gates with their own evidence requirements.
- Added the Sol-owned source tranche: pull-request dependency review, scheduled
  Scorecard analysis, release-time CycloneDX and dependency/license evidence,
  GitHub provenance and SBOM attestations, and a hardened main-only metrics
  archive with bounded network reads and atomic writes. The maintained policy
  records the local evidence contract separately from hosted workflow and
  exact-tag release receipts.
- Recorded ADR-0002 as a defer decision for official OKF v0.2 while the
  38-finding backlog and nested-index profile conflict remain, and ADR-0003 as
  a NO-GO for AAIF submission until governance, adoption, legal, live security,
  and release evidence gates pass. Historical documents and generated Matryca
  projections remain protected from mechanical rewriting.
- Qualified the completed local governance and assurance diff with Ruff, mypy
  on 61 source files, vendor-name and maintained-documentation checks, YAML
  parsing, 603 tests, 92.16% coverage, and a zero-cycle source import check.
  Repeated SBOM generation normalized to identical bytes; all 14 direct
  dependency licenses resolved, while 31 ambiguous transitive records remain
  explicitly visible as non-blocking review debt, and the one VCS record retains
  a validated immutable commit. The checksum contract was also exercised in
  both its internal `dist/` layout and the flat public-download layout. Hosted
  workflow, settings, and release receipts remain separate gates.
## 2026-08-18

- Created [#165](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/165)
  after an impact review of the parser hub and locally implemented its first M7
  slice: a private pure line-classification event. The reducer, AST creation,
  semantic enrichment, deterministic identities, public imports, and
  dependencies remain unchanged. Parser, corpus, adversarial, and work-growth
  gates passed locally; no publication, benchmark, release, or #108-closure
  claim is made.
- Recorded the accepted [source-location contract decision](rfc/SOURCE_LOCATION_RFC.md).
  Existing one-based `line_start`/`line_end` fields remain the supported
  parse-snapshot coordinates for diagnostics, bounded writer splicing, and
  SYNAPSE lineage. CRLF and Unicode line behavior is now covered directly. No
  byte, code-point, column, range, source-map, parser, public-API, dependency,
  or release change is claimed; a future expansion needs the RFC admission
  gate.
- Recorded [ADR-002](decisions/ADR-002-local-graph-assurance-boundary.md) and
  the [local graph assurance reference](reference/LOCAL_GRAPH_ASSURANCE.md) for
  M5. The optional `matryca-parse assure` command is bounded and local-only: it
  emits a fixed aggregate report, does not persist or upload vault data, rejects
  encountered symlinks, and uses only project-owned parser invariants. The
  process-local socket guard is explicitly not represented as an operating-
  system sandbox; no external-oracle, performance, release, or issue-closure
  claim is made.
- Updated the parser-assurance plan and persistent goal after controlled merges
  of M3 [PR #162](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/162),
  M4 [PR #163](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/163),
  and M2 [PR #164](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/164).
  M5 begins from `main@27d0061`; local implementation head `41486b3` is
  retained as a delivery checkpoint only. Exact-head qualification, independent
  review, hosted checks, PR, merge, and release remain separate gates.
- Completed the direct final M5 review and corrected four fail-closed defects at
  code head `e2d0e5a`: arbitrary runtime strings in child reports, path-bearing
  parent tracebacks for symlink loops, dangling graph-root directory links, and
  global graph input ignored by `--self-test`. The corrected code head passed
  622 tests and all maintained local quality gates. Push, PR, hosted checks,
  merge, and release remain separate gates.

## 2026-08-16

- Recorded accepted negative M2 decision
  [ADR-001](decisions/ADR-001-external-oracle-boundary.md). The repository will
  not install, invoke, pin, package, or integrate an external `mldoc`
  executable under the current Apache-2.0 project boundary. The decision is a
  conservative engineering and governance boundary, not legal advice; it
  preserves M3/M4 as project-owned evidence and leaves M5 limited to
  project-owned invariants unless a later ADR satisfies explicit reconsideration
  conditions. No external executable was downloaded or run, and no source,
  dependency, CI, release, issue-ownership, push, PR, or merge claim is made.
- Started M4 from the locally qualified, unpublished M3 commit `3edbefb`.
  M4 is test-only and counts declared Python-owned parser operations across
  fixed size-scaled synthetic families. It treats platform-labelled elapsed
  time and process high-water memory as non-gating observations only, preserves
  #87 and #111 ownership boundaries, and does not add a runtime hook or API.
- Locally qualified M4 code commit `65275cd`: each non-exception operation now
  has its own `2.5x` growth gate, so a growing counter cannot be hidden by the
  aggregate vector; bounded receipts carry their actual timeout in both data and
  replay command. Targeted lint, type, and 64-test regression checks passed.
  The optional RSS probe degrades safely on platforms without the Unix-only
  `resource` module. This is local evidence only; the exact final review and
  every publication gate remain separate.
- Started the M3 parser-assurance laboratory from `main@5b0a73e` after
  [PR #161](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/161)
  merged M1. M3 is explicitly test-only: deterministic original generators,
  source-free replay receipts, subprocess no-hang classification,
  classification-preserving minimization, structural invariants, valid-case
  semantic round trips, a fixed local subset, and a separately scheduled broad
  profile. It does not claim #103 incremental/cold-load equivalence, #111/#87
  performance evidence, external-oracle parity, a public API, or a release.
- Recorded the second frozen Sol review on
  `5007dc357e05775c6221c8aa84f9a11edc695e0d` as `NEEDS_CORRECTION`: mixed
  backtick runs still caused an authentic content wikilink to be removed, and
  the supplied full-patch receipt had been computed from filtered rather than
  raw Git diff bytes.
- Implemented non-amending corrective commit `7870b84` only in
  `tests/parser_assurance/projection.py` and `tests/test_compat_corpus.py`.
  Exact backtick-run matching, closed fence/query boundaries, math closing, and
  unclosed-comment parity now match parser-observable behavior. The exact Sol
  reproducer, three post-region visible-link tests, and a 14-family direct
  differential probe pass. Exact-head snapshot freshness and `make all` passed
  with 584 tests and 92.16% coverage; Ruff, mypy, documentation, vendor-name,
  diff, and zero-cycle checks also passed. No runtime, package, dependency,
  push, PR, merge, or release change occurred.
- Recorded the first frozen Sol review on `6fcf4b274a3a04ef4c9783cf83149d6ef4aeeabb` as `NEEDS_CORRECTION`.
- Implemented non-amending corrective commit `9e8708eef9cfa63fd9f392f5b5a9e7df564072e7` in
  `CHANGELOG.md`, `tests/parser_assurance/projection.py`, and
  `tests/test_compat_corpus.py`. Exact-head validation on a clean worktree passed
  snapshot freshness, `7` focused regressions, `make all` with `579` tests and
  coverage gate, Ruff, mypy, documentation validation, vendor-name check, diff
  check, and zero-cycle check. The implementation covered the first review's
  simple inline-code, HTML-comment, math, fence, query-macro, and query-region
  cases; it also normalized `#[[Foo]]` as `Foo`. A later review found unequal
  backtick parity incomplete. Spark supplied the
  bounded regression scaffolding, which the primary extended and adjudicated;
  no Luna fallback was needed. Historical `8806205`, `996c5a5`, and `6fcf4b2`
  remain rejected or superseded receipts, not current publication evidence. No runtime
  behavior, package, dependency, push, PR, merge, or release claim was made.
- Reconciled an independent `NEEDS_CORRECTION` review of local M1-A commit
  `8806205`. The canonical parser-assurance plan now defines the M1-B corrective
  contract for reference-property semantics, content-wikilink preservation, LF
  fixture bytes, strict diagnostics and integer fields, quality-gate coverage,
  two-commit evidence sequencing, and separate publication approval. Updated
  the persistent goal and added a restart handoff; no corrective implementation,
  push, PR, or merge is claimed.
- Implemented the local #104-A parser compatibility-corpus foundation: one
  private, test-owned projector with exact-parse and semantic-roundtrip
  profiles; six original Apache-2.0 Markdown fixtures; strict source hashes,
  provenance, schema, parser configuration, protected behavior, diagnostics,
  and identity-policy metadata; bounded file-entrypoint assertions; and shared
  projection logic in the deep-refresh regression suite. This tranche does not
  close #104 and does not change runtime code or the public package API.
- Added the maintained
  [lsdoc reference study and parser assurance plan](LSDOC_REFERENCE_STUDY_AND_EXECUTION_PLAN_2026-08-16.md)
  as a subordinate extension of the stellar roadmap. It maps independently
  transferable verification principles to issues #87, #103, #104, #108, and
  #111 while rejecting a Rust rewrite, source/test/corpus/schema copying, and
  unmeasured parity claims.
- Recorded `martinkoutecky/lsdoc@c79cb059` as public comparative prior art with
  its AGPL-3.0-only boundary. Public disclosure is intentionally limited to the
  maintained study and provenance index; the root README remains focused on
  this project's own capabilities.
- Added a concise persistent goal for durable execution and preserved separate
  approval gates for an external oracle, implementation, merge, release, and
  any license-affecting integration.

## 2026-08-08

- Moved 241 lines of detailed release history from the root README into
  [`RELEASE_HIGHLIGHTS.md`](../RELEASE_HIGHLIGHTS.md), retained a one-line
  summary per documented release at the README bottom, and added a prominent
  direct link. The root README falls from 495 to 287 lines and its Quickstart
  moves from line 382 to line 29. The hero navigation is reduced to five
  primary routes and capabilities are grouped by user outcome.
- Added the maintained
  [README human and AI readability report](README_READABILITY_REPORT_2026-08-08.md)
  with official GitHub guidance, mature-project benchmarks, measured findings,
  a proposed human-first outline, plain-language rules, acceptance criteria,
  and approval-separated follow-up phases.
- Expanded [`AGENTS.md`](../AGENTS.md) from audit-only rules into a concise
  product map, task entry guide, source-of-truth statement, execution contract,
  and parser, graph, filesystem, optional-dependency, and validation guardrails.
- Added a proposal-format [`llms.txt`](../llms.txt) with a concise project
  summary, essential documentation and runnable entry points, and an explicit
  `Optional` history section. Added thin
  [GitHub Copilot instructions](../.github/copilot-instructions.md) that route to
  `AGENTS.md`, `docs/index.md`, and `llms.txt` instead of duplicating their
  detailed content. An exhaustive `llms-full.txt` was intentionally omitted to
  avoid stale duplicated documentation and excessive context. A deterministic
  contract test validates the `llms.txt` structure and every linked repository
  target.
- Merged [PR #126](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/126)
  and published the corrective
  [v1.7.1 release](https://github.com/MarcoPorcellato/logseq-matryca-parser/releases/tag/v1.7.1)
  from `main@b68b964ae5270bea8489f4b80fdc3a6a47759296`. The release delivers
  the previously omitted `examples/run_synapse_rag.py`, validates its three
  public SYNAPSE conversion paths and resolved page embed, and constrains the
  optional AI/development lock to `aiohttp>=3.14.3` and `setuptools>=83.0.0`.
- Verified the complete
  [v1.7.1 release run](https://github.com/MarcoPorcellato/logseq-matryca-parser/actions/runs/31240367822),
  PyPI OIDC provenance for both distributions, and matching SHA-256 values
  across GitHub assets, `SHA256SUMS`, GitHub digest metadata, and PyPI. The
  wheel is `6c5f1d96857c27a99ac852d3a7766521ff89641f67cf27de22c160b6cb810901`;
  the sdist is
  `ba45f10b620a801308722a825da000a3519e3955e8e81ab36d05550a84858ec0`.
- Installed the exact public wheel in clean base and AI-qualified environments.
  Runtime and package metadata reported v1.7.1, the CLI help passed, and the
  published example completed all three SYNAPSE exports. Dependabot reports no
  open alerts after the `aiohttp` and `setuptools` lock corrections, and
  [#90](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/90)
  is closed with public evidence.
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
  present in v1.7.0, so #90 remained open pending the corrective release. Added
  a dated changelog erratum and a post-publication correction procedure; the
  v1.7.0 tag, artifacts, attestations, and digests remain unchanged.

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
