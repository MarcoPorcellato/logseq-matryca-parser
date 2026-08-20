---
type: ArchitectureDecisionRecord
title: External oracle boundary for parser assurance
description: Declines external mldoc-oracle adoption under the current Apache-2.0 project boundary while preserving project-owned assurance work.
status: stable
classification: canonical
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
decision_date: 2026-08-16
last_verified: 2026-08-16
verified: 2026-08-16
stale_after: 2027-02-12
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---

# ADR-001: External oracle boundary for parser assurance

## Status

Accepted on 2026-08-16. This is a negative M2 decision: the project will not
adopt an external `mldoc` executable as a parser-assurance oracle under the
current project boundary.

## Context

The parser-assurance plan permits a separate external oracle only after a
decision records its license review, process isolation, dependency provenance,
and publication policy. The project is Apache-2.0 and its assurance artifacts
must remain project-owned, original, and reproducible without an unreviewed
external executable.

On 2026-08-16, the public `logseq/logseq` repository identified its license as
`AGPL-3.0` and its exact `master` revision was
[`bb096a8fbb991c2906b6f9703460d91fc935a408`](https://github.com/logseq/logseq/tree/bb096a8fbb991c2906b6f9703460d91fc935a408).
Its [license text](https://github.com/logseq/logseq/blob/bb096a8fbb991c2906b6f9703460d91fc935a408/LICENSE.md)
is a source observation, not a component-level compatibility determination.
No exact external executable revision, dependency inventory, installation
boundary, original adapter, fixture policy, or maintainer-approved process
boundary has been established for this project.

This ADR is an engineering and project-governance decision, not legal advice.
It does not decide whether every possible isolated use of an external program
would be lawful or compatible in every jurisdiction.

## Decision

Do not install, invoke, package, pin, or integrate an external `mldoc`
executable for parser assurance at this time. In particular, the repository
must not add:

- an external-oracle runtime, build, package, CI, release, or service
  dependency;
- copied or adapted external source, fixtures, expected outputs, schemas,
  control flow, or documentation; or
- an external-parity, compatibility, or release-qualification claim.

M2 is therefore complete with a negative decision. M3 and M4 remain valid
project-owned assurance evidence and require no external oracle. Any future M5
work may evaluate only project-owned invariants unless this ADR is superseded;
the existing filesystem-safety and threat-model dependencies still apply.

## Consequences

- Differential evidence level E3 is unavailable. Project-owned corpus,
  adversarial, and deterministic work-growth evidence remain available.
- Differences from an external parser are not measured or interpreted by this
  repository, and no behavioral parity is implied.
- This decision does not close #104, #87, #103, #111, or #108 and does not
  change their ownership boundaries.
- No source code, package metadata, dependencies, CI configuration, tests, or
  release artifacts change as a result of this ADR.

## Reconsideration and rollback

Supersede this ADR only through a new recorded decision that includes all of
the following before any external executable is obtained or used:

1. an exact upstream revision and a primary-source license and dependency
   inventory;
2. an explicit maintainer-approved process, installation, provenance,
   privacy, retention, and publication boundary;
3. original adapter and fixture designs that preserve the clean-room policy and
   keep external material out of repository artifacts;
4. a fail-closed treatment for unknown mappings, version drift, oracle errors,
   and private-vault data; and
5. qualified legal review if the proposal involves packaging, linking, service
   deployment, source adaptation, or any other integration beyond the isolated
   research boundary described in the assurance plan.

Until then, reverting this ADR means returning to the same no-adoption state;
it does not authorize a temporary local exception.

## Verification evidence

- The upstream repository metadata and license text were inspected read-only
  at the exact revision named above on 2026-08-16.
- No external executable was downloaded, installed, run, pinned, or added to
  this repository.
- M3 and M4 are preserved as separate, locally qualified, unpublished,
  project-owned evidence; this ADR makes no publication claim.
