---
type: Document
---
# Matryca.ai Policy: Ghost Tooling & Static Analysis

## 1. Context and Risk (Restrictive Licenses)

Many advanced development tools (AST indexers, code RAG systems, or specialized MCP servers) are released under restrictive commercial-use licenses, such as **PolyForm Noncommercial 1.0.0**.

Tool licenses must be reviewed for the intended use, including business use.
Running a tool locally does not establish license entitlement, exempt that use
from restrictions, or determine the legal status of resulting source code.
For example, the [official PolyForm Noncommercial terms](https://polyformproject.org/licenses/noncommercial/1.0.0)
grant rights for permitted purposes; local placement alone is not a permitted-purpose test.
This repository policy is a hygiene boundary, not a legal opinion.

## 2. Strategy: Ghost Tooling

**Ghost Tooling** keeps optional maintainer tools out of the product repository
and its automated pipelines. It does not establish compliance with a tool's
license, replace mandatory notices, or remove other applicable obligations:

> Subject to applicable license rights or a separate entitlement, optional
> maintainer tools may be used **only locally** and must not be added to this
> public repository or its CI. This additional repository restriction does not
> authorize an otherwise unlicensed use.

Uncertain business use requires maintainer and appropriate license review before
use. This document does not decide whether any existing tool use is lawful or
unlawful and does not change the Parser's license.

## 3. Operational Rules

### A. Invisible Local File Protection (TRIZ Method)

**Never** add tool-specific names to the public `.gitignore` (that would expose tool usage).

To prevent accidental commits, use **only** Git's local exclusion mechanisms:

1. Open (or create) `.git/info/exclude` in your local clone.
2. Add tool-specific directories (e.g., `.local_ast_cache/`, `.local_code_graph/`, `.claude/skills/`).

This file is never pushed to origin.

### B. CI/CD and Automation (Zero Tolerance)

Protected analysis tools **must never** appear in GitHub Actions, Dockerfiles, or public requirements (`pyproject.toml`, `package.json`). CI must remain focused on core runtime and standard open-source linters (e.g., ruff, mypy, eslint).

### C. Agnostic Language in Documentation

In issues, pull requests, changelogs, or project diaries, it is **strictly forbidden** to name specific unauthorized third-party tools.

- **Wrong:** "Found bug using ToolX."
- **Correct:** "Found bug via local static analysis" or "AST audit completed."

### D. Rules for AI Assistants (`.cursorrules`)

Every Matryca.ai project must include the directive in [`.cursorrules`](../../.cursorrules) at the repository root. Maintainers should also mirror it in a local `.cursor/rules/06-ghost-tooling-policy.mdc` with `alwaysApply: true` (the `.cursor/` directory is not committed in this repo).

## 4. PR and Issue Template

If an external contributor or AI proposes integrating such a tool into the repository, close the PR immediately with:

> *"Closing this PR. We've decided to keep our CI and automation scripts strictly focused on the core runtime and standard linters (e.g., ruff/mypy). Advanced local static analysis tools and experimental scripts will be maintained outside the main repository to keep the codebase lightweight, vendor-agnostic, and to reduce maintenance overhead."*

## 5. Local Setup (Maintainers Only)

After removing vendor-specific artifacts from the public repo, maintainers who continue using local analysis tools should:

1. Keep scripts and config in a path **outside** the repository (e.g., `~/matryca-ghost-tools/<project>/`).
2. Populate `.git/info/exclude` with cache and skill directories used locally.
3. Never reference those tools in commit messages, PR descriptions, or public docs.
4. Follow the **local code audit** workflow in [`LOCAL_CODE_STUDY.md`](LOCAL_CODE_STUDY.md) for call-chain audits.
