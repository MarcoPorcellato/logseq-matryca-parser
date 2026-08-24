---
type: DesignSpecification
title: Per-graph mutation and coherent snapshot contract
description: A one-process concurrency design for atomic writer, watcher, and graph-index updates under issue 103.
status: approved
classification: active
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-08-24
verified: 2026-08-24
stale_after: 2026-11-21
parent_plan: docs/LSDOC_REFERENCE_STUDY_AND_EXECUTION_PLAN_2026-08-16.md
issue: 103
base_commit: 8e2bc893dea34b756edb6632e04917b04a68c1e6
---

# Per-graph mutation and coherent snapshot contract

## Purpose

Issue #103 closes two one-process correctness gaps without changing the public
synchronous API:

1. two writers must not lose an update after reading the same source version;
2. graph readers must not observe a page version combined with node, backlink,
   title, or diagnostic indexes from another version.

The observable outcome is that writer and watcher mutations for one
`LogseqGraph` instance are serialized, every successful reload publishes one
complete graph version, every failed reload preserves the complete prior
in-memory version, and user callbacks cannot block mutation processing.

## Verified starting point

- The approved base is `main@8e2bc893dea34b756edb6632e04917b04a68c1e6`,
  the squash merge of PR #178.
- `LogseqGraph.invalidate_and_reload_page()` currently removes stale registry
  entries before parsing and then assigns `pages`, the title map, node registry,
  and backlinks in separate operations.
- `append_child_to_node()` currently performs read-modify-write, atomic
  `os.replace()`, and reload without a per-graph coordinator.
- Watcher user callbacks currently execute inline after reload.
- Three deterministic diagnostic probes reproduced the defects on the
  pre-change implementation:
  - two successful simultaneous appends requested two children but persisted
    one;
  - a reader observed a visible page while its fresh node was absent;
  - a synthetic parse failure preserved the old page while removing its old
    node from the registry.
- Fresh audit-code analysis at the release-preparation checkpoint classified
  `invalidate_and_reload_page` as **HIGH** impact: six direct and eight total
  dependents across four affected flows. The source import graph had zero
  cycles. This HIGH impact is explicitly approved for issue #103.

Re-verify the live base, issue, impact, and cycle state before implementation or
publication. Historical probe output is diagnostic evidence, not qualification
of a future implementation head.

## Scope

- Add one re-entrant lock owned by each `LogseqGraph` instance.
- Build an isolated candidate containing pages, nodes, backlinks, lowercased
  title routing, and diagnostics before publication.
- Retain a private source-path registry for every parsed physical page so an
  incremental edit can restore pages displaced by title or alias collisions.
- Publish all candidate components only while holding the per-instance lock.
- Make supported graph read methods observe one captured version.
- Protect the complete writer read-modify-replace-reload transaction with the
  same lock.
- Route watcher reloads through the same mutation path.
- Dispatch user callbacks in publication order on a separate daemon worker.
- Add deterministic concurrency, rollback, convergence, and parity tests.
- Document the supported one-process concurrency contract.

## Non-goals

- No process-global lock, file-lock protocol, cross-process writer guarantee,
  database, queue service, asynchronous public API, or background graph actor.
- No public mutable transaction object and no public API promotion.
- No parser rewrite, graph storage engine, search index, or filesystem-watcher
  replacement.
- No change to atomic target validation, symlink containment, permission
  preservation, source limits, or `os.replace()` security checks.
- No 1k/10k performance claim or budget; issue #111 owns those measurements.
- No claim that arbitrary direct external mutation of `graph.pages` is safe.

## Selected architecture

### Per-instance coordination

`LogseqGraph` owns a private `threading.RLock`. Re-entrancy is required because
the writer holds the lock across its complete transaction and then invokes the
reload method, which acquires the same lock again. A process-global lock is
forbidden because unrelated vaults must remain independent.

### Coherent candidate

Add a private frozen data class `_GraphSnapshot` with these fields:

```python
@dataclass(frozen=True, slots=True)
class _GraphSnapshot:
    source_pages: dict[str, LogseqPage]
    pages: dict[str, LogseqPage]
    node_registry: dict[str, LogseqNode]
    backlink_registry: dict[str, list[str]]
    lower_title_map: dict[str, str]
    index_diagnostics: tuple[Diagnostic, ...]
```

The frozen wrapper prevents field rebinding; the contained mappings remain
ordinary dictionaries for compatibility. `source_pages` is private and maps a
resolved source path to the parsed page from that physical file before title
overrides, aliases, or collision winners are applied. It is the recovery source
for files hidden from the public `pages` mapping by a collision. Published
dictionaries and backlink lists are immutable by repository convention: a
later candidate must copy them before mutation. No supported library mutation
may alter a previously published dictionary or list.

`invalidate_and_reload_page()` acquires the lock, captures the current
snapshot, and constructs the candidate from private copies. It removes the
touched source path from `source_pages`, reparses only that file when it still
exists, and deterministically derives the public page mapping and current
collision diagnostics from all retained in-memory source pages. This restores
a previously displaced collision participant without reparsing unrelated
files. Enrichment, node-registry construction, targeted backlink repair,
title-map construction, and validation all finish before publication. An
exception at any point leaves every current field untouched.

Publication assigns `_source_pages`, `pages`, `_node_registry`,
`_backlink_registry`, `_lower_title_map`, and `_index_diagnostics` while the same
lock excludes all supported read methods. Direct `graph.pages` access receives
either the old or new mapping object because publication replaces the reference
and never mutates the published mapping afterward. Separate raw mapping reads
are not a public transaction; callers needing coherent graph operations must
use supported methods.

### Incremental backlink preservation

Do not replace the current incremental path with
`_build_backlink_registry(candidate.pages)`. The existing regression that
forbids a global backlink rebuild remains authoritative.

Instead, refactor the current purge, capture, append, and incoming-link reindex
operations into private helpers that receive explicit candidate mappings.
Candidate backlink lists must be deep-copied. Compare every old and candidate
source node's resolved backlink-key contribution, remove only changed source
UUIDs from their prior keys, and append only their candidate contributions.
This comparison also covers collision participants that become visible or
hidden. A full node scan for affected links is acceptable; rebuilding all
backlink entries is not.

### Reader contract

Every supported read method either:

- holds the `RLock` for the complete operation; or
- captures references to one published snapshot while holding the lock, then
  iterates those references after releasing it.

This applies to page and UUID lookup, backlinks, canonical-page iteration,
attached-node iteration, queries, effective properties, tag/content search,
namespace and relative-link resolution, broken-reference checks, diagnostics,
and writer lookup helpers. Nested calls are safe because the lock is re-entrant.

### Writer transaction

`append_child_to_node()` enters the graph's private mutation scope before
looking up the target node. It remains inside that scope through target
validation, source reading, patch construction, temporary-file creation,
identity revalidation, atomic replacement, and incremental reload. Dry-run
patch construction uses the same scope so it cannot combine a stale node with a
new source.

Filesystem replacement remains atomic and security checks remain unchanged.
If reload fails after an external file change, the prior in-memory snapshot
remains complete and the failure propagates. Automatic disk rollback is not
part of this issue because a watcher may be observing a user-authored change.

### Watcher and callback contract

Watcher create, modify, delete, and both sides of a move continue to call the
same incremental reload method. The graph lock serializes overlapping timer,
writer, and caller reloads. Replaying the same path is idempotent and converges
to current disk state.

User callbacks are submitted only after a successful publication. A private
ordered dispatcher owns one daemon thread and one FIFO queue per watcher. It
catches and logs callback exceptions so one callback cannot terminate later
delivery. `stop()` closes admission, enqueues a sentinel, and performs a bounded
join; it must not wait indefinitely for an untrusted callback.

The debounce router has a close boundary separate from callback shutdown. Once
closing begins, it rejects new timers, cancels pending timers, and waits for any
route that already entered publication processing to finish before `stop()`
returns. User callback execution is not part of this quiescence wait. Therefore
no graph mutation from that watcher may occur after a successful `stop()`
return, while an admitted slow callback remains subject to the existing bounded
dispatcher join.

The callback sequence follows successful publication order. Failed reloads do
not enqueue callbacks, and a route rejected by watcher shutdown performs no
publication and submits no callback.

## Rejected alternatives

1. **Lock only the existing mutations.** Rejected because current methods
   mutate published registries before parsing and therefore cannot roll back a
   failed refresh.
2. **Global lock.** Rejected because issue #103 is per-vault and unrelated
   graphs must not serialize one another.
3. **Actor or asynchronous mutation queue.** Rejected because it changes the
   synchronous API and adds lifecycle complexity without a demonstrated need.
4. **Full backlink rebuild per reload.** Rejected because the repository
   already protects incremental backlink behavior and issue #111 owns measured
   justification for broader algorithms.
5. **Full vault reparse after a collision.** Rejected because a private
   source-path registry can restore a displaced parsed page without filesystem
   work for unrelated files.
6. **Recover collision participants from diagnostics alone.** Rejected because
   diagnostics describe a prior derived state and cannot serve as the complete
   source-page inventory.
7. **Cross-process file locking.** Deferred; the accepted scope is one vault in
   one process.

## Required behavior and deterministic evidence

The implementation is not complete until tests prove all of the following
without `time.sleep()`:

- two simultaneous appends preserve both children;
- a query racing a reload observes only the complete old or complete new
  version;
- a parse failure preserves the complete prior pages, UUID lookup, backlinks,
  title routing, and diagnostics;
- create, edit, delete, and both rename-event orders match a cold load;
- edit, delete, and rename resolution of canonical/canonical and
  alias/canonical collisions match a cold load for pages, UUID lookup, title
  routing, backlinks, and diagnostics;
- title and alias changes repair all affected backlink routes without a global
  backlink rebuild;
- writer reload followed by the watcher replay converges to a cold load;
- callbacks return control immediately, retain publication order, isolate
  exceptions, and stop with bounded lifecycle behavior;
- a debounce route already firing when shutdown begins either completes before
  `stop()` returns or is rejected before publication; it never mutates the graph
  afterward;
- existing synchronous signatures and filesystem-security tests remain green;
- two different `LogseqGraph` instances do not share a lock.

Use `threading.Barrier`, `threading.Event`, futures with bounded timeouts, and
controlled monkeypatch boundaries. Timeouts detect deadlock; they must not be
used as timing-based success criteria.

## Security and compatibility boundaries

- Vault Markdown remains untrusted data and never grants authority.
- Keep all path, symlink, `file://`, identity-revalidation, source-size,
  permission, and temporary-file protections unchanged.
- Do not expose the lock, source-page registry, candidate, callback queue, or
  dispatcher from the package root.
- Keep optional watchdog behavior lazy and the base parser dependency-light.
- Preserve deterministic UUIDs, tree order, parent and left pointers, source
  ranges, alias routing, backlinks, and parse/serialize behavior.
- Do not commit vault content, generated receipts, caches, credentials, or
  local audit indexes.

## Qualification and publication gates

The exact implementation head requires:

```bash
rtk env UV_CACHE_DIR=/private/tmp/logseq-matryca-parser-103-uv-cache make all
rtk make vendor-name-check
rtk git diff --check origin/main...HEAD
```

It also requires focused graph, writer, security, runtime-evidence, and new
concurrency tests; zero source import cycles; exact-head impact and change-flow
review; an independent concurrency review; and successful hosted checks on the
published head.

Commit, push, draft PR, ready-for-review, merge, issue closure, release, and
performance-budget promotion remain separate gates. Issue #103 may close only
after the implementation PR merges and its acceptance matrix is posted with
exact receipts.

## Completion checklist

- [ ] Every supported mutation uses the per-instance coordinator.
- [ ] No candidate operation mutates a published mapping or backlink list.
- [ ] Every supported reader observes one version.
- [ ] Writer and watcher races converge without lost updates.
- [ ] Failed refresh preserves the complete prior in-memory version.
- [ ] Callback dispatch is ordered, isolated, nonblocking, and bounded at stop.
- [ ] Deterministic tests cover all issue requirements without sleeps.
- [ ] Incremental backlink behavior remains protected.
- [ ] Full local, structural, independent-review, and hosted gates pass at the
  exact published head.
- [ ] Documentation states the one-process boundary and does not overclaim
  cross-process safety.
