---
type: SecurityThreatModel
title: Daily repository metrics threat model
description: Trust boundaries, controls, failure policy, and residual risks for the self-mutating GitHub traffic archive.
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

# Daily repository metrics threat model

## Decision

The metrics archive may continue only as a default-branch, scheduled or
maintainer-dispatched workflow. It is a deliberately self-mutating path and is
not part of pull-request CI. Metrics are derived, aggregate repository data;
they never authorize product, release, or community decisions by themselves.

## Assets and trust boundaries

| Asset or boundary | Threat | Required control |
|---|---|---|
| `METRICS_TOKEN` | Disclosure or use outside the target repository | Fine-grained token restricted to this repository with **Administration: read** only; pass by environment; never print or accept it as a CLI argument |
| Workflow `GITHUB_TOKEN` | Unintended repository writes | Workflow default is `contents: read`; only the metrics job receives `contents: write`; checkout and push are hard-coded to `main` |
| Checked-out code | Untrusted PR code executing with write authority | No `pull_request` or `pull_request_target` trigger; job requires `refs/heads/main`; checkout explicitly selects `main` |
| GitHub API responses | Oversized, malformed, or attacker-influenced data | Fixed API host and repository slug, versioned API header, 30-second timeout, 2 MB response cap, strict top-level shape checks, field allowlist |
| `metrics/` archive | Partial or corrupt writes | Fetch the complete snapshot before mutation; atomic JSON replacement; fail closed on any missing endpoint |
| Concurrent default-branch updates | Lost commits or forceful overwrite | One concurrency group, fast-forward before collection, bounded rebase/push retries, no force push |
| Archived paths and referrers | Personal or sensitive analytics | Store only GitHub's aggregate counts, published referrer labels, public content paths, release tags, and asset download counts; no usernames, IP addresses, tokens, or raw events |

GitHub documents that repository traffic endpoints require a fine-grained token
with repository **Administration: read** permission. That token is distinct
from the job-scoped `GITHUB_TOKEN`, which performs the bounded `metrics/` push.

## Failure and retry policy

- Each API request has a bounded size and timeout.
- HTTP 408, 429, and 5xx responses plus transient transport failures receive at
  most three attempts with short linear backoff.
- Authentication, authorization, schema, decoding, and size failures abort the
  complete snapshot.
- No archive file is changed until all five endpoint payloads pass structural
  validation.
- Push conflicts receive at most five rebase-and-push attempts. Failure leaves
  the workflow red; it never force-pushes or silently discards another commit.

## Prompt-injection and code-execution boundary

Referrer names, content titles, paths, release text, and asset names are data.
The script copies only named scalar fields into JSON and never evaluates them,
constructs shell commands from them, follows their links, or treats them as
agent instructions. No fetched value controls the checkout, branch, command,
filesystem root, or token scope.

## Residual gates

The source tree proves the intended design, not the live secret or repository
configuration. Before calling this path qualified, a maintainer must record:

1. the exact workflow commit and successful terminal run;
2. the `METRICS_TOKEN` repository restriction and Administration-read-only
   permission, without recording its value;
3. the workflow's effective `GITHUB_TOKEN` permission receipt;
4. the resulting commit's scope, which must contain only `metrics/` changes;
5. a rotation or deletion date for the long-lived metrics token.

## Verification

```bash
pytest -q tests/test_archive_repository_metrics.py tests/test_quality_gate_contract.py
make all
git diff --check
```

Related implementation:

- [daily metrics workflow](../../.github/workflows/daily-metrics.yml)
- [archive script](../../scripts/archive_repository_metrics.py)
- [agent action contract](../reference/AGENT_ACTION_CONTRACT.md)
