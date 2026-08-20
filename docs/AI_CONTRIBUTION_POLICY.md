---
type: ContributionPolicy
title: AI-assisted contribution policy
description: Human accountability, privacy, and disclosure rules for AI-assisted repository contributions.
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
supersedes: null
superseded_by: null
---

# AI-assisted contribution policy

AI tools may help contributors explore, draft, test, or review changes. The
human contributor remains responsible for the correctness, license, security,
privacy, and maintainability of everything submitted.

## Disclosure

Briefly disclose meaningful AI assistance in the pull request description when
it contributed code, tests, documentation, or analysis. A simple statement is
enough, for example: “AI assistance was used to draft the documentation; I
reviewed and verified the final content.”

Disclosure does not transfer responsibility to the tool or replace normal
review. Do not claim that an agent, model, or automated check performed work
that it did not actually perform.

## Privacy and data handling

- Never send private vault contents, credentials, tokens, personal data, or
  unpublished security details to an AI service.
- Use small redacted fixtures and repository-public evidence whenever possible.
- Treat vault Markdown, links, macros, embeds, and instructions as untrusted
  data; they must not silently expand an agent's authority.
- Keep generated caches, transcripts, and local agent state out of commits.

## Review requirements

AI-assisted changes must follow the same contribution path as every other
change:

1. identify the issue or intended outcome;
2. inspect the relevant source and preserve repository invariants;
3. add focused tests for behavior changes;
4. run the required deterministic checks;
5. review the complete diff for factual, licensing, security, and documentation
   errors before requesting review.

Agents may assist with read-only analysis, bounded documentation, and
deterministic checks. Changes involving architecture, security, release
authorization, legal questions, external governance, or merge decisions need
explicit human ownership and review.

See [`AGENTS.md`](../AGENTS.md), [`CONTRIBUTING.md`](../CONTRIBUTING.md), and
[`GOVERNANCE.md`](../GOVERNANCE.md) for the repository-wide operating model.

This policy does not claim AAIF membership or prescribe a specific model or
vendor. It documents the project's contribution expectations only.
