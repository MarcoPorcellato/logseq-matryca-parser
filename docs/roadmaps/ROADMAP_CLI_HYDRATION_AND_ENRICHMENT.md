# 📜 Architectural Contract: CLI Graph Integration & Metadata Hydration

**Contract Status:** Executed (Wave 5 — green pipeline)

**Target Stack:** Python 3.12+ | Pydantic V2 | Local-First No-DB

**Inspiration Frameworks:**

- `langchain/langgraph` (State orchestration and universal metadata-hydration patterns)
- `typer/rich` (Advanced CLI multi-format argument processing architectures)

---

## 🎯 Task 1: Hydrate Enriched Chunks with Effective Structural Properties

- [x] Ensure that downstream vector stores receive the fully inherited property stack (metadata, tags, project bounds) within the chunk object dictionary, closing the loop on our hierarchical engine.

**Target Files:**

- `src/logseq_matryca_parser/synapse.py`
- `tests/test_synapse.py`

**Implementation Specifications:**

1. Open `src/logseq_matryca_parser/synapse.py` and navigate to the `to_context_enriched_chunks` method.
2. For each node being iterated, extract its complete top-down resolved lineage properties by invoking `graph.get_effective_properties(node.uuid)`.
3. Inject this resolved dictionary into the LangChain `Document` metadata payload under the dedicated key `effective_properties`.
4. Ensure that original structural fields (`source_path`, `line_start`, `parent_id`) remain preserved in the root metadata dictionary level alongside the newly injected properties.
5. **Quality Gate:** Update `test_synapse_context_enriched_chunking` in `tests/test_synapse.py` to assert that the generated dictionary contains the `effective_properties` key and accurately reflects inherited page-frontmatter tags.

---

## 🎯 Task 2: Implement Unified `langchain-enriched` Export Format in KINETIC CLI

- [x] Replace isolated single-file parsing during CLI orchestration with full-graph loading, exposing our context-rich topological chunking strategy as a direct terminal command.

**Target Files:**

- `src/logseq_matryca_parser/kinetic.py`
- `tests/test_kinetic.py`

**Implementation Specifications:**

1. Update the `ExportFormat` Enum class inside `kinetic.py` to introduce a new target token format: `LANGCHAIN_ENRICHED = "langchain-enriched"`.
2. Refactor the main `@app.command() def export(...)` handler. When the user requests `--format langchain-enriched`, bypass the traditional file-isolated `_parse_graph(graph_path)` loop.
3. Instead, initialize the unified graph container via `graph = LogseqGraph.load_directory(graph_path)`.
4. Implement a helper function `_export_langchain_enriched(graph: LogseqGraph, output_path: Path) -> Path` that flattens all nodes across all parsed graph pages, passes them to `SynapseAdapter.to_context_enriched_chunks(all_nodes, graph)`, and serializes the list of documents into a unified json file named `langchain_enriched.json` inside the output directory.
5. Use `Rich` console logs to inform the user about the total count of synthesized contextual chunks successfully written to disk.
6. **Quality Gate:** Add a dedicated test inside `tests/test_kinetic.py` named `test_export_command_langchain_enriched_writes_hydrated_file` ensuring the command runs end-to-end via `CliRunner` and outputs valid JSON containing breadcrumbs and metadata configurations, maintaining overall suite status at 100% green.
