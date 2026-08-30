# Native GitHub Actions Assurance Design

## Status

Approved by the maintainer on 2026-08-30.

## Objective

Make standard GitHub-hosted Actions the repository's complete continuous
integration and release assurance surface. The design must remain readable to
contributors, reproducible from `uv.lock`, secure for pull requests from forks,
and explicit about which checks run on pull requests, schedules, and tags.

## Baseline

The approved implementation starts from `origin/main` commit
`044b81d0b0ed869ac5213d4a79e10949b9930633`. That source already provides:

- Python 3.12 and 3.13 testing on Linux;
- a wheel and source-distribution contract;
- pull-request dependency review;
- weekly parser adversarial assurance;
- OpenSSF Scorecard publication;
- a sequential PyPI and GitHub Release workflow with OIDC, SBOMs, checksums,
  provenance attestations, and immutable artifact reuse.

The baseline gaps are duplicated quality work across the Python matrix,
unlocked dependency synchronization in development workflows, incomplete job
timeouts, Linux-only runtime testing despite an OS-independent package claim,
and no committed workflow-semantic/security analysis or dependency-declaration
hygiene workflow.

## Architecture

### Pull-request and main CI

`.github/workflows/ci.yml` is the primary required workflow and exposes four
independent job families:

1. `quality` runs Ruff, Mypy, documentation validation, repository policy
   checks, and the clean-checkout assertion once on Python 3.12/Linux.
2. `tests` runs the complete Pytest suite on Python 3.12 and 3.13 across pinned
   standard Linux, macOS, and Windows runner images.
3. `dependency-audit` audits the locked base and optional production
   dependency set once on Python 3.12/Linux.
4. `package-contract` builds the wheel and source distribution once, validates
   wheel metadata and PEP 561, runs Twine metadata validation, and type-checks a
   downstream consumer installed from the wheel.

Every job has a timeout, read-only permissions, immutable action pins,
credential-free checkout, a pinned `uv` version, and `uv sync --locked` where a
project environment is required. Pull requests may restore caches only within
GitHub's event-scoped cache boundary; release jobs do not use dependency
caches.

### Cross-platform test portability

The tests must not require GNU Make merely to inspect the Makefile contract.
The quality-contract test reads the repository's deliberately small Makefile
syntax directly, expands reachable prerequisites in deterministic depth-first
order, and fails closed on unsupported or ambiguous declarations. This keeps
the same assertions executable on Windows without weakening the Makefile
contract.

### Workflow and dependency hygiene

`.github/workflows/workflow-analysis.yml` runs only when automation-related
files change. It validates workflow semantics with a checksum-verified pinned
actionlint archive and audits workflow security with a pinned zizmor release.
It has no secrets and no write permission.

`.github/workflows/dependency-hygiene.yml` runs monthly and on manual dispatch.
It checks declared dependencies with a pinned deptry release against the locked
environment. It is diagnostic maintenance assurance, not a required
pull-request check.

Dependabot retains weekly Python and GitHub Actions updates and adds a
seven-day cooldown for routine version updates. Security updates remain
governed by GitHub's security-update setting.

### Existing specialized workflows

- Dependency Review remains pull-request-only and blocks newly introduced
  moderate-or-higher vulnerabilities.
- Parser Adversarial Laboratory remains scheduled/manual and uses locked
  dependencies.
- Scorecard remains scheduled and default-branch scoped.
- Daily Metrics remains the only workflow that intentionally persists checkout
  credentials and writes to `main`; its existing threat model remains
  authoritative.
- CodeQL remains GitHub default setup. No advanced `codeql.yml` is added.

### Release

The release graph remains sequential: exact-tag pre-flight, one immutable
build, checksums and supply-chain evidence, GitHub attestations, PyPI Trusted
Publishing, then GitHub Release publication from the same downloaded bundle.
The change pins standard runner images, disables checkout credential
persistence in read-only release jobs, disables dependency caches, and adds
bounded timeouts without changing artifact identity or publication order.

## Security boundaries

- Never use `pull_request_target` for code execution.
- Keep workflow-level permissions read-only and grant write permissions only to
  the exact release, SARIF, attestation, or metrics job that needs them.
- Pin every external action to a full 40-character commit SHA.
- Do not expose repository secrets to pull-request jobs.
- Do not cache credentials, tokens, build artifacts, or mutable source trees.
- Treat hosted green checks as evidence only for the exact commit and runner
  matrix that produced them.

## Documentation

Create `docs/CI_ASSURANCE.md` as the canonical human and AI map of pull-request,
scheduled, settings-managed, and release assurance. Link it from the human and
machine documentation indexes, the contributor guide, and the agent
orientation. Keep `docs/CODEQL.md`, `docs/RELEASE_PROCESS.md`, and the daily
metrics threat model as focused authorities for their respective subsystems.

## Verification and completion

Local source qualification requires:

```text
uv sync --locked --all-extras
make all
make vendor-name-check
actionlint over every workflow
zizmor offline workflow audit
deptry declaration audit
wheel/sdist build, wheel contract, Twine check, and downstream Mypy check
clean Git status
```

Local qualification does not prove Windows, Linux, hosted CodeQL, repository
settings, or release publication. After a pull request is opened, all hosted
matrix and security checks must pass on its exact head before ruleset changes or
merge. CodeQL default setup, secret scanning, push protection, and required
checks must be verified live through GitHub settings after authentication.

## Explicit non-goals

- No self-hosted or larger runners.
- No custom CodeQL advanced workflow.
- No release tag or package publication.
- No reduction of the 80% coverage floor.
- No changes to parser, graph, writer, or public API behavior.
