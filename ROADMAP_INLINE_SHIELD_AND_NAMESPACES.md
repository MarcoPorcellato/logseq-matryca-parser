# 📜 Architectural Contract: Inline Token Shielding & Namespace Hierarchy Resolution
**Contract Status:** Executed (Wave 3 — green `make check` + pytest)
**Target Stack:** Python 3.12+ | Pydantic V2 | Local-First No-DB
**Inspiration Repositories:**
- `markdown-it-py` (Inline state masking / literal text protection)
- `logseq/mldoc` (Relative path resolution based on multi-segment page namespaces)

---

## 🎯 Task 1: Code-Span & Macro Shielding Engine for Inline Content
* **Objective:** Prevent regex false-positives during entity extraction (`wikilinks`, `tags`, `block_refs`) by temporarily masking inline code spans (text wrapped inside backticks `` `...` `` or triple backticks) and macros, matching robust production-grade compiler tokens.
* **Target Files:**
    * `src/logseq_matryca_parser/logos_parser.py`
    * `tests/test_logos_parser.py`
* **Implementation Specifications:**
    1. [x] Implement a private helper function `_shield_inline_code(content: str) -> tuple[str, list[str]]` inside `logos_parser.py`. It must find all text segments wrapped in inline backticks (single or multiple) or standard Logseq macros `{{...}}`.
    2. [x] Replace these protected segments with placeholder tokens (e.g., `___LOGOS_SHIELD_TOKEN_0___`) to construct a "sanitized" line profile, while keeping an ordered recovery list of the original literals.
    3. [x] Modify `_extract_tags`, `_extract_block_refs`, and the main parsing loop where `LOGSEQ_PATTERNS["wikilink"]` is run, ensuring they run their matches against the sanitized/shielded string rather than raw content.
    4. [x] Ensure the actual `content` and `clean_text` stored in the final `LogseqNode` retain their pristine user-facing code syntax blocks (the shield is only a transient proxy for index extraction).
    5. [x] **Quality Gate:** Add a test case `test_inline_entity_extraction_shields_code_spans` ensuring that given a block text like `- Investigate code block `[[FalseLink]]` and tag #[[NotATag]]`, no wikilinks or tags are extracted, while regular extraction outside code spans functions normally.

---

## 🎯 Task 2: Hierarchical Namespace Resolver & Navigation Vectors
* **Objective:** Expand the `LogseqGraph` orchestrator with first-class capabilities to traverse multi-segment namespaces (e.g., `Projects/AI/Matryca`) and accurately resolve relative page links according to Logseq OG inheritance standards.
* **Target Files:**
    * `src/logseq_matryca_parser/graph.py`
    * `tests/test_graph.py`
* **Implementation Specifications:**
    1. [x] Add a public method to `LogseqGraph`: `def resolve_relative_page_link(self, current_page_title: str, link_target: str) -> Optional[str]`.
    2. [x] **Resolution Logic:** If `link_target` exists as a literal page name, return it. If not, split `current_page_title` into its namespace segments. Recursively append `link_target` to the ancestor chains (e.g., if on page `A/B` and linking to `[[C]]`, check for existence of page `A/B/C`, then page `A/C`). Return the absolute structural match string if found, mirroring Logseq OG's scoping resolution.
    3. [x] Add a public navigation query method: `def get_namespace_children(self, namespace_prefix: str) -> list[LogseqPage]`. It must scan `self.pages` and return all pages whose titles start with the prefix followed by a forward slash (e.g., prefix `Projects/AI` returns `Projects/AI/Matryca` and `Projects/AI/Parser`).
    4. [x] **Quality Gate:** Add a comprehensive integration test suite inside `tests/test_graph.py` named `test_namespace_hierarchy_and_relative_resolution` validating both absolute/relative context matches and children collection vectors against temporary filesystem mocks.
