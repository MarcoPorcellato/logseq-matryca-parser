---
type: StaticAnalysisEvaluation
title: Static analysis evaluation and adoption plan
description: Evidence-based comparison of static analysis coverage, gaps, candidates, and approval gates.
status: stable
classification: canonical
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

# Static analysis evaluation and adoption plan

## Decision summary

Logseq Matryca Parser already has a strong quality baseline. The next step
should be a small, evidence-led expansion rather than a collection of
overlapping linters.

The first three advisory pilots are complete. Their exact-revision evidence,
finding classifications, runtime observations, and integration gates are in the
[`static analysis pilot results`](STATIC_ANALYSIS_PILOT_RESULTS_2026-08-26.md).
The resulting order was:

1. design a bounded blocking integration for the clean `actionlint` baseline;
2. remediate and document the offline `zizmor` baseline before considering a
   blocking gate;
3. consider `deptry` first as a periodic non-blocking audit with two narrow,
   measured scope rules;
4. strengthen the existing Ruff and Mypy configurations in bounded slices;
5. test whether Import Linter earns a tracked architecture gate;
6. consider ShellCheck and a periodic external-link check as smaller follow-up
   improvements.

The first three steps are now implemented under the
[`static analysis and CCP integration record`](STATIC_ANALYSIS_AND_CCP_INTEGRATION_2026-08-26.md).
Every later pilot must record findings, false positives, runtime, configuration,
license, installation source, and overlap before it can become a blocking gate.
Installation, dependency changes, pre-commit integration, CI integration, and
publication are separate maintainer decisions.

## Evidence boundary

This evaluation is bound to:

- repository branch `fix/v1.8.2-path-docs`;
- implementation anchor
  `7b1061f50c2ea96b0e40ec87455d05c452ec3edd`;
- last observed `origin/main`
  `b35f5d15952d7338f08abb37fdce94f256d3e4d9`;
- source and workflow inspection on 2026-08-25;
- advisory pilots on exact source commit
  `1deebea5ed74969b3a3673cc45c29d849ea524bb` from 2026-08-25 through
  2026-08-26;
- four independent, read-only delegated research tranches covering Python
  analysis, security and supply chain, documentation and repository files, and
  repository-specific coverage gaps;
- official project documentation, official repositories, package registries,
  and GitHub documentation for external tool facts.

Version observations are discovery evidence, not installation pins. Recheck
the current release, complete license text, artifact provenance, checksums, and
platform support immediately before approving any installation.

## Current baseline

| Area | Current gate | Assessment |
|---|---|---|
| Python linting | Ruff with `E`, `F`, `I`, `UP`, `B`, and `SIM` | Fast and reliable, but the selected rule families are intentionally narrow and `scripts/` is excluded. |
| Typing | Mypy across package, tests, examples, and selected scripts | Strong baseline; repository sources are not yet checked with strict mode. The built-wheel public API has a separate strict downstream check. |
| Tests | Pytest with an 80% coverage floor | Broad semantic coverage, including parser adversarial cases, deep outlines, graph concurrency, writer confinement, packaging, and documentation contracts. |
| Architecture | Project-owned layer-boundary tests and local graph-based audit code | Direct forbidden imports are tracked. The documented zero-cycle expectation is not a portable tracked gate. |
| Dependency security | `pip-audit` plus GitHub dependency review | Strong Python vulnerability coverage for production exports and changed runtime/development dependencies. |
| Hosted SAST | GitHub CodeQL default setup | Appropriate low-maintenance semantic SAST. Its hosted state and exact run remain external evidence, not a local source claim. |
| Supply chain | Lock, SBOM, license inventory, checksums, attestations, Scorecard, wheel and Twine checks | Strong release and repository-governance evidence. |
| Documentation | Project-owned metadata, freshness, local-link, anchor, containment, and canonical-role validator | Strong repository semantics for the maintained allowlist; it intentionally does not check external link availability or prose style. |
| Workflow policy | SHA pinning and quality-contract tests | Strong policy coverage, but no semantic GitHub Actions parser currently runs in the tracked gate. |
| Shell | Tests for relevant Python automation; no ShellCheck | Three tracked shell scripts have no dedicated shell static analysis. |

The parser's highest-risk properties remain semantic: outline and identity
preservation, vault containment, symlink behavior, atomic writes, graph snapshot
coherence, and parse/serialize round trips. Generic static analysis cannot prove
these properties and must not replace their focused tests.

## Highest-value gaps

1. **Workflow semantics and workflow-specific security.** YAML parsing and
   string-based contract tests do not fully validate expressions, action
   inputs, shell fragments, permission use, template injection, or credential
   persistence.
2. **Declared dependency correctness.** Vulnerability scanning does not detect
   missing, unused, transitive, or development/runtime-misclassified
   dependencies, especially across optional extras.
3. **Portable architecture enforcement.** Direct import strings are tested,
   but indirect layer relationships and the zero-cycle expectation are not
   represented by one portable tracked gate.
4. **Incremental type and rule strictness.** Ruff and Mypy can provide more
   signal without adding a second broad linter or type checker, but the rollout
   must be measured to avoid suppressions and optional-adapter noise.
5. **Support-surface coverage.** Ruff excludes `scripts/`; selected scripts are
   typed, shell scripts are not statically checked, and external documentation
   links are not availability-checked.

Two adjacent package-contract gaps were also observed but belong to a separate
implementation decision: CI does not request `uv sync --locked`, and the custom
package contract validates the wheel but not an explicit source-distribution
allowlist/install smoke test.

## Candidate evaluation

### Recommended pilots

| Candidate | Unique value | Overlap and burden | Proposed tier |
|---|---|---|---|
| [`actionlint`](https://github.com/rhysd/actionlint) | Semantic GitHub Actions checks for expressions, inputs, outputs, shell blocks, action metadata, and common injection risks. | Two deterministic runs were clean and effectively instantaneous. Complements `zizmor`; does not replace repository policy tests. ShellCheck integration remains unmeasured. | **Ready for a separately approved local and blocking-CI design.** |
| [`zizmor`](https://docs.zizmor.sh/) | Workflow-security analysis for permissions, template injection, credential persistence, unpinned references, and related GitHub Actions risks. | Two offline runs produced the same 11 findings. Five checkout changes, two release-cache changes, two cooldown settings, one metrics exception, and one optional release-action migration require distinct treatment. | **Remediate and document the baseline before proposing a blocking gate.** |
| [`deptry`](https://deptry.com/) | Detects missing, unused, transitive, and development/runtime dependency mistakes; supports PEP 621 and uv projects. | The no-config baseline produced 60 self-reference artifacts and two legacy-only findings. Two narrow scope rules produced a deterministic clean result in under one second. Upstream remains classified Alpha. | **Periodic non-blocking audit first; do not promote yet.** |
| [Import Linter](https://import-linter.readthedocs.io/en/stable/) | Declarative forbidden, layered, independence, and protected import contracts, including indirect relationships. | Partly overlaps project-owned boundary tests. Contract design must follow the maintained flat-module architecture and must not create a second architectural truth. | **Proof of concept; tracked gate only if it replaces or materially strengthens existing tests.** |
| [ShellCheck](https://github.com/koalaman/shellcheck) | Shell syntax, quoting, expansion, portability, and control-flow defects in tracked shell scripts. | Small target surface; actionlint can use ShellCheck for inline workflow shell but does not cover every external script by itself. GPL tool usage requires an explicit policy decision even though it is not shipped with the package. | **Small follow-up pilot; local and CI if clean.** |

### Improve existing tools before adding substitutes

| Existing tool | Proposed change | Adoption rule |
|---|---|---|
| [Ruff](https://docs.astral.sh/ruff/rules/) | Audit high-signal families such as `RUF`, `PTH`, `RET`, `ASYNC`, and selected security rules. Consider bringing maintained scripts into scope. | Enable one family or bounded subset at a time. Prefer Ruff security rules before adding Bandit. Do not blanket-ignore findings. |
| [Mypy](https://mypy.readthedocs.io/en/stable/existing_code.html) | Phase stricter settings through stable core parser and graph modules, then adapters and operational code. | Start with an exact module allowlist and zero new errors. Do not turn optional integration boundaries into broad `Any` or ignore regions. |
| Project-owned architecture tests | Express the zero-cycle and indirect-boundary expectations portably, either with a small standard-library check or an admitted Import Linter configuration. | Keep one source of architectural truth and retain the local graph-based audit as non-public, revision-specific maintainer evidence. |

### Periodic or non-blocking candidates

| Candidate | Appropriate use | Reason not to block pull requests now |
|---|---|---|
| [`lychee`](https://github.com/lycheeverse/lychee) | Scheduled external-link audit that complements the local deterministic documentation checker. | Network availability, redirects, and rate limits can create unrelated failures. |
| [`vulture`](https://pypi.org/project/vulture/) | High-confidence, reviewed dead-code inventory. | Typer entry points, optional adapters, `__all__`, and dynamic imports can create false positives; never automate deletion. |
| [Gitleaks](https://github.com/gitleaks/gitleaks) | Bounded local or periodic diff/history scan after a baseline and license review. | Hashes, action pins, UUIDs, fixtures, and documentation may require careful allowlisting. |
| [`codespell`](https://github.com/codespell-project/codespell) | Non-blocking spelling audit after creating a Matryca/Logseq technical dictionary. | Domain terminology creates predictable noise; it does not validate technical truth. |
| [Vale](https://vale.sh/) | Optional editorial consistency review after adopting a prose style policy. | High policy and vocabulary burden; findings are often subjective. |

### Retain, defer, or reject

| Candidate | Decision | Reason |
|---|---|---|
| GitHub [CodeQL default setup](https://docs.github.com/en/code-security/concepts/code-scanning/setup-types) | **Retain.** | Appropriate hosted SAST with less maintenance than advanced setup. Move to advanced setup only for justified custom queries or models. |
| `pip-audit`, dependency review, Scorecard, SBOM and attestations | **Retain.** | They already cover vulnerability, changed-dependency, repository-governance, and release-provenance responsibilities. |
| Bandit | **Defer.** | Pilot Ruff's security rules first. Add Bandit only if a measured rule-class gap remains. |
| Pyright, basedpyright, Pyrefly, or `ty` | **Defer as blocking gates.** | A second type engine adds configuration and diagnostic duplication before strict Mypy has been phased in. A bounded shadow comparison may be useful later. |
| Pylint | **Defer.** | High overlap with Ruff and Mypy, higher configuration/runtime burden, and no demonstrated unique repository gap. |
| `check-jsonschema` and `yamllint` | **Defer.** | `actionlint` is the stronger first semantic gate for workflows. Reconsider schema validation for issue forms or Dependabot only after a concrete gap is demonstrated. |
| Markdown style linters | **Defer.** | One hundred heterogeneous Markdown files would create substantial stylistic churn without improving the maintained metadata and link contract. |
| Radon and Xenon | **Defer.** | Complexity thresholds are subjective, compatibility evidence is weaker, and the parser already uses deterministic work-growth tests for critical behavior. |
| OSV-Scanner | **Defer.** | It currently duplicates Python coverage from `pip-audit`, dependency review, and locked SBOM evidence. Reconsider for a genuine multi-ecosystem artifact. |
| Semgrep Community rules | **No repository integration without separate legal and hosted-boundary review.** | The engine and maintained rule collections have different license terms; the standard registry path would add unresolved legal and service boundaries. |
| Hadolint and container scanners | **Reject for current scope.** | The repository does not ship a Dockerfile or container image. |

## Proposed adoption protocol

For each approved candidate:

1. re-verify the exact release, full license, platform artifact, checksum or
   immutable source, and maintenance status;
2. install only in an isolated, reviewable context at a pinned version;
3. run an advisory baseline against an exact clean commit;
4. classify every finding as defect, useful hardening, accepted exception,
   duplicate, false positive, or unknown;
5. record elapsed time, output stability, network access, files scanned, and
   configuration required;
6. prefer an existing tool or project-owned deterministic check when it covers
   the same rule class with less burden;
7. add focused tests for any behavior changed because of a finding;
8. promote to local development, pre-commit, blocking CI, or periodic audit
   only after explicit maintainer approval;
9. pin dependencies and workflow actions according to repository policy;
10. run the full repository and package gates before publication.

### Acceptance criteria for a blocking gate

- The tool covers a documented gap not already enforced elsewhere.
- Its license and distribution path are compatible with repository policy.
- It has no unreviewed network, upload, token, or hosted-service requirement.
- It runs on the supported Python/platform matrix where relevant.
- Its findings are deterministic for the same source and configuration.
- All baseline findings are fixed or narrowly documented; no broad suppressions
  are introduced.
- Runtime remains proportionate to the pull-request gate.
- Failure output is actionable for a first-time contributor.
- The tool, version, purpose, local command, CI command, and update procedure are
  documented.

## Measured pilot outcome

The approved pilots are complete. In summary:

- `actionlint` 1.7.12: zero findings across two runs;
- offline `zizmor` 1.29.0: 11 stable findings requiring remediation or a
  narrow documented exception;
- `deptry` 0.25.1: 62 baseline findings, all explained by the project
  self-reference and historical `legacy/` scope; zero findings across two runs
  with the minimum two scope rules.

See the
[`full pilot evidence and classifications`](STATIC_ANALYSIS_PILOT_RESULTS_2026-08-26.md)
and the subsequent
[`integration record`](STATIC_ANALYSIS_AND_CCP_INTEGRATION_2026-08-26.md).

## Explicit unknowns

- The exact strict-Mypy error volume and expanded-Ruff finding volume are
  unknown.
- Release-workflow runtime cost without shared caches remains unmeasured; the
  post-remediation offline `zizmor` baseline is clean with two localized,
  documented exceptions.
- `deptry` behavior across the full supported Python matrix and its long-term
  maintenance cost remain unmeasured.
- The final Import Linter contract design and whether it earns its maintenance
  cost remain unknown.
- Hosted CodeQL settings and successful runs are GitHub-side facts that must be
  checked live for the exact candidate commit.
- External-link reliability and secret-scanner baseline noise are unmeasured.

## Maintainer decision checklist

- [x] Approve and complete a read-only local pilot of `actionlint`.
- [x] Approve and complete a read-only offline pilot of `zizmor`.
- [x] Approve and complete a read-only local pilot of `deptry`.
- [x] Approve and integrate actionlint, remediate and baseline offline zizmor,
      and schedule deptry with the two measured scope rules.
- [x] Approve a CCP matrix bootstrap for staged GitHub Actions savings without
      activating hosted-job skipping.
- [ ] Approve a bounded Ruff rule-family and Mypy strictness audit.
- [ ] Approve an Import Linter proof of concept or choose a project-owned
      standard-library architecture check instead.
- [ ] Approve ShellCheck and periodic link-checking follow-ups.
- [x] Select the first integration tiers without adding Python analyzers to the
      project dependency lock.

The completed boxes cover only the recorded pilot and first integration
tranche. The remaining boxes authorize no additional dependency, tool tier,
workflow routing, push, pull request, merge, or release change.
