## [2026-04-24] Static Analysis & Linter Refactoring (Mypy / Pylance / Ruff)

### Module: `kinetic.py`
* **Issue:** Strict type checkers (`mypy`, `pylance`) flagged missing type stubs for external CLI/UI dependencies (`typer`, `rich`).
* **Resolution:** Appended `# type: ignore` directives to the respective import statements. This strategically suppresses false-positive "missing library" warnings in the IDE while preserving full runtime execution capability.

### Module: `synapse.py`
* **Issue 1:** The `Ruff` linter detected unused import statements (specifically `Dict`).
* **Resolution 1:** Purged unused imports to enforce a clean namespace and reduce overhead.
* **Issue 2:** "Invalid Type Form" error. The fallback assignment `Document = None` (triggered via `ImportError` when `langchain-core` is not installed locally) broke the static analyzer when evaluating the forward reference `List['Document']`. 
* **Resolution 2:** 1. Replaced the strict `List['Document']` return type hints with `List[Any]` to satisfy the type checker regardless of the fallback state.
  2. Injected `# type: ignore` on the `langchain_core` optional import to bypass missing import warnings in environments where the ecosystem adapter is not strictly required.

### Module: `logos_parser.py`
* **Issue:** The parser failed to distinguish between secondary text lines and Logseq block properties (e.g., `id::`, `custom::`). This resulted in properties being concatenated into the node's content and native IDs being ignored in favor of generated UUIDs.
* **Resolution:** 1. Enhanced the FSM logic to check for property patterns (`prop_regex`) on non-bullet lines.
    2. Implemented an override mechanism: if an `id::` property is detected, it immediately updates the `node.uuid`, ensuring deterministic alignment with Logseq's internal graph.
    3. Modified content accumulation to skip lines identified as properties, ensuring "Clean-RAG" output.
* **Verification:** Added `tests/test_logos_parser.py` covering hierarchical depth and property isolation. All tests passed (`pytest -v`).

---

## [2026-05-15] Developer Experience (DX) & AST Identity Fixes (v0.2.1 - v0.2.2)

### Module: `__init__.py` & `logos_parser.py` (DX Patch v0.2.1)
* **Issue 1:** `ForgeExporter` and visitor classes were hidden in submodules, causing `ImportError` for external integrations.
* **Resolution 1:** Re-exported core Forge classes in `__init__.py` and added them to `__all__` for Plug & Play imports.
* **Issue 2:** `parse_page_file` and `parse_file` strictly demanded `pathlib.Path` objects, crashing on standard string paths.
* **Resolution 2:** Updated type hints to `Path | str` and injected early polymorphic casting (`path = Path(path)`).

### Module: `forge.py` (DX Patch v0.2.1)
* **Issue:** `MarkdownForgeVisitor` was serializing internal AST properties (e.g., `[:heading_level 2]`) into the output markdown because it relied on raw `node.content`.
* **Resolution:** Switched to using `node.clean_text` to strictly isolate user content from parser metadata.

### Module: `logos_core.py` & `logos_parser.py` (AST Identity Collision - v0.2.2)
* **Issue:** Generating block UUIDs purely from `page_title` and `content` resulted in identical UUIDs for repeated blocks (e.g., recurring identical tasks). This caused critical node-merging collisions when ingested into downstream Graph Databases and GraphRAG engines.
* **Resolution:** 1. Updated the `_deterministic_uuid` hashing algorithm to include physical file position (`line_start`) as a primary entropy source.
  2. Preserved the native Logseq `id::` property safely into a separate `source_uuid` field.
  3. Upgraded the `LogseqNode` model to capture rich topological metadata: `line_start`, `line_end`, `source_path`, and `outline_path`.
* **Verification:** Merged PR from `@slikts`. Regression tests for duplicate same-content blocks and JSON exports passed successfully.

### Module: `scripts/parse_logseq.py` (Claude Skill & Linter Refactoring)
* **Issue 1:** The Claude skill script contained hardcoded personal PII paths, breaking portability.
* **Resolution 1:** Refactored the script to use `os.environ.get("LOGSEQ_GRAPH_PATH")` as an environment-agnostic fallback.
* **Issue 2:** Ruff linter threw `E741` due to ambiguous variable naming (`l` in a comprehension).
* **Resolution 2:** Renamed `l` to `line_str` resolving the linter error without needing `per-file-ignores` in `pyproject.toml`.
* **Issue 3:** Missing precise source citation for the LLM.
* **Resolution 3:** Leveraged the new `line_start` property from v0.2.2 in `format_node`, injecting `[Riga N]` into the output to enable exact file-line tracking for LLM citations.