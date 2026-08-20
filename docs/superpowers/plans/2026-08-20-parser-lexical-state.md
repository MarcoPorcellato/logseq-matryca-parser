# Private Parser Lexical State Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract private YAML, fence, query, drawer, and eligibility state from `StackMachineParser.parse()` without changing parser semantics or public API.

**Architecture:** Add one dependency-free private lexical-state module with a mutable `_LexicalState` data object and named transition methods. `logos_parser.py` continues to classify lines, build and refresh AST nodes, own pending property lists, and perform every semantic operation; it delegates only the six existing lexical flags and their transitions. Focused state tests establish the transition contract, while existing parser/corpus/round-trip/adversarial/work-growth tests prove no externally observable drift.

**Tech Stack:** Python 3.12+, standard-library `dataclasses` and `typing`, `pytest`, existing `StackMachineParser`, compatibility corpus, parser-assurance laboratories, Ruff, mypy, and Make targets.

**Spec:** `docs/superpowers/specs/2026-08-20-parser-lexical-state-design.md`

## Global Constraints

- Work only from a clean isolated branch based on the live `origin/main` anchor recorded in the specification; retry the all-extras bootstrap if its Git dependency fetch is unavailable.
- Keep the feature private: no package-root export, CLI command, dependency, public type, runtime hook, filesystem authority, or network operation.
- Preserve page title/properties/order, AST node identity, parent/left relations, source lines, references, strict-reference behavior, serialization, recovery, and deterministic tree order.
- `_LineClassification` remains the syntax recognizer. The new module accepts only primitive flags and must not import graph, writer, CLI, adapters, `LogseqNode`, or `LogseqPage`.
- Do not copy or adapt external parser code, test material, schemas, control flow, or documentation. Do not commit vault data, generated caches, or runtime receipts.
- Before modifying `StackMachineParser.parse`, run fresh impact analysis, review direct callers, and stop on an unresolved HIGH or CRITICAL finding unless the maintainer explicitly approves continuation.
- Treat `make all` as unavailable—not passing—if the isolated dependency bootstrap fails. Do not push, create a PR, close an issue, merge, or release without separate explicit authority.

---

## File structure

| Path | Responsibility |
| --- | --- |
| `src/logseq_matryca_parser/_lexical_state.py` | Private mode and eligibility state plus deterministic transition methods. |
| `src/logseq_matryca_parser/logos_parser.py` | Replaces local lexical booleans with `_LexicalState` calls while retaining parser control flow and AST work. |
| `tests/test_parser_lexical_state.py` | Direct unit contract for every lexical state transition, with no AST dependency. |
| `tests/test_logos_parser.py` | Parser-level boundary regressions for transitions that change what a line means. |
| `docs/LSDOC_REFERENCE_STUDY_AND_EXECUTION_PLAN_2026-08-16.md` | Records the M9 implementation checkpoint and remaining #108 boundary only after exact-head qualification. |
| `docs/goals/LSDOC_PARSER_ASSURANCE_GOAL.md` | Advances the persistent assurance anchor only after qualification; it must not claim epic or issue closure. |

## Task 0: Re-establish the isolated baseline

**Files:**

- Modify: none.

**Interfaces:**

- Consumes: the clean worktree and locked project dependencies.
- Produces: a known baseline result or an explicit unavailable dependency receipt before any source edit.

- [ ] **Step 1: Confirm the exact starting point and worktree cleanliness**

Run:

```bash
rtk git status --short --branch
rtk git rev-parse HEAD
rtk git rev-parse origin/main
```

Expected: the working tree is clean and the branch is based on the recorded `origin/main` anchor. If `origin/main` has moved, fetch it, review the intervening commits, and rebase before changing source.

- [ ] **Step 2: Retry the complete baseline once with a writable temporary cache**

Run:

```bash
UV_CACHE_DIR=/private/tmp/logseq-matryca-parser-m9-uv-cache rtk uv sync --all-extras
rtk make all
rtk make vendor-name-check
```

Expected: dependency resolution completes, the complete suite passes, and the vendor-name gate is `OK`. If the pinned `nltk` Git fetch fails again, record the exact transport failure as unavailable, do not edit parser code, and request an environment retry before resuming implementation.

- [ ] **Step 3: Record the parser-hub impact before editing**

Run the repository's configured audit-code impact command against the exact `StackMachineParser.parse` symbol, inspect direct callers and affected processes, then run the zero-cycle check.

Expected: every direct caller is enumerated, the risk is recorded in the implementation notes, and `src/` has zero import cycles. A HIGH or CRITICAL unresolved finding stops this plan pending maintainer approval.

## Task 1: Specify lexical transitions with failing private tests

**Files:**

- Create: `tests/test_parser_lexical_state.py`
- Create later in this task: `src/logseq_matryca_parser/_lexical_state.py`

**Interfaces:**

- Consumes: no parser model or syntax-recognition object; only booleans that `logos_parser.py` already derives from `_LineClassification`.
- Produces: private `_LexicalState` with `mode`, `frontmatter_active`, `properties_allowed`, and named transitions used by `StackMachineParser.parse`.

- [ ] **Step 1: Write the failing transition-contract tests**

Create `tests/test_parser_lexical_state.py` with these assertions:

```python
from logseq_matryca_parser._lexical_state import _LexicalState


def test_yaml_frontmatter_close_disables_page_frontmatter() -> None:
    state = _LexicalState()
    assert state.frontmatter_active is True
    assert state.properties_allowed is True

    state.begin_yaml_frontmatter()
    assert state.mode == "yaml"

    state.finish_yaml_frontmatter()
    assert state.mode == "normal"
    assert state.frontmatter_active is False


def test_code_and_query_closures_restore_existing_eligibility() -> None:
    state = _LexicalState()
    state.begin_code_block()
    state.consume_code_line(is_code_fence=True)
    assert state.mode == "normal"
    assert state.properties_allowed is True

    state.begin_query_block()
    state.consume_query_line(is_query_end=True)
    assert state.mode == "normal"
    assert state.frontmatter_active is False


def test_drawer_bullet_returns_to_normal_processing() -> None:
    state = _LexicalState()
    state.begin_drawer()
    assert state.mode == "drawer"

    assert state.consume_drawer_line(is_drawer_end=False, is_bullet=True) is False
    assert state.mode == "normal"


def test_structural_property_and_continuation_events_match_current_flags() -> None:
    state = _LexicalState()
    state.observe_structural_node()
    assert state.frontmatter_active is False
    assert state.properties_allowed is True

    state.observe_continuation(is_code_fence=True, is_query_begin=False)
    assert state.mode == "code"
    assert state.properties_allowed is False
```

- [ ] **Step 2: Run the new tests and confirm the expected collection failure**

Run:

```bash
rtk uv run pytest -q tests/test_parser_lexical_state.py
```

Expected: collection fails because `logseq_matryca_parser._lexical_state` does not exist. Do not weaken the tests to pass without the private module.

- [ ] **Step 3: Implement the smallest dependency-free state unit**

Create `src/logseq_matryca_parser/_lexical_state.py` using a private mutable data class and these exact members:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

_LexicalMode = Literal["normal", "yaml", "code", "query", "drawer"]


@dataclass
class _LexicalState:
    mode: _LexicalMode = "normal"
    frontmatter_active: bool = True
    properties_allowed: bool = True

    def begin_yaml_frontmatter(self) -> None:
        self.mode = "yaml"

    def finish_yaml_frontmatter(self) -> None:
        self.mode = "normal"
        self.frontmatter_active = False

    def begin_code_block(self) -> None:
        self.mode = "code"
        self.frontmatter_active = False
        self.properties_allowed = False

    def consume_code_line(self, *, is_code_fence: bool) -> None:
        if is_code_fence:
            self.mode = "normal"
            self.properties_allowed = True
        self.frontmatter_active = False

    def begin_query_block(self) -> None:
        self.mode = "query"
        self.frontmatter_active = False
        self.properties_allowed = False

    def consume_query_line(self, *, is_query_end: bool) -> None:
        if is_query_end:
            self.mode = "normal"
        self.frontmatter_active = False

    def begin_drawer(self) -> None:
        self.mode = "drawer"

    def consume_drawer_line(self, *, is_drawer_end: bool, is_bullet: bool) -> bool:
        if is_drawer_end or is_bullet:
            self.mode = "normal"
            return False
        return True

    def observe_structural_node(self) -> None:
        self.frontmatter_active = False
        self.properties_allowed = True

    def observe_property(self) -> None:
        self.frontmatter_active = False

    def observe_continuation(self, *, is_code_fence: bool, is_query_begin: bool) -> None:
        self.frontmatter_active = False
        self.properties_allowed = False
        if is_code_fence:
            self.begin_code_block()
        if is_query_begin:
            self.begin_query_block()

    def observe_nonstructural_line_without_node(self) -> None:
        self.frontmatter_active = False
```

`consume_drawer_line()` returns `True` only when the caller must keep treating the line as drawer payload. It must return `False` and restore `normal` mode for `:END:` and a bullet, so `parse()` retains its current bullet-processing path. The module must import only the standard library.

- [ ] **Step 4: Run the state contract and static checks**

Run:

```bash
rtk uv run pytest -q tests/test_parser_lexical_state.py
rtk uv run ruff check src/logseq_matryca_parser/_lexical_state.py tests/test_parser_lexical_state.py
rtk uv run mypy src/logseq_matryca_parser/_lexical_state.py
```

Expected: all state tests, lint, and typing pass without importing parser models or public package symbols.

- [ ] **Step 5: Commit the private-state unit**

```bash
rtk git add -- src/logseq_matryca_parser/_lexical_state.py tests/test_parser_lexical_state.py
rtk git commit -m "refactor(parser): isolate lexical state transitions"
```

## Task 2: Add parser-level boundary regressions before routing the loop

**Files:**

- Modify: `tests/test_logos_parser.py`
- Modify: `tests/test_pre_release_roundtrip.py`

**Interfaces:**

- Consumes: the existing `StackMachineParser` public behavior and the private state contract from Task 1.
- Produces: parser-level guardrails that make a lexical extraction fail on semantic drift.

- [ ] **Step 1: Add one mixed-boundary regression**

Add this test to `tests/test_logos_parser.py`:

```python
def test_lexical_boundaries_keep_properties_out_of_query_and_drawer(
    parser: StackMachineParser,
) -> None:
    source = (
        "- Root\n"
        "  ```\n"
        "  literal:: fence\n"
        "  ```\n"
        "  tags:: [[Visible]]\n"
        "  #+BEGIN_QUERY\n"
        "  query:: [[HiddenQuery]]\n"
        "  #+END_QUERY\n"
        "  :LOGBOOK:\n"
        "  collapsed:: true\n"
        "  :END:\n"
        "  - Child"
    )

    page = parser.parse(source, page_title="lexical-boundaries")
    root = page.root_nodes[0]

    assert root.properties["tags"] == "[[Visible]]"
    assert "query" not in root.properties
    assert "collapsed" not in root.properties
    assert "literal:: fence" in root.content
    assert "query:: [[HiddenQuery]]" in root.content
    assert "collapsed:: true" in root.properties["logbook"]
    assert root.children[0].content == "Child"
```

- [ ] **Step 2: Add a frontmatter-eligibility regression**

Add this test to `tests/test_logos_parser.py`:

```python
def test_nonstructural_preamble_closes_page_frontmatter_eligibility(
    parser: StackMachineParser,
) -> None:
    page = parser.parse(
        "title:: Page title\nplain preamble\nalias:: MustNotBecomePageProperty\n- Root",
        page_title="fallback",
    )

    assert page.title == "Page title"
    assert page.properties == {"title": "Page title"}
    assert page.root_nodes[0].content == "Root"
```

- [ ] **Step 3: Run the new parser tests and verify they pass before production routing**

Run:

```bash
rtk uv run pytest -q \
  tests/test_logos_parser.py::test_lexical_boundaries_keep_properties_out_of_query_and_drawer \
  tests/test_logos_parser.py::test_nonstructural_preamble_closes_page_frontmatter_eligibility
```

Expected: both tests pass on the un-routed parser, proving they freeze existing behavior rather than specifying a new feature.

- [ ] **Step 4: Run the reusable lexical regressions**

Run:

```bash
rtk uv run pytest -q \
  tests/test_logos_parser.py::test_yaml_frontmatter_is_parsed_as_page_properties \
  tests/test_logos_parser.py::test_fenced_code_shields_graph_tokens \
  tests/test_logos_parser.py::test_tilde_fence_shields_graph_tokens \
  tests/test_logos_parser.py::test_query_block_shields_graph_tokens \
  tests/test_logos_parser.py::test_properties_allowed_after_code_fence \
  tests/test_logos_parser.py::test_official_logbook_drawer_preserves_clock_metadata \
  tests/test_pre_release_roundtrip.py::test_logbook_drawer_roundtrip \
  tests/test_pre_release_roundtrip.py::test_yaml_frontmatter_roundtrip_preserves_block_uuid
```

Expected: all pass before `logos_parser.py` is changed.

## Task 3: Route `StackMachineParser.parse()` through the private state

**Files:**

- Modify: `src/logseq_matryca_parser/logos_parser.py:696-1057`
- Test: `tests/test_parser_lexical_state.py`
- Test: `tests/test_logos_parser.py`
- Test: `tests/test_pre_release_roundtrip.py`

**Interfaces:**

- Consumes: `_LexicalState` from Task 1 and `_LineClassification` already produced by `_classify_line()`.
- Produces: the same `LogseqPage` result as before, with lexical flags no longer stored as local booleans in `parse()`.

- [ ] **Step 1: Import and initialize only the private state object**

Replace the six local lexical booleans in `parse()` with:

```python
from ._lexical_state import _LexicalState

# inside StackMachineParser.parse()
lexical_state = _LexicalState()
```

Keep `pending_list_key`, `pending_list_items`, `pending_list_indent`,
`current_node`, `stack`, and all AST collections local to `parse()`.

- [ ] **Step 2: Route YAML transitions without moving page-property ownership**

Use `lexical_state.mode == "yaml"`,
`lexical_state.begin_yaml_frontmatter()`, and
`lexical_state.finish_yaml_frontmatter()` in the existing YAML branches. Keep
the current `page_properties`, `page_properties_order`, and title-override
updates in `parse()` exactly where they are.

- [ ] **Step 3: Route query, fence, and drawer transitions without moving content handling**

Replace only the mode/eligibility assignments in existing branches:

```python
lexical_state.consume_query_line(is_query_end=line.is_query_end)
lexical_state.consume_code_line(is_code_fence=line.is_code_fence)
keep_drawer_payload = lexical_state.consume_drawer_line(
    is_drawer_end=line.is_drawer_end,
    is_bullet=line.bullet_match is not None,
)
```

When `keep_drawer_payload` is `False`, preserve the current `continue` behavior
for `:END:` and preserve fall-through to normal bullet processing for a bullet.
Do not move LOGBOOK metadata, CLOCK parsing, node refresh, or pending-list
clearing into `_lexical_state.py`.

- [ ] **Step 4: Route normal-mode eligibility updates**

Replace each existing assignment to `frontmatter_active` or
`properties_allowed` with the matching state transition:

```python
lexical_state.observe_structural_node()
lexical_state.observe_property()
lexical_state.observe_continuation(
    is_code_fence=line.is_code_fence,
    is_query_begin=line.is_query_begin,
)
lexical_state.observe_nonstructural_line_without_node()
```

Use `lexical_state.frontmatter_active` and
`lexical_state.properties_allowed` in the unchanged property branches. Do not
introduce a generic dispatcher or alter branch ordering.

- [ ] **Step 5: Run focused equivalence and static validation**

Run:

```bash
rtk uv run pytest -q \
  tests/test_parser_lexical_state.py \
  tests/test_logos_parser.py \
  tests/test_pre_release_roundtrip.py \
  tests/test_compat_corpus.py \
  tests/test_parser_adversarial.py \
  tests/test_parser_deep_refresh.py \
  tests/test_parser_work_growth.py
rtk uv run ruff check src/logseq_matryca_parser/_lexical_state.py src/logseq_matryca_parser/logos_parser.py tests/test_parser_lexical_state.py tests/test_logos_parser.py tests/test_pre_release_roundtrip.py
rtk uv run mypy src/logseq_matryca_parser/_lexical_state.py src/logseq_matryca_parser/logos_parser.py
```

Expected: every targeted semantic, deep-refresh, corpus, and work-growth test passes; lint and typing pass.

- [ ] **Step 6: Commit the routed parser slice**

```bash
rtk git add -- src/logseq_matryca_parser/_lexical_state.py src/logseq_matryca_parser/logos_parser.py tests/test_parser_lexical_state.py tests/test_logos_parser.py tests/test_pre_release_roundtrip.py
rtk git commit -m "refactor(parser): route lexical modes through private state"
```

## Task 4: Qualify the exact head and update assurance records

**Files:**

- Modify: `docs/LSDOC_REFERENCE_STUDY_AND_EXECUTION_PLAN_2026-08-16.md`
- Modify: `docs/goals/LSDOC_PARSER_ASSURANCE_GOAL.md`

**Interfaces:**

- Consumes: the exact implementation SHA, terminal validation results, impact/cycle evidence, and independent review conclusion.
- Produces: a precise M9 checkpoint that does not claim #108, #87, #103, #104, or #111 closure.

- [ ] **Step 1: Run exact-head repository qualification**

Run:

```bash
rtk make all
rtk make vendor-name-check
rtk git diff --check origin/main...HEAD
```

Expected: all commands pass from a clean worktree. If the dependency bootstrap blocks `make all`, leave documentation unchanged and recover the environment first.

- [ ] **Step 2: Run final structural checks and inspect the complete diff**

Run the repository's audit-code cycle check, then its change-impact command
against `origin/main...HEAD`. Inspect every parser-related affected process and
all direct dependents before review.

Expected: zero source import cycles, no unexpected API or dependency impact,
and a complete diff limited to the private lexical module, parser routing,
tests, and the two evidence records.

- [ ] **Step 3: Request an independent exact-head review**

Give a low-cost reviewer only the exact base SHA, implementation SHA, changed
files, focused test results, full-suite result, impact summary, and the
requirement that it report only actionable correctness defects. The primary
maintainer decides whether any finding is valid and runs a focused regression
before accepting a correction.

Expected: no unresolved actionable finding. A valid finding restarts the
relevant focused test and exact-head qualification cycle.

- [ ] **Step 4: Record only terminal evidence**

Update the M7/M8 continuation and execution ledger in
`docs/LSDOC_REFERENCE_STUDY_AND_EXECUTION_PLAN_2026-08-16.md` with the exact
M9 SHA, tested scope, validation results, reviewer conclusion, and residual
boundary. Update `docs/goals/LSDOC_PARSER_ASSURANCE_GOAL.md` to point to the
new checkpoint. State explicitly that this is a second private #108 slice and
that the epic, #87, #103, #104, and #111 remain open.

- [ ] **Step 5: Validate records and commit the evidence update**

Run:

```bash
rtk make docs-check
rtk make vendor-name-check
rtk git diff --check origin/main...HEAD
```

Then commit only the two evidence records:

```bash
rtk git add -- docs/LSDOC_REFERENCE_STUDY_AND_EXECUTION_PLAN_2026-08-16.md docs/goals/LSDOC_PARSER_ASSURANCE_GOAL.md
rtk git commit -m "docs(parser): record lexical state slice"
```

Expected: documentation validation and the vendor-name gate pass. The commit is local evidence only until a separately authorized push and PR.

## Final review checklist

- [ ] The private module contains only lexical state and standard-library imports.
- [ ] `StackMachineParser.parse()` retains AST, identity, property-value, and recovery behavior.
- [ ] The new direct-state tests and parser boundary regressions pass on the exact implementation head.
- [ ] Corpus, round-trip, deep-refresh, adversarial, and work-growth evidence pass on the same head.
- [ ] Full qualification, vendor-name check, diff check, impact review, zero-cycle check, and independent review are terminal.
- [ ] Documentation records only verified evidence and does not close the parent epic or unrelated issues.
- [ ] Push, PR creation, merge, issue changes, and release remain separate explicit gates.
