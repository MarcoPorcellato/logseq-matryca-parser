# Graph Mutation Coherence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serialize one-process graph mutations and publish complete graph-index versions so writers, watchers, and readers cannot lose updates or observe mixed state.

**Architecture:** Add a private frozen `_GraphSnapshot` candidate and one `RLock` per `LogseqGraph`. Build every incremental delta against copied mappings, publish all fields under the lock, make readers capture one version, wrap the writer's complete transaction in the same re-entrant scope, and move user callbacks to an ordered daemon dispatcher. Preserve synchronous APIs and targeted backlink repair.

**Tech Stack:** Python 3.12+, standard-library `dataclasses`, `threading`, and `queue`, Pydantic v2 private attributes, pytest, existing watchdog mocks, Ruff, mypy, and repository Make targets.

**Spec:** `docs/superpowers/specs/2026-08-21-graph-mutation-coherence-design.md`

## Global Constraints

- Start from a clean branch whose verified base contains `main@8e2bc893dea34b756edb6632e04917b04a68c1e6`; fetch and review any newer `origin/main` before editing.
- Use one private `threading.RLock` per `LogseqGraph`; never add a process-global lock.
- Preserve all synchronous public signatures and package-root exports.
- Never mutate a published pages dictionary, registry dictionary, or backlink list while constructing a candidate.
- Preserve targeted incremental backlink repair; do not call `_build_backlink_registry()` from incremental reload.
- Keep writer path, symlink, `file://`, size, identity, permission, `fsync`, temporary-file, and `os.replace()` protections unchanged.
- Callbacks run only after successful publication, in publication order, outside the graph lock.
- Use `Barrier`, `Event`, and bounded future waits; do not add `time.sleep()` to concurrency tests.
- Keep all documentation and operator messages in English and use neutral `audit code` terminology.
- Do not push, mark ready, merge, close #103, publish, or release without the separately required maintainer gate.

---

## File structure

| Path | Responsibility |
| --- | --- |
| `src/logseq_matryca_parser/graph.py` | Snapshot candidate, per-instance coordination, coherent readers, incremental publication, watcher callback dispatcher. |
| `src/logseq_matryca_parser/agent_writer.py` | Complete writer transaction under the graph mutation scope. |
| `tests/test_graph_concurrency.py` | Deterministic rollback, reader, rename, convergence, callback, and per-instance-lock tests. |
| `tests/test_agent_writer.py` | Concurrent append regression and normal writer refresh behavior. |
| `tests/test_graph.py` | Existing watcher and incremental-registry contracts; modify only where a new helper is the real production boundary. |
| `tests/test_writer_security.py` | Existing security suite; add no weaker expectations. |
| `docs/ARCHITECTURE.md` | Supported one-process mutation and point-in-time `pages` compatibility contract. |
| `docs/CLEAN_CODE_ARCHITECTURE.md` | Ownership and dependency boundary for graph coordination. |
| `docs/reference/AGENT_ACTION_CONTRACT.md` | Writer/watcher authority and receipt behavior if the new contract changes operator guidance. |

## Task 0: Re-establish the exact baseline

**Files:**

- Modify: none.

**Interfaces:**

- Consumes: the approved design, live `origin/main`, local audit-code index, and locked dependencies.
- Produces: exact baseline receipts and a clean execution branch.

- [ ] **Step 1: Verify path, branch, HEAD, base, and cleanliness**

Run:

```bash
rtk git status --short --branch
rtk git rev-parse HEAD
rtk git rev-parse origin/main
rtk git merge-base HEAD origin/main
```

Expected: no tracked changes before implementation. If `origin/main` moved,
fetch it, inspect the intervening commits, and reconcile before changing source.

- [ ] **Step 2: Run the focused pre-change baseline**

Run:

```bash
rtk env UV_CACHE_DIR=/private/tmp/logseq-matryca-parser-103-uv-cache uv run pytest -q tests/test_graph.py tests/test_agent_writer.py tests/test_writer_security.py tests/test_runtime_evidence.py
```

Expected: the existing focused suite passes. A failure is a baseline defect and
must be diagnosed before implementation.

- [ ] **Step 3: Refresh and record hub impact**

Refresh the local audit-code index, then run upstream impact for
`LogseqGraph.invalidate_and_reload_page`, context for
`append_child_to_node` and watcher routing, change detection, and the source
cycle check.

Expected: the HIGH reload impact is acknowledged under the maintainer's #103
approval, direct callers are enumerated, and source import cycles equal zero.

## Task 1: Freeze rollback and coherent-reader behavior with RED tests

**Files:**

- Create: `tests/test_graph_concurrency.py`
- Modify later: `src/logseq_matryca_parser/graph.py`

**Interfaces:**

- Consumes: current `LogseqGraph.load_directory()`, public page/node/backlink lookup, and `invalidate_and_reload_page()`.
- Produces: tests that fail on partial publication and failed-refresh corruption.

- [ ] **Step 1: Add a reusable public-state projection**

Create `tests/test_graph_concurrency.py` with a helper that derives expectations
from public behavior rather than implementation dictionaries:

```python
def _public_graph_projection(graph: LogseqGraph, targets: tuple[str, ...]) -> dict[str, object]:
    pages = tuple(
        (page.title, tuple(node.uuid for node in _walk(page.root_nodes)))
        for page in graph.iter_canonical_pages()
    )
    return {
        "pages": pages,
        "nodes": tuple(
            (uuid, graph.get_node_by_uuid(uuid) is not None)
            for _title, uuids in pages
            for uuid in uuids
        ),
        "backlinks": tuple(
            (target, tuple(node.uuid for node in graph.get_backlinks(target)))
            for target in targets
        ),
        "casefold_pages": tuple(
            (target, graph.get_page(target.casefold()).title if graph.get_page(target.casefold()) else None)
            for target in targets
        ),
        "diagnostics": graph.index_diagnostics,
    }
```

Implement `_walk()` as an iterative local test helper. Do not call private graph
builders to compute expected values.

- [ ] **Step 2: Add the failed-refresh rollback test**

Add a test that loads a page and backlink source, records the public projection,
changes the source file, patches `StackMachineParser.parse_page_file` to raise
`RuntimeError`, invokes reload, and asserts the exception propagates and the
entire prior projection is unchanged.

Production mutation that this test catches: stale UUID/backlink removal before
parsing succeeds.

- [ ] **Step 3: Add the reader-versus-reload test**

Use two `Event` objects and patch `_build_lower_title_map` to pause candidate
construction. Start reload in one future, wait until the build boundary is
entered, read page, UUID, backlink, and title routing from another future, then
release the builder and inspect the new version.

Assert that the concurrent read equals either the complete old projection or
the complete new projection and never a mixture. Do not assert elapsed time.

Production mutation that this test catches: assigning pages or removing nodes
before all candidate indexes are ready.

- [ ] **Step 4: Verify RED for the expected reasons**

Run:

```bash
rtk env UV_CACHE_DIR=/private/tmp/logseq-matryca-parser-103-uv-cache uv run pytest -q \
  tests/test_graph_concurrency.py::test_failed_refresh_preserves_complete_prior_version \
  tests/test_graph_concurrency.py::test_reader_never_observes_mixed_indexes_during_reload
```

Expected on the pre-change implementation: both tests fail on projection
mismatch, not collection, syntax, or timeout errors.

## Task 2: Build and publish an isolated candidate

**Files:**

- Modify: `src/logseq_matryca_parser/graph.py`
- Test: `tests/test_graph_concurrency.py`
- Test: `tests/test_graph.py`

**Interfaces:**

- Produces: `_GraphSnapshot`, `_capture_snapshot_locked()`,
  `_build_incremental_candidate_locked()`, `_publish_snapshot_locked()`, and
  `_mutation_scope()`.
- Consumes: existing page enrichment and targeted backlink semantics.

- [ ] **Step 1: Add the private snapshot and per-instance lock**

Add standard-library imports for `contextmanager`, `dataclass`, and
`AbstractContextManager` only as needed. Define:

```python
@dataclass(frozen=True, slots=True)
class _GraphSnapshot:
    pages: dict[str, LogseqPage]
    node_registry: dict[str, LogseqNode]
    backlink_registry: dict[str, list[str]]
    lower_title_map: dict[str, str]
    index_diagnostics: tuple[Diagnostic, ...]
```

Add this Pydantic private attribute:

```python
_coordination_lock: threading.RLock = PrivateAttr(default_factory=threading.RLock)
```

Expose no package-root symbol. Add a private context manager `_mutation_scope()`
that acquires the lock and yields `None`.

- [ ] **Step 2: Refactor incremental helpers to explicit candidate mappings**

Extract pure private helpers with these responsibilities and signatures:

```python
def _clone_backlink_registry(registry: dict[str, list[str]]) -> dict[str, list[str]]: ...
def _purge_stale_page_uuids_from(
    node_registry: dict[str, LogseqNode],
    backlink_registry: dict[str, list[str]],
    stale: set[str],
) -> None: ...
def _register_page_nodes_in(registry: dict[str, LogseqNode], page: LogseqPage) -> None: ...
def _append_page_backlinks_in(
    pages: dict[str, LogseqPage],
    registry: dict[str, list[str]],
    page: LogseqPage,
) -> None: ...
```

Refactor incoming-wikilink capture and reindex helpers to accept explicit old
or candidate pages, nodes, and backlinks. Keep the current deterministic source
ordering. Existing wrapper methods may delegate to the new helpers while tests
are migrated, but no candidate helper may touch `self`.

- [ ] **Step 3: Build the candidate before publication**

Inside `_build_incremental_candidate_locked(resolved: Path)`, capture current
references, copy `pages`, deep-copy backlink lists, and copy the node registry.
Remove the old page only from candidate mappings. Parse and enrich the fresh
page if it exists. Recompute the lower title map after enrichment. Repair old
and new incoming wikilink contributions against explicit mappings.

Return `_GraphSnapshot`; do not assign graph fields in this method. Preserve
the current diagnostics tuple unless this task adds a separately tested
diagnostic rebuild.

- [ ] **Step 4: Publish all fields under the lock**

Implement `_publish_snapshot_locked(candidate)` as the only assignment point
for the five graph-version fields. Rewrite `invalidate_and_reload_page()` to:

```python
with self._mutation_scope():
    resolved = Path(file_path).expanduser().resolve()
    if not self._resolved_path_is_tracked_markdown(resolved):
        return
    candidate = self._build_incremental_candidate_locked(resolved)
    self._publish_snapshot_locked(candidate)
```

Logging occurs only after publication. Any exception propagates before the
assignment point.

- [ ] **Step 5: Make supported readers capture one version**

Wrap complete scalar/list-producing read operations in the same lock. Iterator
methods capture immutable references or materialized tuples while locked and
yield afterward. Ensure nested methods use the `RLock` rather than bypassing
coordination.

At minimum audit every method reading `pages`, `_node_registry`,
`_backlink_registry`, `_lower_title_map`, or `_index_diagnostics` with:

```bash
rtk rg -n "self\.(pages|_node_registry|_backlink_registry|_lower_title_map|_index_diagnostics)" src/logseq_matryca_parser/graph.py
```

- [ ] **Step 6: Verify GREEN and existing incremental behavior**

Run:

```bash
rtk env UV_CACHE_DIR=/private/tmp/logseq-matryca-parser-103-uv-cache uv run pytest -q \
  tests/test_graph_concurrency.py \
  tests/test_graph.py::test_graph_incremental_page_invalidation \
  tests/test_graph.py::test_invalidate_and_reload_purges_deleted_page \
  tests/test_graph.py::test_incremental_rename_reindexes_backlinks_without_a_global_rebuild \
  tests/test_graph.py::test_incremental_deletion_rebuilds_backlinks_like_cold_load
rtk uv run ruff check src/logseq_matryca_parser/graph.py tests/test_graph_concurrency.py
rtk uv run mypy src/logseq_matryca_parser/graph.py tests/test_graph_concurrency.py
```

Expected: new rollback/reader tests and existing incremental tests pass. The
global-backlink-rebuild guard must remain active.

- [ ] **Step 7: Commit the coherent graph core**

```bash
rtk git add -- src/logseq_matryca_parser/graph.py tests/test_graph_concurrency.py tests/test_graph.py
rtk git commit -m "feat(graph): publish coherent incremental snapshots"
```

## Task 3: Serialize the complete writer transaction

**Files:**

- Modify: `tests/test_agent_writer.py`
- Modify: `src/logseq_matryca_parser/agent_writer.py`
- Verify: `tests/test_writer_security.py`

**Interfaces:**

- Consumes: `LogseqGraph._mutation_scope()` and re-entrant reload.
- Produces: lost-update-free append and coherent dry-run generation.

- [ ] **Step 1: Add a deterministic simultaneous-append regression**

Create two worker calls to append distinct child literals to the same parent.
Patch `_read_validated_target` with a wrapper whose first two thread entries
meet at a `Barrier` with a bounded timeout before returning the real read.

On the old code both calls read the same source and only one child persists. On
the coordinated code the first waiter reaches the timeout, completes, and the
second call reads the updated source. Assert both futures return successfully,
each literal appears exactly once on disk, and a cold load sees both children.

Do not patch `os.replace()` or reload; the test must exercise the real writer
transaction.

- [ ] **Step 2: Verify RED**

Run:

```bash
rtk env UV_CACHE_DIR=/private/tmp/logseq-matryca-parser-103-uv-cache uv run pytest -q tests/test_agent_writer.py::test_simultaneous_appends_preserve_both_children
```

Expected: FAIL because one requested child is absent.

- [ ] **Step 3: Wrap append and dry-run in the graph mutation scope**

Move the existing function body under:

```python
with graph._mutation_scope():
    return _append_child_to_node_locked(...)
```

Extract the existing body to one private helper only if needed to keep nesting
readable. Preserve every validation and exception path. The scope begins before
`get_node_by_uuid()` and ends after `invalidate_and_reload_page()`.

- [ ] **Step 4: Verify GREEN and the security boundary**

Run:

```bash
rtk env UV_CACHE_DIR=/private/tmp/logseq-matryca-parser-103-uv-cache uv run pytest -q tests/test_agent_writer.py tests/test_writer_security.py tests/test_graph_concurrency.py
rtk uv run ruff check src/logseq_matryca_parser/agent_writer.py tests/test_agent_writer.py
rtk uv run mypy src/logseq_matryca_parser/agent_writer.py tests/test_agent_writer.py
```

Expected: concurrent append passes and every writer security regression remains
green.

- [ ] **Step 5: Commit writer serialization**

```bash
rtk git add -- src/logseq_matryca_parser/agent_writer.py tests/test_agent_writer.py
rtk git commit -m "fix(writer): serialize graph append transactions"
```

## Task 4: Isolate and order watcher callbacks

**Files:**

- Modify: `tests/test_graph_concurrency.py`
- Modify: `src/logseq_matryca_parser/graph.py`
- Verify: `tests/test_graph.py`

**Interfaces:**

- Produces: `_OrderedCallbackDispatcher`, watcher reload convergence, and
  bounded callback lifecycle.
- Consumes: the coherent reload and existing debouncer.

- [ ] **Step 1: Add RED tests for callback nonblocking, order, and isolation**

Use the existing mocked `watchdog.observers.Observer` pattern to obtain the
real scheduled event handler. Supply a callback that records paths, blocks the
first delivery on an `Event`, and optionally raises on one path.

Assert without sleeps that:

- handler-triggered reload returns before the blocked callback is released;
- two published paths are observed in publication order;
- an exception from the first callback does not prevent the second;
- `watcher.stop()` returns within its documented bounded join after callback
  admission closes.

Expected on the old implementation: the nonblocking test cannot reach the
post-handler assertion until the callback is released.

- [ ] **Step 2: Add RED rename and writer-replay convergence tests**

For rename, drive the real handler with a fake moved event in both source-first
and destination-first scheduling orders. For writer replay, append a child and
then route the resulting destination path again. Compare the public projection
with a cold load after each sequence.

- [ ] **Step 3: Implement the ordered daemon dispatcher**

Add a private queue-backed dispatcher that:

```python
class _OrderedCallbackDispatcher:
    def __init__(self, callback: Callable[[Path], None]) -> None: ...
    def start(self) -> Self: ...
    def submit(self, path: Path) -> None: ...
    def close(self, *, timeout: float = 5.0) -> None: ...
```

It owns one daemon `threading.Thread`, one FIFO `queue.Queue`, one sentinel, and
one closed flag. `_run()` catches `Exception` around each user callback and logs
it without recording source content. `submit()` is nonblocking and rejects
admission after close. `close()` enqueues the sentinel once and performs only a
bounded join.

- [ ] **Step 4: Route watcher callbacks after successful publication**

Start the dispatcher only when a user callback exists. `_route_event()` calls
the coherent reload first and then `dispatcher.submit(path)`. A reload exception
must skip callback submission and remain visible through logging or the current
watcher error path. `stop()` cancels timers, stops the observer, and closes the
dispatcher without holding the graph lock.

- [ ] **Step 5: Verify GREEN**

Run:

```bash
rtk env UV_CACHE_DIR=/private/tmp/logseq-matryca-parser-103-uv-cache uv run pytest -q tests/test_graph_concurrency.py tests/test_graph.py
rtk uv run ruff check src/logseq_matryca_parser/graph.py tests/test_graph_concurrency.py tests/test_graph.py
rtk uv run mypy src/logseq_matryca_parser/graph.py tests/test_graph_concurrency.py tests/test_graph.py
```

Expected: callback, rename, replay, and existing watcher tests pass without new
sleeps.

- [ ] **Step 6: Commit watcher isolation**

```bash
rtk git add -- src/logseq_matryca_parser/graph.py tests/test_graph_concurrency.py tests/test_graph.py
rtk git commit -m "feat(graph): isolate ordered watcher callbacks"
```

## Task 5: Complete lifecycle parity and documentation

**Files:**

- Modify: `tests/test_graph_concurrency.py`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/CLEAN_CODE_ARCHITECTURE.md`
- Modify if behavior requires: `docs/reference/AGENT_ACTION_CONTRACT.md`

**Interfaces:**

- Produces: the #103 acceptance matrix and the lifecycle evidence later consumed by #104.

- [ ] **Step 1: Add table-driven create/edit/delete/rename parity**

For each operation, build one incremental graph and one cold graph from the same
final source. Compare canonical pages, node identities, case-insensitive title
routing, aliases, and backlinks with `_public_graph_projection()`.

Add a separate test proving two graph instances have distinct coordination
locks and can mutate unrelated vaults without serializing on one shared lock.

- [ ] **Step 2: Document the supported contract**

Add an English architecture section stating:

- guarantees are one vault, one `LogseqGraph`, one process;
- supported readers see complete versions;
- `graph.pages` is a point-in-time compatibility mapping and direct mutation is
  unsupported;
- writers and watchers share one per-instance coordinator;
- callbacks are ordered and isolated after successful publication;
- cross-process locking is deferred.

Update clean-code ownership tables without introducing a new public layer or
dependency. Update the agent action contract only if its current writer/watcher
authority text would otherwise become false.

- [ ] **Step 3: Run focused issue qualification**

Run:

```bash
rtk env UV_CACHE_DIR=/private/tmp/logseq-matryca-parser-103-uv-cache uv run pytest -q \
  tests/test_graph_concurrency.py tests/test_graph.py tests/test_agent_writer.py \
  tests/test_writer_security.py tests/test_runtime_evidence.py tests/test_compat_corpus.py
rtk make docs-check
rtk make vendor-name-check
rtk git diff --check origin/main...HEAD
```

Expected: all focused behavior and documentation gates pass.

- [ ] **Step 4: Commit lifecycle evidence and documentation**

```bash
rtk git add -- tests/test_graph_concurrency.py docs/ARCHITECTURE.md docs/CLEAN_CODE_ARCHITECTURE.md docs/reference/AGENT_ACTION_CONTRACT.md
rtk git commit -m "docs(graph): define coherent mutation contract"
```

If `AGENT_ACTION_CONTRACT.md` is unchanged, omit it from `git add`.

## Task 6: Exact-head qualification and review

**Files:**

- Verify: the complete branch.
- External state later: draft PR and issue #103.

**Interfaces:**

- Consumes: all previous commits.
- Produces: exact-head local evidence and a reviewable branch; no merge or issue closure by implication.

- [ ] **Step 1: Run the full repository gate**

Run:

```bash
rtk env UV_CACHE_DIR=/private/tmp/logseq-matryca-parser-103-uv-cache make all
rtk make vendor-name-check
rtk git diff --check origin/main...HEAD
rtk git status --short --branch
```

Expected: Ruff, mypy, docs, vendor check, full tests, and coverage gate pass on
the exact clean head.

- [ ] **Step 2: Run final structural and impact checks**

Refresh the audit-code index at the exact head. Run source cycle check, compare
change detection against `origin/main`, and rerun upstream impact for reload and
writer hubs. Inspect every direct dependent and every affected process.

Expected: zero source import cycles, no unexplained file or public API impact,
and all HIGH-risk paths covered by focused tests.

- [ ] **Step 3: Obtain independent concurrency review**

Provide the reviewer with the exact base/head SHAs, spec, full diff, RED/GREEN
receipts, focused/full results, impact summary, and these review questions:

- Can any published mapping or list still be mutated after publication?
- Can any supported reader combine two versions?
- Can writer or watcher paths bypass the coordinator?
- Can a callback block mutation or terminate later callback delivery?
- Do failure paths preserve the prior complete in-memory version?

Any actionable concurrency, security, or compatibility finding requires a
focused regression, correction, re-review, and a fresh full gate.

- [ ] **Step 4: Publish only under the existing maintainer gate**

Push the exact qualified branch and update or create one draft PR against the
live `main`. Link #103 without a closing keyword until hosted checks and review
are terminal. Record AI assistance and exact validation. Do not mark ready,
merge, close #103, or release without separate authorization.

## Final review checklist

- [ ] All three original failure modes were RED before implementation and GREEN afterward.
- [ ] Published dictionaries and backlink lists are never mutated by later candidates.
- [ ] Every supported reader captures one version.
- [ ] Concurrent appends preserve both updates.
- [ ] Delete, rename, writer replay, and title/alias changes converge to cold-load behavior.
- [ ] Callback execution is ordered, isolated, nonblocking, and bounded at stop.
- [ ] Existing writer security and incremental backlink guards remain unchanged and green.
- [ ] Focused, full, docs, vendor, diff, cycle, impact, and independent-review gates are terminal at one exact head.
- [ ] Public documentation states the one-process boundary accurately.
- [ ] Merge, issue closure, release, and #104/#111 claims remain separate gates.

