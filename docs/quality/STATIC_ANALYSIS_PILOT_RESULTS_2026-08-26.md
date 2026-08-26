---
type: StaticAnalysisPilotResults
title: Static analysis pilot results
description: Exact-revision evidence and dispositions for the actionlint, zizmor, and deptry advisory pilots.
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

# Static analysis pilot results

## Decision summary

The commands for three maintainer-approved advisory pilots completed without
changing a dependency declaration, lockfile, project environment, workflow,
pre-commit configuration, or tracked source file.

| Candidate | Baseline result | Disposition |
|---|---|---|
| `actionlint` 1.7.12 | Two clean and deterministic runs | **Ready for a separately approved blocking-gate integration.** |
| `zizmor` 1.29.0 offline | Eleven deterministic findings requiring four distinct dispositions | **High value, but not baseline-clean. Remediate or document every finding before integration.** |
| `deptry` 0.25.1 | Sixty-two deterministic baseline findings; zero after two narrow, explained scope rules | **Adopt only as a periodic non-blocking audit first. Reconsider blocking status after repository and upstream experience.** |

The maintainer subsequently approved the three recommendations and a CCP
bootstrap. The resulting tracked implementation is documented in the
[`static analysis and CCP integration record`](STATIC_ANALYSIS_AND_CCP_INTEGRATION_2026-08-26.md).
Push, pull request, merge, hosted-CI routing, receipt publication, and release
remain separate maintainer gates.

## Evidence boundary

- Repository branch: `fix/v1.8.2-path-docs`.
- Pilot source commit:
  `1deebea5ed74969b3a3673cc45c29d849ea524bb`.
- Last observed `origin/main`:
  `b35f5d15952d7338f08abb37fdce94f256d3e4d9`.
- Host used for the local observations: macOS on arm64.
- Pilot dates: 2026-08-25 through 2026-08-26.
- Every candidate ran from isolated temporary storage. Network access was used
  only to obtain the pinned candidate artifact; analysis itself was local, and
  the `zizmor` and `deptry` measured runs were explicitly offline.
- Repeated JSON outputs were compared where supported. Runtime values are local
  observations, not cross-platform budgets.

The source commit was clean before the first pilot. During the final pilot, the
only tracked modification was this study's previously reviewed restart
checkpoint. The project manifest and lockfile retained their pre-pilot SHA-256
digests throughout:

- `pyproject.toml`:
  `8232425a87bb8606532faf0798262bff9df02f59847b80e5d562e4acc6567247`;
- `uv.lock`:
  `6ba1dd9c9d2ee9e3650b11d55d835db0da7a5ad8c30b757214d5d26d9d3010a9`.

## Artifact and execution evidence

| Candidate | Verified distribution evidence | Execution boundary |
|---|---|---|
| `actionlint` 1.7.12 | Official macOS arm64 release archive; SHA-256 `aba9ced2dee8d27fecca3dc7feb1a7f9a52caefa1eb46f3271ea66b6e0e6953f`; GitHub artifact attestation verified; MIT license | Release binary executed locally twice with no repository configuration. ShellCheck was absent. |
| `zizmor` 1.29.0 | PyPI macOS arm64 wheel; SHA-256 `5aafe617d7b1e0c0c15d58fdf20495f360f74a791dfa136f76630b4cc06c2a34`; Trusted Publishing; MIT license | Pinned ephemeral environment, tokens unset, offline mode, strict collection, no configuration or ignore file. |
| `deptry` 0.25.1 | PyPI CPython abi3 macOS arm64 wheel; SHA-256 `c67c666d916ef12013c0772e40d78be0f21577a495d8d99ec5fcb18c332d393d`; Trusted Publishing; MIT license; upstream maturity classifier `Alpha` | Pinned ephemeral overlay on the existing Python 3.13.2 project environment; locked and offline measured runs; no tracked configuration. |

The external distribution facts above were rechecked against the official
[`actionlint` releases](https://github.com/rhysd/actionlint/releases),
[`zizmor` PyPI record](https://pypi.org/project/zizmor/1.29.0/), and
[`deptry` PyPI record](https://pypi.org/project/deptry/0.25.1/) immediately before
the pilots.

## `actionlint` result

Both repository-wide runs completed with no findings and stable output. The
observed runtime was effectively instantaneous for this workflow set.

### Classification

- **Unique signal:** GitHub Actions expression, event, input, output, and workflow
  semantic validation not provided by the repository's string-based policy
  tests.
- **Noise:** none observed.
- **Limitation:** ShellCheck was not present, so the optional deeper analysis of
  inline shell fragments was not exercised.
- **Recommendation:** propose a pinned local and blocking-CI integration in its
  own reviewable change. Preserve the existing workflow policy tests because
  they enforce repository-specific contracts outside `actionlint`'s scope.

## Offline `zizmor` result

Two identical scans completed in approximately 0.24 seconds each. Both reported
the same 11 findings:

| Audit | Count | Tool severity/confidence | Repository disposition |
|---|---:|---|---|
| `artipacked` | 6 | Medium / Low | Five useful hardening changes and one intentional functional exception. |
| `cache-poisoning` | 2 | High / Low | Credible release-hardening defects in the tag-triggered release pre-flight and build jobs. |
| `dependabot-cooldown` | 2 | Medium / High | Useful supply-chain hardening proposal for the pip and GitHub Actions updaters. |
| `superfluous-actions` | 1 | Informational / High | Optional dependency-reduction change; not a security defect by itself. |

### Finding classification

1. Five checkout steps in `ci.yml`, `parser-adversarial.yml`, and the pre-flight
   and build jobs of `pypi_publish.yml` do not need credentials after checkout.
   Explicitly disabling credential persistence is a useful hardening change.
2. `daily-metrics.yml` must commit and push its bounded metrics archive. Its
   persisted checkout credential is therefore an intentional exception, not a
   candidate for automatic removal. Any future configuration must document the
   exact workflow and reason rather than suppressing the entire audit.
3. The release pre-flight and build jobs enable shared `uv` caches before
   producing the publication bundle. Disabling those caches is the recommended
   release-hardening fix; the performance impact must be measured in the release
   workflow rather than assumed.
4. A seven-day Dependabot cooldown is a reasonable stability and supply-chain
   proposal. GitHub documents that cooldown applies to version updates and does
   not delay security updates. The final duration remains a maintainer policy
   choice.
5. Replacing the pinned release action with the runner's preinstalled `gh` CLI
   could reduce third-party action surface. The current action is SHA-pinned and
   contract-tested, so this is a separate non-urgent migration, not part of the
   minimum security fix.

### Recommendation

Do not add a blocking `zizmor` gate over the current baseline. First review and
implement the five checkout hardening changes, the two release-cache changes,
the two cooldown settings, and the one narrow metrics exception. Re-run offline
with zero unexplained findings before proposing integration.

## `deptry` result

Two no-configuration scans were byte-for-byte identical. Each scanned 34 Python
files in 0.36 seconds and reported:

| Code | Count | Module | Classification |
|---|---:|---|---|
| `DEP004` | 60 | `logseq_matryca_parser` | Configuration artifact: the uv development group references `logseq-matryca-parser[all,watch]`, causing legitimate first-party imports to appear as imports from a development dependency. |
| `DEP001` | 2 | `smart_router` | Historical out-of-scope code under `legacy/`, which is already excluded from maintained lint scope and is not shipped as the package. |

Two additional runs used only the minimum explained scope rules:

- ignore `DEP004` only for the first-party `logseq_matryca_parser` module;
- extend the default exclusion set with `legacy/`.

Both configured outputs were byte-for-byte identical empty JSON arrays. The
first configured run took 0.86 seconds and the warm repeat took 0.35 seconds.
No general error code was disabled, no optional dependency was ignored, and no
maintained source directory was excluded.

### Limitations and recommendation

- The default scan excludes tests, so this result does not prove that every
  development dependency is used correctly.
- The pilot found no missing, unused, or transitive dependency defect in the
  maintained package and support files after the two justified scope rules.
- The upstream project supports PEP 621 and uv, but its published maturity
  classifier remains `Alpha` and this repository needs a self-reference
  exception.

For those reasons, begin with a pinned periodic advisory audit if integration is
approved. Do not make it a pull-request blocker or add it to the package's
runtime dependencies. Promotion requires stable results across the supported
Python matrix, contributor-friendly diagnostics, and an explicit review of the
upstream maturity and update procedure.

## Integration decision gates

The next maintainer decision should be made separately for each candidate:

- [x] Approve a bounded `actionlint` integration design.
- [x] Approve remediation and exception design for the 11 `zizmor` findings.
- [x] Approve a periodic, non-blocking `deptry` integration design with only the
      two measured scope rules.
- [x] Decide whether the three tools remain external pinned executables or any
      Python tool becomes a development dependency.
- [x] Require focused workflow-contract tests for workflow changes and the full
      repository/package gates before publication.

The selected implementation keeps the Python analyzers ephemeral, adds a
commit-pinned local actionlint hook, and binds hosted execution to fixed tool
versions and checksums. See the integration record for the exact boundary and
the still-unapproved savings activation.

## Documentation checkpoint verification

The synthesized documentation passed the complete repository quality gate on
2026-08-26: Ruff, Mypy across 78 source files, the vendor-name policy, the
maintained-documentation validator, and 763 tests at 91.20% coverage. This proves
only the recorded documentation checkout and does not qualify an unimplemented
tool integration or an unexecuted CI platform.
