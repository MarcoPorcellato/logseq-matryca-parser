# 📜 Architectural Contract: Live Incremental Invalidation & File Watcher
**Contract Status:** Wave 7 — Implemented (incremental invalidation + lazy watchdog watcher)

> **Implementation note (v1.3.0):** `LogseqGraph` now uses `validate_assignment=True` (not `frozen=True`); the watcher debounces events (~500ms) and ignores editor temp files. Historical spec text below describes the original contract.
**Target Stack:** Python 3.12+ | Pydantic V2 | Watchdog (Optional/Lazy Dependency)
**Inspiration Architectures:**
- `Microsoft/language-server-protocol` (Incremental text document synchronization and dependency invalidation)
- `watchdog` (Event-driven filesystem monitoring)

---

## 🎯 Task 1: Incremental Graph Invalidation Engine
* **Objective:** Avoid full-graph directory parsing sweeps when a single file changes. Implement surgical cache and registry invalidation to update memory maps in O(1) page-level time.
* **Target Files:**
    * `src/logseq_matryca_parser/graph.py`
    * `tests/test_graph.py`
* **Implementation Specifications:**
    1. Open `src/logseq_matryca_parser/graph.py`. Since `LogseqGraph` is currently a frozen Pydantic model (`frozen=True`), implement a dedicated, mutable internal mechanism or a structured state mutator method: `def invalidate_and_reload_page(self, file_path: Path) -> None`.
    2. **Surgical Invalidation Algorithm:**
       * Identify the page currently associated with the target `file_path`. If it exists in `self.pages`, extract all its current node UUIDs.
       * **Node Registry Purge:** Evict those stale UUIDs from the private `_node_registry` map.
       * **Backlink Registry Purge:** Iterate over `_backlink_registry` and remove the stale node UUIDs from any source tracking array to prevent orphaned memory references.
       * **Re-Parsing Phase:** Instantiate a fresh `StackMachineParser` specifically for this single file.
       * **Re-Hydration Phase:** Inject the newly parsed `LogseqPage` back into `self.pages` and safely append its fresh nodes and backlinks into `_node_registry` and `_backlink_registry`.
    3. Ensure this mutator bypasses frozen restrictions safely (e.g., using `object.__setattr__` for private registries or internal dictionaries since fields themselves hold mutable collections).
    4. **Quality Gate:** Add a test case `test_graph_incremental_page_invalidation` verifying that mutating a single file dummy content and triggering the invalidation correctly refreshes lookup queries and purges dead backlinks without full reloads.

- [x] Task 1 complete (tests + `make check` green)

---

## 🎯 Task 2: Live Background File Observer (`watch` interface)
* **Objective:** Provide a long-running, non-blocking interface that hooks into the filesystem, automatically executing Task 1 whenever an agent or user saves a file.
* **Target Files:**
    * `src/logseq_matryca_parser/graph.py`
    * `tests/test_graph.py`
* **Implementation Specifications:**
    1. Introduce a new class `LogseqGraphWatcher` or a public method inside `LogseqGraph`: `def start_watching(self, callback: Callable[[Path], None] | None = None) -> Any`.
    2. **Lazy Import Architecture:** Protect the core module from rigid heavy dependencies. Wrap the `watchdog.observers` and `watchdog.events` imports cleanly inside the method body.
    3. Create an internal event handler inheriting from `FileSystemEventHandler` that filters exclusively for `.md` files.
    4. Upon receiving a `on_modified` or `on_created` event, execute the `invalidate_and_reload_page` mutator pipeline, then optionally trigger the user-supplied `callback` hook (ideal for downstream vector store live-syncing).
    5. **Quality Gate:** Write an isolated testing suite inside `tests/test_graph.py` named `test_graph_watcher_filesystem_events` using a mocked or transient watchdog trigger to certify file events route accurately to the invalidation core.

- [x] Task 2 complete (tests + `make check` green)
