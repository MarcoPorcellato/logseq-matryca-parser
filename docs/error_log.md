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