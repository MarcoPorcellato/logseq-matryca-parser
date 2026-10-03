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
last_verified: 2026-10-03
verified: 2026-10-03
stale_after: 2027-03-31
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---

# Documentation evolution log

## 2026-10-03 — Bounded graph construction property assurance

- Completed the maintainer-approved, test-only local graph-routing increment for
  #104 from `3070a8f1d788a295849ad34f263f63ef83b464ab`. A finite synthetic
  model supplies independent canonical-page, alias-ownership, and backlink
  expectations before comparing disk and snapshot constructions.
- The [implementation record](quality/GRAPH_PROPERTY_ASSURANCE_2026-10-03.md)
  records the reviewed scope, generation limits, oracle sensitivity,
  qualification status, and deferred work. Eleven focused tests pass;
  read-only GPT-6.1 Sol re-review returned PASS after repairs to replay
  metadata, independent outline validation, and corruption-control baselines.
  The final full local gate passed with 1,081 tests, five native-platform
  skips, and 89.79% coverage. No production code, dependency, workflow, or Org
  behavior changed. This evidence describes the uncommitted local
  qualification checkpoint; no hosted qualification or completion of #104
  is claimed. The maintainer subsequently authorized a feature-branch
  commit, push, and draft pull request for exact-head hosted qualification,
  without authorizing merge or release.

## 2026-10-03 — Bounded malformed Markdown assurance

- Added a test-only follow-up to #104, based on v1.11.0 source
  `5d577631e68e695071a0badd440c7b374ea8931d`. Five synthetic stress families
  use finite recipe fields and the existing adversarial subprocess runner;
  the production parser, dependencies, workflows, and Org reader are unchanged.
- Fast and broad generation are opt-in and independently cap parser children
  at twenty and sixty. Each child retains the existing three-second timeout.
  Failures stop the profile without retries or automatic minimization and emit
  source-free replay metadata. This is not a hard parent-command time limit,
  exhaustive malformed grammar, or semantic round-trip claim.
- The initial broad profile passed sixty cases (48 parsed, 12 typed errors).
  Independent Sol review identified a wrong-error acceptance gap, now repaired
  with a specific `BlockReferenceError` oracle and negative controls. The
  thirty-two focused harness tests pass. Post-review `make all` passed with
  1064 tests, five native-platform skips, and 89.79% coverage; the focused
  Markdown regression set passed 119 tests. Wheel/source metadata, isolated
  downstream typing, exact archive byte matching, and bounded artifact privacy
  inspection passed; the full record is in the
  [implementation record](superpowers/plans/2026-10-03-hypothesis-malformed-markdown.md).
- #104 remains open. Trama benefits through the accepted Parser → Plumber →
  Trama/Brain boundary; this increment adds no direct consumer integration.
- Draft PR #232's initial hosted checks completed with thirteen successes and
  one failure in the existing adversarial fast-profile assertion on Windows
  Python 3.13. All thirty-two new harness tests passed there; the opaque
  assertion did not identify the failed case or classification. Added only
  source-free failure receipts and six negative controls to that test, without
  changing the parser, timeout, accepted outcomes, workflow, or retry policy.
  The forty-four focused tests pass locally. This diagnostic change does not
  establish the original failure's cause or resolve it; hosted qualification
  remains required before the draft can be considered merge-ready.
- The diagnostic revision passed local `make all` with 1,070 tests, five
  native-platform skips, and 89.79% coverage, as well as package/typing checks
  and a bounded exact-artifact inspection. Independent read-only Sol review
  returned PASS. These results do not qualify the unexecuted diagnostic CI
  matrix or supersede the initial hosted failure.
- Subsequent hosted qualification passed all fourteen checks on the
  diagnostic revision. PR #232 was squash-merged as
  `3070a8f1d788a295849ad34f263f63ef83b464ab`; its post-merge hosted run
  [37096526012](https://github.com/MarcoPorcellato/logseq-matryca-parser/actions/runs/37096526012)
  passed all nine jobs, including the six native-platform test combinations.
  The original Windows failure did not recur, but its cause remains unknown;
  a later passing run does not explain or erase that historical result.

## 2026-10-02 — v1.11.0 release preparation and Org reader limits

- Reconciled the release-facing docs for v1.11.0 while preserving the verified
  latest-published and supported version as v1.10.0. The 1.11.0 tag does not yet
  exist; a tag push follows the separate PyPI and GitHub Release workflow.
- Documented that the experimental Org reader is private, read-only, and
  non-stable; its diagnostics are selected rather than exhaustive, and retained
  source is not proof of semantic understanding. D3 graph integration is
  deferred; Markdown remains the primary supported parser surface.
- Fixed source-distribution hygiene so selected ignored local maintainer and
  tool-cache directories are excluded. The exact release-candidate source
  archive and wheel were rebuilt and checked; this is artifact evidence, not a
  publication.
- Updated the AI-agent, LLM, support, API-stability, compatibility, and
  documentation indexes to expose the experimental boundary without claiming
  full GNU Org or Logseq conformance.
- Added a dated status refresh to the LlamaIndex companion migration records:
  Parser v1.10.0 is published, Parser PR #225 and Org parser PR #229 are merged,
  and companion PR #1 remains a draft. Rebind its live state before resuming.

## 2026-09-30 — Org reader design gate closed

- The maintainer selected one absolute caller-supplied `.org` path, without a
  vault-root containment promise, and accepted the bounded platform policy and
  stated residuals: OS/provider effects may precede rejection; remote-backed
  I/O may occur; physical locality, immutable snapshots under concurrent
  writes, and a hard wall-clock I/O deadline are not promised.
- The experimental D1 contract records Linux ext-family, macOS APFS, and
  Windows NTFS runner profiles, component-at-a-time no-follow handling,
  same-handle checks, fixed path-free diagnostics, and fail-closed behavior
  outside the selected matrix. These mechanisms are not yet runtime-qualified;
  Windows ABI/adversarial tests and the parser security review remain later
  D2 gates.
- The project-authored corpus and design gates passed before implementation.
  Those results describe the design phase only; they do not qualify the parser
  implementation or any native runtime.
- Sol XHigh approved the final design and D1 contract. This approval covers
  the specification only; it does not qualify the implementation or native
  Windows behavior.
- The design and plan preserve a finite, source-only Org subset; they do not
  claim complete GNU Org or Logseq OG parity. No production parser/API,
  Beads/GitHub mutation, commit, push, PR, merge, or release was made.

## 2026-09-27 — LlamaIndex companion boundary

- Began the LlamaIndex companion separation: Parser `[ai]` and `[all]` now
  exclude `llama-index-core` and NLTK; `SynapseAdapter.to_llamaindex_nodes()`
  remains as a lazy bridge, with native node tests moving to the companion gate.
- Removed the temporary NLTK advisory waiver from Parser CI and release audits.
  A fresh no-waiver audit of the exact locked all-extras production export found
  no known vulnerabilities; this resolves Parser exposure only, not the
  upstream advisory or the companion's future dependency policy.
- Updated the support matrix, API contract, cookbook, architecture guides, and
  agent-facing indexes to mark the proposed companion as not yet published on
  PyPI. Its repository, package ownership, real-node tests, and release remain
  separate authorization and acceptance gates.

## 2026-08-30 — v1.8.2 publication

- Published v1.8.2 from PR #198 merge SHA
  `976d5413df27330226d9b3a65b005d129de236b0` at tag `v1.8.2`.
- Release workflow run [#33295184723](https://github.com/MarcoPorcellato/logseq-matryca-parser/actions/runs/33295184723) completed successfully, creating the [GitHub Release](https://github.com/MarcoPorcellato/logseq-matryca-parser/releases/tag/v1.8.2) and [PyPI 1.8.2](https://pypi.org/project/logseq-matryca-parser/1.8.2/) publication.
- Downloaded release assets matched `SHA256SUMS`, and GitHub attestation
  verification passed for every listed artifact against this repository:

  | Artifact | SHA-256 | Attestation |
  | --- | --- | --- |
  | `logseq_matryca_parser-1.8.2-py3-none-any.whl` | `1b3deb43466c63c46ca3b11cd35a2b4436b0ba3528a5f82bcc52fd0a10cd4820` | Verified |
  | `logseq_matryca_parser-1.8.2.tar.gz` | `aa9a15ab43c1197724550fde121023da52d4ade49f9886eaa0c48df04c37be08` | Verified |
  | `SBOM.cdx.json` | `67802e45427a76f0de1bd9ce544eb5199ac48aa00611fca807b5d5fd01c131e0` | Verified |
  | `DEPENDENCY_LICENSES.json` | `fb75132dd4562d8b25dd8dda45ef41ff0fe64a7966d6967cd859071802f20834` | Verified |

## 2026-08-30 — v1.8.2 release candidate

- Prepared the v1.8.2 release candidate from
  `main@e836f82b09784baf909bc3ec233bed06fa055fc7`, incorporating #194
  (`347ee7a5e9b4a667a39c16699fa4fe868a8adfa2`), #195
  (`7329c182f3df16fcba98328a33a4de7aadaad861`), #196
  (`3e3c9f0cf9cee29c46a94343ff7f4c66a2623d5b`), and #197
  (`e836f82b09784baf909bc3ec233bed06fa055fc7`).
- Reconciled the version source, changelog, release history, reader highlights, security support status, contributor guidance, and maintained Clean Architecture metadata without rewriting historical release records.
- The v1.8.2 tag, PyPI publication, GitHub Release, public hashes, and attestations are pending the ordered tag workflow. A post-publication entry must record the exact public evidence after that workflow succeeds.

## 2026-08-30

- Added the maintained
  [continuous integration assurance map](CI_ASSURANCE.md), separating
  pull-request, scheduled, settings-managed, and release checks and defining
  distinct local, hosted, settings, and publication evidence labels.
- Documented the native GitHub Actions architecture: locked Python 3.12/3.13
  quality and package gates, a six-cell Linux/macOS/Windows runtime matrix,
  pull-request dependency review, path-scoped workflow analysis, monthly
  dependency hygiene, scheduled parser and Scorecard assurance, and the
  existing single-build release chain.
- Reconciled contributor, agent, CodeQL, release, human-index, machine-index,
  and quality navigation without claiming an unexecuted hosted run or an
  unverified repository setting.

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
- Rebased, requalified, and merged dependency PRs #182, #183, and #184 in order
  as `9a3b58dc`, `c43218a8`, and `9ba89162`; then refreshed contributor PR #147,
  dismissed its satisfied change request, recorded a fresh approval, and
  merged it as `8852bab8`, automatically closing #130. The #184 correction
  synchronized the immutable attestation-action pin and release-contract
  expectation, passed 761 local tests at 91.20% coverage plus the package
  contract, and received eight successful hosted checks on its exact head.
- Delivered the bounded LENS alias regression in test-only
  [PR #192](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/192).
  A historical literal-reference mutation produced duplicate nodes `P` and
  `Alt` (RED); the current graph-aware implementation retained only canonical
  `P` (GREEN). Twelve focused tests, 762 full-suite tests at 91.20% coverage,
  wheel and Twine contracts, and eight hosted checks passed. The PR merged as
  `2e3e3689`, closed #92, and moved its Project #5 item to **Done** with E2
  maintained-corpus evidence.

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

## 2026-09-24

- Added the current live issue reconciliation after GitHub search found 33 open
  issues and four open pull requests; retained the August ledger as historical
  evidence and linked the successor from maintained documentation indexes.
- Replaced the repository policy scan's unavailable `rg` dependency with a
  standard-library scanner that includes hidden and non-ignored untracked files,
  and fails closed when Git cannot enumerate or read repository content.
- Added regression tests for hidden-path detection, explicit exemptions,
  binary files, untracked files, and Git-enumeration failure.

## 2026-09-26

- Recorded one partial local increment for parser assurance issue #104:
  bounded, grammar-valid Hypothesis outline and semantic round-trip properties.
  Validation used source `HEAD` `d85ea35ec2dbd37f5121d5052bf1e481bded973d`
  plus the uncommitted Task 1–3 worktree changes; it is not a hosted CI or
  released-artifact claim.
- With CI-pinned uv 0.11.7 and Python 3.12.13, the focused parser/corpus tests
  passed (70 tests), `make all` passed (821 tests, 91.18% coverage against the
  unchanged 80% floor), and the wheel/sdist package contract passed, including
  wheel metadata, pinned Twine 6.2.0, and downstream strict typing with mypy
  1.20.2. Hypothesis 6.168.1 remains development-only; its locked dependency
  `sortedcontainers` 2.4.0 was already present in the lock and both packages
  are absent from the production dependency export. No separate high-example
  CI job was added; the local full suite took 67.10 seconds, while hosted CI
  duration and cost impact were not measured.
- The isolated mypy pre-commit environment pins Hypothesis 6.168.1 so the
  repository's test-tree check can resolve the new development-only import;
  no hosted CI workflow or job was added.
- The generated input is bounded by the recorded strategy limits, but Hypothesis
  example count is a target rather than a hard execution cap. This slice adds
  no hard timeout, general parser-correctness, or no-hang claim. Existing M3
  adversarial, replay, and subprocess-timeout evidence remains separate and
  authoritative. This work does not close issue #104; malformed-input strategies,
  graph/filesystem behavior, and concurrency remain deferred Hypothesis-specific
  expansions.

## 2026-10-01 — Org parser enters native CI qualification

- Added a private, read-only Org parser and synthetic adversarial coverage
  without changing Markdown parsing, graph loading, package-root exports, or
  runtime dependencies.
- The documented scope remains experimental and limited to a finite Logseq OG
  subset. Graph loading, writing, watcher integration, Logseq DB support, and
  full Org-mode conformance remain out of scope.
- The earlier local checkpoint passed 1,027 tests with five platform-specific
  skips at 89.78% coverage; its whole-branch review was **BLOCKED** pending
  filesystem-transition coverage and clean-source package evidence. Those
  repairs were completed and reviewed in the subsequent checkpoint.
- The final local macOS arm64 gate passed 1,032 tests with five platform-specific
  skips at 89.79% coverage. The skips include native Linux and Windows reader
  checks; local results do not qualify either platform.
- The final clean-source package gate passed wheel contract, Twine 6.2.0,
  downstream strict typing, and scoped artifact privacy checks. Its sdist had
  303 entries, included each of the 16 changed Markdown documents exactly once,
  and excluded the local restart handoff and cache/build artifacts.
- Native Linux x86-64 and Windows x64 qualification remains open for the draft
  GitHub Actions matrix. This CI-qualification draft is not merge-ready.
- No release, package publication, public API promotion, or merge is implied.
