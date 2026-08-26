---
type: QualityIntegrationRecord
title: Static analysis and CCP integration
description: Reviewed integration contract for workflow analysis, dependency hygiene, and staged local CI qualification.
status: stable
classification: active
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-08-26
verified: 2026-08-26
stale_after: 2027-02-22
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---

# Static analysis and CCP integration

## Outcome

The first three static-analysis recommendations are now represented by narrow,
version-pinned repository contracts:

| Control | Integration tier | Trigger and authority |
|---|---|---|
| `actionlint` 1.7.12 | Local pre-commit plus blocking, path-scoped workflow CI | Pull requests and `main` pushes that change workflow-analysis inputs |
| `zizmor` 1.29.0 | Blocking, offline, path-scoped workflow CI | Same workflow-change boundary; no token or online audit |
| `deptry` 0.25.1 | Periodic advisory workflow | Monthly schedule or explicit manual dispatch; never a pull-request requirement |
| Commit CI Preflight (CCP) | Local matrix bootstrap and observation | Maintainer-controlled clean-checkout qualification; no hosted skip yet |

The Python analyzers remain ephemeral overlays rather than runtime or permanent
development dependencies. The package lock therefore does not absorb analyzer
implementation dependencies.

## Workflow hardening dispositions

The eleven pilot findings have explicit outcomes:

- five non-writing checkout steps now disable credential persistence;
- the two release jobs that produce or qualify publication artifacts disable
  the shared `uv` cache;
- both Dependabot ecosystems apply a seven-day cooldown to version updates;
- the metrics writer retains credentials through an inline, rule-scoped
  `artipacked` exception because its bounded job must push to `main`;
- the immutable, contract-tested release action retains one line-scoped
  `superfluous-actions` exception. Replacing it with `gh release` remains a
  separate non-security migration.

No audit is globally disabled. The repository-specific immutable-action and
workflow-shape tests remain in force because neither analyzer replaces them.

## GitHub Actions cost boundary

The two new hosted workflows are deliberately bounded:

- workflow analysis runs only when workflow policy inputs change;
- dependency hygiene runs once per month or manually;
- concurrency cancels obsolete workflow-analysis runs;
- analyzer versions and the actionlint release checksum are fixed;
- shared caches are disabled in security-sensitive and publication jobs.

CCP is the staged route to larger savings. The committed matrix covers the
complete Python 3.12 repository gate and the Python 3.13 test suite using
digest-pinned runtime images. Its policy binds every required check, runtime,
image, platform, normalized runtime digest, and outer matrix digest.

This integration does **not** yet skip unconditional hosted CI. Local evidence
must first demonstrate exact-head parity and trustworthy receipt handling.
Only a separately reviewed activation change may add an exact-head receipt
gate and conditionally route eligible same-repository pull requests away from
duplicated hosted work. Forks, Dependabot, missing or invalid receipts, release
tags, and selected fallback cases must retain hosted qualification.

## CCP operator contract

Tracked inputs:

- [`.commit-ci-preflight.toml`](../../.commit-ci-preflight.toml): matrix-v2
  execution plan;
- [`.commit-ci-policy.toml`](../../.commit-ci-policy.toml): reviewed exact
  digest and required-check policy;
- [`scripts/run_qualified_ccp.sh`](../../scripts/run_qualified_ccp.sh):
  fail-closed executable-path and SHA-256 guard;
- `make ccp-plan`, `make ccp-doctor`, `make ccp-dry-run`, and
  `make ccp-verify`: non-heavy planning or receipt-verification entry points.

There is intentionally no `make ccp-run` shortcut. An official run is a heavy,
authority-bearing operation that requires a clean selected checkout, fresh
resource/admission/runtime checks, an explicit generation, and the separate
authorization envelope defined by the maintainer operator contract.

The normalized policy boundary on 2026-08-26 is:

| Item | Digest |
|---|---|
| Outer matrix | `sha256:4fb7f31095c8c74938df25f623cddb7feacc96d5fa9fe7364bf25b679a4796a2` |
| Python 3.12 plan | `sha256:28e8e38ea6eb7eef702b36f57f8c373ecc125896b3a3c30c021c501a0bc70a3f` |
| Python 3.13 plan | `sha256:82ed2a348589b029b4feeb03f34c46d9c12039dd9f113691de706c39606cf9b3` |

Any config, image, check, policy, or digest change creates a new qualification
boundary and requires policy regeneration from a reviewed `ccp-plan`, never
from a completed receipt.

## Local validation evidence

On the integration working tree based on
`546f1d87c71dd61332acaafc73d442acd22bdcad`:

- the workflow contract completed its red-green cycle and passed 26 focused
  tests;
- actionlint completed with no findings;
- configured offline zizmor completed with no unexplained findings;
- deptry completed with no findings while running against the project
  environment and the two measured scope rules;
- CCP `plan`, matrix-aware `doctor`, and `dry-run` completed with matching
  outer and per-runtime digests; the doctor observed OrbStack 29.4.0 with
  memory and swap limits available for both pinned runtimes.
- the complete repository gate passed Ruff, Mypy across 78 source files, the
  vendor policy, maintained-documentation validation, and 774 tests at 91.20%
  coverage;
- a clean wheel and source distribution passed the wheel contract, Twine, and
  strict downstream Mypy against the installed wheel under Python 3.12.

These checks qualify only the recorded local working tree and temporary package
artifacts. No CCP heavy run, receipt publication, push, pull request, merge,
branch-protection change, or release is authorized by this record.

## Next savings gate

Before hosted jobs may be skipped:

1. run at least one authorized CCP matrix qualification on an exact clean
   candidate commit and verify its receipt against the tracked policy;
2. compare the same commit with unconditional hosted Python 3.12/3.13 results;
3. exercise rejection cases for missing, stale, malformed, wrong-head,
   wrong-policy, incomplete, and failed receipts;
4. retain hosted fallback for forks, dependency automation, releases, and
   infrastructure uncertainty;
5. measure minutes saved from GitHub billing evidence rather than estimating
   from job duration alone;
6. obtain explicit approval for the trusted receipt workflow, routing change,
   and any branch-protection update.
