---
type: Document
title: Continuous integration assurance
description: Canonical map of pull-request, scheduled, settings-managed, and release checks.
status: stable
classification: canonical
audience: contributors
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-08-30
verified: 2026-08-30
stale_after: 2027-02-26
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---

# Continuous integration assurance

GitHub Actions is the repository's hosted continuous-integration system. This
page explains which checks exist, when they run, and what their results prove.
It is the shared map for contributors, maintainers, and AI agents; focused
security and release documents remain authoritative for their own boundaries.

## Pull-request and main checks

[`Logos Protocol CI`](../.github/workflows/ci.yml) runs for every pull request,
every push to `main`, and manual dispatch. Each job is independent so a failure
identifies the affected contract directly.

| Job | Platform | Purpose |
|---|---|---|
| `quality` | Ubuntu 24.04, Python 3.12 | Ruff, Mypy, documentation validation, repository policy, and clean-checkout verification |
| `tests` | Ubuntu 24.04, macOS 15, Windows 2025; Python 3.12 and 3.13 | Complete Pytest suite and the 80% coverage floor on all six supported runtime cells |
| `dependency-audit` | Ubuntu 24.04, Python 3.12 | `pip-audit` over locked base and optional production dependencies |
| `package-contract` | Ubuntu 24.04, Python 3.12 | Wheel/sdist build, package metadata, PEP 561, Twine, and downstream strict typing |

[`Dependency Review`](../.github/workflows/dependency-review.yml) is a separate
pull-request check. It rejects newly introduced runtime or development
dependencies with known vulnerabilities of moderate severity or higher. It
uses the unprivileged `pull_request` event, not `pull_request_target`, and does
not receive repository secrets.

[`Workflow Static Analysis`](../.github/workflows/workflow-analysis.yml) runs
when workflow, Dependabot, pre-commit, or workflow-security configuration
changes. It validates workflow semantics with a checksum-verified actionlint
binary and audits workflow security offline with a pinned zizmor release. It is
path-scoped, so it must not be configured as a globally required check: GitHub
can leave path-filtered required workflows pending when they do not run.

All project environments synchronize with `uv.lock`. External actions are
pinned to complete commit SHAs, read-only checkouts discard credentials, jobs
have explicit timeouts, and standard runner images are versioned.

## Scheduled and settings-managed assurance

| Assurance | Trigger | Boundary |
|---|---|---|
| [`Parser Adversarial Laboratory`](../.github/workflows/parser-adversarial.yml) | Weekly and manual | Bounded generated parser cases; no vault source is uploaded |
| [`Dependency Hygiene Audit`](../.github/workflows/dependency-hygiene.yml) | Monthly and manual | Detects unused, missing, and transitive dependency declarations with pinned deptry |
| [`OpenSSF Scorecard`](../.github/workflows/scorecard.yml) | Push to `main` and weekly | Publishes supply-chain posture as SARIF and a short-retention artifact |
| [`Daily Metrics Saver`](../.github/workflows/daily-metrics.yml) | Daily and manual | Main-only traffic archive; the [metrics threat model](security/DAILY_METRICS_THREAT_MODEL.md) governs its write token and data boundary |
| CodeQL default setup | GitHub-managed | Python SAST without a custom workflow; see [`CODEQL.md`](CODEQL.md) |
| Secret scanning and push protection | GitHub settings | Repository-level secret detection; source files cannot prove that the settings are enabled |
| Dependabot alerts and security updates | GitHub settings | Advisory detection and security-update pull requests; routine version updates follow [`.github/dependabot.yml`](../.github/dependabot.yml) |

Scheduled workflow files express intended behavior. A current claim requires a
successful hosted run on the exact workflow revision. Settings-managed features
require a live Settings or API readback; documentation is not a substitute.

## Release assurance

[`Release`](../.github/workflows/pypi_publish.yml) starts only from a `v*` tag
and remains sequential:

```text
Python 3.12/3.13 pre-flight
  -> exact tag/version/changelog contract
  -> one wheel and sdist build
  -> wheel, Twine, SBOM, license inventory, and checksum contracts
  -> GitHub provenance and SBOM attestations with in-job verification
  -> PyPI Trusted Publishing
  -> GitHub Release from the same downloaded bundle
```

Release jobs do not restore dependency caches. Read-only checkouts do not keep
credentials. Only the exact build job receives attestation permissions, the
PyPI job receives OIDC for Trusted Publishing, and the final GitHub Release job
receives `contents: write`. Follow [`RELEASE_PROCESS.md`](RELEASE_PROCESS.md)
for preparation, failure handling, and post-publication verification.

## Contributor workflow

Before opening a pull request, run:

```bash
uv sync --locked --all-extras
make all
make vendor-name-check
```

When automation files change, also run actionlint and zizmor using the pinned
versions documented in `workflow-analysis.yml`. When packaging changes, build
wheel and sdist, run `scripts/check_wheel_contract.py`, Twine 6.2.0, and the
downstream strict-Mypy sample.

Do not add secrets to workflow files, caches, fixtures, artifacts, logs, or
pull-request comments. A contributor pull request must never be changed to
`pull_request_target` merely to gain a token or secret.

## Maintainer ruleset guidance

After the first exact-head hosted run confirms the new job names, protect
`main` with the always-emitted CI and Dependency Review checks. Require a pull
request, require the branch to be current before merge, dismiss stale
approvals when the protected diff changes, and block force pushes and branch
deletion. Keep path-scoped workflow analysis outside the global required-check
list, while treating any emitted failure as blocking review evidence.

Verify CodeQL default setup, Dependabot alerts/security updates, secret
scanning, push protection, Actions SHA-pinning policy, and the PyPI environment
directly in repository settings. Do not claim any setting from this file.

## Cache and fork safety

Development jobs may use the uv cache. Pull-request caches are scoped by
GitHub's event and merge reference and contain only downloaded dependencies;
they must not contain tokens, credentials, source snapshots, or release
artifacts. Release and workflow-analysis jobs disable shared dependency caches.

Fork pull requests run untrusted repository code with read-only permissions and
without secrets. No privileged workflow checks out or executes a contributor's
head through `pull_request_target`, `workflow_run`, an issue comment, or another
indirect trigger.

## Evidence boundaries

| Evidence label | What is required | What it proves |
|---|---|---|
| **Local PASS** | Fresh complete commands and a clean diff on one exact commit | Source contracts pass on the recorded local OS and Python runtime |
| **Hosted PASS** | Successful GitHub Actions jobs on the exact head SHA | Those workflow jobs passed on their recorded hosted runners |
| **Settings PASS** | Current authenticated Settings or API readback | The named repository security or ruleset option is enabled at readback time |
| **Publication PASS** | Exact-tag workflow success plus downloaded artifact, checksum, and attestation verification | The named package and release artifacts match the qualified tag |

One label never implies another. In particular, local workflow validation does
not prove hosted Windows behavior, and a workflow source file does not prove a
repository setting or a published release.

## Related authorities

- [`CODEQL.md`](CODEQL.md) — default-setup boundary and status navigation
- [`RELEASE_PROCESS.md`](RELEASE_PROCESS.md) — release execution and recovery
- [`reference/DEPENDENCY_LICENSE_POLICY.md`](reference/DEPENDENCY_LICENSE_POLICY.md) — dependency, SBOM, checksum, license, and attestation contract
- [`security/DAILY_METRICS_THREAT_MODEL.md`](security/DAILY_METRICS_THREAT_MODEL.md) — self-mutating metrics workflow boundary
- [`DOCUMENTATION_SYSTEM.md`](DOCUMENTATION_SYSTEM.md) — documentation lifecycle and authority
