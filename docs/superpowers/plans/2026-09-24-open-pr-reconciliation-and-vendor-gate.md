# Open PR Reconciliation and Vendor Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair current GitHub issue evidence and make the vendor-name policy gate complete and fail-closed, then merge only PRs that satisfy exact-head review and CI gates.

**Architecture:** Keep the August ledger as immutable history and add a new maintained dated snapshot for live issues and PRs. Replace the shell utility dependency with a small standard-library Python scanner that gets candidate paths from Git and treats enumeration failure as an error.

**Tech Stack:** Markdown frontmatter, TOML maintained-document profile, Python 3.12 standard library, pytest, Make, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-24-open-pr-quality-gates.md`

## Global Constraints

- Keep all repository documentation and maintainer-authored GitHub text in English.
- Preserve the exact primary checkout and do not alter parser/runtime behavior.
- Keep forbidden-name patterns encoded; never add prohibited vendor product names to repository files, fixtures, comments, or workflow output.
- Current `main` anchor is `ac91aca6a3d6bf3ad5f6f952ff4b8b366bdc9941`; refresh it before publication.
- `make all` and `make vendor-name-check` are mandatory repository gates.
- `gh` writes are forbidden while `gh auth status` reports an invalid token.
- Merge only against exact current PR heads after all repository-required checks and review gates pass.

## Review Focus

- Hidden Git paths such as `.github/` must be scanned, not silently skipped.
- Git enumeration failure or absent Git must return nonzero, never success.
- Binary files and explicit exemptions must not create false positives.
- Issue ledger must distinguish current live issue state from historical audit claims.
- PR approval-required/skipped checks must never be described as passing.

---

### Task 1: Freeze live issue and PR evidence

**Files:**
- Read: `docs/quality/ISSUE_RECONCILIATION_2026-08-06.md`
- Create: `docs/quality/OPEN_ISSUE_RECONCILIATION_2026-09-24.md`

**Interfaces:**
- Consumes: GitHub live search result for 33 open issues; PR metadata and
  workflow runs for #218–#221.
- Produces: dated issue table and explicit next actions; no issue state changes.

- [x] Record exact list of 33 open issue numbers and titles from live search.
- [x] Group concise dispositions by existing roadmap wave, newcomer scope,
  research, and dependency; call out #152/#218 linkage and exact PR blockers.
- [x] Mark #218 workflow approval as pending, #219/#220/#221 as failed or
  stale-base until fresh runs exist. Do not infer merge readiness.
- [x] Reconcile exact issue set against table, then add the snapshot to the
  maintained profile and quality/documentation indexes.
- [x] Mark August file historical without changing its historical claims.

### Task 2: Prove the policy-scanner defect with tests

**Files:**
- Create: `tests/test_check_vendor_free_docs.py`
- Create: `scripts/check_vendor_free_docs.py`

**Interfaces:**
- `scan_repository(root: Path) -> list[Finding]`
- `Finding` carries repository-relative path and line number only.
- CLI exits `0` only for a completed clean scan, `1` for findings, and `2` for
  scan/configuration errors.

- [x] Write tests using base64-decoded pattern bytes, not literal restricted
  names. Stage temporary fixture files in a temporary Git repository.
- [x] Assert a match under a hidden path is reported with path and line.
- [x] Assert `uv.lock`, the checker itself, and binary blobs are exempt.
- [x] Run the CLI from a non-Git directory and assert an error exit;
  assert CLI reports an error and exits `2`.
- [x] Verify RED on the legacy wrapper: hidden path and non-Git assertions
  failed because it ignored `--root` and reported success.

### Task 3: Implement portable fail-closed scanning

**Files:**
- Modify: `scripts/check_vendor_free_docs.py`
- Modify: `scripts/check_vendor_free_docs.sh`
- Modify: `Makefile`
- Modify: `tests/test_check_vendor_free_docs.py`

**Interfaces:**
- Shell compatibility wrapper delegates to Python and propagates its exit code.
- Make target remains `vendor-name-check` and preserves existing workflow calls.

- [x] Enumerate tracked and non-ignored untracked file paths with `git ls-files`
  in NUL-delimited mode; treat process failure as a scan error.
- [x] Inspect regular files without traversing symlink targets. Include dotfiles.
- [x] Search byte content case-insensitively, skip NUL-containing binary files,
  and report only repository-relative path and line.
- [x] Keep pattern encoded and keep the documented file exemptions.
- [x] Add and verify missing tracked-file failure; do not report a partial scan
  as clean.
- [x] Run the focused tests and `make vendor-name-check`; inspect exit codes and
  output.

### Task 4: Reconcile documentation navigation and lifecycle

**Files:**
- Modify: `docs/quality/README.md`
- Modify: `docs/index.md`
- Modify: `docs/README.md`
- Modify: `docs/DOCUMENTATION_SYSTEM.md`
- Modify: `docs/maintained.toml`
- Modify: `docs/quality/ISSUE_RECONCILIATION_2026-08-06.md`

- [x] Link the 2026-09-24 snapshot as current and the August ledger as
  historical evidence.
- [x] Record this lifecycle transition in `docs/log.md`.
- [x] Run maintained-document validation with UTC date `2026-09-24`.
- [x] Review local links, frontmatter dates, and canonical document type.

### Task 5: Verify integrated branch

**Files:**
- Validate all files changed above; no additional scope.

- [x] Run focused scanner tests: 5 passed.
- [x] Run `make vendor-name-check` and documentation validation.
- [x] Final full `make all`: Ruff, Mypy, docs, vendor check, and tests passed;
  815 tests passed with 91.20% coverage against an 80% floor.
- [x] Run `git diff --check`; confirm only planned files changed.
- [x] Sol review: final `PASS_WITH_NOTES`, no blocking finding. Added the
  requested symlink and ignored-file regression coverage; the scanner skips
  symlink entries instead of reading target text. A theoretical path-swap race
  remains outside this static repository check's threat model.
- [x] Run full `make all` after the final scanner and test changes; lint, type
  check, docs, vendor check, tests, and coverage floor all passed.
- [ ] Confirm exact base/current refs, commit the reviewed patch, and verify
  clean worktree after commit.

### Task 6: Publish, rerun PR gates, and close only safe candidates

**Files:**
- No local source changes unless review requires a scoped repair.

- [ ] Reverify live `main`, target PR heads, auth and branch protection.
- [ ] Commit and push the repair branch, then open a PR against current `main`.
- [ ] Wait for repair PR checks and merge only after all required gates pass.
- [ ] Refresh all four original PRs. Ask for or approve workflow execution for
  #218 only when GitHub requires maintainer approval and the exact diff remains
  the reviewed test-only contribution.
- [ ] Update each stale branch to current `main` using a safe non-force path;
  rerun required CI and dependency review.
- [ ] Merge one PR at a time only when its current head is green, review threads
  are resolved, and branch protection allows it. Stop on any ambiguous,
  skipped, or failed gate.
- [ ] Record merged PR SHAs or precise hold reasons in the current dated ledger.
