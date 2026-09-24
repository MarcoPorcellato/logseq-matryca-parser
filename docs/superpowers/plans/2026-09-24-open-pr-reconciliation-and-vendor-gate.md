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
- [x] Re-run final full `make all` after the maintainer-approved AnyIO 4.14.2
  lock update: Ruff, Mypy (83 source files), documentation validation, vendor
  check, and all 815 tests passed; coverage was 91.18% against an 80% floor.
- [x] Verify dependency and package contracts: `uv lock --check`,
  `uv sync --locked --all-extras`, production `pip-audit` (no known
  vulnerabilities; one existing documented ignore), wheel/sdist build, wheel
  contract, Twine check, and strict downstream typing all passed.
- [x] Run `git diff --check`; confirm only planned files changed.
- [x] Initial Sol review: `PASS_WITH_NOTES`, no blocker; scanner now skips
  symlink entries and tests ignored-file behavior.
- [x] Final Sol review: `PASS_WITH_NOTES`; fake timer removes the observed
  scheduler race without runtime changes. No merge approval; exact-head hosted
  checks remain required.

### Hosted CI findings and scope gate

- Repair PR #222 was opened at 2026-09-24 07:03 UTC from commit
  `5d9afe891514554320b6123a7c9fef6174595e4f`, based on live `main`
  `ac91aca6a3d6bf3ad5f6f952ff4b8b366bdc9941`.
- Exact-head Logos Protocol CI run `35967619072`: Quality and package-contract
  jobs passed; production dependency audit failed on AnyIO 4.13.0
  (`CVE-2026-63374`); both macOS jobs failed
  `test_debounced_graph_event_router_coalesces_rapid_events`. CI logs show
  Python 3.12 observing an empty callback list after a fixed sleep; source
  review found the assertion races with the timer thread. No parser/runtime
  code change is planned; the unit test now uses a deterministic fake timer.
- Follow-up exact-head run `35970787660` on `f744dbf`: the debounce test passed
  on both macOS versions and Linux, but Windows 3.12 and 3.13 each failed two
  scanner error-path tests. They invoked the Bash wrapper, whose `python3`
  alias launched an uninstalled WSL distribution instead of the job's Python;
  this returned exit 1 before the scanner could return its expected exit 2.
  The scoped test fix invokes the Python checker with `sys.executable`, still
  exercising its real CLI without depending on shell or WSL aliases.
- Windows repair evidence: focused scanner tests 5/5 passed; final local
  `make all` passed all 815 tests with 91.18% coverage, Ruff, Mypy, docs and
  vendor checks. Sol reviewed the exact test diff `PASS_WITH_NOTES`; it notes
  that the shell wrapper itself remains unverified on Windows, while Ubuntu
  Quality exercises it.
- The Windows test-launch fix was committed as `4268dfe` and pushed. Exact-head
  Logos Protocol CI run `35971538946` passed Quality, package contract, and
  all six Linux/macOS/Windows Python 3.12/3.13 test jobs; Dependency Review
  `35971538926` passed. The only failed job is production dependency audit,
  which reports AnyIO 4.13.0 vulnerabilities `CVE-2026-63374` and
  `CVE-2026-64847`, both fixed by 4.14.2. Keep the dependency boundary fail
  closed.
- Sol security review of #219 verified its exact registry artifact URLs and
  hashes for AnyIO 4.14.2 and confirmed the upstream advisory's fixed version.
- On 2026-09-24, the maintainer explicitly amended the earlier no-dependency
  boundary to authorize integrating only #219's existing AnyIO 4.14.2 lockfile
  update into #222. No dependency declarations, other packages, or runtime
  code are in scope; #219 remains open until the equivalent change reaches
  `main`.
- Therefore #222 and #219–#221 are not mergeable now. #218 still requires
  maintainer approval to execute hosted workflows; do not treat
  `action_required` as PASS or approve it without a fresh exact-diff decision.
- [x] Confirm exact base/current refs, commit the reviewed patch as
  `4840d32` (`test: make graph debounce test deterministic`) and its evidence
  update as `71adef2`; verify the isolated worktree is clean.

### Task 6: Publish, rerun PR gates, and close only safe candidates

**Files:**
- No local source changes unless review requires a scoped repair.

- [x] Initial publication: PR #222 was opened against `main` and the first
  patch was pushed. The reviewed deterministic timer-test fix is committed as
  `4840d32`; evidence update `71adef2` is pushed to the same PR branch.
- [x] Refresh exact heads for #218–#222 after push. On #222 head
  `71adef291f4849d91274e29b860322202d3fbfd2`, Dependency Review run
  `35970490531` passed; Logos Protocol CI run `35970490464` has Quality and
  package-contract jobs passed, but its production dependency audit failed on
  AnyIO 4.13.0 while the platform test matrix is still running. Do not merge.
- [x] Confirm all five PRs have no unresolved inline review threads. Current
  original PR states remain: #218's two checks are `action_required`; #219's
  Logos CI is failed and Dependency Review passed; #220 and #221 have failed
  Logos CI with their Dependency Review and Workflow Static Analysis checks
  passed. Their heads remain based on older `main` commits; preserve them open.
- [x] Refresh live PR metadata, heads, workflow runs, and review threads. PR
  #222 still targets base SHA `ac91aca6a3d6bf3ad5f6f952ff4b8b366bdc9941`;
  the GitHub integration does not expose branch protection (403), and stored
  GitHub CLI authentication is invalid. No merge attempted.
- [x] Push the reviewed follow-up to PR #222. Exact code head `4268dfe`
  resolves the Windows test-launch failure across Python 3.12/3.13; only the
  AnyIO production audit remains failed. The PR remains open and unmerged.
- [x] Refresh all four original PRs. Hold #218 for `action_required`; hold
  #219 for failed Logos CI despite useful, independently reviewed security
  update; hold #220 and #221 for failed Logos CI and stale bases. Do not approve
  #218 or close any original PR based on these states.
- [ ] Update each stale branch to current `main` using a safe non-force path;
  rerun required CI and dependency review only after #222 is mergeable and
  incorporated, or after separate explicit scope direction.
- [ ] Merge one PR at a time only when its current head is green, review threads
  are resolved, and branch protection allows it. Stop on any ambiguous,
  skipped, or failed gate.
- [x] Record the precise hold reasons and latest exact-head evidence here; the
  07:00 UTC issue ledger remains a time-bound snapshot taken before #222.

### Current stop condition

- The exact PR #219 lockfile delta is applied locally as the only change to
  `uv.lock`; its wheel and sdist URLs, SHA-256 digests, sizes, and upload times
  match official PyPI metadata. Sol security review: `PASS_WITH_NOTES`.
- All local code, lock, package, and audit checks pass. Final Sol review:
  `PASS_WITH_NOTES`; no blocker, but it correctly notes that fresh exact-head
  hosted CI is still pending. Remaining gates: commit and push the lock update
  plus evidence amendments to #222, then verify every hosted check against the
  resulting exact head. Stop before merge; the maintainer authorized this
  bounded integration and checks, not merge.
