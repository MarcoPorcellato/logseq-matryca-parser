---
type: ReadmeReadabilityReport
title: README human and AI readability report - 2026-08-08
description: Evidence-backed assessment and phased proposal for a shorter human README and a clearer AI-agent entry path.
status: draft
classification: active
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: advisory
last_verified: 2026-08-08
verified: 2026-08-08
stale_after: 2027-02-04
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---

# README human and AI readability report — 2026-08-08

## 1. Purpose and decision boundary

This report separates two kinds of work:

1. **Implemented now:** move detailed release narratives out of the root README,
   retain a one-line-per-release summary at its bottom, add a prominent link to
   the detailed history, improve the root AI-agent instructions, publish a
   proposal-format `llms.txt`, and add a thin GitHub-specific instruction
   adapter.
2. **Proposed for maintainer approval:** simplify and reorder the remaining
   README without removing product capabilities or changing technical claims.

The report is advisory. Sections 6–10 are a decision aid, not authorization to
rewrite the rest of the README.

## 2. Measured baseline and immediate result

Before this change, the root README was 495 lines long. Detailed release
material occupied lines 109–349: 241 lines, or approximately 49% of the file.
The core capability table began at line 350 and the Quickstart began at line
382. A first-time reader therefore encountered release archaeology before
installation or a runnable example.

The implemented separation produces this result:

| Measure | Before | After this change | Effect |
|---|---:|---:|---|
| Root README length | 495 lines | 287 lines | 208 fewer lines, about 42% shorter |
| Detailed release history in README | 241 lines | 0 lines | Moved without loss to `RELEASE_HIGHLIGHTS.md` |
| Quickstart position | Line 382 | Line 29 | 353 lines earlier |
| Release summary | Multiple tables and examples | One line per documented release | Scannable chronology at the bottom |
| AI-agent orientation | Audit-tool rules only | `AGENTS.md`, `llms.txt`, canonical machine index, and thin Copilot adapter | Faster, safer cross-tool orientation |

The detailed history is now in [`RELEASE_HIGHLIGHTS.md`](../RELEASE_HIGHLIGHTS.md).
The exhaustive source of individual changes remains [`CHANGELOG.md`](../CHANGELOG.md).

## 3. Evidence from GitHub guidance

GitHub says a README is often the first item a repository visitor sees and
typically needs to explain what the project does, why it is useful, how to get
started, where to get help, and who maintains it. GitHub also recommends moving
longer documentation out of the README and supports relative links so those
documents remain valid across branches. See
[About the repository README file](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes).

GitHub automatically derives a table of contents from headings. This favors a
small number of stable, descriptive sections over many repetitive release
headings. The same official guide confirms that relative links are the correct
way to route readers from the root README into repository documentation.

For AI tooling, GitHub documents `AGENTS.md` as repository agent instructions
and recommends short, repository-specific context that helps an agent
understand, build, test, and validate changes. See
[Adding repository custom instructions for GitHub Copilot](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/add-custom-instructions/add-repository-instructions)
and
[About customizing GitHub Copilot responses](https://docs.github.com/en/copilot/concepts/prompting/response-customization).

These sources support the chosen split:

- `README.md` is the short human front door.
- `RELEASE_HIGHLIGHTS.md` holds reader-friendly release history.
- `CHANGELOG.md` is the exhaustive change ledger.
- `AGENTS.md` is the execution-oriented AI-agent entry point.
- `llms.txt` is the concise inference-time discovery and capability index.
- `.github/copilot-instructions.md` adapts the canonical guidance for GitHub
  tooling without becoming another source of truth.
- `docs/index.md` remains the canonical maintained machine knowledge map.

The [`llms.txt` proposal](https://github.com/AnswerDotAI/llms-txt) defines the
chosen format: one H1, a concise blockquote, optional explanatory text, H2 link
groups, and a specially named `Optional` section for material that can be
skipped under tighter context budgets. The filename is plural by specification.
This is a community proposal, not a guarantee that any particular model or
agent will fetch the file automatically; its immediate value is a compact,
explicit, human-readable project map.

## 4. Patterns from mature open-source READMEs

The repositories below are not treated as an objective ranking. They are a
benchmark sample of mature, widely adopted projects with clear README patterns.

### 4.1 uv

The [`astral-sh/uv` README](https://github.com/astral-sh/uv) opens with one
sentence, a compact highlights list, installation, and task-oriented examples.
Detailed reference material is delegated to the documentation site. The useful
pattern for this repository is progressive disclosure: value first, first
success second, deeper capability families later.

### 4.2 Rich

The [`Textualize/rich` README](https://github.com/Textualize/rich) quickly moves
from a plain-language product statement to compatibility, installation, and a
minimal executable example. It demonstrates features through small examples
rather than describing every historical addition before the first command.

### 4.3 FastAPI

The [`fastapi/fastapi` README](https://github.com/fastapi/fastapi) establishes a
single product definition, lists reader outcomes, then provides install, create,
run, and verify steps. The lesson is not its total length; it is the explicit
success path and the repeated use of concrete output over abstract subsystem
language.

### 4.4 Pydantic and HTTPX

The [`pydantic/pydantic` README](https://github.com/pydantic/pydantic) and
[`encode/httpx` README](https://github.com/encode/httpx) use a recognizable
library sequence: concise purpose, install command, minimal API example,
capabilities, documentation, and contribution links. This is a strong model for
a Python parser whose primary adoption path is package installation.

## 5. What already works well

The current README has valuable material that should be preserved:

- a memorable problem statement;
- visible CI, Python, license, PyPI, and status signals;
- a live visual demonstration;
- a concrete comparison with naive Markdown chunking;
- a topology diagram that explains why hierarchy matters;
- a broad and accurate capability inventory;
- CLI and Python examples;
- direct routes to architecture, Cookbook, security, and contribution guides;
- explicit local-first and zero-telemetry positioning.

The goal is not to make the README generic. It is to make these strengths appear
in the order a new reader needs them.

## 6. Remaining human-readability findings

### 6.1 The first success now appears immediately

The Quickstart now begins at line 29 instead of line 382. It contains one
install command, one parse command, an observable-result explanation, and
short routes into the main workflows. Advanced examples remain in the later
Usage section.

**Result:** the first-command-before-line-80 acceptance target is met without
removing the deeper examples needed by experienced users.

### 6.2 The value proposition repeats

The hero, Vision, Matryca Solution, PKM Landscape, Problem, Solution, comparison
table, and Core Capabilities repeat overlapping claims about hierarchy,
plain-text sovereignty, and AI-ready context.

**Recommendation:** keep one two-sentence definition, one short “why it matters”
comparison, and one diagram. Move broader market positioning to a dedicated
document if it remains important.

### 6.3 Marketing language sometimes outruns evidence

Words such as “ultimate,” “perfect,” “immortality,” and unqualified performance
claims are vivid but can reduce technical trust. Claims such as “60FPS,” “10k+
nodes,” or “35×” should point to a reproducible benchmark or be softened.

**Recommendation:** prefer measured outcomes and scope qualifiers. Example:
“keeps Markdown as the source of truth” is clearer than “immortality of
plain-text.”

### 6.4 The opening navigation is dense

The hero currently exposes many same-weight links in one line. Architecture,
clean architecture, AST primer, Cookbook, issues, knowledge bundle, docs system,
security tooling, changelog, and release process do not all serve the same
first-time-reader need.

**Result:** the hero now keeps five primary routes: Quickstart, Documentation,
Cookbook, Release highlights, and the AI/LLM index. Specialist links remain in
the documentation index.

### 6.5 Wide tables are hard to scan on narrow screens

The four-column PKM landscape and long Core Capabilities cells work on desktop
but are costly on mobile and difficult for screen readers or text extraction.

**Recommendation:** use short bullets for the core promise and reserve tables
for true side-by-side decisions. Split capabilities into four outcome groups:
parse, understand, export, and automate.

### 6.6 Reader identity is implicit

The README serves several audiences—Logseq users, RAG engineers, Python
integrators, agent builders, and contributors—but does not offer an early route
for each.

**Recommendation:** add a compact “Choose your path” block with links:

- Parse one page or a vault.
- Build a RAG pipeline.
- Export to Obsidian or JSON.
- Read or write with an AI agent.
- Contribute to the parser.

## 7. Proposed human-first README architecture

The following order is recommended for a second, separately reviewed change:

1. **Hero:** name, one-sentence outcome, badges, demo.
2. **What it does:** three bullets describing input, transformation, and output.
3. **60-second Quickstart:** install, one CLI command, one observable result.
4. **Choose your workflow:** parse, RAG, export, visualize, agent access.
5. **Why topology matters:** one compact comparison or the existing diagram.
6. **Capabilities:** four grouped blocks with links to detailed docs.
7. **Python API:** one minimal stable-import example.
8. **Safety and compatibility:** local-first, supported Python, optional extras,
   filesystem-write boundary.
9. **Documentation, help, and contribution:** one small resource table.
10. **Roadmap and support.**
11. **Release history:** the one-line list, always at the bottom.

The first successful command is now before line 80 and capabilities are grouped
by user outcome. A future editorial pass may still pursue the 180–220-line
target by consolidating the overlapping positioning sections.

## 8. Plain-language editorial rules

Apply these rules during the proposed rewrite:

- Start sections with the user outcome, then name the subsystem.
- Define LOGOS, SYNAPSE, FORGE, KINETIC, and LENS only where each first appears.
- Prefer sentences with one main idea and concrete verbs.
- Replace broad superlatives with testable, scoped statements.
- Use “Logseq graph” or “vault” consistently; explain the chosen term once.
- Show one canonical install path first; list alternatives afterward.
- Keep code examples runnable and no longer than needed to produce a result.
- Use meaningful link text instead of generic “here” or emoji-only links.
- Treat test counts and release metrics as dated facts; avoid duplicating them in
  evergreen capability sections.
- Link detailed architecture, governance, and historical evidence rather than
  reproducing it.

## 9. AI-agent layer

### 9.1 Implemented now

The AI entry layer now includes:

- [`AGENTS.md`](../AGENTS.md), which gives an arriving agent:

  - a one-paragraph product and source-of-truth definition;
  - a capability-to-entry-point map;
  - stable documentation routes;
  - the install and validation commands;
  - parser, graph, serialization, filesystem, and optional-dependency guardrails;
  - the existing audit-code impact and cycle policy;
- [`llms.txt`](../llms.txt), which follows the proposed standard and supplies a
  curated project summary, essential links, runnable entry points, contribution
  routes, and a lower-priority `Optional` history group; a deterministic
  contract test verifies its structure and every repository target;
- [`.github/copilot-instructions.md`](../.github/copilot-instructions.md), a thin
  GitHub-specific adapter that points back to the canonical agent and machine
  entry points.

The root README links prominently to both `AGENTS.md` and `llms.txt`. This keeps
the human README focused while supporting both operational agents and
inference-time discovery.

### 9.2 Recommended next AI improvements

1. Do not add a manually maintained `llms-full.txt`: the repository already
   publishes Markdown sources, and concatenating them would increase drift and
   context cost. Generate one only when a concrete consumer requires it.
2. Add task-specific nearest-scope `AGENTS.md` files only where parser,
   filesystem-writing, or documentation rules materially differ.
3. Keep `docs/index.md` as the canonical machine entry point and add new
   maintained documents to its executable profile.
4. Test agent onboarding with bounded tasks: locate the stable parser import,
   run one example, identify the write safety boundary, and name the full gate.
5. If the discovery surface expands, generate new entries from the maintained
   profile rather than adding a second manually curated inventory.

## 10. Phased decision plan

| Phase | Change | Expected value | Risk | Approval recommendation |
|---|---|---|---|---|
| **A — complete** | Extract detailed releases, add bottom summary and direct link | High immediate scanability | Low | Keep |
| **B — complete** | Add `AGENTS.md` orientation, `llms.txt`, and thin Copilot routing | Faster, safer cross-tool agent onboarding | Low | Keep |
| **C — complete** | Move Quickstart directly below the hero | Faster first success | Low | Keep |
| **D — proposed** | Collapse Vision, landscape, Problem, and Solution into one concise explanation | Removes repetition and marketing density | Medium editorial judgment | Review wording before merge |
| **E — complete** | Group capabilities by user outcome and shorten the hero navigation | Better scanning and mobile readability | Low | Keep |
| **F — proposed** | Add evidence links or soften performance and comparative claims | Higher technical credibility | Medium; may alter positioning | Review claim by claim |
| **G — optional** | Generate a full-context bundle or scoped agent files | Wider agent compatibility | Risk of duplicated truth | Add only with a concrete consumer |

## 11. Acceptance criteria for the next rewrite

A future README simplification should be accepted only if:

- a new reader can identify input, output, and primary benefit in the first
  screen;
- installation and one successful command appear before line 80;
- the document remains between 180 and 220 lines unless a reviewed example
  justifies exceeding the target;
- all current capability families remain discoverable through direct links;
- stable imports and optional extras remain accurate;
- filesystem-writing features are not presented as unrestricted;
- release detail remains in `RELEASE_HIGHLIGHTS.md` and the summary stays at the
  bottom of the root README;
- human documentation links and AI-agent routes pass deterministic validation;
- `make all`, `make vendor-name-check`, and the zero-cycle check pass;
- no measured claim is added without a reproducible source.

## 12. Recommended next decision

Review Phase D and F separately as the next possible tranche: consolidate the
overlapping positioning sections, then qualify comparative and performance
claims one by one. Both require maintainer review because they change product
voice and positioning, not just document structure.
