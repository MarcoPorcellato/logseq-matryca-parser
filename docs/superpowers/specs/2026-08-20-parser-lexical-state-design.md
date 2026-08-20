---
type: DesignSpecification
title: Private parser lexical-state extraction
description: A behavior-preserving second #108 parser phase slice after M7 line classification.
status: proposed
classification: active
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-08-20
verified: 2026-08-20
stale_after: 2026-11-20
parent_plan: docs/LSDOC_REFERENCE_STUDY_AND_EXECUTION_PLAN_2026-08-16.md
issue: 108
base_commit: b56c0c6a6f9f2bc4766c07736c6c566da8c77c3e
---

# Private parser lexical-state extraction

## Purpose

Deliver the next deliberately narrow implementation slice for issue #108. The
current parser has already separated pure per-line classification (M7), but
`StackMachineParser.parse()` still owns the lexical mode flags and their
transitions directly. This slice makes that lexical state an explicit private
unit without changing the parser's public API or observable output.

The falsifiable outcome is that the parser produces the same page title,
properties, root-node order, node UUIDs, parent and left links, source lines,
references, and serialized semantic round trip for all existing corpus and
regression inputs, while `parse()` delegates lexical-mode state ownership to a
private module.

## Verified starting point

- `origin/main` was fetched on 2026-08-20 at
  `b56c0c6a6f9f2bc4766c07736c6c566da8c77c3e` after merged PR #175.
- M7 / PR #170 already routes the parser through private `_LineClassification`
  values. Repeating that extraction is out of scope.
- `StackMachineParser.parse()` still carries state for YAML frontmatter, code
  fences, query blocks, LOGBOOK drawers, page-frontmatter eligibility, and
  block-property eligibility.
- The indexed source import graph has zero cycles at this starting point.
- An isolated all-extras baseline could not complete because the pinned Git
  fetch for transitive `nltk` failed with an HTTP/2 transport error. It is not
  a test result and must be retried before implementation qualification.

## Selected approach

Introduce a private lexical-state unit, owned only by the parser package. It
will represent the existing six mode flags and provide named, deterministic
transitions for the already-classified events that enter or leave those modes.
`StackMachineParser.parse()` remains the sole owner of:

- AST stack reduction and root-node attachment;
- node construction, refresh, UUID/source-UUID registration, and references;
- page property values and serialization-facing model construction;
- error propagation, `strict_refs`, and file-entrypoint behavior.

The lexical unit must not inspect Markdown independently, read files, mutate
nodes, build diagnostics, or gain a package-root export. `_LineClassification`
continues to recognize syntax. The new unit consumes those classification
signals and the explicitly supplied parse context needed to preserve existing
control flow.

## Alternatives considered

1. **Selected: lexical-state extraction.** It removes a cohesive private
   responsibility while retaining the already-proven M7 classifier and the AST
   reducer. The cost is a careful equivalence suite around mode transitions.
2. **Fence/query-only extraction.** It would be smaller, but leaves YAML and
   drawer eligibility state intertwined in `parse()` and does not create a
   durable lexical boundary.
3. **AST stack-reducer extraction.** It has a much larger blast radius across
   immutable refresh, identities, hierarchy, and parser recovery. It is
   deferred until the lexical boundary has its own exact evidence.

## Required behavior

The extracted state must preserve the current meanings of:

- a first-line YAML delimiter, YAML properties, closing delimiter, and title
  override;
- code-fence entry and closure, including property eligibility after closure;
- query macro entry and closure while content is appended to the active node;
- LOGBOOK drawer entry, `:END:` closure, and a bullet that returns processing
  to normal block handling;
- the distinction between page-frontmatter eligibility and block-property
  eligibility;
- current pending-list finalization and continuation behavior at lexical-mode
  boundaries.

No behavior change is authorized for malformed Markdown, recovery, timing
budgets, diagnostics, parsing of untracked files, graph construction, writer
operations, or optional SYNAPSE integrations. If source inspection shows that
any transition needs a new compatibility decision, stop this slice and record
the decision instead of changing semantics incidentally.

## Internal boundary

The implementation may add one private module under
`src/logseq_matryca_parser/` and private types/functions with underscore names.
It may adjust `logos_parser.py` only to construct, query, and advance that
state. The private module may depend on a narrow protocol or primitive values;
it must not import `LogseqNode`, `LogseqPage`, graph, writer, CLI, or optional
adapter modules. This keeps lexical state acyclic and independently testable.

## Evidence and validation

Before any parser edit, run fresh impact analysis on the exact
`StackMachineParser.parse` hub and inspect direct callers. Do not proceed past
an unresolved HIGH or CRITICAL finding without explicit maintainer approval.

The implementation must add focused tests that exercise every listed
transition, including mixed boundaries such as a property after a closed fence,
a query closure followed by ordinary content, and a drawer terminated by a
bullet. Existing compatibility-corpus, deep-refresh, adversarial, round-trip,
and deterministic work-growth tests must preserve their current contracts.

Qualification of the exact implementation head requires:

```bash
rtk make all
rtk make vendor-name-check
rtk git diff --check origin/main...HEAD
```

It also requires the focused parser, corpus, deep-refresh, adversarial, and
work-growth selectors recorded in the implementation plan; a zero-cycle source
check; a fresh exact-head impact review; and an independent final review. The
runtime-evidence harness may be replayed as diagnostic evidence, but it is not
a timing gate or a performance claim for this slice.

## Security, licensing, and privacy

The work remains Apache-2.0 clean-room. No external parser code, tests,
fixtures, schemas, control flow, or documentation may be copied or adapted.
No vault data, credentials, generated caches, or benchmark receipts may be
committed. The slice introduces no network operation, dependency, public API,
or filesystem authority.

## Publication and completion boundary

This specification authorizes only a second private #108 slice; it does not
close issue #108. It does not close #87, #103, #104, or #111, and it makes no
release, cross-machine, 1k/10k-scale, or performance-budget claim.

After this specification is approved, a detailed TDD implementation plan will
define exact file ownership, transition tests, commit checkpoints, validation,
and review gates. Implementation, push, pull-request creation, merge, issue
closure, and release remain separate maintainer gates.
