# Post-M9 Documentation Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconcile the maintained parser-assurance documentation with the merged PR #176 receipt while keeping the unfinished #108 epic historically accurate. Issue #108 is currently CLOSED with reason `completed`; reactivation is planned after the source PR is reviewable.

**Architecture:** Update only current maintained status and chronology surfaces. Preserve the accepted M9 design and implementation plan as historical records of the pre-publication boundary. Reopen #108 as a controller-owned GitHub action after the source documentation is reviewable; do not imply that reducer, semantic-enrichment, benchmark, or release gates are complete.

**Tech Stack:** English Markdown, Matryca-v1 maintained-document metadata, the repository documentation validator, Git, and GitHub issue state.

**Spec:** `docs/LSDOC_REFERENCE_STUDY_AND_EXECUTION_PLAN_2026-08-16.md`

## Global Constraints

- Source files and committed documentation in this repository remain authoritative; derived Matryca Knowledge projections are not editing origins.
- Maintained Matryca-v1 entry points retain `type`, `title`, `description`, `status`, and fresh `last_verified` metadata with valid local links.
- Preserve historical pre-publication claims in `docs/superpowers/specs/2026-08-20-parser-lexical-state-design.md`, `docs/superpowers/plans/2026-08-20-parser-lexical-state.md`, and `docs/quality/ISSUE_RECONCILIATION_2026-08-06.md`.
- Record PR, issue, checks, merge, release, and performance claims only from exact live receipts.
- Keep #87, #103, #104, and #111 ownership unchanged.
- Use neutral `audit code` terminology in repository artifacts.
- Prefix every shell command with `rtk`.

---

### Task 1: Reconcile current maintained status

**Files:**
- Modify: `docs/LSDOC_REFERENCE_STUDY_AND_EXECUTION_PLAN_2026-08-16.md`
- Modify: `docs/goals/LSDOC_PARSER_ASSURANCE_GOAL.md`
- Modify: `docs/log.md`

**Interfaces:**
- Consumes: PR #176 head `a8558aca305c43bbadb66b884b9def945f8af36c`, squash merge `2a3679e176772bfcc57ed49b2c7c63d9d7d72346`, successful CodeQL run `32434564524`, successful Dependency Review run `32434567688`, and successful Logos Protocol CI run `32434567730`.
- Produces: current maintained documentation that describes M9 as merged and hosted-validated while recording #108 as CLOSED with reason `completed`; reactivation is planned after the source PR is reviewable, with reducer, semantic enrichment, final equivalence, and benchmark gates remaining.

- [x] **Step 1: Update authoritative anchors and M9 status**

  In the canonical execution plan, replace the local-only M9 anchor with the exact PR, source-head, merge, and hosted-check receipts. Update the current source anchor to `2a3679e176772bfcc57ed49b2c7c63d9d7d72346`. State that #108 is currently CLOSED with reason `completed`; reactivation is planned after the source PR is reviewable because the merged artifacts delivered only the second private slice.

- [x] **Step 2: Preserve the M9 local receipt and add the publication receipt**

  Keep the exact local qualification evidence for `d3dd316d4536ea428747dc3a4895ad633ffa6993`. Add a separate hosted-publication paragraph and a newest-first execution-ledger row for PR #176. Do not rewrite the local receipt as if hosted checks ran on `d3dd316`.

- [x] **Step 3: Update the persistent assurance goal**

  Change M9 from `locally qualified, unpublished` to merged through PR #176. Record the exact source head and squash merge, the three successful hosted workflows, and the residual #108 boundary. Replace stale statements that all broader issues remain open with the exact current state after reconciliation.

- [x] **Step 4: Add the newest-first documentation log entry**

  Add `## 2026-08-21` above the existing `2026-08-20` entry. Record PR #174, PR #175, and PR #176 as distinct post-v1.8.0 deliveries; explain that #108 is currently CLOSED with reason `completed` and reactivation is planned after the source PR is reviewable. Update `last_verified`, `verified`, and `stale_after` using the repository validator's accepted dates.

- [x] **Step 5: Run focused documentation validation**

  Run:

  ```bash
  rtk env UV_CACHE_DIR=/private/tmp/logseq-matryca-parser-post-m9-uv-cache uv run python scripts/check_documentation.py --root . --profile docs/maintained.toml --as-of-date 2026-08-21
  rtk make vendor-name-check
  rtk git diff --check
  ```

  Expected: all commands exit 0 and no historical design/plan file changes.

  Task 1 status: documentation edits, focused validation, and the bounded fix
  review are complete. Publication of this reconciliation and #108
  reactivation remain pending.

- [x] **Step 6: Commit the documentation reconciliation**

  Stage only the three maintained documents and this plan, then commit:

  ```bash
  rtk git add -- docs/LSDOC_REFERENCE_STUDY_AND_EXECUTION_PLAN_2026-08-16.md docs/goals/LSDOC_PARSER_ASSURANCE_GOAL.md docs/log.md docs/superpowers/plans/2026-08-21-post-m9-reconciliation.md
  rtk git commit -m "docs(parser): reconcile M9 publication state"
  ```

### Task 2: Qualify and publish the reconciliation

**Files:**
- Verify: all files changed by Task 1
- External state: GitHub issue #108 and the reconciliation pull request

**Interfaces:**
- Consumes: Task 1 exact commit and successful documentation gates.
- Produces: reviewed source change, planned reactivation of currently CLOSED issue #108 after the source PR is reviewable, and a durable hosted receipt.

- [x] **Step 1: Run exact-head repository gates**

  Run:

  ```bash
  rtk env UV_CACHE_DIR=/private/tmp/logseq-matryca-parser-post-m9-uv-cache make all
  rtk make vendor-name-check
  rtk git diff --check origin/main...HEAD
  rtk git status --short --branch
  ```

  Expected: 685 or more tests pass, coverage remains at or above 80%, all static/documentation gates pass, and the tracked worktree is clean.

  Local result before publication: `make all` passed with 685 tests and 89.73%
  coverage; Ruff, mypy, documentation, vendor-name, and diff gates passed. The
  ignored SDD workspace retains the raw transcript and its exact-head manifest.

- [ ] **Step 2: Obtain an independent bounded review**

  Review the complete `origin/main...HEAD` range for factual receipt accuracy, Matryca-v1 metadata, historical-record preservation, links, and issue-state consistency. Any Important or Critical finding must be corrected and re-reviewed before publication.

- [ ] **Step 3: Publish a draft pull request**

  Push the exact branch and create a draft PR against `main`. The PR must link #108 without a closing keyword, list the exact local validation, disclose AI assistance, and state that historical pre-publication plans remain unchanged.

- [ ] **Step 4: Reopen and annotate #108**

  After the source PR is reviewable, reopen #108 and add one concise English comment: PR #170 completed private line classification, PR #176 completed private lexical state, and reducer/semantic-enrichment plus final equivalence and benchmark gates remain. This is a controller-owned GitHub mutation.

- [ ] **Step 5: Verify hosted state**

  Verify the PR base/head SHA, draft state, mergeability, checks, and issue #108 state separately. Do not merge until every exact-head required check and review is terminally successful.

## Completion checklist

- [ ] Current maintained docs name PR #176 and its exact source/merge receipts.
- [ ] Historical M9 design and implementation-plan records remain unchanged.
- [ ] Matryca-v1 maintained metadata and links pass deterministically.
- [ ] Issue #108 is reactivated after the source PR is reviewable and describes the residual reducer, semantic enrichment, final equivalence, and benchmark scope.
- [ ] #87, #103, #104, and #111 ownership is unchanged.
- [ ] The reconciliation PR is reviewable with exact-head local and hosted evidence.
