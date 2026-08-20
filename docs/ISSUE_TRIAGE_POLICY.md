---
type: IssueTriagePolicy
title: Issue triage and stale-work policy
description: Maintainer policy for issue classification, priorities, contributor handoff, and transparent closure.
status: stable
classification: active
audience: contributors
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-08-19
verified: 2026-08-19
stale_after: 2027-02-19
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: docs/quality/ISSUE_TRIAGE_2026-07.md
superseded_by: null
---

# Issue triage and stale-work policy

This policy applies to new and existing GitHub issues. It replaces the July 2026
triage snapshot as the current operating policy; the older file remains
historical evidence and must not be rewritten as current state.

## Triage goals

- make the next maintainer action visible;
- keep good-first issues genuinely bounded and safe for newcomers;
- separate confirmed bugs from feature requests, questions, and unverified
  reports;
- close obsolete work with an explanation and a link to its successor;
- avoid collecting private vault data or security details in public issues.

## Labels and priority

The version-controlled label manifest is [`.github/labels.yml`](../.github/labels.yml).
Its labels become live only after a maintainer synchronizes them to GitHub and
records the result. The intended taxonomy is:

| Category | Labels | Meaning |
|---|---|---|
| Type | `bug`, `enhancement`, `documentation`, `tests` | What kind of work is requested |
| Area | `area: parser`, `area: graph`, `area: agent`, `area: cli`, `area: docs`, `area: ci` | Primary ownership or expertise boundary |
| Priority | `priority: critical`, `priority: high`, `priority: medium`, `priority: low` | Impact and urgency, not contributor status |
| State | `triage`, `status: needs-reproduction`, `status: blocked`, `status: stale` | Current next action or evidence gap |
| Contribution | `good first issue`, `help wanted` | Suitable newcomer work or request for additional help |

`priority: critical` is reserved for active security, data-loss, or widespread
release-blocking situations. Public security reports must be redirected to
[`SECURITY.md`](../SECURITY.md), not triaged in public.

## Normal issue flow

1. A maintainer classifies a new issue as bug, enhancement, documentation,
   tests, or a redirect to support/security guidance.
2. Incomplete reports receive `status: needs-reproduction` and a request for a
   minimal, redacted reproduction.
3. Confirmed work receives one priority and one primary area label.
4. Work that needs design, maintainer capacity, or an external dependency gets
   `status: blocked` with the exact dependency stated in a comment.
5. Work ready for a newcomer may receive `good first issue` only after it has
   scope, acceptance criteria, non-goals, likely files, and verification steps.

The target is an initial classification within 14 calendar days when maintainer
capacity permits. This is a transparency target, not a support SLA. Security
response timing is defined separately in [`SECURITY.md`](../SECURITY.md).

## Good-first issue lifecycle

A good-first issue remains eligible only while its scope is small, independent,
and backed by a reproducible check. When a contributor claims it, the issue
should record that claim and a reasonable check-in date. If there is no update
after 30 days, a maintainer may invite another contributor without blaming the
original claimant.

Remove `good first issue` if the work becomes cross-cutting, security-sensitive,
or blocked on a design decision. Link to the follow-up issue rather than hiding
the changed scope.

## Stale and closure policy

After 60 days without activity, an issue that is waiting only for a reproduction
or reporter response may receive `status: stale` and a clear request for the
missing evidence. After a further 30 days, it may be closed if no new evidence
arrives. Do not auto-close:

- security reports handled through the private process;
- confirmed data-loss or correctness defects;
- active contributor work with an agreed check-in;
- issues blocked by a documented maintainer or release dependency.

Every closure should state one of: completed, duplicate, out of scope, cannot
reproduce, superseded, or waiting for evidence. Link to the relevant pull
request, release, decision, or successor issue whenever it exists.

## Review cadence and evidence

Review the open backlog before a release and at least once per calendar month
when maintainer capacity permits. Record dated snapshots as historical
documents; never use a historical issue count as current evidence.
