# 📜 Architectural Contract: Synthetic UUID Hardening & Graph Orchestration Module
**Contract Status:** Completed (Autonomous Execution)

> **Implementation note (v1.3.0):** `discover_graph_files` lives in `logseq_paths.py` (not `kinetic.py`); `LogseqGraph` uses `validate_assignment=True` instead of `frozen=True`. Historical spec text below describes the original contract.
**Target Stack:** Python 3.12+ | Pydantic V2 (Strict/Frozen Models) | Local-First No-DB

**Execution checklist**
- [x] Task 1: Topological Synthetic UUID Hardening
- [x] Task 2: High-Level `LogseqGraph` Orchestrator Module (No-DB In-Memory)

---

## 🎯 Task 1: Topological Synthetic UUID Hardening [x]
* **Objective:** Eliminate any cryptographic collision risk for synthetic UUIDs generated for blocks containing identical text on the exact same line number (e.g., repeated macros or logging edge-cases) by injecting spatial topology into the deterministic hashing mechanism, without altering Logseq OG's native UUID properties.
* **Target Files:**
    * `src/logseq_matryca_parser/logos_parser.py`
    * `tests/test_logos_parser.py`
* **Implementation Specifications:**
    1. Modify the `_deterministic_uuid(self, page_title: str, line_start: int, content: str)` method inside `StackMachineParser` to accept a fourth mandatory parameter: `parent_uuid: str | None`.
    2. Update the cryptographic payload formulation: `payload = f"{page_title}:{line_start}:{parent_uuid}:{content}".encode("utf-8")`. If the node is a root-level node, `parent_uuid` must default to `"root"`.
    3. Update the core processing loop inside the `parse()` method to resolve the parent node's state from the active indentation `stack` when invoking `_build_node`, successfully extracting the actual parent's UUID.
    4. **Safety Net:** Preserve intact the absolute priority of `source_uuid` if `id::` or inline UUID syntax is matched via `uuid_match` or `inline_uuid_match` (ensuring 100% Logseq OG compatibility).
    5. **Quality Gate:** Add a test case inside `tests/test_logos_parser.py` named `test_deterministic_uuid_topological_uniqueness` asserting that two blocks with identical content and line numbers, but nested under different parent nodes, resolve to distinct synthetic UUIDs.

---

## 🎯 Task 2: High-Level `LogseqGraph` Orchestrator Module (No-DB In-Memory) [x]
* **Objective:** Introduce a high-level, unified public API class that bulk-loads an entire Logseq graph directory in memory, populates global entity mappings, and permits lightning-fast lookups without forcing the consumer to manage single markdown files.
* **Target Files:**
    * `src/logseq_matryca_parser/graph.py` (New File)
    * `src/logseq_matryca_parser/__init__.py`
    * `tests/test_graph.py` (New File)
* **Implementation Specifications:**
    1. Define a Pydantic V2 model named `LogseqGraph` with strict configuration (`model_config = ConfigDict(strict=True, frozen=True)`).
    2. Model Fields:
        * `graph_path: Path`
        * `pages: dict[str, LogseqPage]` (mapping page titles to page models)
        * `_node_registry: dict[str, LogseqNode]` (private registry for O(1) global node lookup by their `uuid`).
    3. Implement a classmethod factory: `def load_directory(cls, graph_path: Path) -> "LogseqGraph"`. It must leverage `_discover_graph_files` from `kinetic.py` and utilize a `concurrent.futures.ThreadPoolExecutor` to instantiate the `StackMachineParser` across files concurrently, maximizing parsing throughput for 10k+ node graphs.
    4. Expose the following strictly type-hinted Public Query Methods:
        * `get_node_by_uuid(self, uuid: str) -> Optional[LogseqNode]`
        * `get_nodes_by_tag(self, tag: str) -> list[LogseqNode]`
        * `search_content(self, query: str) -> list[LogseqNode]` (fast in-memory linear scan against the `clean_text` field).
    5. Register and expose `LogseqGraph` in the root `__init__.py` package exports.
    6. **Quality Gate:** Author a complete test suite in `tests/test_graph.py` using `tmp_path` fixtures to simulate a dummy Logseq vault directory, validating that bulk initialization, cross-page lookups, and global tag querying work flawlessly, keeping the global `make check` suite at 100% green passing.