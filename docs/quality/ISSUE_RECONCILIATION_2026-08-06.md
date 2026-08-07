---
type: IssueReconciliation
title: GitHub issue reconciliation - 2026-08-06
description: Evidence-backed disposition of every open repository issue after the stellar audit.
status: stable
classification: active
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-08-07
verified: 2026-08-07
stale_after: 2026-09-05
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: docs/quality/ISSUE_TRIAGE_2026-07.md
superseded_by: null
publication_pr: 112
---

# GitHub issue reconciliation — 2026-08-06

This ledger reviews all 37 issues that were open at the audit baseline. A
closure is justified only by current code, tests or an explicit duplicate;
runtime behavior without a dedicated regression test remains tracked.

The reconciliation was published in [PR #112](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/112).
After the actions below and the merged follow-up PRs #114-#116, live
verification on 2026-08-07 found 27 open issues, including the parser P0 whose
implementation is pending in the stacked PR sequence.

## Decisions

| Issue | Decision | Wave | Evidence or dependency |
|---:|---|---|---|
| #3 | Keep as canonical GUI RFC | Later | Requires adoption evidence and #111 budgets |
| #4 | Keep; make contract-first | Next | Depends on #107 public API and #110 diagnostics |
| #5 | Keep as integration epic | Later | Depends on #4, #106, #107 and #110 |
| #6 | Close as duplicate of #3 | — | Same desktop GUI outcome |
| #7 | Keep, defer | Later | Measure topology scale under #111 first |
| #8 | Close completed | Shipped | Obsidian visitor, CLI export, docs and tests exist |
| #25 | Close completed | Shipped | `docs/COOKBOOK.md` and links exist |
| #26 | Close completed | Shipped | Docs index, historical warning and contributor link exist |
| #28 | Close completed | Shipped | Example uses package imports and English operator text |
| #33 | Keep as bounded contributor feature | Later | No CSV exporter exists |
| #34 | Keep as draft RFC | Next | RFC exists; approval and implementation slices remain |
| #63 | Close completed | Shipped | Malformed JSON and wrapper tests exist |
| #64 | Keep | Next | Strict indentation remains opt-in design work; depends on #104/#110 |
| #66 | Close completed | Shipped | Missing page and block embeds now both fail-safe to empty |
| #69 | Closed by merged [PR #114](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/114) | Shipped | Optional-dependency operator messages are standardized in English |
| #87 | Keep, high priority | Now | Deterministic pathological parser latency; feeds #111 |
| #88 | Keep | Next | Direct strategy-module tests are still absent |
| #89 | Keep as canonical graph API test issue | Next | Dedicated boundary tests remain incomplete |
| #90 | Keep | Next | `examples/run_synapse_rag.py` is absent |
| #91 | Keep | Next | Direct `kinetic_export` tests are absent |
| #92 | Keep, narrow to regression protection | Next | Runtime resolves canonical aliases; dedicated alias test is absent |
| #93 | Keep, narrow to LENS recipe | Next | Broken-ref tip exists; complete visualization recipe is absent |
| #94 | Keep as test-only | Next | Runtime deduplicates page objects; alias regression test is absent |
| #95 | Keep | Next | Requested table-driven CLI matrix remains incomplete |
| #96 | Close completed | Shipped | Current symmetric empty replacement is table-tested |
| #97 | Close as duplicate of #89 | — | Orphan exclusion is a subset of #89 |
| #101 | Closed by merged [PR #116](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/116) | Shipped | Verification-only lint, opt-in fix target, non-mutating `make all`, and checkout-integrity assertion |
| #102 | Implementation in [PR #120](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/120) | Wave 2 | Stable collision diagnostics, preserved winner policy, typed strict mode, CLI rendering, and no-ghost tests; pending merge |
| #103 | Expand | Wave 0/3 | Add rename/backlink cold-load equivalence |
| #104 | Expand | Wave 0/3 | Add arbitrary-depth parser regression matrix |
| #105 | Keep | Wave 4 | Immutable build-once release lineage remains absent |
| #106 | Implementation in [PR #121](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/121) | Wave 0 | Vault confinement, target identity, metadata preservation, dry-run patch, limits, typed diagnostics, symlink and `file://` tests; pending merge |
| #107 | Implementation in [PR #117](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/117) | Wave 1 | PEP 561 wheel marker, derived version contract, API tiers, import/signature tests, and downstream Mypy probe; pending merge |
| #108 | Keep blocked by prerequisites | Wave 6 | Begin only after deep parser fix and #104 corpus |
| #109 | Source gate merged in [PR #115](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/115); keep open | Wave 1 | Maintained bundle, metadata, lifecycle, links, anchors, freshness, and deterministic source CI are active; private profile/projection and executable snippet coverage remain |
| #110 | Foundation in [PR #119](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/119) | Wave 2 | Stable payload, broken-reference code, JSON CLI, and path policy implemented; collision producer in PR #120, while parser-recovery, filesystem, and reload producers remain |
| #111 | Expand | Wave 5 | Include #87 seed and incremental/cold-load correctness budgets |
| #113 | Implementation in [PR #118](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/118) | Wave 0 | Iterative leaf-to-root rebuild and depth/family regression matrix; pending merge |

## GitHub actions applied

- Opened [#113](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/113)
  with the minimized probe, impact result, depth matrix, round-trip invariants
  and prerequisite links to #104 and #108.
- Closed completed issues #8, #25, #26, #28, #63, #66 and #96 with live
  implementation/test evidence.
- Closed #6 as a duplicate of #3 and #97 as a duplicate subset of #89.
- Added audit dispositions and dependencies to every remaining strategic,
  product and contributor issue whose scope or priority changed.
- Expanded #103, #104, #106, #108, #109, #110 and #111 with the new acceptance
  criteria from the audit.

## Operating order

```text
deep parser P0 + #106 filesystem boundary
  -> #103 snapshot correctness + #104 semantic corpus
  -> #101 + #107 + #109 trust baseline
  -> #102 + #110 safe diagnostics
  -> #105 release provenance
  -> #111 measured scale
  -> #108 parser phase extraction
```

Product RFCs and contributor issues may proceed in parallel only when they do
not touch protected parser/graph hubs or weaken these gates.

## Post-baseline documentation progress

- Merged [PR #114](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/114)
  standardizes repository documentation and maintainer-facing text in English
  and closes #69.
- Merged [PR #115](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/115)
  activates the deterministic maintained-document source gate. Private profile
  activation, executable snippet coverage, and projection verification remain
  open under #109 before MKQ-4 can be claimed.
- Merged [PR #116](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/116)
  closes #101 with a non-mutating quality gate and checkout-integrity check.
- Draft PRs #117-#121 form a verified implementation stack for #107, #113,
  the #110 diagnostics foundation, #102, and #106 respectively.
- Draft [PR #122](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/122)
  publishes the final live-backlog reconciliation and stack merge protocol on
  top of #121 without claiming additional implementation scope.
