# v1.8.2 path and documentation checkpoint — 2026-08-25

This handoff records a restart checkpoint. It is not a release, publication, or
static-analysis qualification receipt.

The static-analysis pilot portion of this checkpoint continued on 2026-08-26.
Its implemented state and CCP bootstrap are now governed by the
[`static analysis and CCP integration record`](../quality/STATIC_ANALYSIS_AND_CCP_INTEGRATION_2026-08-26.md).

## Safe resume point

- Repository: `/Users/marco1/Documents/CODICE con VS CODE/logseq-matryca-parser`
- Additional worktree: none
- Branch: `fix/v1.8.2-path-docs`
- Saved implementation HEAD: `7b1061f50c2ea96b0e40ec87455d05c452ec3edd`
- Base and last observed `origin/main`:
  `b35f5d15952d7338f08abb37fdce94f256d3e4d9`
- Remote feature branch: not published at this checkpoint
- Pull request: none
- Working tree before this handoff was added: clean

Re-verify every anchor live after a restart. The commit containing this handoff
will necessarily postdate the saved implementation HEAD above.

## Completed and terminally verified

- `LogseqGraph.load_directory` accepts `pathlib.Path` and string graph roots.
- Runtime and downstream typing coverage exercise both accepted path forms.
- Human and agent documentation now matches the implemented CLI commands,
  default `scan` behavior, write side effects, graph model, parser finalization,
  and current contributor entry points.
- The architecture documentation contains updated high-level data-flow and
  parser-finalization Mermaid diagrams.
- A delegated read-only documentation review identified four bounded accuracy
  findings; all four were corrected before the implementation commit.
- Final `make all` passed with 763 tests and 91.20% coverage, including Ruff,
  Mypy, documentation validation, and the local vendor-name policy check.
- A clean final wheel and source distribution passed the wheel contract,
  `twine check`, and strict downstream Mypy against the built wheel.
- Local structural analysis reported zero import cycles. Its revision-specific
  index was treated as orientation only; live source and exact-run gates were
  authoritative.

## Saved but not yet published or released

- Commit `7b1061f50c2ea96b0e40ec87455d05c452ec3edd` is local only.
- The package version remains `1.8.1`; the new work is recorded under
  `Unreleased` and is a candidate for v1.8.2.
- No push, pull request, merge, tag, GitHub release, or package publication has
  been performed for this branch.

## Current static-analysis study

- Scope: compare suitable static-analysis tools for this Python repository,
  including correctness, typing, security, architecture, dependency hygiene,
  dead code, complexity, documentation, and supply-chain coverage.
- Current state: the research is complete and synthesized in
  [`../quality/STATIC_ANALYSIS_EVALUATION_2026-08-25.md`](../quality/STATIC_ANALYSIS_EVALUATION_2026-08-25.md).
- Measured pilot evidence:
  [`../quality/STATIC_ANALYSIS_PILOT_RESULTS_2026-08-26.md`](../quality/STATIC_ANALYSIS_PILOT_RESULTS_2026-08-26.md).
- Persistent execution pointer:
  [`../goals/STATIC_ANALYSIS_ADOPTION_GOAL.md`](../goals/STATIC_ANALYSIS_ADOPTION_GOAL.md).
- Delegation: four independent read-only Luna tranches covered Python analysis,
  security and supply chain, documentation and repository files, and a local
  gap inventory. The primary review reconciled disagreements and retained only
  non-overlapping, evidence-led recommendations.
- Approved pilot tranche: `actionlint`, offline `zizmor`, and `deptry`; followed
  only after a separate decision by a bounded Ruff/Mypy strictness audit and an
  architecture-gate proof of concept.
- Pilot anchor: clean branch `fix/v1.8.2-path-docs` at
  `1deebea5ed74969b3a3673cc45c29d849ea524bb`.
- `actionlint` 1.7.12 completed twice against the tracked workflows with no
  findings. The official macOS arm64 archive checksum and GitHub artifact
  attestation verified before execution. The command completed effectively
  instantaneously. ShellCheck was not installed, so the optional inline-shell
  integration was outside this pilot.
- Offline `zizmor` 1.29.0 completed twice with stable results in about 0.24
  seconds: 11 findings across `artipacked` (6), `cache-poisoning` (2),
  `dependabot-cooldown` (2), and `superfluous-actions` (1). No token was exposed,
  no online audit ran, and no repository configuration or ignore file was used.
- The six checkout findings split into five useful hardening candidates and one
  intentional credential-persistence requirement in `daily-metrics.yml`, whose
  job commits and pushes archived metrics. The two release-workflow cache
  findings are credible release-hardening defects because the tag-triggered
  pre-flight and build jobs consume shared dependency caches before producing
  publication artifacts. The Dependabot cooldown findings are useful
  supply-chain hardening; GitHub documents that cooldown affects version updates
  but not security updates. Replacing the pinned release action with the runner's
  `gh` CLI is an informational dependency-reduction option, not an urgent defect.
- `deptry` 0.25.1 completed two identical baseline scans. Each scanned 34 files
  in 0.36 seconds and produced the same 62 findings: 60 `DEP004` artifacts from
  the project's development-group self-reference and two `DEP001` findings in
  historical `legacy/` code. Two additional runs with only a rule-scoped
  first-party exception and the existing legacy boundary produced identical
  empty JSON outputs in 0.86 and 0.35 seconds. The project manifest and lockfile
  digests remained unchanged.
- The completed pilot synthesis passed `make all`: Ruff, Mypy across 78 source
  files, vendor-name and maintained-documentation checks, and 763 tests at
  91.20% coverage.
- Installation state: temporary, isolated pilot artifacts only. No dependency,
  lock, configuration, workflow, pre-commit, global tool, or project virtual
  environment was changed.
- Policy: standard permissively licensed open-source linters may be considered
  for repository integration. Restricted or experimental graph indexers remain
  local-only Ghost Tooling and must not be named in public artifacts.

## Exact resume sequence

1. Run `rtk git status --short --branch`, `rtk git rev-parse HEAD`, and
   `rtk git rev-parse origin/main`.
2. Read `AGENTS.md`, `docs/internal/STATIC_ANALYSIS_POLICY.md`, this handoff,
   the static-analysis evaluation, and the persistent adoption goal.
3. Confirm that no worker or heavy process is still active.
4. Review the complete pilot results and choose separately whether to design an
   `actionlint` gate, remediate and baseline `zizmor`, or introduce a periodic
   non-blocking `deptry` audit.
5. Treat dependency edits, tracked configuration, CI mutation, push, PR, merge,
   and release as separate approval gates.
6. After an approved integration, run targeted checks first and `make all`
   before claiming integration success.

## Boundaries that must survive the restart

- Do not install, download, configure, or enable a new tool without maintainer
  approval of its exact scope and integration tier.
- Do not add restricted or experimental indexers to dependencies, CI,
  Dockerfiles, public configuration, or public naming.
- Do not weaken Ruff, Mypy, coverage, documentation, package, or supply-chain
  gates to accommodate a new tool.
- Do not publish or release the v1.8.2 candidate without fresh exact-head
  verification and separate authorization.
- Do not treat a tool's green output as proof outside its documented rule set,
  platform, revision, and configuration.
