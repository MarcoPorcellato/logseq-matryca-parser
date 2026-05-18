# 📜 Architectural Contract: Graph-Wide Backlinks & Property Inheritance
**Contract Status:** Complete — Wave 2 executed (autonomous implementation verified)
**Target Stack:** Python 3.12+ | Pydantic V2 (Strict/Frozen Models) | Local-First No-DB
**Reference & Study Repositories:** - `logseq/mldoc` (Logseq OG official AST compiler architecture)
- `orgparse/orgparse` (Emacs Org-Mode hierarchical property stacking parser)

---

## [x] 🎯 Task 1: Bidirectional Link Indexing & Backlink Engine
* **Objective:** Power GraphRAG capabilities by tracking bidirectional connections across the entire vault in memory, enabling downstream LLMs to discover which blocks or pages reference a specific context.
* **Inspiration & Source Logic:** `logseq/mldoc` (Clojure/Rust) — Mimics how Logseq's official core maps block-to-block relational tracking (`:block/left`, `:block/path_refs`) and pages to build its local Datascript graph index.
* **Target Files:**
    * `src/logseq_matryca_parser/graph.py`
    * `tests/test_graph.py`
* **Implementation Specifications:**
    1. [x] Update the `LogseqGraph` model to introduce a private backlink index registry: `_backlink_registry: dict[str, list[str]] = PrivateAttr(default_factory=dict)`. It will map a target destination (either a lowercase Page Title or a Block UUID) to a list of source `LogseqNode.uuid` strings.
    2. [x] During the `load_directory` post-parsing indexing phase, iterate over all flattened nodes. For every node, inspect its `wikilinks`, `tags`, and `block_refs`.
    3. [x] Populate `_backlink_registry` accordingly (ensure page links are normalized to lowercase to prevent casing mismatches).
    4. [x] Implement a public query method: `def get_backlinks(self, target: str) -> list[LogseqNode]`. This method must look up the target in `_backlink_registry` and return the corresponding unique `LogseqNode` objects from the global registry.
    5. [x] **Quality Gate:** Add a test case `test_graph_backlink_resolution_cross_page` verifying that if Page A references `((block-uuid-from-page-b))` or `[[Page B]]`, querying backlinks for Page B or the block UUID correctly resolves and returns Page A's node.

---

## [x] 🎯 Task 2: Hierarchical Property Inheritance Engine
* **Objective:** Prevent LLM context fragmentation. When a leaf node block is ingested by a RAG pipeline, it must automatically inherit the metadata/properties of its ancestral lineage and page frontmatter, preserving project scope and security classifications.
* **Inspiration & Source Logic:** `orgparse/orgparse` (Python) — Emulates how Emacs Org-Mode manages property drawers (`:PROPERTIES:` stacking), where nested outlines inherit parent properties up to the global document layout.
* **Target Files:**
    * `src/logseq_matryca_parser/graph.py`
    * `src/logseq_matryca_parser/logos_core.py`
    * `tests/test_graph.py`
* **Implementation Specifications:**
    1. [x] Add a public method to `LogseqGraph`: `def get_effective_properties(self, node_uuid: str) -> dict[str, Any]`.
    2. [x] **Resolution Algorithm:** Given a node UUID, fetch the node. Traverse its lineage upwards using its parent chain (leverage the node's `path` field or parent lookups).
    3. [x] Read the properties of each ancestor block up to the root node, and finally merge them with the `LogseqPage.properties` (frontmatter) of the owning page.
    4. [x] **Merge Order Resolution:** Properties must be merged from the top down (Page Frontmatter -> Root Node -> Ancestor -> Leaf Node), ensuring that a more specific property defined on a child block correctly overrides a generic property inherited from a parent or page.
    5. [x] **Quality Gate:** Write a test case `test_property_inheritance_overrides` asserting that a leaf block correctly inherits a `:project:: Matryca` tag defined at the page frontmatter, but overrides a `:status:: WIP` if the child explicitly declares `:status:: DONE`.
