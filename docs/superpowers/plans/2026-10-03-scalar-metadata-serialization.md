---
type: ImplementationPlan
title: Bounded scalar metadata serialization correction
description: Correct metadata placement without changing parsing or complex property layouts.
status: stable
classification: active
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-10-03
verified: 2026-10-03
stale_after: 2026-11-03
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---

# Scalar Metadata Serialization Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for the single correction task. Steps use checkbox tracking. The controller may assign one bounded implementation worker and an independent reviewer, but owns integration and validation. No commit is authorized.

**Goal:** Preserve genuine scalar block metadata when multiline Markdown is serialized and parsed again.

**Architecture:** Correct the serializer's ordering for eligible nodes only. Keep the parser's property-window rule, continuation indentation, child order, and existing complex metadata output unchanged.

**Tech Stack:** Existing Python package, pytest, Ruff, mypy, and the existing semantic projection. No dependencies or workflows added.

**Spec:** [Composite assurance and diagnostic record](../../quality/COMPOSITE_MARKDOWN_ASSURANCE_2026-10-03.md).

**Design review:** Independent Sol High review returned PASS_WITH_NOTES. The material eligibility notes below are incorporated; this is not implementation qualification or permission to bypass the impact gate.

## Global Constraints

- Baseline HEAD is `0e2b0187ddc54abd92f6a50e7dbde5166e474ffd`; preserve the existing dirty test/documentation increment and use the current checkout.
- The maintainer explicitly accepted the CRITICAL impact warning and approved this bounded correction, independent Sol review, and complete local regressions on 2026-10-03. No commit or push is authorized.
- No parser, graph, filesystem policy, Org, public signature, dependency, tracker, or workflow changes. No commit, push, PR, merge, tag, or publication.
- The historical audit graph reports one direct caller, nine affected symbols, and five affected flow entries. It points to an older checkout/revision, not current whole-repository evidence. The targeted serializer/parser source has no committed difference against that revision; preserve the warning conservatively rather than treating stale counts as current completeness.
- Moving genuine metadata is not permission to reinterpret property-like text after a continuation. Scalar properties on nodes with complex layouts remain outside the correction.
- Do not run generic recipe replay, the consumed diagnostic entry point, or smoke/broad campaigns under this plan. Generic replay/import/runtime binding remains incomplete.

## Review Focus

1. Explicit child UUID metadata must not become text or lose identity after round-trip.
2. A late property-like literal line must remain text even when genuine earlier metadata exists.
3. Root and child continuation alignment must survive two/four-space outlines and LF/CRLF input; serialization may normalize output to LF.
4. Nodes with drawers, list-shaped properties, or multiline metadata values must retain legacy output order; this is not a claim that all legacy mixed layouts round-trip correctly.
5. The semantic assertion must check actual original/reparsed pages and independent literal values, not a constructed AST or a stubbed parser outcome.

## Task 1: Correct eligible scalar metadata placement

**Files:**
- Modify: `src/logseq_matryca_parser/logseq_markdown.py`, `_serialize_logseq_node_lines(node: LogseqNode, tab_size: int) -> list[str]` only, with a small private predicate if necessary.
- Modify/test: `tests/test_logseq_markdown.py`.
- Reuse without changing expectations: `tests/test_pre_release_roundtrip.py`, `tests/test_logos_parser.py`, and `tests/test_compat_corpus.py`.
- Update evidence: the linked assurance record, `docs/ROADMAP_2026-2027.md`, and `docs/log.md`.

**Interfaces:** Consume actual `LogseqNode.properties` and existing `format_logseq_block_property_lines`; produce the same list-of-lines interface and public `serialize_logseq_page` API. Only eligible property placement changes.

- [x] **Step 1: Confirm impact authorization and live anchors.** Reverify HEAD, owned dirty state, and reviewed source. Stop on drift or missing explicit CRITICAL-impact acceptance.
- [x] **Step 2: Write and observe the focused RED regression.** Add `test_scalar_metadata_survives_multiline_roundtrip`, parameterized over tab size 2/4 and LF/CRLF. Use the literal structure below, with child indentation matching the selected tab size:

```markdown
- root
  literal-key:: kept
  root continuation
  lateproperty:: literal
  - child
    id:: 11111111-1111-1111-1111-111111111111
    literal-key:: child-value
    child continuation
```

Assert original metadata equals the literals `kept` and `child-value`; original/reparsed content and properties match; `lateproperty` stays absent from metadata and present in text; child `source_uuid` equals the literal UUID and `synthetic_id` is false. Compare `semantic_roundtrip_v1` with `synthetic_uuid="recomputed"`, `source_uuid="preserve"`, and `relations="outline_paths"`. Require property lines before their respective prose and preserve one root/one child.

- [x] **Step 3: Implement minimal eligible ordering correction.** For nodes with normal prose continuations and emitted ordinary single-line scalar properties, emit genuine properties directly after the opening bullet and before continuations. Require at least one emitted nonempty scalar and an explicit scalar-type allowlist; an arbitrary object's single-line string representation does not establish eligibility. Reject the node if any emitted value is empty after the parser's existing whitespace/quote normalization (`value.strip().strip('"').strip("'")`, followed by the existing emptiness check), contains CR/LF, or has an excluded shape. Exclude logbook/drawer metadata, list/tuple/set properties, and non-scalar containers. Conservatively exclude code, query, drawer, and uncertain complex content layouts; arbitrary nonempty content is not normal prose. Property-like text already following ordinary prose remains literal and must not be mined for metadata. Ignore derived timing keys that are not emitted, without changing their serialization policy. For ineligible nodes, preserve legacy output order. Never modify parser behavior or add lexical-state machinery.
- [x] **Step 4: Correct the conflicting layout expectation.** Keep `test_multiline_block_continuation_lines_use_bullet_text_alignment` but expect its genuine `id::` metadata before its two continuation lines. This is the explicitly reviewed correction, not removal of the alignment assertion.
- [x] **Step 5: Pin excluded-layout behavior and verify focused GREEN.** Add constructed exact-output fixtures for mixed drawer/list/scalar layouts, non-scalar containers, multiline values, empty/whitespace/quote-only scalars, and excluded complex content. Require unchanged legacy output, without claiming semantic correctness on reparse for these excluded layouts. Run the serializer, existing pre-release round-trip, compatibility corpus, and misplaced-property regressions. Stop on an unexpected failure; do not expand to global list/drawer reordering.
- [x] **Step 6: Obtain independent Sol review.** Review the actual diff and RED/GREEN evidence. Require PASS or PASS_WITH_NOTES without unresolved blockers. Repair only within approved scope; an expansion requires a new maintainer decision.
- [x] **Step 7: Run complete local quality gates.** Run `make all` and `make vendor-name-check` with the established isolated cache. Record every failure/skip and coverage; never lower the floor or weaken assertions. These are regression gates, not hosted qualification or random-campaign evidence.
- [x] **Step 8: Record result and stop.** Update the evidence record and roadmap, distinguish fixed scalar behavior from excluded mixed layouts and replay limitations, and stop before commit/push. No previously consumed diagnostic authorization is reused.

## Local completion evidence

All eight steps completed locally on the reviewed uncommitted source. The actual-parse test observed RED in four newline/indent combinations, followed by focused GREEN (312 tests). Independent GPT-6.1 Sol High implementation review returned PASS_WITH_NOTES without blocking findings. Complete `make all` passed Ruff, mypy (103 files), documentation/vendor checks, and pytest (1,153 passed, five native-platform skips, 89.83% coverage). No coverage floor or oracle was weakened.

The admission predicate is a conservative alphanumeric/selected-marker heuristic, not a complete complex-layout classifier. Specifically excluded layouts keep characterized legacy output; residual mixed-layout semantic defects and generic composite replay/campaign limitations remain outside local completion. Reviewed source/test hashes and complete qualification details are in the linked assurance record. The original six dirty files are preserved alongside this source/test correction. No new worktree, commit, push, publication, tracker mutation, or cleanup occurred.
