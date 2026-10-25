---
type: IssueReconciliation
title: Open GitHub issue reconciliation - September baseline and October review
description: Dated open-issue and pull-request facts, proposed next actions, and a preserved historical baseline.
status: stable
classification: canonical
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-10-25
verified: 2026-10-25
stale_after: 2026-11-24
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: docs/quality/ISSUE_RECONCILIATION_2026-08-06.md
superseded_by: null
---

# Open GitHub issue reconciliation

September 24 baseline; latest factual refresh: **2026-10-25 12:16 UTC**.

The repository-scoped, read-only GitHub snapshot returned **32 open issues**
and **nine open pull requests**. The observed main revision was
[`03333cca9ca0ed33c0a5bd0603a278e1497b357e`](https://github.com/MarcoPorcellato/logseq-matryca-parser/commit/03333cca9ca0ed33c0a5bd0603a278e1497b357e).
These are dated observations, not live counters or authorization to change
issues, dependencies, projects, checks or releases. Reverify the exact source,
review state and checks before acting.

The existing filename and links are retained. The original September body is
preserved below as labelled history; its uses of “current,” “live” and “existing”
refer only to that earlier snapshot. Extending this document's review window
follows a factual refresh, not a waiver of the documentation freshness gate.

## Current open issues

All 32 observed open issues are listed below. Scope descriptions are in English;
the linked GitHub issue remains authoritative for its exact title and criteria.
“Verify” is a proposed maintainer action, not a claim that acceptance criteria
have already been satisfied or that a new implementation is necessary.

| Issue | English scope summary and next action |
|---|---|
| [#4](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/4) | On-demand AST contract for agentic retrieval: recheck the contract-first proposal against the stable public API before scheduling work. |
| [#5](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/5) | MCP server: keep implementation deferred until protocol, authority and privacy contracts are approved. |
| [#33](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/33) | Minimal CSV exporter: agree columns and CLI scope before implementation. |
| [#34](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/34) | Optional local-RAG RFC: reconcile the existing proposal with its criteria; do not infer runtime or installation authority. |
| [#64](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/64) | Strict indentation mode: preserve the lenient default and require a settled contract and regression matrix first. |
| [#88](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/88) | Embed-expansion strategies: verify dedicated assertions for both strategies before closure. |
| [#89](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/89) | Public graph API coverage: verify attached-node and tracked-path boundary tests. |
| [#91](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/91) | Obsidian-export path helpers: verify direct canonical-path and output-file assertions. |
| [#95](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/95) | CLI error paths: reconcile table-driven missing-path and optional-extra diagnostic coverage. |
| [#108](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/108) | Residual parser-phase extraction: reassess against frozen semantic contracts and preceding assurance evidence; no refactor is authorized here. |
| [#109](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/109) | Documentation lifecycle: retain mechanical validation and track remaining executable-example, private-profile and projection work separately; do not claim full MKQ-4. |
| [#110](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/110) | Structured diagnostics: reconcile remaining parser-recovery and reload producers against the stable payload contract. |
| [#111](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/111) | Decision-performance evidence: continue the [recorded measurement contract](../reference/PERFORMANCE_EVIDENCE.md), keeping native fixture qualification, runtime admission and benchmarks separately gated. The private binding and sampling tests are unmeasured; no numerical budget or issue-completion claim follows. |
| [#131](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/131) | Diagnostic payloads: verify constructor, normalization, ordering and immutability assertions. |
| [#132](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/132) | Human-readable diagnostics: verify table content, source location, exit status and clean-vault output. |
| [#133](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/133) | Nested graph statistics: verify exact page, block, tag and task totals on a multi-level fixture. |
| [#134](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/134) | LOGBOOK serialization: reconcile the requested table-driven cases with recent regressions before claiming closure. |
| [#137](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/137) | Optional extras and troubleshooting: compare maintained references with the issue criteria and link exact evidence. |
| [#138](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/138) | Contributor catalog: verify the recorded wave and remove stale completion claims only with evidence. |
| [#149](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/149) | YAML frontmatter: verify deterministic quoting assertions for sensitive property values. |
| [#150](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/150) | Duplicate block identities: verify deterministic exporter anchor-suffix allocation. |
| [#151](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/151) | Empty and mixed block properties: reconcile writer behavior and dedicated assertions. |
| [#152](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/152) | Packaging diagnostics: review [contributor PR #218](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/218) on its current head and establish hosted-check visibility before acceptance. |
| [#153](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/153) | Reference-style Markdown links: verify definition and use-site coverage in the documentation gate. |
| [#154](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/154) | Page titles, filenames and namespaces: reconcile documentation with tested path mapping and reserved-character behavior. |
| [#155](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/155) | Python library quickstart: verify a minimal local-vault example using stable package imports. |
| [#156](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/156) | Agent-write walkthrough: retain preview, review, containment and explicit apply authority. |
| [#157](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/157) | Compact compatibility map: distinguish supported, preserved, exported and unsupported constructs using current evidence, without universal compatibility claims. |
| [#158](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/158) | Test-contribution guide: verify the fixture, assertion and validation workflow in contributor onboarding. |
| [#185](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/185) | Logseq DB export conformance: keep research-only, with synthetic fixtures, provenance and official export evidence before any adapter proposal. |
| [#213](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/213) | LENS migration governance: retain compatible maintenance until the recorded decision and explicit Trama readiness support a transition. |
| [#227](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/227) | Optional post-parse adapter example: document an adapter boundary without changing Parser core or inferring model/runtime execution authority. |

Compared with September, [#94](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/94)
and [#104](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/104)
are now closed, with observed closure dates September 28 and October 21
respectively; #227 is now in the open set. This refresh verifies GitHub state,
not the complete acceptance evidence for either closure. Issue #111 remains
open and no benchmark or new native correctness run is delivered by this ledger.

## Open pull requests at the October 25 snapshot

Check counts below are the rollup reported for each exact recorded head.
Neutral is not success, and an empty rollup does not prove that checks passed
or that no checks are required. Underlying failure causes and merge readiness
were not re-audited by this snapshot.

| PR | Recorded head | Observed state and check counts | Next action |
|---|---|---|---|
| [#218](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/218) | `3eb261450ac19b82ead5f9d090a1eddde9edf797` | Open, non-draft; no checks reported in the rollup. | Verify contributor diff and check visibility/approval before acceptance; do not reuse September's head or run state. |
| [#235](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/235) | `32246494f794320b25c50c1f1a9f15f59d47fe44` | Open, non-draft; 3 success, 7 failure, 1 neutral. | Review the Hatchling update and diagnose current exact-head test/package failures separately. |
| [#250](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/250) | `5093fdbaeaf9adba6860f966b29e8e13b290f870` | Open, non-draft; 11 success, 1 neutral. | Review the download-action update and current workflow/security evidence separately. |
| [#251](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/251) | `8e9f141262b23250007efa76cfda4a410ab1ea91` | Open, non-draft; 5 success, 6 failure, 1 neutral. | Diagnose test failures before considering the scorecard-action update. |
| [#252](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/252) | `080602d497f1fa7d36745fb758d53267da795237` | Open, non-draft; 11 success, 1 neutral. | Review the upload-action pin and settings-managed security checks separately. |
| [#253](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/253) | `42a45bd8a72c02ebafcdd323ba8aae208795c322` | Open, non-draft; 11 success, 1 neutral. | Review the environment-setup action update independently; no approval follows from this ledger. |
| [#254](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/254) | `52ce1b95bdc447fd514e3f1276e0d9bafe085cf6` | Open, non-draft; 11 success, 1 neutral. | Review the upload-artifact update and require fresh exact-head evidence before integration. |
| [#265](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/265) | `4473e00b76c8b6e07192ee0e244ca4bbf953206d` | Open, draft; 14 success. | Local EOF/documentation corrections are not yet on this published head. Require their complete gates and new-head CI before readiness/controlled integration; the separate native fixture remains unexecuted. |
| [#266](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/266) | `ff614b33608e08b0be74a409d0593841596c041e` | Open, non-draft; 9 success, 1 failure, 1 neutral. | Review the virtualenv update and diagnose the observed quality failure separately; no cause or fix is inferred here. |

PR #265 is included in this pre-publication snapshot. Its later update or merge
will change the live head/state and possibly the open-PR count; that does not
rewrite the observation above. The recorded success on its old head predates
the expired-document gate and is not qualification of the unpublished fixes.

## Verification and lifecycle

- Read the public repository's complete open-issue and open-PR result sets;
  neither bounded result reached its retrieval cap. Fetch the selected main
  independently and verify the two observed closed issues separately.
- Preserve the distinction between source facts, proposed next actions and
  unexecuted acceptance work. No issue, project, dependency or CI mutation was
  performed to produce the snapshot.
- Recheck current source, heads, reviews, checks and issue criteria before any
  action. This ledger neither closes issues nor authorizes implementation,
  model execution, benchmarks, native checks, merge or release.
- Refresh within 30 days. If current data cannot be verified, retain the last
  verification date and mark the snapshot historical rather than renewing its
  freshness without evidence. The documentation checker and its current-date
  freshness policy are unchanged.

## Historical September 24 baseline

The following body is retained from September 24. Its counts, revisions, CI
results, proposed next actions and claims of “current” state apply only to that
date; they are not the October 25 snapshot.

<details>
<summary>Original September 24 issue and PR reconciliation</summary>

# Open GitHub issue reconciliation — 2026-09-24

This is the current issue ledger. At 2026-09-24 07:00 UTC, a live GitHub
search for open issues in `MarcoPorcellato/logseq-matryca-parser` returned 33
open issues. The current `main` anchor was
[`ac91aca6a3d6bf3ad5f6f952ff4b8b366bdc9941`](https://github.com/MarcoPorcellato/logseq-matryca-parser/commit/ac91aca6a3d6bf3ad5f6f952ff4b8b366bdc9941).
The prior August ledger remains preserved as historical evidence; its dated
counts and decisions are not current status.

## Current open issues

| Issue and exact GitHub title | Maintainer next action |
|---:|---|---|
| [#4](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/4) — `[Feature/MCP]: Implement "On-Demand AST Contract" Tool for Agentic RAG` | Recheck the contract-first proposal against the current stable public API before scheduling implementation. |
| [#5](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/5) — `[Feature/Integration]: Implement Logseq MCP (Model Context Protocol) Server` | Keep deferred until contract, privacy, and protocol boundaries are explicitly approved. |
| [#33](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/33) — `feat(forge): add minimal CSV exporter` | Keep as unscheduled feature work; agree exported columns and CLI scope before implementation. |
| [#34](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/34) — `docs: RFC Ollama one-click local RAG` | Compare the existing RFC with issue acceptance criteria, then split implementation follow-ups or close with evidence. |
| [#64](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/64) — `feat(parser): implement strict indentation mode (LogseqIndentationError)` | Preserve lenient default; schedule only with a settled strict-mode contract and regression matrix. |
| [#88](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/88) — `test(synapse_embed): unit tests for embed expansion strategies` | Verify direct coverage for both strategies; close only if dedicated assertions now exist. |
| [#89](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/89) — `test(graph): public API coverage for iter_attached_nodes() and is_tracked_markdown_path()` | Add or verify dedicated attached-node and tracked-path boundary tests. |
| [#91](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/91) — `test(kinetic_export): unit tests for export_obsidian path helpers` | Add or verify direct `kinetic_export` tests for canonical paths and output files. |
| [#94](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/94) — `test(lens): get_deep_statistics dedupes alias page duplicates (BUG-019)` | Add or verify a focused regression assertion for duplicate page-object inputs. |
| [#95](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/95) — `test(kinetic): table-driven CLI error-path coverage` | Complete the table-driven missing-path and optional-extra diagnostics tests. |
| [#104](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/104) — `test(parser): add versioned Logseq compatibility corpus and metamorphic invariants` | Continue bounded corpus and metamorphic-invariant expansion; preserve fixture provenance. |
| [#108](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/108) — `refactor(parser): extract parser phases behind frozen semantic contracts` | Keep blocked until phase boundaries and semantic contracts are frozen by preceding assurance work. |
| [#109](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/109) — `docs: make quality facts and document lifecycle mechanically current` | Source validation is active; track remaining executable examples, private profile, and projection separately. Do not claim full MKQ-4. |
| [#110](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/110) — `feat(diagnostics): expose structured parser and graph diagnostics` | Track remaining parser-recovery and reload diagnostic producers against the stable payload contract. |
| [#111](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/111) — `perf: establish reproducible vault-scale benchmarks and budgets` | Continue reproducible cold/incremental benchmarks and correctness budgets after prerequisite parser fixes. |
| [#131](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/131) — `test(diagnostics): cover payload validation and context determinism` | Verify constructor, normalization, ordering, and immutability assertions remain complete. |
| [#132](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/132) — `test(kinetic): cover the human-readable diagnostics table` | Add or verify stable table content, source location, exit code, and clean-vault message. |
| [#133](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/133) — `test(kinetic): specify nested graph statistics table counts` | Assert exact page, block, tag, and task totals on a multi-level fixture. |
| [#134](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/134) — `test(markdown): add table-driven LOGBOOK drawer serialization cases` | Complete table-driven indentation, blank-entry, tuple/list, and empty-metadata cases. |
| [#137](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/137) — `docs: add a concise optional extras and troubleshooting reference` | Compare current troubleshooting docs with acceptance criteria; close only with exact links and coverage evidence. |
| [#138](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/138) — `docs(contributors): publish wave 5 in the good-first-issue catalog` | Verify catalog content and stale completion notes, then close or narrow the remaining gap. |
| [#149](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/149) — `test(forge): cover YAML frontmatter quoting for special property values` | Cover YAML-sensitive values with deterministic output assertions. |
| [#150](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/150) — `test(forge): specify deterministic anchor suffixes for duplicate block identities` | Assert deterministic suffix allocation for collision-prone identities. |
| [#151](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/151) — `test(markdown): cover empty and mixed block property values` | Cover writer behavior for empty values and mixed list content. |
| [#152](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/152) — `test(packaging): cover invalid wheel archives and CLI failure output` | Review contributor PR #218; wait for maintainer-approved hosted checks on its exact head before closure. |
| [#153](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/153) — `test(docs): cover Markdown reference-style links in the documentation gate` | Add focused documentation-gate tests for definition and use-site behavior. |
| [#154](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/154) — `docs(reference): explain Logseq page titles, filenames, and namespaces` | Document tested path mapping and reserved-character behavior. |
| [#155](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/155) — `docs(COOKBOOK): add a minimal Python library quickstart` | Add a minimal local-vault script and verify it against stable package imports. |
| [#156](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/156) — `docs(reference): add a safe agent-write dry-run walkthrough` | Publish a safety-first example that shows preview, review, and explicit apply boundaries. |
| [#157](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/157) — `docs: add a compact compatibility table for supported Logseq Markdown constructs` | Build the compact supported/preserved/exported/unsupported construct map from current contracts. |
| [#158](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/158) — `docs(contributors): add a focused test-contribution guide` | Link a concise fixture, assertion, and verification workflow from contributor onboarding. |
| [#185](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/185) — `research(logseq-db): measure official export semantic conformance on synthetic fixtures` | Keep research-only; use synthetic fixtures and official export artifacts before proposing an adapter. |
| [#213](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/213) — `[Architecture] Govern LENS deprecation and migration to Trama` | Keep compatibility maintenance bounded; track migration only against the recorded decision and explicit Trama readiness. |

The table above is the complete result set, not a claim that every scope was
retested in this ledger. Where the next action says “verify,” inspect current
source and dedicated tests before closing the issue.

## Open pull requests reviewed with this snapshot

Live PR search returned four open pull requests. Their recorded heads and CI
evidence are snapshots; re-fetch head, base, review threads, and checks before
any merge.

| PR | Head | Snapshot | Next action |
|---:|---|---|---|
| [#218](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/218) | `75b84d731e4b056a214e35aa63d4974b583ecceb` | Base `d990b9a`; Logos Protocol CI run `34034862360` and Dependency Review run `34034862408` both require maintainer approval (`action_required`). | Inspect unchanged diff, authorize checks, then require all exact-head jobs to pass. |
| [#219](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/219) | `63207c96e7f19b12c8a6cfa204d69f774753b41e` | Base `9757647`; Logos Protocol CI run `35405884365` failed; Dependency Review run `35405885270` passed. | Update base after scanner repair, rerun complete required checks, review security result. |
| [#220](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/220) | `a6fa0a30a58b88057cd1363a396395d542b454bd` | Base `584d9ed`; Logos Protocol CI run `35500357616` failed; Dependency Review `35500357720` and Workflow Static Analysis `35500357610` passed. | Update base after scanner repair and rerun all required checks. |
| [#221](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/221) | `18174d2c37d28b809f4f83cd7fcabeea93d18406` | Base `584d9ed`; Logos Protocol CI run `35500363792` failed; Dependency Review `35500363735` and Workflow Static Analysis `35500363753` passed. | Update base and rerun all required checks, including publishing-path static review. |

The existing vendor-policy step produced `rg: command not found` followed by
`vendor-name-check: OK`; do not treat that apparent success as trustworthy.
Its replacement is tracked in the implementation plan. #218's
`action_required` result is neither PASS nor FAIL, and a local test run cannot
substitute for its hosted checks.

## Reconciliation method

- Issue set: live GitHub search for `is:open is:issue`, repository scoped, at
  the timestamp above.
- PR set: live GitHub search for `is:open`, repository scoped; each PR's
  metadata, current head/base, review threads, and latest workflow runs were
  fetched separately at 2026-09-24 07:00 UTC. All four PRs remain open; none is
  merge-ready. The live main commit remains `ac91aca6a3d6bf3ad5f6f952ff4b8b366bdc9941`.
- Code baseline: current default branch commit above. Historical issue counts
  remain in the dated ledgers where they were originally verified.
- Refresh this document within 30 days. If live GitHub state is unavailable,
  preserve the last verification date and identify the ledger as historical
  rather than extending its freshness date.

</details>
