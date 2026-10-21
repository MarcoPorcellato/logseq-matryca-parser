---
type: AssuranceAcceptanceRecord
title: Bounded parser assurance acceptance package for issue 104
description: Evidence crosswalk, execution limits and explicit maintainer decisions for the delivered property-based assurance scope.
status: draft
classification: active
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-10-21
verified: 2026-10-21
stale_after: 2027-01-16
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---

# Issue #104: bounded parser assurance acceptance package

## Current acceptance status

The five-family matrix and earlier documentation were published in
[#259](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/259) and
merged as
[`4d96d248bf60c3d9ee24e5691cf93daf612680a9`](https://github.com/MarcoPorcellato/logseq-matryca-parser/commit/4d96d248bf60c3d9ee24e5691cf93daf612680a9).
Its [main CI](https://github.com/MarcoPorcellato/logseq-matryca-parser/actions/runs/39569903453)
completed successfully, including all six native operating-system/Python test
cells. That evidence qualifies the published baseline, not the local
completion candidate below.

### Local worker-diagnostic and refresh-path completion candidate

The subsequent acceptance audit identified a parent-runner diagnostic gap:
a process-start `OSError` could escape without a source-safe case receipt.
The local candidate catches it only at the subprocess launch boundary and
returns the existing nonpassing `runner_failure` classification, fixed
exception type `OSError`, case/family/seed/index, input length/digest and a
false semantic-roundtrip flag. Exception messages, filenames and source text
are not included. The timeout handler and existing limits are unchanged.
Cancellation/control-flow exceptions are not swallowed.

Focused fault-injection regressions exercise the actual launch boundary,
the fast-profile reporting assertion, and malformed profile/replay reporting.
The malformed caller stops after its first failed launch and retains its
exact source-safe recipe. The runner does not retry that launch; this does
not change the separate deterministic profile's existing minimization policy.

The [depth suite](../../tests/test_parser_deep_refresh.py) additionally covers
empty LOGBOOK initialization, LOGBOOK clock payload, and both `collapsed::`
boolean values at depths **1, 2, 3, 4, 8 and 32**. These parse-level assertions
check independent metadata values, prose separation, source ranges, outline
relations and repeat-parse UUIDs. They add no serializer round-trip promise
for system metadata. All five existing families and the six other original
deep regressions remain.

A bounded runtime caller observation mapped the following eleven distinct
`_refresh_node` call sites to actual cases at every declared depth:

| Immutable refresh caller | Witness family at each declared depth |
|---|---|
| Pending list finalization | List-property |
| Query payload | Query |
| Fenced-code payload | Fenced-code |
| LOGBOOK payload and clock metadata | LOGBOOK clock |
| LOGBOOK initialization | Empty LOGBOOK and LOGBOOK clock |
| Collapsed metadata | Collapsed true and false |
| List-property item update | List-property |
| List-property declaration/order | List-property |
| Scalar block property | Block-property |
| Soft-break continuation | Soft-break |
| Bottom-up metadata finalization | Existing and new selected families |

This is a finite caller/depth crosswalk, not every branch, arbitrary depth or
universal Logseq conformance. Targeted process-local metadata-loss mutations
were rejected by the new assertions; production parser files were not edited.

At the local-review snapshot on **2026-10-21**, the completion candidate was
local and uncommitted. Its final exact-diff
offline gates, independent review and any later publication/native-CI evidence
are separate records. This section does not assert those later gates passed
or close [#104](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/104).
The approved scalar-regression policy remains unchanged. No #111 benchmark,
cache, default-executor change, tag or release follows from this candidate.

## Preserved PR #259 candidate record

The following record retains its pre-publication source and status wording.
Its then-pending publication/native-CI statements are superseded only by the
published-baseline read-back above, not by the later local candidate.

Verified on **2026-10-21**. The source baseline is
[`a00a7ccb72accca696ab3fcd9ebb0a48023fcdf5`](https://github.com/MarcoPorcellato/logseq-matryca-parser/commit/a00a7ccb72accca696ab3fcd9ebb0a48023fcdf5),
which includes the published v1.11.1 source and the later Obsidian
documentation. The additional depth-matrix tests and this documentation remain
a local candidate, not a published or native-CI-qualified increment.

### Approved scalar-regression policy

The maintainer approved the interpretation on **2026-10-20**: the reviewed
permanent scalar-metadata regressions from
[#234](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/234) suffice
for that finding. No duplicate `compat/v1` fixture is required. Formal corpus
admission still requires the existing schemas, hashes, identity policy,
review and provenance whenever a case is actually admitted. A targeted
regression is not relabeled as a formal corpus fixture.

This resolves the scalar-promotion policy question in the dated baseline
below. It does not accept or close #104 or authorize unrelated work.

### Targeted refresh-depth completion

Review identified a narrower historical test domain than the August 6
“each refresh path” wording could suggest. The retained suite previously
covered soft-break refresh at depths 1, 2, 3, 4, 8 and 32, while the other
four families had depth-eight round trips. That was a coverage-evidence gap,
not a demonstrated parser failure.

The [focused depth tests](../../tests/test_parser_deep_refresh.py) now cover
each of these five named families at **1, 2, 3, 4, 8 and 32**:

| Family | Protected behavior |
|---|---|
| Soft-break | Leaf continuation and source end, repeat-parse UUID stability, parent/left relations |
| Block-property | Explicit scalar value survives semantic round trip and tree invariants |
| Fenced-code | Literal code payload survives semantic round trip and tree invariants |
| Query | Query payload survives while `Ghost` is not interpreted as a visible wikilink |
| List-property | Existing `[[AI]]` to `AI` normalization, tags and stable UUID policy survive round trip |

There are **30 selected family/depth combinations**: six existing soft-break
cases and 24 round-trip family cases. The complete focused file passed
**36 tests** locally, including its six unchanged sibling, deep-chain,
copy-budget and file-entrypoint cases. No depth was skipped or xfailed.
The semantic/identity policy, 1,024-node tests, existing limits and production
code are unchanged. This matrix does not prove every internal refresh branch,
all depths, all malformed layouts or universal Logseq semantics.

### Current evidence and remaining acceptance gates

The existing [nine-job main CI result](https://github.com/MarcoPorcellato/logseq-matryca-parser/actions/runs/39447719967)
qualifies exact baseline `a00a7ccb`, not the new local matrix or documentation.
The fenced-code correction and lexical-source re-admission from
[#256](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/256)
postdate the original baseline below; their changed source must not inherit
the older source-admission or runtime qualification by inference.

[#104](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/104)
remains open. Acceptance still requires the exact candidate's local gates and
independent review, required native CI, a stable published evidence link and
separate maintainer acceptance/issue-update authority. Local gate receipts
remain separate from hosted, package and release evidence. The approved
scalar policy need not be decided again.

Further randomized expansion remains parked. No #111 benchmark, #108
extraction, new corpus fixture, issue closure, tag or release follows from
this record.

## Historical baseline — 2026-10-18

The sections below retain their source, counts, policy proposal and
then-pending decisions as a dated baseline. In particular, their statements
that scalar policy awaits approval or that no further gap was identified do
not supersede the current status above. Historical qualification is not
qualification of this later candidate.

## Decision requested, not acceptance recorded

[Issue #104](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/104)
remains open at this verification date. This package maps its existing criteria
to delivered implementation and evidence. It does not change GitHub checkboxes,
close the issue, authorize more tests, or establish complete Logseq correctness.

The implementation baseline is
[`0f357160be3dd9c15ccd3600f112e60ae201b987`](https://github.com/MarcoPorcellato/logseq-matryca-parser/commit/0f357160be3dd9c15ccd3600f112e60ae201b987),
the S4e squash merge. Its existing
[main CI run](https://github.com/MarcoPorcellato/logseq-matryca-parser/actions/runs/39121335890)
completed successfully: quality, production dependency audit, package contract,
and all six native combinations of Ubuntu 24.04, macOS 15 and Windows 2025 with
Python 3.12/3.13. This is read-back evidence for that exact commit, not a new
CI run or qualification of a later documentation diff or release candidate.

The [current delivery table](COMPOSITE_MARKDOWN_ASSURANCE_2026-10-03.md#current-delivery-status-as-of-2026-10-18)
links the merged increments and preserves their separate historical checkpoints.
S4f and further randomized expansion are parked. Their absence is not an
additional acceptance condition unless a specific existing criterion is unproven.

## Disposition vocabulary

- **Demonstrated:** source and exact-baseline qualification support the stated
  requirement for the selected finite domains, not all possible input.
- **Not demonstrated:** the required behavior or evidence is absent; name the
  exact gap before proposing a new bounded slice.
- **Needs owner decision:** the remaining question is an acceptance-policy
  interpretation or approval, not a reason to invent another campaign.

## Acceptance crosswalk

The issue's previously checked foundation remains authoritative: versioned
project-authored corpus, projections and fixture-specific `IdentityPolicy`,
deterministic adversarial/replay/minimization machinery, deep/lifecycle/work-growth
checks and its dated v1.8.1 qualification. Those old counts and coverage describe
that release only. This package does not rewrite them as current results.

| Existing unchecked criterion | Disposition | Delivered evidence and boundary |
|---|---|---|
| Same bounded input/options produce the same semantic projection | Demonstrated | [S4e reuse test](../../tests/test_parser_reuse_properties.py), `test_generated_rich_pages_survive_mixed_page_parser_reuse`, compares checked repeated/shared and fresh-parser observations. It also verifies retained earlier results; no universal synthetic-UUID equality is inferred. |
| Valid generated cases preserve declared identity/relations through parse, serialize, parse | Demonstrated | [Valid-outline tests](../../tests/test_parser_properties.py), `test_generated_simple_properties_and_wikilinks_survive_semantic_roundtrip`, and [composite evaluation](../../tests/parser_assurance/composite_properties.py) reuse `semantic_roundtrip_v1` and the established identity policy. The original input is independently checked before relational round-trip comparison. |
| Malformed cases yield a classified result or typed parser error; raw exceptions are findings | Demonstrated | [Malformed recipes](../../tests/parser_assurance/malformed_properties.py), `is_accepted`/`main`, use the existing [adversarial runner](../../tests/parser_assurance/adversarial.py). The strict unresolved-reference family specifically requires `BlockReferenceError`; unexpected exceptions, invariant/runner failures and timeouts are not passing outcomes. |
| Applicable relations, UUID uniqueness, source ranges and task fields satisfy invariants | Demonstrated | [Shared tree invariants](../../tests/parser_assurance/invariants.py) cover UUID uniqueness, parent/left/path/outline relations. `assert_matches_model` in the [composite helper](../../tests/parser_assurance/composite_properties.py) separately checks modeled content, source spans, tasks/priorities, metadata, dates and visible references. |
| Failing examples have deterministic, source-safe replay metadata | Demonstrated within the declared replay protocols | [Malformed replay tests](../../tests/test_parser_malformed_properties.py) verify exact recipe reconstruction, parser options, first-failure stop and source-free output. [Composite schema-3 replay](../../tests/parser_assurance/composite_properties.py) requires matching source/runtime context and digests. The simpler Hypothesis tests request version-coupled reproduction blobs, not portable schema-3 receipts; replay uses the same implementation and locked Hypothesis version. |
| Strategies cap bytes, outline width/depth, properties, delimiter runs and examples/profile | Demonstrated | Explicit independent bounds are summarized below. They belong to their respective generators, not a new universal input limit or a whole-suite wall-clock guarantee. |
| Expensive generation uses a timeboxed job or explicit profile, not an unbounded default gate | Demonstrated | Malformed `fast`/`broad` and composite `smoke`/`broad` paths have explicit finite selection and child caps. CI's native test jobs have a 20-minute job timeout. Ordinary bounded in-process tests remain a separate, deliberately accepted lane without a per-call hard timeout. |
| Promoted permanent-corpus regressions are minimal, synthetic, reviewed and provenance-safe | Needs owner decision | The strict corpus admission rules remain unchanged. The serializer finding has permanent targeted regressions, but no new entry was admitted to `compat/v1`; see the explicit interpretation below. |
| Focused Hypothesis and deterministic replay tests pass | Demonstrated at the baseline | The exact-baseline native suite includes [valid-outline](../../tests/test_parser_properties.py), [malformed/replay](../../tests/test_parser_malformed_properties.py), composite, shielding, mixed/deep, EOF and reuse tests. This is not a claim that a separately selected broad campaign ran in each CI cell. |
| Existing compatibility, adversarial, deep-refresh, lifecycle and work-growth suites remain green | Demonstrated at the baseline | The same exact-baseline native jobs run the complete `tests/` suite. The original [corpus](../../tests/test_compat_corpus.py) and deterministic assets remain present; no threshold or semantic projection was replaced to accept a generated failure. |
| `make all` passes on the exact implementation commit | Demonstrated for the qualified implementation tree | The prior committed S4e feature and squash merge have the identical source tree `5059d323a66eb54c26b498ebd559316c570a70ad`; full local quality passed on that tree. Exact-main hosted quality and native suite jobs also succeeded. New documentation changes require their own local gate and review; they are not covered retrospectively by the earlier CI. |

## Explicit generator and execution limits

| Family | Input and selection bounds | What the bound does not mean |
|---|---|---|
| Simple valid outlines | Depth at most 5, at most 16 nodes, child width at most 3, UTF-8 source at most 16 KiB; each generated test requests 40 Hypothesis examples | Requested examples are not a telemetry count of distinct inputs or a hard cap on shrinking/replay calls; no per-call timeout is installed |
| Malformed recipes | Five finite families; depth 1–4, width 1–3, delimiter run 1–16, property count 0–4, source at most 16 KiB; `fast` selects at most 20 recipes and `broad` at most 60 | Malformed classification is robustness evidence, not an independent semantic oracle; collection completes before parser children |
| Composite schema 3 | At most 32 blocks, depth 8 and 16 KiB/source; `smoke` child cap 4, `broad` cap 120, per-child timeout at most 3 seconds | A cap is not an observed count or a whole-suite resource guarantee; source/runtime admission and first-failure behavior still apply |
| Later S4b–S4e slices | Each owns its separately documented recipe filters, admissions and counters in the [delivery record](COMPOSITE_MARKDOWN_ASSURANCE_2026-10-03.md); S4e permits at most six rich sequences, 30 direct entries and twelve parser objects | Bounds cannot be transferred between lanes. S4d/S4e use ordinary in-process calls, not child containment or native per-recipe telemetry |

No extra profile, broad campaign, new fixture or generated corpus is executed
by preparing this acceptance package. Ordinary local verification may rerun the
existing bounded tests; that is not authority for an opt-in campaign.

## Regression-promotion interpretation requiring owner acceptance

The generated composite investigation did expose a real serializer problem.
It is not accurate to say that no regression needed retaining. The bounded fix
merged in [PR #234](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/234),
with `test_scalar_metadata_survives_multiline_roundtrip` and exclusion/legacy-output
cases in [test_logseq_markdown.py](../../tests/test_logseq_markdown.py). The
project-authored fixture covers the relevant metadata/prose ordering and explicit
block identity under LF/CRLF and tab-size variants. It is a permanent targeted
regression, not a new formal `compat/v1` fixture or a proof of global minimality.

The [corpus manifest](../../tests/fixtures/compat/v1/manifest.json) was not
expanded by these increments. Its [loader](../../tests/parser_assurance/corpus.py)
still requires versioned fixture/snapshot schemas, declared identity policy,
content hashes and `project-authored`/`Apache-2.0` provenance. No third-party
vault or official corpus document was silently admitted to this synthetic corpus.

**Recommended interpretation:** the issue's promotion clause is conditional:
when a case is admitted to the formal corpus, those admission and review rules
apply. It does not require every synthetic bug regression to become another
manifest fixture when a reviewed permanent targeted regression already exists.
This interpretation is proposed, not silently accepted here.

The owner may instead require a dedicated formal corpus entry for the scalar
case before closing #104. That would be one precise fixture/snapshot acceptance
gap, requiring a separate scoped change—not a new randomized campaign, parser
change or expansion into concurrency, filesystems or every Markdown construct.

## Acceptance recommendation and remaining gates

The delivered scope is a **candidate for acceptance after the owner resolves
the promotion interpretation above**. Do not automatically check off the remote
issue or describe #104 as complete from this document. No additional unmet
implementation criterion is asserted by this source/evidence crosswalk; the
independent documentation/acceptance review remains a required gate.

Before an acceptance or publication decision:

1. Verify this baseline and the exact proposed documentation diff; run the local
   documentation, vendor and full quality gates and retain their actual result.
2. Review the acceptance crosswalk independently; do not treat the tests' own
   self-description, a previous review or source inspection as a new runtime pass.
3. Record the owner's promotion-policy choice and any precisely identified gap.
4. Obtain separate authority for GitHub issue/milestone updates. Only then may
   the accepted #104 semantic prerequisite permit separately approved #111 work.

An open #104 does not by itself block an unrelated qualified patch release.
Neither acceptance nor a green local gate authorizes #111 benchmarks, #108 hub
extraction, publication, a tag or package upload. The separate #109 executable
documentation, ADR and private-federation obligations also remain open.

## Claim limits

Finite grammar/model coverage, ordinary test passing and the
[313-document structural corpus result](OFFICIAL_LOGSEQ_MARKDOWN_COMPATIBILITY_2026-10-10.md)
do not prove full Logseq Markdown semantics or correctness for arbitrary vaults.
No complete Org/Logseq DB support, graph cross-process isolation, performance
budget, stable API promotion or downstream Plumber/Trama qualification is added.
Synthetic UUID behavior follows the established fixture policy; byte-for-byte
serializer equality remains a non-goal. Historical failed or incomplete attempts
retain their original status; later successful evidence does not repair them.

