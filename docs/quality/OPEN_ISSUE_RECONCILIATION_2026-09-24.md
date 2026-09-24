---
type: IssueReconciliation
title: Open GitHub issue reconciliation - 2026-09-24
description: Current evidence-backed disposition and next action for every open repository issue.
status: stable
classification: canonical
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-09-24
verified: 2026-09-24
stale_after: 2026-10-24
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: docs/quality/ISSUE_RECONCILIATION_2026-08-06.md
superseded_by: null
---

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
