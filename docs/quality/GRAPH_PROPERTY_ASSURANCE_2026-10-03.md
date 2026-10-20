---
type: ImplementationRecord
title: Bounded graph construction property assurance
description: Reviewed scope, evidence, and limits for the synthetic graph-routing increment of issue 104.
status: draft
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

# Bounded graph construction property assurance

## Delivery status and authority

This is an implementation record, not a new parser design or public API
contract. The maintainer approved the bounded, test-only design on
2026-10-03. Implementation and local qualification are complete for this
bounded increment. At the local qualification checkpoint, the changes were
uncommitted and hosted qualification for this diff had not run.
Commit, push, pull-request creation, issue closure, and release publication
are not authorized by that approval.

The source baseline is `3070a8f1d788a295849ad34f263f63ef83b464ab`, the
squash merge of [PR #232](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/232).
The baseline's hosted run
[37096526012](https://github.com/MarcoPorcellato/logseq-matryca-parser/actions/runs/37096526012)
passed its quality, package, dependency-audit, and six native-platform test
jobs. That result does not qualify this new, uncommitted increment.

This work contributes to
[#104](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/104).
GitHub remains the canonical backlog; no Beads or GitHub issue state is
changed by this record.

## Approved scope

One generated property exercises three existing public graph constructors:
disk loading, a reversed sequence of `SnapshotPage` inputs, and a reordered
snapshot mapping. All constructions use the same normalized temporary graph
root. Production code, dependencies, workflows, and the Org reader remain
outside the change.

The independent literal model contains two to four Markdown pages, each with
a unique ASCII alias and one to three flat root blocks. This depth-zero
renderer stays within the approved maximum depth of one; it does not claim
generated nested-outline coverage. Ring links use canonical titles or aliases
and may repeat within one source block to exercise source-node deduplication.
Each rendered page is capped at
1 KiB, and aggregate Markdown is capped at 4 KiB. Arbitrary paths, explicit
UUIDs, collisions, journals, namespaces, symlinks, writer behavior, and
concurrency are excluded.

Every generated example owns a fresh temporary vault. The test does not
suppress Hypothesis fixture health checks. Its settings follow the existing
property suite: forty target examples, deterministic generation, no database,
no per-example deadline, and replay blobs. The example target and finite input
bounds do not establish a hard wall-clock limit.

## Independent oracle and sensitivity

The literal model, not the graph implementation, supplies expected canonical
page order, alias ownership, and backlink source slots. A source slot is a
pair of page title and outline path; outline paths alone are not globally
unique. Returned backlinks must be the actual attached graph nodes, checked
by object identity. The oracle rejects missing, extra, duplicated, or
misrouted source slots. Backlinks count unique source nodes, not link
occurrences.

Only after these independent assertions pass are per-page semantic
projections compared between constructions. The existing
`semantic_roundtrip_v1` profile is reused with recomputed synthetic UUIDs,
absent source UUIDs, and outline-path relations. This is construction parity,
not a new serialization round-trip test. The constructors share parser and
index-building code, so agreement alone is insufficient evidence.

Negative controls replace an alias owner or backlink source with another
legitimate graph object and require the same oracle to reject the result.
Selected replay metadata contains only the finite recipe, schema, source
digest, bounds, and revision evidence. The source digest binds sorted logical
paths and length-delimited UTF-8 page bytes. Revision evidence consists of the
explicit recipe baseline commit and a runtime SHA-256 of the test file, not a
claim that an uncommitted implementation is present in that baseline commit.
Metadata is attached through Hypothesis failure notes; it does not contain
rendered Markdown or temporary paths. The finite recipe can be reconstructed
with the test-local metadata loader. This does not promise privacy for all
pytest tracebacks or establish automatic verification of a different checkout.

## Review and remaining limits

Luna's source study identified the shared-constructor and fixture-lifecycle
risks. The read-only GPT-6.1 Sol design review returned `PASS_WITH_NOTES`.
Its correctness notes on source-node deduplication, page-qualified slots,
object identity, and construction-parity wording are incorporated above.
Implementation re-review and the final full local gate have passed.

### Qualification ledger

- The first draft added one generated property and five corruption controls.
  Its six focused tests, lint, and typing checks passed. A full local gate
  passed with 1,076 tests, five platform skips, and 89.79% coverage in
  226.05 seconds. This is pre-review draft evidence, not final qualification.
- The GPT-6.1 Sol implementation review returned `BLOCKED`: selected replay
  metadata was absent; independent outline-slot and block-count validation
  was incomplete; and corruption controls had not established a passing
  baseline. The review also requested explicit normalization of the fresh
  graph root. These findings required a test-only repair wave before final
  review and qualification.
- The repair wave added finite metadata reconstruction and source-digest
  validation, independent root-count and ordered-slot checks, passing
  baselines before each corruption control, a duplicate-outline-slot control,
  and explicit normalization of each fresh root. Eleven focused tests, lint,
  and typing passed. Temporarily disabling the test-only alias-identity
  assertion made its corruption control fail with `DID NOT RAISE`; the
  assertion was restored, and all eleven focused tests passed again.
  The repaired test file's SHA-256 is
  `3009ab93ec2d3a4e77fd3c615bda10d3f2d2e9f8fee24f3d147e801b96c2c86a`.
  Scoped re-review returned `PASS`, with all previous findings addressed and
  no new Important or Critical findings. The reviewer inspected the code and documentation read-only;
  testing evidence is from the local executor, not reviewer test execution.
- The repaired full local gate passed with 1,081 tests, five native-platform
  skips, and 89.79% coverage in 232.79 seconds on macOS with Python 3.12.13.
  Lint, typing, vendor-name policy, and maintained-document checks passed.
  The repaired test-file digest was unchanged before and after execution.
  The new file contributes eleven collected tests: one generated property,
  six graph-oracle controls, and four replay-metadata tests. The full suite
  also covers the existing compatibility, adversarial, deep-refresh,
  lifecycle, work-growth, graph, and writer regressions; no coverage floor
  was lowered.
- The first draft incorrectly treated the private backlink registry as a
  deduplicated result. A focused failure exposed that the registry retains
  repeated link occurrences while the public lookup deduplicates source
  nodes. The assertion was corrected to use public observations, without
  changing production behavior. This is a test-assumption correction, not
  evidence of a parser bug.

A current-source static import audit found the existing CLI registration
cycle between `kinetic` and `kinetic_commands`. An older audit index reports
zero cycles but does not describe the current checkout; it is navigation
evidence only. No current zero-cycle claim is made, and repairing that
unchanged cycle is outside this test-only increment.

Broader generated filesystem attacks, graph mutations, concurrency,
serialization coverage, and performance decisions remain separate bounded
work. This increment does not complete issue #104 or prove exhaustive Logseq
compatibility, filesystem security, or hosted platform qualification.

## Continuation boundary

The maintainer separately authorized a feature-branch commit, push, and draft
pull request toward `main` on 2026-10-03, solely to collect hosted
qualification. This authorization does not include merge, tag, release,
package publication, or tracker changes. No new worktree is needed.

Keep the four intended test and documentation files together. The recipe
baseline and test-file digest above identify the local implementation
evidence. Reverify the source baseline, diff, and gates before committing or
publishing. Hosted results must be bound to the exact pull-request head;
the baseline's successful run and local gates cannot substitute for them.
