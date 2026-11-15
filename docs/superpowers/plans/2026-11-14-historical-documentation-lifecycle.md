# Historical Documentation Lifecycle Implementation Plan

> **For agentic workers:** After separate maintainer approval, use the inline executing-plans workflow. The primary activity owns edits and validation; an independent GPT-6 Astra Medium reviewer checks the complete documentation patch. Checkboxes below describe future work, not authorization to execute it.

**Goal:** Make historical plans discoverable and safe to interpret without rewriting their original dates, approvals, measurements, failures, or unfinished checklists.

**Architecture:** Keep every existing path and historical body. Add one navigation index, small dated lifecycle notices, and narrowly enumerated metadata corrections. Link current contracts rather than copy volatile implementation or GitHub status into old plans.

**Tech Stack:** Existing Markdown/YAML, Git evidence, and the repository's documentation and quality gates. No new dependency, checker, profile, workflow, parser change, or generated content.

**Spec:** [Documentation classes](../../DOCUMENTATION_SYSTEM.md#3-documentation-surfaces), [freshness policy](../../DOCUMENTATION_SYSTEM.md#5-freshness-policy), [metadata semantics](../../DOCUMENTATION_SYSTEM.md#4-metadata-contract), and the bounded requirements below. This addresses the historical-lifecycle work deferred from [PR #276](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/276).

**Status:** Proposed implementation plan; planning and independent review only are authorized. Implementation and publication require separate maintainer approval.

## Global Constraints

- Preserve filenames, paths, existing heading anchors, original checkboxes, commands, source hashes, review verdicts, test counts, failure evidence, and decision dates.
- Existing historical `last_verified`, `verified`, `stale_after`, and `base_commit` values remain unchanged. A new lifecycle-review date never means that historical tests or technical claims were requalified.
- A historical document is not execution authority. Old approvals, commands, active-goal wording, and PR instructions do not authorize their replay.
- Do not infer completion of an exact plan from issue closure, presence of similar tests, a feature summary, or release of a related capability.
- Keep lifecycle `status` separate from original proposal/approval decisions. Use only `draft`, `stable`, or `deprecated` for the lifecycle field, and preserve original decision values explicitly in the new notice.
- No moves, deletions, renaming, bulk formatting, checker/allowlist changes, official OKF conformance claims, or new semantic supersession edges without evidence.
- No parser, tests, examples, scripts, dependencies, release/version metadata, GitHub issue/project, Beads, Plumber, advisory, benchmark, or runtime-probe changes. The sole release-document exception proposed for future approval is one documentation-only `Unreleased` changelog entry; published release entries remain unchanged.
- Preserve the existing dirty primary checkout and every branch. Use the selected managed checkout; do not create another worktree merely for this documentation patch.
- Do not install tools or refresh unrelated expired documents to make a gate green. Report a blocker and request the smallest separate authorization.
- All persisted content is normal, clear English. Public material excludes private paths, raw logs, credentials, environment values, and local audit-tool names.

## Review Focus

1. Archive notices must not turn an unproven historical checklist into a completed one. Task 2 validates unchanged checkboxes and explicit unknowns.
2. Metadata corrections must preserve approval meaning and original evidence dates. Tasks 1 and 2 require reversible, field-limited changes.
3. A current-reference link is not automatically a formal replacement. Tasks 2 and 3 distinguish current navigation from complete supersession.
4. Old local or failed-hosted evidence must not become current cross-platform qualification. Task 2 preserves qualification layers and failure records.
5. Navigation must cover every existing planning record without hiding unresolved proposals or enabling old instructions. Tasks 1 and 3 verify exact inventory coverage and authority warnings.

## 1. Verified starting point and approaches

On 2026-11-14, GitHub `main` was verified at
`4c5fa933f008751bbd71294df5e403ff369b3876`, the squash merge of #276.
The selected managed checkout is still on the preserved documentation branch
at `596c791f3548457ab5a7b8154e87de0c55c4fc21`; both commits have tree
`d329307afc27527b6fd095ce79e9977cfee7332a`.
Planning does not require switching branches or updating the dirty primary checkout.
Rebind these facts before future implementation; this is a dated observation.

The existing planning collection contains **26 tracked records: 13 plans,
8 specifications, and 5 receipts**. This new plan is an additional record,
not one of those 26. The earlier audit reviewed 56 historical/navigation
surfaces; this is a targeted lifecycle repair, not a new technical audit of all 56.

Three approaches were considered:

1. **Move old files into an archive directory:** rejected; this creates unnecessary path and anchor migrations.
2. **Bulk-rewrite old status, dates, and checklists:** rejected; this obscures evidence and creates false completion/freshness claims.
3. **Additive lifecycle notices plus one index:** recommended for maintainer approval. This is sufficient under the existing documentation policy and preserves recoverable history.

## 2. Exact proposed file boundary

The future patch has **20 existing files eligible for modification**, one new
index, and this already-created plan. The plan may receive progress/status
notes after execution, but is not a historical input. No other path is eligible
without a scope decision. This proposal includes a narrowly scoped
`CHANGELOG.md` entry because the documentation contribution policy requires it.
Before implementation, obtain approval explicitly covering that entry along
with this plan; if it is excluded, stop and request a policy exception rather
than silently omit or add it. No changelog change is authorized now.

### Lifecycle notices: 12 existing files

Paths in this table are relative to `docs/`.

| Existing paths | Exact disposition and current reference |
|---|---|
| `superpowers/plans/2026-08-20-parser-lexical-state.md`; `superpowers/specs/2026-08-20-parser-lexical-state-design.md` | Historical extraction proposal/plan. The [current backlog](../../quality/CLEAN_ARCH_BACKLOG.md) records delivered lexical phases; residual #108 reducer/enrichment remains separate. Do not mark every old step complete. |
| `superpowers/plans/2026-08-21-graph-mutation-coherence.md`; `superpowers/specs/2026-08-21-graph-mutation-coherence-design.md` | Historical #103 plan/design. The [roadmap](../../ROADMAP_2026-2027.md#evidence-gated-improvement-decisions) records #180 delivery in v1.8.1; preserve unchecked publication/project steps and avoid claiming exact-step execution. |
| `superpowers/specs/2026-08-24-meaningful-test-coverage-design.md` | Archive the dated campaign design, not the general goal of better tests. Link [bounded Tranche A evidence](2026-08-24-local-assurance-coverage.md#completion-receipt); explicitly retain the unmet wider 95% criterion. Do not describe the whole campaign as complete or canceled. |
| `superpowers/specs/2026-09-27-llamaindex-companion-separation-design.md` | Historical separation design. Link its [dated execution checkpoint](2026-09-27-llamaindex-companion-separation.md#current-status-refresh--2026-10-02) and the [migration record](../../internal/LLAMAINDEX_COMPANION_MIGRATION_CHECKPOINT_2026-09-27.md). Do not infer current companion distribution availability or resolution of historical dependency advisories. |
| `superpowers/specs/2026-09-29-logseq-org-parser-design.md` | Retain as active supporting design, with original approval preserved. Add a dated scope notice: bounded D2 delivered, D3 deferred; [experimental status](../../internal/LOGSEQ_ORG_PARSER_EXPERIMENTAL_STATUS.md) and the [post-merge plan](2026-09-29-logseq-org-parser.md#live-checkpoint--2026-10-01--post-merge) provide current scope. No Org extension or requalification. |
| `superpowers/plans/2026-10-03-scalar-metadata-serialization.md` | Historical local implementation checkpoint. Preserve its 2026-11-03 freshness date and local-only completion evidence. Publication of this exact correction is not established by this lifecycle review. Link the [current composite record](../../quality/COMPOSITE_MARKDOWN_ASSURANCE_2026-10-03.md#current-delivery-and-release-status); do not upgrade the old checkpoint to shipped. |
| `superpowers/plans/2026-09-26-hypothesis-parser-properties.md`; `superpowers/plans/2026-10-03-hypothesis-malformed-markdown.md` | Historical #104 planning/execution records. Link [bounded acceptance](../../quality/PARSER_ASSURANCE_ACCEPTANCE_2026-10-18.md); old issue-open/draft statements describe their original checkpoints. Exact checklist completion and the old PR statement are not reverified here; preserve the Windows failure evidence. |
| `internal/M5_LOCAL_GRAPH_ASSURANCE_REVIEW_HANDOFF_2026-08-18.md` | Historical pre-publication handoff, not a live goal or authorization. Link [local assurance](../../reference/LOCAL_GRAPH_ASSURANCE.md) and #104 acceptance as current navigation, not an assertion that they fully replace every M5 substep. |
| `quality/GRAPH_PROPERTY_ASSURANCE_2026-10-03.md` | Adjacent historical assurance checkpoint included because its expired active label presents the same lifecycle ambiguity. Preserve the 2026-11-03 freshness date, local-only qualification, and original baseline CI distinction. Link bounded #104 acceptance/current composite delivery without asserting a new test result. |

### Navigation and chronology: 8 existing files

| Path | Allowed change only |
|---|---|
| `docs/README.md` | Link the new lifecycle index; label planning history separately from active work. Retain direct Org design/plan links and their D2/D3 limits. Link this proposed plan directly while it is active; after completion label it an executed lifecycle record, without erasing its original proposal. |
| `docs/index.md` | Add one discovery link to the lifecycle index; do not promote it to a canonical technical contract or expand the maintained profile. |
| `docs/quality/README.md` | Label the v1.6 roadmap historical and the graph-construction report a dated historical checkpoint; retain links. |
| `docs/design-docs/README.md` | Recommend current compatibility evidence and tests first. Keep mldoc material explicitly historical research, not current official conformance evidence. |
| `docs/decisions/index.md` | Qualify only the official-OKF row: measured findings are dated evidence; the current ADR documents the source-profile exception and keeps conformance deferred. Preserve ADR decision status and all other issue-linked `Proposed` entries. |
| `.github/ISSUE_TEMPLATE/config.yml` | Relabel the existing v1.6 contact link as historical. Keep its URL and all routing behavior unchanged. |
| `docs/log.md` | Add one actual-date entry explaining lifecycle-only scope, preservation checks, and limitations; do not rewrite earlier log entries. |
| `CHANGELOG.md` | After explicit scope approval, add only an `Unreleased` Documentation entry about lifecycle navigation and preservation. Preserve every released section byte-for-byte; no version, release date, tag, or publication claim. |

**Create:** `docs/superpowers/README.md`, a small supporting navigation page,
without claiming maintained-profile admission or adding decorative metadata.

### Explicit no-edit dispositions

- The five v1.8.2 receipts and already archived completion spec/plan retain identical bytes, including historical `status: completed` as part of that archived record. Do not normalize embedded examples or historical metadata globally.
- Other already labeled execution plans, July/August studies, and executed `docs/roadmaps/` records remain unchanged.
- `docs/internal/POST_V1_8_1_BACKLOG_EXECUTION_2026-08-25.md` and `docs/superpowers/specs/2026-09-24-open-pr-quality-gates.md` get index-only dispositions: dated programme/proposal, exact completion unverified. Do not relaunch their gates.
- The first Hypothesis plan also retains explicit exact-plan uncertainty despite issue-level bounded acceptance.
- `docs/error_log.md` already received its historical banner in #276; no duplicate correction.
- No changes to documentation policy, `docs/maintained.toml`, ADR contents, released changelog sections, release highlights, or current roadmap scope.

## 3. Notice and metadata contract

For each of the 12 lifecycle files, insert one uniquely delimited block after
the original first H1, before its original first section:

```markdown
<!-- lifecycle-note:start -->
> **Lifecycle review — YYYY-MM-DD (UTC):** [historical checkpoint / active supporting design].
> [What the old document records, what is known, and what remains unverified.]
> Current reference: [relative link]. This review does not rerun historical
> qualification or authorize replay of the original instructions.
<!-- lifecycle-note:end -->
```

Use the actual execution date, never backdate a later edit. Preserve the
original H1 and its anchor. New notices use paragraphs, not headings, avoiding
duplicate-heading anchor shifts. For frontmatter-bearing records, include the
original `status` and `classification` values verbatim inside the notice.

Only these seven files may change existing frontmatter values:

| Record | Original `status` / `classification` | Proposed lifecycle values |
|---|---|---|
| Lexical-state spec | `proposed` / `active` | `deprecated` / `historical` |
| Graph-coherence spec | `approved` / `active` | `deprecated` / `historical` |
| Meaningful-coverage spec | `approved` / `active` | `deprecated` / `historical` |
| Companion-separation spec | `proposed` / `active` | `deprecated` / `historical` |
| Scalar-serialization plan | `stable` / `active` | `deprecated` / `historical` |
| Graph-property assurance record | `draft` / `active` | `deprecated` / `historical` |
| Org design | `approved` / `active` | `stable` / `active` |

Here `deprecated` retires a document as a current execution contract; it does
not deprecate the implemented capability, cancel an unmet proposal, or revoke a
historical maintainer decision. `stable` for Org means accepted supporting
documentation, not a stable Org API. State those distinctions in the notices.
Do not alter date fields or add speculative `superseded_by` edges.

## 4. Future implementation tasks — not started

### Task 1: Freeze preservation evidence and exact inventory

**Files:** No tracked input changes. Create a private execution manifest and
candidate-diff record outside distributable documentation.

**Interfaces:** Consume the selected source commit/tree and existing tracked
files; produce a path-sorted manifest of original blob hashes/bytes, parsed
frontmatter, ordered checkbox lines, heading anchors, and the exact edit allowlist.

- [ ] Confirm implementation authorization explicitly includes the proposed `Unreleased` changelog entry. Reverify GitHub `main`, managed checkout HEAD/tree/status, and primary preservation evidence. If unrelated drift appears, stop and select the correct source explicitly; do not switch or reset automatically.
- [ ] Enumerate every tracked planning record. Require all 26 baseline paths accounted for; inventory this plan separately. New upstream paths require an explicit disposition, not silent omission or editing.
- [ ] Freeze original bytes for the 20 eligible existing files and all no-edit records, including the original entire changelog. Keep new plan/index outputs out of baseline preservation comparisons.
- [ ] Confirm each proposed original metadata pair against the selected source. A mismatch stops that correction; do not guess an equivalent replacement.

**Acceptance:** A complete pre-edit manifest exists; no existing tracked file
has changed. This manifest is evidence for the future patch, not a new audit
of all technical claims.

### Task 2: Add the 12 notices and seven field-limited corrections

**Files:** Only the 12 lifecycle files in section 2.

**Interfaces:** Consume Task 1 originals and section 3; produce additive notices
and a reversible mapping of the seven permitted frontmatter replacements.

- [ ] Add each notice using the per-file disposition, actual review date, original metadata where present, and current-reference links.
- [ ] Apply only the seven declared status/classification pairs; leave all original dates, base/source hashes, supersession fields, and unrelated frontmatter unchanged.
- [ ] Verify reconstruction: remove exactly one delimited notice per file and restore only its declared metadata pair. The result must be byte-identical to the Task 1 original. Do not normalize whitespace or line endings during this comparison.
- [ ] Verify ordered original checkbox lines and heading anchors remain identical. Explicitly check failed Windows evidence, local-only scalar/graph evidence, unmet 95% scope, deferred Org D3, and the M5 no-replay boundary.

**Acceptance:** All 12 original documents reconstruct exactly; no old task is
marked complete, no new hosted/technical result is claimed, and all required
unknowns remain visible.

### Task 3: Build one lifecycle index and repair navigation

**Files:** Create `docs/superpowers/README.md`; edit only the eight navigation
and chronology files in section 2.

**Interfaces:** Consume Task 1 inventory and Task 2 dispositions; produce one
exhaustive discovery table and current-reference routes, not a second technical
source of truth.

- [ ] Index each of the 26 baseline planning records exactly once, plus this plan separately. Use columns: record link, record kind, lifecycle/disposition, evidence limit, and current reference. Split active supporting records from historical records and unverified completion; paired records still need individual path coverage.
- [ ] Include M5, the post-v1.8.1 programme, and graph-property assurance as separately identified adjacent records, not as extra planning receipts. State that an unresolved historical proposal is neither active execution authority nor proof of cancellation.
- [ ] Retain Org as active supporting design with completed bounded D2/deferred D3. Other archived or unresolved records retain their explicit limitations. The index must not say the entire companion is published, all #104 plan steps passed, or the whole 95% campaign finished.
- [ ] Make the exact section-2 navigation edits, retaining URLs and original technical authorities. Do not convert issue `Proposed` labels into completed ADRs.
- [ ] Add the documentation-log entry with actual edit date. For maintained navigation pages, preserve existing date fields if still valid; if any is expired at execution, stop for a separately scoped substantive refresh instead of extending dates here.
- [ ] Add the approved `Unreleased` Documentation entry. Remove that exact addition in the preservation comparison and require the complete original changelog to reconstruct byte-for-byte. No earlier section or date may change.

**Acceptance:** Every baseline planning path is discoverable, no broken current
route is introduced, and the index clearly distinguishes a dated record, a
current contract, and the authority needed to resume work.

### Task 4: Validate the complete documentation patch and review

**Files:** No additional tracked files. Keep validation logs and preservation
receipts private; this plan may gain a dated progress note without altering
its original proposal or baseline.

**Interfaces:** Consume the whole patch, including untracked proposed files;
produce exact candidate bindings, preservation results, gate outcomes, and an
independent Astra Medium verdict.

- [ ] Verify the full working delta, not only unstaged changes or a three-dot branch diff. Require exactly the declared paths; separately inventory pre-existing ignored/untracked material without adding or deleting it.
- [ ] Require byte-identical no-edit records, released changelog sections, and unchanged production/tests/scripts/dependencies/workflows/release metadata. Recheck primary-checkout preservation. No receipts may be edited.
- [ ] Validate every newly added repository-local target and heading anchor, including the new index and all notices. Existing checker coverage is limited to the maintained profile; inspect actual navigation links outside it without treating fenced/inline syntax examples as broken links. Retain original heading anchors.
- [ ] Verify the selected existing environment and required tools are available; stop if any prerequisite is missing. Run `rtk proxy env UV_OFFLINE=1 UV_NO_SYNC=1 UV_LOCKED=1 make all`, `rtk proxy make vendor-name-check`, and `rtk proxy git diff --check` in that already qualified environment. The locally verified uv controls disable uv network access and environment synchronization and prevent lock updates; they do not establish network isolation for test subprocesses. Do not change the Makefile. Check new untracked Markdown explicitly as well; ordinary `git diff --check` alone does not cover it. Do not install or repair environments without authorization.
- [ ] Run the maintained documentation checker for the actual UTC execution date and two days later, using `rtk proxy uv run --offline --locked --no-sync python scripts/check_documentation.py --root . --profile docs/maintained.toml --as-of-date YYYY-MM-DD` with each exact date. Record unrelated expiry failures separately; do not weaken policy or expand scope.
- [ ] Ask an independent general-purpose `gpt-6-astra` reviewer at `medium` to inspect the exact complete patch, reconstruction proofs, inventory coverage, links, authority boundaries, and gate evidence. Require `PASS` or `PASS_WITH_NOTES` with no unresolved blockers. Reuse that reviewer for scoped corrections; do not substitute a model silently.
- [ ] Save a dated checkpoint with exact source/diff bindings, changed path list, gate results, original-evidence preservation, review verdict, residual unknowns, and next authorization needed. Stop before commit, push, PR, tag, or release.

**Acceptance:** Local gates pass without policy changes, archival bytes are
recoverable exactly, all known uncertainties remain explicit, and Astra has no
unresolved blocker. No CI, runtime compatibility, release qualification, or
external publication is inferred from this documentation-only gate.

## 5. Completion and next authorization

The implementation is complete only when all four task gates pass and the
maintainer can navigate active and historical records without confusing old
instructions with current authority. A later publication request must specify
commit, branch, push, and PR scope; merge, tag, advisory, and release remain
separate decisions. No implementation or publication is performed by creating
or reviewing this plan.

## Local execution record — 2026-11-15 (UTC)

The maintainer subsequently approved local implementation of this plan,
including its documentation-only `Unreleased` entry, offline quality gates
and independent Astra Medium review. The original proposal and its unchecked
planning steps above are retained, not backdated or treated as original
execution receipts.

The local documentation patch adds the lifecycle index, twelve dated notices,
seven field-limited lifecycle corrections and eight navigation/chronology
updates. Original bytes were frozen before editing. Removing each notice and
restoring its declared metadata values reconstructs all twelve original
records exactly. Original evidence dates, checklists, heading anchors and
archived receipts remain unchanged; uncertain completion remains uncertain.

Validation results, exact candidate bindings and independent-review evidence
are retained in the local execution checkpoint. This note records authority
and local edits, not a substitute for those gates or a publication receipt.
No commit, push, PR, merge, tag, advisory or release is authorized by this work.
