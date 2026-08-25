# Post-v1.8.1 backlog execution record — 2026-08-25

This document is the durable execution record for the first repository
reconciliation after v1.8.1. It is an operational checkpoint, not a release,
merge, or universal quality claim.

## Frozen starting point

- Repository: `MarcoPorcellato/logseq-matryca-parser`
- Canonical source: `origin/main`
- Exact source commit:
  `bb8ec6b758e0e7b3429de49ca252ae8b62f97689`
- Isolated branch: `agent/post-v1.8.1-backlog-reconciliation`
- Isolated worktree:
  `/private/tmp/logseq-matryca-parser-post-v181-20260825`
- Primary checkout: preserved and not used as the writer workspace
- Dependency state: `uv sync --locked --all-extras` completed
- Baseline gate: `make all` completed with 760 tests and 91.20% statement
  coverage; Ruff, Mypy, documentation, vendor-name, and package-independent
  quality checks passed

The baseline proves only the exact source, dependency lock, host, and command
recorded above. Hosted checks, a future head, publication, and release remain
separate evidence.

## Objective

Reconcile the post-v1.8.1 programme without inflating completed work or deleting
uncertain history:

1. update the public roadmap, milestones, and Project #5;
2. close or narrow issues only where exact evidence supports the decision;
3. reconcile checklists in #104, #108, #109, #110, and #111;
4. review all seven pull requests open at the frozen starting point;
5. establish #104 as the next implementation tranche and #111 as its successor;
6. investigate and, after design approval, fix bounded LENS bug #92 separately;
7. delete only remote branches proven merged or superseded and not attached to
   an open pull request;
8. qualify and publish each independently reviewable tranche.

## Governing boundaries

- Markdown files and exact live Git/GitHub state outrank cached reports and
  worker summaries.
- All repository-facing text and maintainer messages are English.
- One controller writes. Delegated workers are read-only unless a later task
  explicitly grants a narrow isolated writer role.
- A checked box requires an exact source, test, documentation, workflow, PR, or
  release receipt. Partial evidence remains partial.
- No issue is closed merely because adjacent infrastructure exists.
- No pull request is merged from stale or conflicting evidence. Contributor
  work is preserved or closed only with a concise evidence-based explanation.
- `main`, `gh-pages`, every open-PR branch, and every uncertain remote branch
  are protected from cleanup.
- Issue #92 follows a separate bounded design and test-first cycle. Backlog
  reconciliation does not silently authorize production behavior changes.
- Push, pull-request creation, merge, release, and destructive cleanup are
  distinct external mutations. Existing user instructions authorize the
  repository reconciliation and proven obsolete-branch cleanup, but every
  mutation still requires an exact target and readback.
- No private vault content, credentials, local cache, host identity, or
  source-derived sensitive data enters receipts.

## Frozen live backlog

At the starting point, GitHub reported:

- 38 open issues;
- 24 open issues labelled `good first issue`;
- 7 open pull requests:
  - contributor: #84, #99, #147;
  - automated dependency updates: #181, #182, #183, #184;
- milestone **Parser Assurance: M3-M7** with #104, #108, and #111 open;
- milestone **Evidence-gated improvements** with #185 open and #186 closed;
- 42 remote branches including `main` and `gh-pages`.

Every count is a dated snapshot and must be refreshed before final publication.

## Work packages and completion gates

### R1 — Programme reconciliation

Update `docs/ROADMAP_2026-2027.md` and the assurance goal to record that:

- #103 is merged and its coherent in-process graph-mutation boundary shipped;
- #186 is closed and its stable NLTK registry dependency shipped in v1.8.1;
- M2 supply-chain declaration debt is complete for v1.8.1;
- #104 is the next parser-assurance tranche;
- #111 follows #104 and must not promote budgets before retained measurements;
- #185 remains a research-only interoperability study;
- #108 retains only its residual reducer, semantic-enrichment, equivalence, and
  benchmark gates.

Exit gate:

- active documents agree on status, ordering, and exclusions;
- historical documents are not rewritten as if they were current plans;
- `make docs-check`, `make vendor-name-check`, and `git diff --check` pass.

### R2 — Issue and milestone reconciliation

For #104, #108, #109, #110, and #111:

1. preserve the original intent;
2. mark only items supported by exact evidence;
3. rewrite ambiguous residual work as verifiable acceptance criteria;
4. add a dated reconciliation note or update the body;
5. close only when all acceptance criteria are met, otherwise keep the issue
   open with a smaller explicit scope.

Milestone disposition:

- keep **Parser Assurance: M3-M7** open while #104, #108, or #111 remains;
- keep **Evidence-gated improvements** open while #185 remains;
- do not create a release milestone merely to mirror a published tag.

Exit gate:

- GitHub readback matches the versioned roadmap;
- Project #5 uses the same statuses and next gates;
- no completed item remains described as current focus.

### R3 — Pull-request portfolio

Review #84, #99, #147, and #181–#184 against current `main`.

Each pull request receives one disposition:

- refresh/rebase because unique useful work remains;
- close as superseded, with exact replacement evidence;
- merge only after conflict resolution, exact-head full checks, and review;
- keep open only when an identified external dependency prevents a decision.

Exit gate:

- no open PR is left without a current maintainer decision;
- automated updates are not merged solely because they are newer;
- contributor messages are short, simple, specific, and respectful.

### R4 — Bounded LENS bug #92

Before implementation:

- reproduce or disprove the alias-resolution failure on the current exact base;
- trace the LENS-to-graph resolution path;
- present a short bounded design covering files, behavior, and tests;
- obtain explicit approval for that design.

Implementation gate:

- add the smallest real regression test and observe the expected RED failure;
- make the smallest production change needed for GREEN;
- run focused LENS/graph tests and the complete quality gate;
- update user documentation only if supported behavior changes.

Issue #92 remains separate from #104 and cannot delay documentation-only
backlog reconciliation.

### R5 — Next implementation sequence

#### First: #104 property-based parser assurance

The tranche must reuse existing compatibility fixtures, projectors, semantic
profiles, diagnostic classes, and deterministic replay. It must not create a
second oracle or claim byte-for-byte equivalence where identity policy allows
derived values.

Required planning output:

- bounded Hypothesis strategy grammar;
- explicit size and time limits;
- deterministic seed and minimized replay contract;
- invariant matrix for structure, identity, source lines, references, and
  parse/serialize/parse semantics;
- focused and scheduled workflow placement;
- exact checklist-to-receipt mapping.

#### Second: #111 reproducible performance decisions

Keep the existing small profile immutable. Add large profiles only outside
default CI and preserve source-free receipts. Compare cold load, incremental
edit, controlled search, and context-chunk scenarios. Retain at least three
eligible exact-environment observations before proposing numeric budgets.

No cache, process-pool default, or public performance claim follows
automatically from source inspection or one host.

### R6 — Proven branch cleanup

For each remote branch:

1. identify whether it backs an open PR;
2. test exact ancestry against `origin/main`;
3. locate the merged PR, replacement commit, or release when ancestry alone is
   insufficient;
4. classify it as protected, deletable, or uncertain;
5. delete only the explicitly enumerated deletable set;
6. fetch/prune and confirm each deleted ref is absent.

The cleanup report must retain branch name, proof, deletion result, and
recovery source. No wildcard deletion is permitted.

## Delegation ledger

| Worker tier | Scope | Authority | Required return |
|---|---|---|---|
| GPT-5.3 Codex Spark | issue/checklist evidence audit | read-only | checklist evidence and close/narrow/keep recommendations |
| GPT-5.6 Luna | seven-PR portfolio review | read-only | exact-head disposition and concise maintainer message |
| GPT-5.6 Luna | issue #92 reproduction and design | read-only | reproduction, blast radius, RED test, minimal design |
| GPT-5.3 Codex Spark | remote-branch provenance | read-only | protected/deletable/uncertain table with exact proof |
| Controller | synthesis, writes, GitHub mutations, verification | sole writer | committed diff, live readbacks, qualification receipts |

Worker reports are leads, not proof. The controller independently checks every
claim used for a source edit, GitHub mutation, merge, issue closure, or branch
deletion.

## Publication units

Prefer independently reviewable pull requests:

1. roadmap, goal, and backlog reconciliation record;
2. issue #92 code fix, if the approved design and reproduction support it;
3. #104 implementation design and plan, followed by its own TDD branch;
4. #111 design only after #104 stabilizes;
5. branch cleanup receipt, if a public record adds durable value.

Do not stack behavior changes into the documentation reconciliation PR.

## Restart protocol

On resume:

1. verify `git status --short --branch`, `git rev-parse HEAD`, and
   `git rev-parse origin/main`;
2. preserve any drift or uncommitted work;
3. read this record and the current public roadmap;
4. refresh GitHub issue, PR, milestone, project, and branch state;
5. resume the first incomplete work package;
6. rerun the gate appropriate to every changed file;
7. record exact heads and live readbacks before claiming completion.

## Completion definition

This programme is complete only when:

- active roadmap and assurance documents match live GitHub state;
- the five strategic issue checklists are evidence-reconciled;
- milestones and Project #5 match the documented sequence;
- all seven starting PRs have a documented current disposition;
- #104 is publication-ready as the next implementation tranche and #111 is
  explicitly sequenced behind it;
- #92 is either fixed and qualified or retained with a precise evidence-backed
  blocker;
- every deleted remote branch has exact proof and post-deletion readback;
- the final exact head passes the full applicable local gate and hosted checks
  are reported separately;
- commits, pushes, PRs, merges, and issue/branch mutations have durable URLs or
  hashes.
