# Governance

This document describes how decisions are made in Logseq Matryca Parser. It is
intentionally lightweight: the project is currently maintained by one named
maintainer and should not create committee structure before the contributor
community requires it.

## Project principles

- Logseq Markdown remains the source of truth.
- Parser output is deterministic and preserves hierarchy, identity, ordering,
  source locations, and round-trip behavior.
- Filesystem containment, safe writes, optional integrations, and privacy are
  treated as product boundaries.
- Public claims must be supported by reproducible repository or release
  evidence.

## Decision classes

| Decision | Normal path | Required evidence or review |
|---|---|---|
| Documentation, tests, and maintenance | Issue or pull request | Focused checks and `make all` when the repository contract requires it |
| Parser, graph, CLI, or public API behavior | Design discussion followed by a pull request | Invariant analysis, focused regression tests, and API compatibility review |
| Security, dependency, and release changes | Maintainer-led pull request | Security or release checklist, exact-head validation, and documented receipt |
| External governance, legal, AAIF, or trademark decisions | Explicit maintainer decision | Public rationale plus any required legal or external approval |

## Contribution and review process

1. Use an existing issue or open one before starting a substantial change.
2. Keep one coherent problem per pull request and describe the evidence for the
   change.
3. Preserve the repository invariants and follow [`CONTRIBUTING.md`](CONTRIBUTING.md).
4. Required automated checks must pass before merge.
5. The maintainer records material decisions in the relevant documentation,
   changelog, issue, or release record.

Routine documentation and test changes may be reviewed directly. Changes that
affect parser semantics, graph identity, filesystem writes, security, release
artifacts, or public API compatibility require a deeper review and may be
deferred until an independent reviewer is available.

## Current authority and succession

The current maintainer and release authority are listed in
[`MAINTAINERS.md`](MAINTAINERS.md). The repository's
[CODEOWNERS file](.github/CODEOWNERS) is the operational ownership source for
GitHub pull requests.

A contributor can be considered for maintainership after sustained, high-quality
contributions, reliable review of other contributors' work, familiarity with
the parser and release contracts, and agreement on the project's security and
community standards. A second maintainer should be established before relying
on independent approval as a repository setting.

## Conflicts and urgent decisions

Technical disagreements should be resolved in the relevant issue or pull
request using reproducible evidence and the project invariants. A maintainer
may pause or revert a change that creates an immediate security, data-loss, or
release-integrity risk, then document the reason and follow up publicly.

Security reports must follow [`SECURITY.md`](SECURITY.md), not a public issue.
External legal, trademark, sponsorship, and AAIF participation decisions are
separate from routine code review and require explicit approval.

## Scope and status

This is the repository's current operating model. It does not claim AAIF
membership, multi-organization governance, or any GitHub setting that has not
been verified from the live repository.
