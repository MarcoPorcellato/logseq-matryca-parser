# 📜 Architectural Contract: Lenient Indentation & Multiline Soft-Breaks
**Contract Status:** Wave 9 — Implemented (lenient indent + soft-break accumulator)
**Target Stack:** Python 3.12+ | Pydantic V2 | Pytest
**Inspiration Architectures:** Drive Docs (Claude, Grok, DeepSeek robustness critiques)

---

## 🎯 Task 1: Lenient Indentation & Heuristic Space Alignment
* **Objective:** Prevent the parser from crashing entirely when users create visually inconsistent indents (e.g., 3 spaces instead of 2). Replace strict mathematical jumps with a floor division heuristic fallback.
* **Target Files:**
    * `src/logseq_matryca_parser/logos_parser.py`
    * `tests/test_logos_parser.py`
* **Implementation Specifications:**
    1. Open `logos_parser.py` and navigate to `StackMachineParser._compute_indent_level`.
    2. Instead of raising an error or skipping logic on exact character multiples, implement `level = total_spaces // self.tab_size`.
    3. Remove any occurrence of `LogseqIndentationError` specifically triggered by misaligned trailing whitespace counts.
    4. **Quality Gate:** Update `test_misaligned_indentation_floors_to_nearest_level` (or add it) to ensure that a 3-space indent when `tab_size=2` evaluates cleanly to indentation level 1 without raising an exception.

### Task 1 checklist

- [x] `_compute_indent_level` uses floor division on space-equivalent width
- [x] No `LogseqIndentationError` from misaligned bullet indent in `logos_parser.py`
- [x] `test_misaligned_indentation_floors_to_nearest_level` passes

---

## 🎯 Task 2: Multiline Block Buffer Accumulator (Soft-Break Support)
* **Objective:** Accurately ingest text mutations generated via `Shift + Enter` soft breaks inside Logseq, where subsequent lines do not start with a bullet (`- `) but belong to the current active block text.
* **Target Files:**
    * `src/logseq_matryca_parser/logos_parser.py`
    * `tests/test_logos_parser.py`
* **Implementation Specifications:**
    1. In the main `parse()` loop of `StackMachineParser`, intercept lines that fail the `BULLET_PATTERN`, `HEADING_BLOCK_PATTERN`, and `LOGSEQ_PATTERNS["property"]` checks.
    2. Before discarding them as ambient noise or treating them as a new root, verify if an active block exists at the tip of the stack (`stack[-1]`).
    3. If valid, gracefully concatenate the raw line to that node's `content` (e.g., appending a `\n` and the line text). Use `_refresh_node` to update its state and replace it cleanly at the top of the `stack`.
    4. Guard clause: Ignore system/metadata noise lines entirely (do not append them to the prose).
    5. **Quality Gate:** Add a test case `test_parser_captures_multiline_soft_break_paragraphs` asserting that lines lacking bullets are correctly appended to the content field of the active node immediately preceding them.

### Task 2 checklist

- [x] Non-bullet / non-heading / non-property lines merge into `stack[-1]` when the stack is non-empty
- [x] `is_system_block` and empty lines still short-circuit before prose merge
- [x] `test_parser_captures_multiline_soft_break_paragraphs` passes

---

## Validation

- [x] `make lint`
- [x] `make check`
- [x] `make test` (pytest)
