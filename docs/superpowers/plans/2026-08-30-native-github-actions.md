# Native GitHub Actions Assurance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the repository's optional local CI coordination path with a complete, secure, locked, cross-platform GitHub Actions assurance system for pull requests, schedules, and releases.

**Architecture:** Keep one primary CI workflow with independently readable quality, test-matrix, dependency-audit, and package-contract jobs. Add path-scoped workflow analysis and monthly dependency-declaration hygiene, while hardening the existing specialized and release workflows without changing release artifact identity or order.

**Tech Stack:** GitHub Actions, Python 3.12/3.13, uv 0.11.7, Pytest, Ruff, Mypy, pip-audit, deptry 0.25.1, actionlint 1.7.12, zizmor 1.29.0, Twine 6.2.0.

**Spec:** `docs/superpowers/specs/2026-08-30-native-github-actions-design.md`

## Global Constraints

- Start from `origin/main` commit `044b81d0b0ed869ac5213d4a79e10949b9930633` in the isolated `ci/native-github-actions` worktree.
- Use only standard GitHub-hosted runner images: `ubuntu-24.04`, `macos-15`, and `windows-2025`.
- Support Python `3.12` and `3.13` in the complete runtime test matrix.
- Pin every external action to a full 40-character commit SHA.
- Pin uv to `0.11.7` and use `uv sync --locked --all-extras` for project environments.
- Keep pull-request jobs read-only, secret-free, timeout-bounded, and free of `pull_request_target`.
- Keep CodeQL on GitHub default setup; do not add `.github/workflows/codeql.yml`.
- Keep the release build single-use and preserve SBOM, license inventory, checksum, attestation, PyPI, and GitHub Release order.
- Preserve the coverage floor at 80% or higher.
- Keep all repository documentation and workflow messages in English.

---

### Task 1: Portable Makefile and native CI contract

**Files:**
- Modify: `tests/test_quality_gate_contract.py`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: the existing Makefile targets `all`, `lint`, `lint-fix`, `check`, `vendor-name-check`, `docs-check`, `test`, and `verify-clean`.
- Produces: `_read_makefile_recipes(target: str, makefile: Path = ROOT / "Makefile") -> list[str]` and the stable jobs `quality`, `tests`, `dependency-audit`, and `package-contract`.

- [x] **Step 1: Add failing CI contract tests**

  Add assertions that require the four stable job identifiers, explicit timeouts,
  pinned standard runner labels, a six-cell OS/Python test matrix, locked sync,
  credential-free checkouts, a single dependency audit, Twine package validation,
  and no `pull_request_target`.

  ```python
  def test_ci_uses_locked_cross_platform_native_actions_jobs() -> None:
      workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
      for job in ("quality", "tests", "dependency-audit", "package-contract"):
          assert f"\n  {job}:\n" in workflow
      for runner in ("ubuntu-24.04", "macos-15", "windows-2025"):
          assert runner in workflow
      assert '["3.12", "3.13"]' in workflow
      assert "uv sync --locked --all-extras" in workflow
      assert "twine==6.2.0" in workflow
      assert "pull_request_target" not in workflow
  ```

- [x] **Step 2: Run the new contract and confirm RED**

  Run: `uv run pytest tests/test_quality_gate_contract.py -q`

  Expected: FAIL because the baseline workflow has only `build` and
  `package-contract`, uses moving runner labels, and does not lock development
  synchronization.

- [x] **Step 3: Replace GNU Make subprocess inspection with a deterministic reader**

  Implement `_read_makefile_recipes` inside the test module. It accepts only
  simple target declarations and tab-prefixed recipes, expands reachable
  prerequisites depth-first, rejects duplicates, cycles, unresolved
  prerequisites, orphan recipes, and reachable continuation recipes, and
  returns the exact commands asserted by the existing tests.

- [x] **Step 4: Implement the four-job CI workflow**

  Use a quality job on Ubuntu/Python 3.12, a full six-cell runtime matrix, one
  production dependency audit, and one package build. Keep caches enabled only
  for pull-request/main development jobs and end quality with `make verify-clean`.

- [x] **Step 5: Run the focused contract and confirm GREEN**

  Run: `uv run pytest tests/test_quality_gate_contract.py -q`

  Expected: PASS.

### Task 2: Workflow security and dependency hygiene

**Files:**
- Create: `.github/workflows/workflow-analysis.yml`
- Create: `.github/workflows/dependency-hygiene.yml`
- Modify: `.github/dependabot.yml`
- Modify: `.pre-commit-config.yaml`
- Create: `zizmor.yml`
- Modify: `pyproject.toml`
- Modify: `tests/test_quality_gate_contract.py`

**Interfaces:**
- Consumes: every `.github/workflows/*.yml` file, `uv.lock`, and Python import metadata.
- Produces: path-scoped `Workflow Static Analysis`, scheduled/manual `Dependency Hygiene Audit`, and seven-day Dependabot cooldowns.

- [x] **Step 1: Add failing hygiene contract tests**

  Require SHA-pinned checkout, no persisted credentials, explicit timeout,
  checksum-verified actionlint `1.7.12`, strict zizmor `1.29.0`, monthly
  deptry `0.25.1`, no pull-request trigger for deptry, and two Dependabot
  cooldown blocks.

- [x] **Step 2: Run the focused tests and confirm RED**

  Run: `uv run pytest tests/test_quality_gate_contract.py -q`

  Expected: FAIL because the workflow-analysis, dependency-hygiene, and zizmor
  files do not yet exist.

- [x] **Step 3: Add the path-scoped workflow analysis**

  Download the pinned actionlint archive with TLS-only curl, verify SHA-256
  `8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8`,
  run it over the workflow tree, then execute:

  ```bash
  uvx --from zizmor==1.29.0 zizmor --strict-collection --format=github .
  ```

- [x] **Step 4: Add monthly deptry and measured configuration**

  Run deptry only on schedule/manual dispatch after locked synchronization:

  ```bash
  uv run --with deptry==0.25.1 deptry . --github-output
  ```

  Configure only the measured exclusions needed by the repository; do not add
  blanket rule suppression.

- [x] **Step 5: Add Dependabot cooldowns and the actionlint pre-commit hook**

  Pin the actionlint hook to commit
  `914e7df21a07ef503a81201c76d2b11c789d3fca` and add `default-days: 7`
  cooldowns to both package ecosystems.

- [x] **Step 6: Run the focused contract and confirm GREEN**

  Run: `uv run pytest tests/test_quality_gate_contract.py -q`

  Expected: PASS.

### Task 3: Specialized workflow and release hardening

**Files:**
- Modify: `.github/workflows/dependency-review.yml`
- Modify: `.github/workflows/parser-adversarial.yml`
- Modify: `.github/workflows/scorecard.yml`
- Modify: `.github/workflows/daily-metrics.yml`
- Modify: `.github/workflows/pypi_publish.yml`
- Modify: `tests/test_quality_gate_contract.py`

**Interfaces:**
- Consumes: existing dependency-review, adversarial, Scorecard, metrics, and release behavior.
- Produces: pinned standard runners, explicit timeouts, locked environments, and credential-minimized checkouts without changing triggers or release ordering.

- [x] **Step 1: Add failing hardening contract tests**

  Assert that every job has `timeout-minutes`, every runner uses a pinned
  standard image, all read-only checkouts set `persist-credentials: false`, the
  metrics checkout explicitly retains credentials, adversarial sync is locked,
  and release setup disables caches.

- [x] **Step 2: Run the focused tests and confirm RED**

  Run: `uv run pytest tests/test_quality_gate_contract.py -q`

  Expected: FAIL on missing timeouts, moving runner labels, unlocked
  adversarial synchronization, and release cache usage.

- [x] **Step 3: Harden specialized workflows minimally**

  Preserve all current events and permissions. Add only the approved runner,
  timeout, lock, uv-version, and checkout-credential controls.

- [x] **Step 4: Harden release without changing artifact identity**

  Keep `pre-flight -> build -> publish -> github-release`, one `uv build`, three
  checksum verifications, two GitHub attestations, and the same release bundle.
  Add timeouts, pinned Ubuntu, credential-free read-only checkouts, and disabled
  caches.

- [x] **Step 5: Run the focused contract and confirm GREEN**

  Run: `uv run pytest tests/test_quality_gate_contract.py -q`

  Expected: PASS.

### Task 4: Canonical CI documentation

**Files:**
- Create: `docs/CI_ASSURANCE.md`
- Modify: `docs/README.md`
- Modify: `docs/index.md`
- Modify: `docs/maintained.toml`
- Modify: `CONTRIBUTING.md`
- Modify: `AGENTS.md`
- Modify: `docs/CODEQL.md`
- Modify: `docs/RELEASE_PROCESS.md`
- Modify: `docs/quality/README.md`
- Modify: `docs/log.md`
- Modify: `tests/test_quality_gate_contract.py`

**Interfaces:**
- Consumes: final workflow names, triggers, job identifiers, and evidence boundaries.
- Produces: one maintained CI assurance map linked from human, machine, contributor, maintainer, and agent entry points.

- [x] **Step 1: Add a failing documentation contract test**

  Require `docs/CI_ASSURANCE.md` to exist, be listed in `docs/maintained.toml`,
  and be linked from `docs/README.md`, `docs/index.md`, `CONTRIBUTING.md`, and
  `AGENTS.md`.

- [x] **Step 2: Run the documentation contract and confirm RED**

  Run: `uv run pytest tests/test_quality_gate_contract.py -q`

  Expected: FAIL because the canonical assurance document does not exist.

- [x] **Step 3: Write the maintained assurance map**

  Include frontmatter, pull-request jobs, scheduled workflows, settings-managed
  security, release gates, contributor commands, maintainer ruleset guidance,
  fork safety, cache policy, and an evidence table separating local, hosted,
  settings, and publication claims.

- [x] **Step 4: Reconcile focused documentation**

  Link rather than duplicate. `CODEQL.md` remains the CodeQL authority,
  `RELEASE_PROCESS.md` remains the release authority, and the metrics threat
  model remains the self-mutating workflow authority.

- [x] **Step 5: Run documentation and focused tests and confirm GREEN**

  Run: `uv run pytest tests/test_quality_gate_contract.py tests/test_check_documentation.py -q`

  Expected: PASS.

### Task 5: Full source qualification and local checkpoint

**Files:**
- Review: all modified files

**Interfaces:**
- Consumes: Tasks 1-4.
- Produces: a clean, locally committed branch ready for hosted validation.

- [x] **Step 1: Run workflow-specific analyzers**

  Run actionlint `1.7.12` with its verified archive, zizmor `1.29.0`,
  and deptry `0.25.1`. Record exact exit codes.

- [x] **Step 2: Run the full repository gate**

  Run: `make all`

  Expected: Ruff PASS, Mypy PASS, documentation PASS, 80% or higher coverage,
  and all tests PASS.

- [x] **Step 3: Run the complete package contract**

  Build wheel and sdist in a temporary directory, run
  `scripts/check_wheel_contract.py`, Twine `6.2.0`, and strict downstream Mypy
  against the installed wheel.

- [x] **Step 4: Review diff and source state**

  Run `git diff --check`, inspect `git diff --stat` and `git diff`, verify no
  generated caches or private evidence are tracked, and confirm the exact base
  and branch head.

- [x] **Step 5: Commit the verified local checkpoint**

  Stage only reviewed files and commit with:

  ```text
  ci: adopt native cross-platform GitHub assurance
  ```

- [x] **Step 6: Stop before external mutation**

  Do not push, open a pull request, alter repository settings, update required
  checks, tag, publish, or merge. Report which hosted and settings gates remain
  unverified.

## Execution record

The isolated branch was qualified locally on 2026-08-30 before publication:

- `make all`: PASS on Python 3.12; 786 tests passed with 91.20% coverage.
- Complete test suite: PASS on Python 3.13; 786 tests passed with 91.20% coverage.
- actionlint 1.7.12: PASS using the checksum-verified release archive.
- zizmor 1.29.0: PASS with strict collection and no findings.
- deptry 0.25.1: PASS with no dependency issues.
- Hash-preserving dependency export and pip-audit: PASS with no known vulnerabilities.
- Wheel contract, Twine 6.2.0, and downstream Mypy 1.20.2: PASS.
- Luna final diff audit: the clean-runner blocker it found was corrected, release
  dependency-audit scope was aligned with CI, and no remaining blocker was reported.

Hosted Linux, macOS, and Windows execution, repository rulesets, GitHub default
CodeQL, and publication remain explicitly unverified until the branch is pushed
and reviewed through GitHub.
