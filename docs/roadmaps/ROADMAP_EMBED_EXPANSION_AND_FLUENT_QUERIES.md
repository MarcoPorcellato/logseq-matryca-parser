# Architectural Contract: Recursive Embed Transclusion & Fluent Topological Queries

**Contract Status:** Wave 6 — executed (suite green)
**Target Stack:** Python 3.12+ | Pydantic V2 | Local-First No-DB
**Inspiration Frameworks:**

- `logseq/mldoc` (Dynamic cross-reference resolution and transclusion compiler logic)
- `Tana` (Granular node attribute search and graph-filtering mechanics)

---

## Task 1: Recursive Embed & Macro Transclusion Engine

- [x] Ensure that when text chunks are prepared for AI ingestion, any embedded block (`{{embed ((uuid))}}`) or embedded page (`{{embed [[Page]]}}`) has its actual text contents expanded recursively in-place, preventing black-box data gaps in vector storage.
- [x] **Target Files:** `src/logseq_matryca_parser/synapse.py`, `tests/test_synapse.py`
- [x] Implement `_expand_macros_and_embeds(text: str, graph: LogseqGraph, visited_uuids: set[str]) -> str` with cycle safety and integrate into `to_context_enriched_chunks` (expansion scans `LogseqNode.content` so `((uuid))` inside macros survives `clean_text` stripping).
- [x] **Quality Gate:** `test_synapse_recursive_embed_expansion` in `tests/test_synapse.py`.

---

## Task 2: Fluent, Chainable Graph Query API over `LogseqGraph`

- [x] Provide `GraphQuery` in `src/logseq_matryca_parser/graph.py` with `has_tag`, `with_priority`, `under_parent`, `is_task_state`, `execute`, and `LogseqGraph.query()`.
- [x] **Target Files:** `src/logseq_matryca_parser/graph.py`, `tests/test_graph.py`
- [x] **Quality Gate:** `test_fluent_graph_query_pipeline` in `tests/test_graph.py`.

**Support API:** `LogseqGraph.get_node_by_embed_ref` resolves Logseq `id::` / `properties["id"]` in addition to synthetic `uuid` for block embeds.
