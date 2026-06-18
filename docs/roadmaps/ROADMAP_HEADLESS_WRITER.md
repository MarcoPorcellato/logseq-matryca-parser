# 📜 Architectural Contract: Headless Write Engine & AST Linters
**Contract Status:** Wave 12 — executed (suite green)
**Target Stack:** Python 3.12+ | Pydantic V2
**Inspiration:** Decoupling downstream applications (like LLM Wiki) from the Logseq HTTP API by providing native, alias-aware Markdown splicing.

---

## 🎯 Task 1: Native Registry Serialization (Support for LLM Wiki)
* **Objective:** Equip the `SessionAliasRegistry` with native JSON serialization so downstream stateful applications don't have to write their own manual dictionary parsing logic.
* **Target Files:**
    * `src/logseq_matryca_parser/agent_press.py`
    * `tests/test_agent_press.py`
* **Implementation Specifications:**
    1. Add `def save_to_disk(self, filepath: Path) -> None` to export the `_alias_to_uuid` mapping to a JSON file.
    2. Add `@classmethod def load_from_disk(cls, filepath: Path) -> "SessionAliasRegistry"` to reconstruct the registry from the JSON file.
    3. **Quality Gate:** Test that a registry can be saved to a temporary JSON file, reloaded into a new instance, and successfully resolve an existing alias.

- [x] Task 1 complete

---

## 🎯 Task 2: The Headless Markdown Splicer
* **Objective:** Implement a deterministic write engine that mutates raw `.md` files based on AST topology, allowing downstream MCP servers to append blocks without Logseq's HTTP API.
* **Target Files:**
    * `src/logseq_matryca_parser/agent_writer.py`
    * `tests/test_agent_writer.py`
* **Implementation Specifications:**
    1. Create `agent_writer.py` exposing `def append_child_to_node(graph: LogseqGraph, target_uuid: str, content: str) -> None`.
    2. **Splicing Logic:**
       * Fetch `target_node` from `graph.get_node_by_uuid()`.
       * Calculate the exact line insertion index (immediately after the target block's text, or after its last existing child).
       * Calculate the exact indentation (`target_node.level + 1` multiplied by `graph.tab_size`).
       * Splice the string `- {content}` into the raw file lines and atomically write it back to disk.
    3. **Quality Gate:** Add a test verifying `append_child_to_node` correctly inserts a properly indented bullet point below a designated block in a dummy markdown file.

- [x] Task 2 complete

---

## 🎯 Task 3: Broken Reference AST Linter
* **Objective:** Provide downstream applications with a structural linter to identify broken `((uuid))` links without relying on regex.
* **Target Files:**
    * `src/logseq_matryca_parser/graph.py`
    * `tests/test_graph.py`
* **Implementation Specifications:**
    1. Add `def get_broken_references(self) -> list[LogseqNode]` to `LogseqGraph`.
    2. It must scan `self._node_registry`. For any node containing items in its `block_refs` array, verify if those target UUIDs exist in the registry. If a target is missing, yield or return the originating node.
    3. **Quality Gate:** Add a test where a node contains `((fake-uuid))` and assert `get_broken_references()` successfully flags it.

- [x] Task 3 complete
