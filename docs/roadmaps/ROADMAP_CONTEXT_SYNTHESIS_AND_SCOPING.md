# 📜 Architectural Contract: Context-Enriched Chunking & Scoping Priority Shadowing
**Contract Status:** Wave 4 — executed
**Target Stack:** Python 3.12+ | Pydantic V2 | Local-First No-DB
**Inspiration Frameworks:**
- `logseq/mldoc` (For precise namespace inheritance and relative name shadowing lookup order)
- `langchain/langgraph` (Context anchoring and metadata-hydration patterns for vector synthesis)

---

## 🎯 Task 1: Correct Logseq OG Scoping Shadowing Order
* **Objective:** Align `resolve_relative_page_link` perfectly with Logseq's native behavior where nested relative namespace paths shadow global names, reversing the current lookup prioritization.
* **Target Files:**
    * `src/logseq_matryca_parser/graph.py`
    * `tests/test_graph.py`
* **Implementation Specifications:**
    1. Refactor the `resolve_relative_page_link(self, current_page_title: str, link_target: str)` method inside `LogseqGraph`.
    2. **New Lookup Sequence (Strict Logseq OG Matching):** First, split `current_page_title` into namespace segments. Loop from the deepest nesting level down to 1, building candidates by appending `link_target` (e.g., if on page `A/B/C` and looking for `D`, check `A/B/C/D`, then `A/B/D`, then `A/D`). If an intersected match is found within `self.pages`, return it immediately. Only if all relative namespace checks fail, fall back to checking the literal global `link_target` string in `self.pages`.
    3. **Quality Gate:** Update `test_namespace_hierarchy_and_relative_resolution` or add a new test asserting that if both a global page `Sviluppo` and a contextual page `Progetti/AI/Sviluppo` exist, calling resolution from `Progetti/AI/Matryca` returns the shadowed contextual namespace page, not the global one.

---

## 🎯 Task 2: Context-Enriched Topological Chunking Exporter (Synapse Upgrade)
* **Objective:** Supercharge RAG extraction capabilities. When exporting nodes to LangChain or LlamaIndex, synthesize a context-anchored text block so that leaf nodes don't lose their semantic meaning when retrieved as isolated vectors.
* **Target Files:**
    * `src/logseq_matryca_parser/synapse.py`
    * `tests/test_synapse.py`
* **Implementation Specifications:**
    1. Add a new public staticmethod to `SynapseAdapter`: `to_context_enriched_chunks(nodes: list[LogseqNode], graph: LogseqGraph, format_template: str = "[{breadcrumbs}] {content}") -> list[Any]`.
    2. **Context Synthesis Algorithm:** For each node in the flattened list, resolve its ancestor line using `node.path`. Fetch the text content of its parent nodes from the graph.
    3. Concatenate the page title and parent contents using a clean separator (e.g., `Page Title > Parent Block Text > Child Block Text`) to generate the `{breadcrumbs}` string.
    4. Strip markdown formatting from the breadcrumb text to optimize vector embeddings.
    5. Construct the returned LangChain `Document` objects where the `page_content` is the fully populated `format_template` string, while keeping the native clean text in the metadata.
    6. **Quality Gate:** Add a comprehensive unit test suite in `tests/test_synapse.py` named `test_synapse_context_enriched_chunking` confirming that a deeply nested child node exported via this method includes its parent structural markers embedded directly within its primary text string, keeping `make check` 100% green.

---

## Wave 4 completion checklist
- [x] Task 1: `resolve_relative_page_link` shadowing order + tests
- [x] Task 2: `to_context_enriched_chunks` + tests
- [x] `make check` and `make test` green
- [x] `make lint` clean
