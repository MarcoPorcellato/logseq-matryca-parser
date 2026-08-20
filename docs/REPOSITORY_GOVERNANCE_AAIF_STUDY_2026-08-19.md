---
type: RepositoryGovernanceStudy
title: GitHub and AAIF repository readiness study
description: Evidence-backed governance, security, documentation, agent-interoperability, and AAIF-readiness study for Logseq Matryca Parser.
status: stable
classification: active
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-08-19
verified: 2026-08-19
stale_after: 2026-11-17
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---

# GitHub and AAIF repository readiness study

> **Decision record:** The repository has a strong technical and documentation
> foundation, but it is not yet ready to present itself as an AAIF project or to
> claim official OKF v0.2 conformance. The next gains come from governance,
> independent security settings, adoption evidence, and a small number of
> machine-enforced contracts—not from adding another parser framework.

## 1. Purpose and falsifiable outcome

This study turns the request to make the repository “stellar” into a reviewable
programme covering:

1. GitHub repository health and contributor experience;
2. branch, review, Actions, dependency, release, and supply-chain controls;
3. documentation authority, freshness, discoverability, and federation;
4. AI-agent context, safe tool boundaries, and interoperability readiness;
5. the public expectations and admission criteria published by the Agentic AI
   Foundation (AAIF);
6. a dependency-ordered implementation plan with evidence gates.

The outcome is considered achieved only when each proposed improvement has a
named owner, a bounded change, an acceptance receipt, and a clear distinction
between repository-local proof and GitHub-hosted proof.

This is a specification and readiness study. It does not authorize repository
settings changes, issue creation, a project submission to AAIF, a release, a
commit, a push, or a pull request.

## 2. Executive verdict

### Current position

| Area | Evidence-backed assessment | Confidence |
|---|---|---:|
| Product and technical identity | Strong: deterministic parser, typed AST, graph, optional adapters, bounded writes | High |
| Human documentation | Strong foundation: README, cookbook, docs portal, release highlights, contributor guide | High |
| Agent discoverability | Strong foundation: `AGENTS.md`, `llms.txt`, package map, explicit safety boundaries | High |
| Local quality and release engineering | Strong in the inspected checkout: pinned Actions, non-mutating CI contract, immutable release bundle, PyPI OIDC history | High for local files; remote settings still separate |
| GitHub community health | Good files are present; branch rules, security settings, and live issue/PR state were not readable in this run | Medium |
| Maintainer governance | Public governance, maintainer, support, ownership, triage, and decision surfaces now exist locally; independent review still requires a second accepted maintainer | High for source files; external practice remains unproved |
| Supply-chain assurance | Dependency review, Scorecard, release SBOM, dependency/license inventory, GitHub attestations, and metrics hardening are implemented and locally tested; hosted PR, schedule, and release receipts remain pending | High for local source; external execution remains unproved |
| Matryca documentation quality | Matryca-v1 passed in the latest federation snapshot; official OKF v0.2 remains a separate migration with 38 parser findings | High for the cited snapshot |
| AAIF readiness | Plausible alignment candidate, not an AAIF project and not yet supported by the adoption/diverse-governance evidence required for Growth or Impact | High |

### Recommended decision

Proceed with a **governance and assurance hardening phase**. Do not submit to
AAIF yet. First establish a public maintainer and decision model, verify GitHub
settings, publish machine-verifiable supply-chain evidence, correct documentation
drift, and collect adoption evidence. Reassess AAIF only after those receipts
exist.

### What “AAIF-ready” means here

AAIF is a foundation and project-governance process, not a universal badge that
can be added to a README. The current AAIF Project Lifecycle Policy asks a
proposal to document the project, mission alignment, related AAIF projects,
use cases and adoption, OSI-approved permissive licensing, public repository,
automated delivery, release mechanics, contribution process, issue tracker,
dependencies and licenses, maintainers, leadership and decision-making,
governance, communication channels, website, sponsorship, and infrastructure.

The policy also states that Growth and Impact admission depends on activity,
community, adoption, maintainership, and Technical Committee judgment. The
repository should therefore use **AAIF-aligned readiness** as the target claim,
not **AAIF membership**, **AAIF certification**, or **official OKF conformance**.

## 3. Evidence envelope and current anchors

### 3.1 Repository checkout inspected

| Anchor | Value | Meaning |
|---|---|---|
| Local branch | `agent/parser-assurance-m1` | Active assurance branch, not `main` |
| Local `HEAD` | `1947251d2df79f37550a40cda3c0c26bb602245f` | Exact committed checkpoint beneath the current Terra and Sol source tranche |
| Published branch head | Historical: `f04f9d2e83a34871a5aceb70197217e6226dbf53` | Last fresh branch readback recorded by this study; not current publication evidence |
| Fresh remote `main` | Historical: `8de6f9a02d00f0a42a4f25ec07b8fb3f25dae7e5` | Last exact public base observed; must be refreshed before integration |
| Local `origin/main` ref | Cached and divergent | `git status` reports the assurance branch ahead 10 and behind 6; this is not a live remote receipt |
| Worktree | intentionally dirty | Terra policy files plus the Sol supply-chain, metrics, release, decision, test, and documentation tranche are under review; no commit claim is made |
| GitHub API/settings | Unknown | `gh auth status` reports an invalid token; no settings claim is made |

The exact local commands were:

```text
rtk git status --short --branch
rtk git rev-parse HEAD
rtk git diff --check
rtk git worktree list --porcelain
```

The initial study probe failed because `github.com` could not be resolved. A
later authorized push and readback succeeded for an earlier feature-branch
checkpoint, while GitHub CLI API reads still reported an invalid token. That
historical publication does not cover the current worktree. Repository
settings, rulesets, security toggles, issues, projects, pull requests, and the
current branch head remain unverified until a fresh readback succeeds.

### 3.2 Matryca Knowledge evidence

The Matryca Knowledge implementation used for the final local audit is on
branch `codex-deepseek-harness-study-20260819` at
`63a3162ca5cbc1110e7e95be38c97de992ce597d`; its checkout is dirty and its
local branch is 14 commits behind its tracking branch. Its current working-tree
`sources.toml` contains the parser's maintained entry points, but that local
state is not a clean federation receipt. The dated federation audit at
`docs/FEDERATED_DOCUMENTATION_AUDIT_2026-08-19.md` records the latest exact
source snapshot used by the coordination plane:

| Parser federation result | Evidence |
|---|---|
| Exact parser source audited | `27d006153e45f2c4ae37ca03136114fb8246ac88` |
| Matryca-v1 profile | Conformant, 0 findings |
| Official OKF v0.2 profile | Nonconformant, 38 findings |
| Federation-wide official OKF findings | 577 across six sources |
| Source authority | Parser repository; `knowledge/` is a generated reviewed projection |

A read-only dual-profile rerun on 2026-08-19 against the current parser
worktree, explicitly labeled
`worktree-1947251d2df79f37550a40cda3c0c26bb602245f-dirty-sol-final`, inspected 64
Markdown documents. It preserved the same official result: nonconformant with
38 findings (35 invalid/missing concept frontmatters, two forbidden nested-index
frontmatters, and one invalid root-index version), while the declared
Matryca-v1 profile remained conformant with zero findings. Because the parser
worktree and the Matryca coordination checkout were not both clean immutable
commits, this rerun is local migration evidence, not federation publication or
official conformance proof.

This corrects an important documentation hazard in older parser documents:
some still cite the older Matryca Knowledge revision `7a3ebd8` and say that the
parser entry points are not declared. The latest local coordination evidence
shows that entry-point declaration has been added. It does not, by itself,
prove that the current public parser `main` or the next projection refresh has
been re-audited.

### 3.3 Evidence vocabulary

Every future milestone in this study uses the following vocabulary:

| Term | Meaning |
|---|---|
| **Verified** | Proved against the exact named commit, workflow run, artifact, or GitHub API response |
| **Historical** | True for an older revision or run, but not current-state evidence |
| **Proposed** | A recommendation not yet implemented or qualified |
| **Unknown** | The relevant evidence was unavailable or too weak to support a claim |
| **Blocked** | The work cannot proceed without a named external decision or resource |
| **Ready** | All applicable acceptance evidence exists; it is not the same as merged or released |

## 4. Scope, non-goals, and invariants

### In scope

- Repository metadata, community files, contribution paths, and discoverability.
- GitHub branch/ruleset, review, Actions, security, issue, project, and release
  controls.
- Python package distribution, provenance, dependency and license visibility.
- Human and AI documentation, including the AAIF-stewarded `AGENTS.md` format.
- Agent-read/write safety, model-neutral integration boundaries, and future MCP
  or A2A interoperability decisions.
- Maintainer diversity, decision transparency, adoption evidence, and AAIF
  proposal readiness.

### Non-goals

- No parser rewrite, database, search-engine, GUI, plugin registry, or model
  orchestration in the core package.
- No forced MCP or A2A dependency merely to appear aligned with AAIF.
- No claim that an OpenSSF badge, AAIF stage, or official OKF status exists
  without the corresponding external receipt.
- No mass rewrite of historical documentation or imported Matryca projection.
- No changes to GitHub settings or remote project metadata in this study.

### Product invariants that every improvement must preserve

- Markdown files remain the source of truth.
- Parser output remains deterministic for the same input and configuration.
- UUIDs, tree order, parent/left pointers, line ranges, properties, references,
  and parse/serialize round trips remain stable unless a separately reviewed
  compatibility decision says otherwise.
- Vault containment, symlink handling, asset paths, target identity, atomic
  replacement, dry-run behavior, and bounded writes remain security boundaries.
- Optional AI, watcher, and visualization integrations stay lazy and do not make
  the base parser heavy or model-dependent.
- Generated projections, metrics, audit indexes, and agent state remain derived
  artifacts and never become a second source of truth.

## 5. Local repository inventory

### 5.1 Strong existing surfaces

| Surface | Current evidence | Keep / improve |
|---|---|---|
| Human entry point | `README.md`, quickstart, capability map, release-history link | Keep concise; remove stale metrics and unsupported comparative claims |
| Maintained docs portal | `docs/index.md`, `docs/README.md`, `docs/DOCUMENTATION_SYSTEM.md` | Keep as the source-owned navigation model |
| Agent entry point | Root `AGENTS.md` with product map, commands, safety, and hub rules | Keep; add explicit authority, scope, and safe escalation semantics if needed |
| LLM discovery | `llms.txt` with raw GitHub links and capability map | Keep as an optional discovery index; do not treat it as an enforcement standard |
| Contribution path | `CONTRIBUTING.md`, issue forms, PR template, good-first-issue catalogue | Add governance, AI contribution disclosure, support expectations, and a triage policy |
| Safety path | `SECURITY.md`, CodeQL documentation, filesystem safety reference, metrics threat model | Verify remote security features and hosted workflow execution |
| Release path | `CHANGELOG.md`, `RELEASE_HIGHLIGHTS.md`, release process, pinned workflow, local SBOM/inventory/attestation contract | Qualify the new evidence on a real exact-tag run |
| License and notices | Apache-2.0 `LICENSE`, root `NOTICE`, package notice, version-exact override policy, generated inventory | Review the real release inventory and preserve legal review as a human gate |
| Ownership | `.github/CODEOWNERS` | Split ownership by security, release, parser, graph, and docs when a second maintainer exists |
| Automation | CI, package contract, release, Dependabot, dependency review, Scorecard, hardened daily metrics | Collect hosted receipts and verify remote token/settings boundaries |

### 5.2 Current documentation and governance boundaries

| Boundary | Current local evidence | Remaining work |
|---|---|---|
| Governance, maintainer, support, citation, and AI policy | Public source files now exist and are linked from contribution/documentation entry points | Establish an independent maintainer before requiring a second approval |
| Agent authority and interoperability | Action contract, AAIF alignment page, support matrix, and protocol-adapter ADR are source-owned documents | Any networked protocol needs the separate schema, threat-model, permission, and conformance gates |
| Ownership | `.github/CODEOWNERS` now maps governance, delivery, product, and documentation paths to the current maintainer | Add a second owner only after that person accepts the role; do not claim independent review enforcement before then |
| Community process | Public roadmap, issue triage policy, label manifest, issue routing, and PR template now describe the intended workflow | Synchronize labels and measure activity only after authenticated GitHub readback |
| GitHub settings | Branch rules, security toggles, discussions, projects, and rulesets remain remote state | P0 receipt still required; local files cannot prove a setting |
| Official OKF v0.2 migration | Matryca audit records 38 parser findings | Separate reviewed source/profile/projection migration |
| Federation references | `docs/reference/index.md` now records current local entry-point evidence | Projection refresh and current public-source audit remain separate evidence gates |

The absence of a file is a local fact. The absence of a remote setting is not
claimed until the GitHub API or settings UI is read successfully.

## 6. GitHub best-practice benchmark

### 6.1 Official GitHub baseline

GitHub's repository guidance treats a README, license, citation file,
contribution guidelines, and code of conduct as the human contract. It also
recommends Dependabot alerts, secret scanning, push protection, and code
scanning as the minimum public-repository security baseline. Its pull-request
guidance recommends templates, CODEOWNERS, protected branches or rulesets, and
automated checks.

Primary sources:

- [GitHub repository best practices](https://docs.github.com/en/repositories/creating-and-managing-repositories/best-practices-for-repositories)
- [GitHub community health files](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file)
- [Standardizing pull requests](https://docs.github.com/en/pull-requests/reference/managing-and-standardizing-pull-requests)
- [Code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
- [Protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches)

The repository already covers most file-level expectations. The main missing
piece is not another template: it is the public decision and maintainer model
behind those templates.

### 6.2 Security and Actions baseline

GitHub's secure-use guidance recommends least-privilege `GITHUB_TOKEN`
permissions, full-length commit-SHA pinning for third-party Actions, auditing
action source, and restricting which Actions may run. The inspected workflows
already pin their Actions to full SHAs and declare read-only contents
permissions at workflow level where appropriate. The daily metrics workflow is
different: it intentionally has `contents: write` and a secret-backed token.
That workflow needs a separate threat model and remote policy receipt.

Primary sources:

- [GitHub Actions secure-use reference](https://docs.github.com/en/actions/reference/security/secure-use)
- [GitHub repository Actions settings](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository)
- [GitHub artifact attestations](https://docs.github.com/en/actions/concepts/security/artifact-attestations)
- [Using artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations)
- [OpenSSF Scorecard](https://scorecard.dev/)

### 6.3 Required GitHub readback

The next verification run must collect, without mutation:

```bash
gh auth status
gh repo view MarcoPorcellato/logseq-matryca-parser --json \
  nameWithOwner,defaultBranchRef,visibility,licenseInfo,stargazerCount,forkCount,\
  hasIssuesEnabled,hasProjectsEnabled,hasDiscussionsEnabled,securityPolicyUrl,\
  codeOfConduct,issueTemplates,pullRequestTemplates,repositoryTopics,url
gh api repos/MarcoPorcellato/logseq-matryca-parser/branches/main/protection
gh api repos/MarcoPorcellato/logseq-matryca-parser/rulesets
gh api repos/MarcoPorcellato/logseq-matryca-parser/actions/permissions
gh api repos/MarcoPorcellato/logseq-matryca-parser/vulnerability-alerts
gh api repos/MarcoPorcellato/logseq-matryca-parser/dependabot/alerts
gh api repos/MarcoPorcellato/logseq-matryca-parser/secret-scanning/alerts
gh api repos/MarcoPorcellato/logseq-matryca-parser/code-scanning/alerts
gh issue list --repo MarcoPorcellato/logseq-matryca-parser --state open --limit 100
gh pr list --repo MarcoPorcellato/logseq-matryca-parser --state open --limit 100
gh project list --owner MarcoPorcellato
```

The command list is an acceptance recipe, not evidence that the commands have
passed. A future receipt must record the date, authenticated identity without
tokens, exact `main` SHA, setting response, and any redacted permission errors.

## 7. Prior-art patterns worth adopting

This section uses a small, relevant sample rather than treating star count as a
quality metric. Each pattern is adopted only when it fits this repository.

### AGENTS.md open format

The [AGENTS.md format](https://agents.md/) is stewarded by AAIF and describes a
predictable Markdown place for project context, build commands, testing,
security considerations, and contribution instructions. It explicitly
complements a human README rather than replacing it.

**Already adopted:** root `AGENTS.md`, product map, commands, invariants,
security boundaries, and agent-specific entry points.

**Next improvement:** keep the file short enough to load reliably, state which
documents are authoritative, and add nested guidance only when the repository
gains genuinely separate subsystems. Do not duplicate the entire documentation
portal in it.

### Model Context Protocol Python SDK

The [MCP Python SDK `AGENTS.md`](https://github.com/modelcontextprotocol/python-sdk/blob/main/AGENTS.md)
and [MCP contribution guide](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/CONTRIBUTING.md)
show a useful pattern for an agent-facing protocol library:

- explicit stable and maintenance branch semantics;
- a public API surface and migration documentation;
- a conformance suite tied to upstream specification changes;
- frozen dependency commands that avoid incidental lockfile edits;
- explicit disclosure of AI-assisted contributions;
- documentation and link checks in the same contribution path.

**Adopt:** a compatibility/conformance matrix for parser semantics, a public
AI-assistance disclosure rule, and a versioned support/deprecation table.

**Do not copy blindly:** MCP's protocol release cadence and branch model are
larger than this package needs; use only the contracts that reduce ambiguity.

### AAIF goose

The [goose repository](https://github.com/aaif-goose/goose) is a current AAIF
project. Its public tree exposes `GOVERNANCE.md`, `MAINTAINERS.md`, `SECURITY.md`,
`RELEASE.md`, `RELEASE_CHECKLIST.md`, `ACCEPTABLE_USAGE.md`, and explicit
community channels. Its [governance document](https://github.com/aaif-goose/goose/blob/main/GOVERNANCE.md)
connects maintainership, community responsiveness, releases, and governance
changes.

**Adopt:** a lightweight governance file, named maintainers, release authority,
security escalation, community channel, and release checklist. The repository
does not need goose's application-level acceptable-use policy unless its agent
capabilities expand.

### Kubernetes community model

The [Kubernetes contribution surface](https://github.com/kubernetes/kubernetes/contribute)
and [Kubernetes community repository](https://github.com/kubernetes/community)
show how a large project makes newcomer work discoverable through curated
good-first issues, labels, contributor pathways, and domain-oriented ownership.

**Adopt later:** a triage rotation, area labels, a contributor ladder, and
maintainer groups once more than one active maintainer is available. Do not
create SIG-like bureaucracy before the contributor volume justifies it.

## 8. AAIF alignment assessment

### 8.1 AAIF's published expectations

The [AAIF project submission page](https://aaif.io/submit-a-project/) says a
successful project should be technically strong, broadly useful, healthy
enough to grow beyond one company or maintainer group, useful to agentic
interoperability or reliability, and backed by a realistic 6–12 month roadmap.

The [AAIF Technical Committee Project Lifecycle Policy](https://github.com/aaif/technical-committee/blob/main/governance/project-lifecycle-policy.md)
lists proposal requirements including:

- project history, value, and mission alignment;
- relationship to existing AAIF projects;
- use cases and adoption evidence;
- OSI-approved permissive license and public repository;
- automated validation, release methodology, and public contribution process;
- public issue tracker and dependency-license information;
- maintainers, leadership, decision-making, governance, channels, website,
  sponsorship, and infrastructure needs.

For Growth, the policy additionally expects a Technical Committee sponsor, a
growth plan for diverse maintainership, broad production use, ongoing commits
and merged contributions, and sufficient community participation. Impact adds
industry adoption, multi-organization maintainership, a public roadmap and
release process, and committers from at least two organizations.

### 8.2 Requirement-by-requirement matrix

| AAIF expectation | Current evidence | Readiness | Required next proof |
|---|---|---|---|
| Clear name, history, and value | README, architecture, changelog, release highlights | Present | Keep claims dated and evidence-linked |
| Alignment with AAIF mission | Agent access and agent-readable docs are relevant; no dedicated statement | Partial | Publish a short alignment page without claiming membership |
| Relationship to AAIF projects | `AGENTS.md` alignment; no MCP/A2A integration claim | Partial | Document interoperability boundaries and optional adapters |
| Use cases and adoption | Examples and downstream Matryca references; no independent adoption dossier | Partial | Collect opt-in case studies, downstream links, and usage evidence |
| OSI-approved permissive license | Apache License 2.0 and NOTICE | Present | Add machine-readable license/dependency inventory |
| Public repository | Public GitHub repository | Present, but live API readback pending | Capture exact public-repo receipt |
| Automated validation | CI, package contract, docs gate, release pre-flight | Present locally | Verify required checks and branch rules on current public `main` |
| Release mechanics | `docs/RELEASE_PROCESS.md`, pinned workflow, immutable bundle, PyPI OIDC history | Strong | Add GitHub artifact attestation and SBOM verification |
| Public contribution process | `CONTRIBUTING.md`, templates, good-first issues | Present | Add governance, AI disclosure, support, and triage rules |
| Public issue tracker | GitHub issues configured in repository history | Unknown current setting | GitHub API readback |
| Dependency licenses | `pyproject.toml`, `uv.lock`, optional extras | Partial | Generate and review a release license inventory |
| Core maintainers | CODEOWNERS names Marco only | Incomplete | Add `MAINTAINERS.md` and path ownership; recruit a second maintainer |
| Leadership and decisions | Implicit owner model; no `GOVERNANCE.md` | Incomplete | Publish decision classes, review authority, and maintainer path |
| Communication channels | Homepage and email are present; no clear support/community file | Partial | Add `SUPPORT.md` and a response/support boundary |
| Website and social presence | Links exist in README/repository metadata | Partial | Verify current links and record them in proposal dossier |
| Financial sponsorship | Funding file exists | Present | Record whether sponsorship is active or not applicable |
| Infrastructure needs | Not documented in an AAIF-shaped dossier | Missing | Add a proposal appendix when submission is considered |
| Six-to-twelve-month roadmap | Multiple dated roadmaps and quality backlog | Strong but fragmented | Produce one public milestone view with owners and exit evidence |
| Diverse community | Contributor PRs and good-first issues exist; one CODEOWNER | Partial | Measure contributors, response times, and organizations over time |
| Growth/Impact production adoption | No evidence sufficient for AAIF stage criteria | Not ready | Gather real, permissioned adoption evidence before submission |

### 8.3 AAIF readiness conclusion

The repository is a credible **future Growth candidate only after** governance,
adoption, and maintainer diversity improve. It is not currently supported as an
Impact candidate. The correct near-term action is to make the public project
healthy and interoperable, participate in relevant AAIF communities where
useful, and defer submission until the proposal matrix can be filled with
receipts rather than aspirations.

Joining AAIF would also involve a contribution agreement, transfer of project
trademarks/assets, and adoption of a technical charter. Those are external legal
and governance decisions and must remain a separate approval gate.

## 9. Agent and interoperability readiness

### 9.1 What is already good

- `AGENTS.md` gives multiple agent tools one repository contract.
- `llms.txt` provides a compact discovery surface.
- The source-of-truth model is explicit: Markdown first, derived graph second.
- Agent reads are token-efficient and agent writes are bounded, append-oriented,
  and documented.
- Filesystem containment, dry-run, atomic replacement, limits, and structured
  diagnostics are treated as safety boundaries.
- Optional adapters stay lazy and model-neutral.

### 9.2 What should be added

1. **Agent action contract:** document capabilities as read-only, proposal-only,
   or mutating; state required human approval for each mutation.
2. **Authority and provenance:** every agent-generated result should identify
   source path, source commit where relevant, action type, and whether it was
   applied or merely proposed.
3. **Prompt-injection boundary:** explain that vault Markdown is data, not
   trusted instructions, and require safe handling of embedded links, macros,
   and agent-authored text.
4. **AI contribution policy:** disclose generated or assisted code in issues/PRs,
   require human ownership of correctness, and never upload private vault data
   to obtain a review.
5. **Protocol-neutral interoperability:** publish an adapter table for MCP,
   A2A, LangChain, and LlamaIndex. Add a protocol implementation only when a
   concrete user workflow, security model, and compatibility test exist.
6. **Conformance vectors:** make the compatibility corpus and semantic
   projection the reusable test surface for any future adapter.

AAIF alignment should improve trust and interoperability without moving parser
authority into a hosted service or making an external protocol a runtime
dependency.

## 10. Prioritized improvement backlog

### P0 — establish public trust and exact state

| ID | Change | Acceptance evidence |
|---|---|---|
| P0-01 | Capture a fresh GitHub repository/settings receipt | Exact public `main` SHA, rulesets/protection, Actions permissions, security toggles, issues/projects/discussions, open PR/issue state |
| P0-02 | Add `GOVERNANCE.md` | Decision classes, review authority, emergency path, release authority, conflict handling, amendment process |
| P0-03 | Add `MAINTAINERS.md` or `OWNERS.md` | Named roles, current/emeritus maintainers, path ownership, how a contributor becomes a maintainer |
| P0-04 | Strengthen `CODEOWNERS` in stages | Security, release, parser, graph, docs paths; enforce ownership only when reviewers exist |
| P0-05 | Reconcile documentation with current Matryca Knowledge state | Exact source/profile heads, parser entry points, official OKF v0.2 status, and no stale claim in maintained docs |

### P1 — make security and delivery independently verifiable

| ID | Change | Acceptance evidence |
|---|---|---|
| P1-01 | Verify or enable Dependabot alerts, security updates, secret scanning, push protection, and CodeQL default setup | GitHub settings/API receipt; no secret or vulnerability claim from local files alone |
| P1-02 | Add dependency review to pull requests | A workflow or ruleset blocks newly introduced vulnerable dependencies with a documented exception path |
| P1-03 | Add GitHub artifact attestations to release artifacts | `actions/attest` receipt and successful `gh attestation verify` for wheel and sdist or a documented package-specific equivalent |
| P1-04 | Publish an SBOM for each release | Stable format, exact artifact binding, verification command, and retention policy |
| P1-05 | Generate a dependency/license inventory | Runtime, optional, development, and VCS dependencies with license evidence and review date |
| P1-06 | Threat-model daily metrics automation | Minimal token, branch allowlist, no untrusted code execution, retry policy, and a receipt for the self-mutating path |
| P1-07 | Add `CITATION.cff` | Valid citation metadata, author identity, version/release link, and a validation check |

### P1 — improve human and agent contribution flow

| ID | Change | Acceptance evidence |
|---|---|---|
| P1-08 | Add `SUPPORT.md` | What belongs in an issue, what belongs in a security report, support scope, and expected response boundary |
| P1-09 | Add AI-assisted contribution policy | Plain-English disclosure, privacy rule, human review responsibility, and no secret/vault upload rule |
| P1-10 | Consolidate the public roadmap | One 6–12 month view with milestone owners, dependencies, status vocabulary, and exit evidence |
| P1-11 | Add conformance/support matrix | Python versions, package API tier, CLI contract, Logseq semantics, optional adapters, and deprecation policy |
| P1-12 | Define issue triage and stale-work policy | Labels, priority definitions, good-first issue lifecycle, response targets, and closure rules |

### P2 — build ecosystem durability

| ID | Change | Acceptance evidence |
|---|---|---|
| P2-01 | Publish an AAIF alignment page | Mission relation, AGENTS.md usage, interoperability boundaries, adoption evidence, and explicit non-membership disclaimer |
| P2-02 | Publish a protocol adapter decision | MCP/A2A integration is accepted only with a threat model, stable schema, bounded permissions, and conformance tests |
| P2-03 | Add OpenSSF Scorecard monitoring | Baseline score, remediated high-risk checks, scheduled re-evaluation, and no score inflation claims |
| P2-04 | Complete the official OKF v0.2 maintained-bundle migration | Deterministic parser findings reduced by reviewed source PRs; historical docs remain protected from mass rewrite |
| P2-05 | Add community health dashboard | Response time, contributor retention, merged PRs, issue age, release cadence, and security response metrics without personal tracking |
| P2-06 | Establish a second maintainer and reviewer | Independent review of security/release changes and evidence of more than one organization when available |

### P3 — adoption and visibility

| ID | Change | Acceptance evidence |
|---|---|---|
| P3-01 | Publish two or three permissioned integration case studies | Reproducible use case, scale range, version, limitations, and downstream link |
| P3-02 | Improve repository metadata and topic discovery | Short description, stable topics, demo link, PyPI link, citation link, and accurate current release |
| P3-03 | Offer a small contributor workshop or issue sprint | New contributors complete a test/docs task with documented onboarding friction |
| P3-04 | Reassess AAIF proposal readiness | A completed AAIF matrix with evidence, sponsor discussion, legal decision, and explicit GO/NO-GO |

### 10.1 Terra implementation state

The following cross-file source changes are implemented in the authorized Terra
tranche and require only normal repository validation/publication:

| Capability | Source evidence | Boundary retained |
|---|---|---|
| Agent action, provenance, and prompt-injection contract | `docs/reference/AGENT_ACTION_CONTRACT.md` and `AGENTS.md` | No new runtime authority or network access |
| Compatibility and support matrix | `docs/reference/CONFORMANCE_SUPPORT_MATRIX.md` | No external conformance claim |
| Public roadmap and current triage policy | `docs/ROADMAP_2026-2027.md`, `docs/ISSUE_TRIAGE_POLICY.md`, label manifest, issue/PR templates | No claim that labels or GitHub settings are already live |
| Staged ownership | `.github/CODEOWNERS` path map | No invented second maintainer or independent-review requirement |
| AAIF alignment and protocol decision | `docs/AAIF_ALIGNMENT.md`, `docs/decisions/ADR-0001-PROTOCOL_ADAPTER_BOUNDARY.md` | No AAIF membership, protocol endpoint, legal, or submission claim |

### 10.2 Sol implementation state

The security-sensitive source tranche is implemented in the current worktree:

| Capability | Local source evidence | Still required before a public claim |
|---|---|---|
| Dependency review | `.github/workflows/dependency-review.yml` blocks newly introduced moderate-or-higher vulnerabilities on `pull_request` without write permissions | Successful hosted PR run and any required-check/ruleset receipt |
| Scorecard monitoring | `.github/workflows/scorecard.yml` uses pinned actions, read-only checkout, bounded SARIF retention, and code-scanning upload | Successful `main` or scheduled run plus reviewed findings; no badge or score claim yet |
| Release SBOM and license inventory | `scripts/generate_supply_chain_evidence.py`, version-exact override policy, tests, and `docs/reference/DEPENDENCY_LICENSE_POLICY.md` | Exact-tag artifact review and legal escalation for material license questions |
| GitHub release attestations | Release build requests only `id-token` and `attestations` writes, attests all checksummed evidence, binds the SBOM to distributions, and verifies before transport | A terminal tag run and independent `gh attestation verify` against downloaded artifacts |
| Metrics automation | Main-only workflow, separate traffic and write credentials, bounded API reads, full-snapshot validation, atomic writes, and threat model | Live token-scope receipt, successful run, and proof that the resulting commit touches only `metrics/` |
| Official OKF v0.2 | ADR-0002 records the 38 findings and the nested-index/profile conflict | Separate reviewed dual-profile migration; no mechanical zero-finding rewrite |
| AAIF submission | ADR-0003 records a NO-GO and evidence-based reconsideration gate | Maintainer diversity, adoption, sponsor, legal review, live assurance, and a new explicit authorization |

Local end-to-end generation on 2026-08-19 produced a 130-component inventory
with 14 direct dependencies, one VCS dependency, and zero unresolved direct
licenses from the current lockfile. The VCS record retains and validates its
immutable 40-character commit revision. The inventory also exposes 31
transitive dependencies whose installed metadata does not resolve to a specific
license expression;
those remain visible non-blocking review debt rather than guessed identifiers.
This is a local contract receipt, not a release or legal-compatibility
conclusion.

Remote settings, legal decisions, official OKF migration, community adoption,
and any AAIF contact or submission remain explicit maintainer/external gates.

## 11. Recommended target configuration

### GitHub repository settings

The maintainer should configure and then read back, in this order:

1. Keep `main` protected by pull request, required CI, conversation resolution,
   and no force-push/delete.
2. Require at least one independent maintainer approval once a second reviewer
   exists; until then document the narrowly scoped emergency/admin bypass.
3. Dismiss stale approvals after new commits and require the branch to be
   current before merge.
4. Restrict Actions to trusted, SHA-pinned actions and keep default token
   permissions read-only.
5. Enable Dependabot alerts and security updates, secret scanning and push
   protection, CodeQL, and dependency review where the public plan supports
   them.
6. Keep squash merge as the default if it preserves one reviewable change per
   issue; document whether linear history is required.
7. Keep automatic head-branch deletion enabled after merge.
8. Use milestones for releases and security/assurance waves; use one project
   board only if it reduces issue-search cost rather than duplicating labels.
9. Keep Discussions disabled until there is a moderator and a clear category
   model; enable it later for design questions that do not belong in issues.
10. Treat stars as an outcome of usefulness and discoverability, not as a gate
    or a metric to inflate.

### GitHub Actions

Keep the current strong patterns:

- full commit-SHA pinning with a human-readable version comment;
- workflow-level `permissions: contents: read` by default;
- separate pre-flight, immutable build, publish, and release jobs;
- exact digest verification before publication;
- `uv sync --locked` in release jobs;
- non-mutating CI followed by an explicit clean-checkout assertion.

The current source tranche adds GitHub attestations for release distributions
and evidence files, a bound production SBOM, pull-request dependency review,
scheduled Scorecard analysis, policy tests for the metrics write path, and
explicit artifact retention. These remain **implemented locally**, not
**verified remotely**, until their exact hosted runs pass.

Still evaluate through GitHub settings or a later bounded change:

- explicit repository-level action allowlisting;
- a dedicated shell/YAML/action lint gate if existing tests prove insufficient;
- retention and deletion settings outside the workflow files;
- whether dependency review should become a required ruleset check after the
  first successful run.

Do not make the CI run untrusted PR code with write-capable tokens. Do not use
`pull_request_target` for build/test execution unless the checkout and data flow
are deliberately constrained and independently reviewed.

### Documentation architecture

Keep the current separation:

```text
README.md              human product and quickstart portal
AGENTS.md              agent behavior, boundaries, and validation contract
llms.txt               compact discovery index
docs/index.md          machine-oriented maintained bundle
docs/README.md         human documentation portal
CONTRIBUTING.md        contributor workflow
GOVERNANCE.md          decision and maintainer model
MAINTAINERS.md         named ownership and succession
SUPPORT.md             support and communication boundary
SECURITY.md            vulnerability reporting
RELEASE_PROCESS.md     release mechanics
```

The README should remain concise and route detail to these documents. The
maintained bundle should use the Matryca metadata contract. Historical reports
should retain their original evidence and never be silently refreshed.

### Agent safety contract

Document every agent capability using this table shape:

| Capability | Default | Reads | Writes | Approval | Evidence |
|---|---|---|---|---|---|
| X-Ray / outline read | Allowed | vault Markdown | none | none | source paths and query |
| Parse / scan / export | Allowed | vault Markdown | derived output only | none | command, version, output hash |
| Dry-run write | Allowed | vault Markdown | patch preview only | none | unified diff and target |
| Append/write | Opt-in | bounded target | confined Markdown | human or explicit caller | action receipt and target identity |
| Release publication | Maintainer-only | exact tag/build | PyPI/GitHub | explicit release gate | exact artifact and attestation |
| Documentation federation | Reviewed | exact source commit | proposal/projection | source PR plus federation review | source SHA, path, content hash |

Treat all vault content as untrusted data. A Markdown block, link, macro, or
embedded instruction must never silently expand agent authority.

## 12. Six-to-twelve-month execution roadmap

| Milestone | Scope | Primary owner | Exit evidence |
|---|---|---|---|
| M0 — Public baseline | Fresh GitHub readback and exact public `main` receipt | Maintainer | Settings, security, issue/PR/project, and head SHA receipt |
| M1 — Governance minimum | `GOVERNANCE.md`, `MAINTAINERS.md`, `SUPPORT.md`, AI policy | Maintainer + reviewer | Docs gate, link check, decision-table review, published docs |
| M2 — Supply-chain proof | Dependency review, Scorecard baseline, attestations, SBOM, license inventory | Release owner | Verified artifact/SBOM/provenance receipts |
| M3 — Documentation convergence | Update stale Matryca references, complete maintained OKF v0.2 slices, preserve history | Docs owner | Exact-head source audit, zero new maintained-doc findings |
| M4 — Semantic assurance | Compatibility corpus, metamorphic properties, incremental/cold-load equivalence, bounded adversarial profiles | Parser owner | `make all`, corpus manifest, exact test receipt, no invariant regression |
| M5 — Community durability | Triage policy, roadmap, issue labels, contributor response loop, second reviewer | Maintainers | Six-month activity report and independent review path |
| M6 — Interoperability/adoption | Protocol decision, case studies, downstream integration evidence | Product + community | Threat model, adapter conformance, permissioned adoption receipts |
| M7 — AAIF decision gate | Complete proposal matrix and choose defer / discuss sponsor / submit | Maintainer + legal reviewer | Written GO/NO-GO; no submission by default |

Dependencies are intentional: governance precedes external submission; supply
chain precedes trust claims; semantic assurance precedes broad adapter promises;
adoption evidence precedes AAIF stage claims.

## 13. Cost-aware delegation policy

Use deterministic repository tools before an LLM. Keep architecture, security,
legal, release, merge, and AAIF readiness decisions with the primary maintainer
or a high-capability reviewer.

| Work | Cheapest suitable route | Primary retains |
|---|---|---|
| File inventory, link/anchor inventory, issue chronology | Script or Luna | Synthesis and priority |
| Frontmatter or index maintenance with named files | Luna | Factual review and integration |
| Test execution, log distillation, artifact hash collection | Deterministic tools, then Luna | Pass/fail qualification |
| Isolated workflow or documentation edit | Luna first, Terra if cross-file | Security and integration review |
| Governance design, cross-file policy, workflow permissions | Terra | Entire decision and review |
| Security threat model, license boundary, release/AAIF gate | Sol or primary | Entire decision |

Delegates must receive exact files, commits, scope, prior evidence, and output
format. They must stop and report uncertainty rather than widening scope.

## 14. Completion checklist

The study is complete as a planning artifact when these items remain true:

- [x] Existing repository instructions and current local Git state were read.
- [x] Public state was separated from the local assurance branch.
- [x] GitHub official guidance was reviewed for repository health, community
  files, pull requests, ownership, protected branches, Actions security, and
  artifact provenance.
- [x] AAIF's public submission expectations and Technical Committee lifecycle
  policy were reviewed.
- [x] A relevant prior-art sample was inspected without treating it as a
  compliance checklist.
- [x] Current files, missing governance surfaces, and remote-evidence gaps were
  recorded.
- [x] AAIF alignment was separated from AAIF membership and official OKF status.
- [x] Prioritized improvements have bounded acceptance evidence.
- [x] A dependency-ordered 6–12 month roadmap exists.
- [x] Delegation and approval boundaries are explicit.
- [x] The authorized Luna tranche added lightweight governance, maintainer,
  support, citation, and AI-contribution documentation without changing code,
  workflows, or remote GitHub state.
- [x] The authorized Terra tranche added cross-file agent, compatibility,
  roadmap, triage, ownership, AAIF-alignment, and protocol-adapter policy
  surfaces without claiming remote configuration or creating a new runtime.
- [x] The Sol source tranche added dependency review, scheduled Scorecard,
  release SBOM and dependency/license evidence, GitHub attestations, hardened
  metrics collection, focused tests, and maintained security/release policy.
- [x] Official OKF v0.2 and AAIF submission decisions are recorded as explicit
  defer/NO-GO gates rather than inferred conformance or membership claims.
- [x] Local supply-chain generation resolved every direct dependency license
  from the current lockfile and retained the VCS revision in evidence.
- [ ] Fresh GitHub API/settings readback is still required before any remote
  readiness claim.
- [ ] Hosted dependency-review and Scorecard runs are required before those
  workflows can be called operational.
- [ ] A real tag run and downloaded-artifact verification are required before
  the new release provenance, SBOM, and inventory contract can be called
  qualified.
- [ ] Metrics token scope and the first successful main-only write must be
  verified without exposing the token.
- [ ] Official OKF migration, legal review, independent maintainership,
  adoption evidence, and any AAIF reconsideration remain external gates.

## 15. Copy-paste persistent execution goal

Use this as the next bounded execution pointer:

```text
Qualify the implemented GitHub and AAIF readiness source tranche defined in
docs/REPOSITORY_GOVERNANCE_AAIF_STUDY_2026-08-19.md. Preserve the current dirty
worktree until its complete diff passes focused tests, make all, documentation
validation, YAML parsing, supply-chain generation, and manual security review.
Then, only with explicit publication authority, commit and publish one
reviewable branch and obtain hosted dependency-review and Scorecard receipts.
Separately verify the exact public main SHA, rulesets/protection, Actions
permissions, security features, issue/PR/project state, and Matryca Knowledge
profile head. Qualify release provenance only through a real exact-tag run and
downloaded-artifact verification; do not tag or release without a separate
maintainer gate. Preserve Markdown authority, parser determinism, vault
containment, lazy optional integrations, exact-head evidence, and distinct
commit, push, PR, merge, settings, release, legal, OKF, and AAIF gates.
```

## 16. References

### Official GitHub and supply-chain guidance

- [Best practices for repositories](https://docs.github.com/en/repositories/creating-and-managing-repositories/best-practices-for-repositories)
- [Community health files](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file)
- [Managing and standardizing pull requests](https://docs.github.com/en/pull-requests/reference/managing-and-standardizing-pull-requests)
- [About code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
- [Managing protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches)
- [Secure use of GitHub Actions](https://docs.github.com/en/actions/reference/security/secure-use)
- [Artifact attestations](https://docs.github.com/en/actions/concepts/security/artifact-attestations)
- [OpenSSF Scorecard](https://scorecard.dev/)

### AAIF and agent interoperability

- [AAIF project submission](https://aaif.io/submit-a-project/)
- [AAIF Technical Committee](https://github.com/aaif/technical-committee)
- [AAIF Project Lifecycle Policy](https://github.com/aaif/technical-committee/blob/main/governance/project-lifecycle-policy.md)
- [AGENTS.md format](https://agents.md/)
- [AAIF project catalogue](https://github.com/aaif)

### Prior art

- [MCP Python SDK agent guidance](https://github.com/modelcontextprotocol/python-sdk/blob/main/AGENTS.md)
- [MCP contribution guide](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/CONTRIBUTING.md)
- [AAIF goose repository](https://github.com/aaif-goose/goose)
- [goose governance](https://github.com/aaif-goose/goose/blob/main/GOVERNANCE.md)
- [Kubernetes contribution entry point](https://github.com/kubernetes/kubernetes/contribute)
- [Kubernetes community repository](https://github.com/kubernetes/community)

### Repository-local authority

- [`AGENTS.md`](../AGENTS.md)
- [`docs/DOCUMENTATION_SYSTEM.md`](DOCUMENTATION_SYSTEM.md)
- [`docs/REPOSITORY_STELLAR_ROADMAP_2026-08-06.md`](REPOSITORY_STELLAR_ROADMAP_2026-08-06.md)
- [`docs/README_READABILITY_REPORT_2026-08-08.md`](README_READABILITY_REPORT_2026-08-08.md)
- [`docs/maintained.toml`](maintained.toml)
- [Matryca Knowledge federation audit](https://github.com/MarcoPorcellato/Matryca-knowledge/blob/main/docs/FEDERATED_DOCUMENTATION_AUDIT_2026-08-19.md)

## 17. Handoff status

The published Luna checkpoint and the current Terra plus Sol source tranche do
not alter package runtime, remote repository settings, or external services. At
the time of this record:

- local `HEAD` is `1947251d2df79f37550a40cda3c0c26bb602245f` and the intended
  governance/assurance changes remain uncommitted above it;
- governance, maintainer, support, citation, AI-contribution, agent,
  compatibility, roadmap, triage, ownership, AAIF-alignment, protocol,
  supply-chain, release, metrics-security, and decision documents exist in the
  worktree;
- workflows and tests now cover dependency review, Scorecard, release evidence,
  and metrics hardening, while package runtime remains unchanged;
- the completed local diff passes Ruff, mypy on 61 source files,
  `vendor-name-check`, the maintained documentation gate, YAML parsing, 603
  tests, 92.16% coverage, and a zero-cycle source import check; two independent
  SBOM exports normalize to identical bytes, the current inventory resolves all
  14 direct licenses, and its single VCS dependency retains a validated
  immutable commit; the checksum manifest verifies both inside the build
  bundle and after flattening assets into the public GitHub Release layout;
- no GitHub setting, issue, project, milestone, pull request, merge, release,
  legal acceptance, OKF projection, or AAIF submission was performed by this
  tranche;
- earlier feature-branch publication receipts remain historical and do not
  prove publication of this worktree;
- fresh GitHub API/settings readback remains required before any remote-state
  claim.

Exact-worktree validation and Sol diff review are complete. Publication and
hosted qualification now require their own explicit maintainer gates; release,
legal, official OKF, and AAIF actions remain separate.

### 17.1 Final Sol completion audit

| Planned Sol responsibility | Final local disposition | Evidence still external |
|---|---|---|
| P1-02 dependency review | Source-qualified: PR-only trigger, read-only permissions, SHA-pinned action, moderate-or-higher vulnerability gate | First hosted PR run and required-check decision |
| P1-03 artifact provenance | Source-qualified: all checksummed release evidence is attested and verified before transport | Exact-tag terminal run and downloaded-artifact verification |
| P1-04 reproducible SBOM | Source-qualified: two independent locked exports normalized to identical bytes | Exact-tag SBOM and attestation receipt |
| P1-05 dependency/license inventory | Source-qualified: 130 components, 14 direct licenses resolved, 31 unresolved transitive records visible, one immutable VCS commit, two content-addressed overrides | Material legal questions and real-release review |
| P1-06 metrics write path | Source-qualified: main-only execution, separated credentials, bounded reads, schema validation, atomic writes, and non-force retry | Secret-scope readback and first clean hosted metrics commit |
| P2-03 Scorecard | Source-qualified: restricted official job shape, bounded SARIF artifact, code-scanning upload | First hosted `main` or scheduled run and findings review |
| P2-04 official OKF v0.2 | Decision-complete: ADR-0002 defers migration and preserves the measured 38-finding backlog | A separately reviewed profile migration |
| M7 AAIF gate | Decision-complete: ADR-0003 records NO-GO without membership or conformance claims | Governance, adoption, sponsor, legal, and renewed explicit authorization |
| Repository structural gate | Qualified: public diagnostics behavior preserved and the current `src/` import graph has zero cycles | Hosted CI after publication |

**Local Sol verdict: QUALIFIED FOR REVIEW.** This verdict covers the complete
source implementation and exact-worktree evidence in this tranche. It does not
authorize or claim a commit, push, pull request, settings mutation, tag, release,
legal approval, official OKF migration, or AAIF contact.
