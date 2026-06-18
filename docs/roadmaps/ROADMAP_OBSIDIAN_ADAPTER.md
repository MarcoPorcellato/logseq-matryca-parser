# 📜 Architectural Contract: Obsidian Vault Native Compiler

**Contract Status:** Delivered (Wave 10)  
**Target Stack:** Python 3.12+ | Pydantic V2  
**Inspiration Architectures:** Obsidian Markdown Specifications (YAML Frontmatter & `^block-id` block references)

---

## 🎯 Task 1: The Obsidian Forge Exporter

- **Objective:** Create a dedicated exporter that translates Logseq's native outliner AST into Obsidian-compatible Markdown, converting properties to valid YAML frontmatter and translating UUIDs to Obsidian's native block IDs.
- **Target Files:**
  - `src/logseq_matryca_parser/forge.py`
  - `tests/test_forge.py`
- **Implementation Specifications:**
  1. Create a new visitor class `ObsidianForgeVisitor(ASTVisitor)` inside `forge.py`.
  2. **Frontmatter Translation:** When evaluating the first node or page properties, format the inherited `LogseqPage.properties` into a valid YAML frontmatter block `--- \n key: value \n ---` at the top of the exported string.
  3. **Block Reference Translation:** Obsidian does not use `((uuid))`. It uses `[[Page Name#^uuid]]` for links and appends `^uuid` at the end of the target block. The visitor must append ` ^{node.uuid[:8]}` (or the full UUID) to the end of the Markdown line if the block is referenced elsewhere.
  4. **Wikilink Normalization:** Ensure wikilinks `[[Page]]` remain intact.
  5. Add a static method `to_obsidian_markdown(nodes: list[LogseqNode], page_properties: dict) -> str` to the `ForgeExporter` facade class.
  6. **Quality Gate:** Add `test_forge_obsidian_markdown_translation` ensuring YAML frontmatter is generated and block IDs use the `^id` syntax instead of `id::`.

---

## 🎯 Task 2: CLI Integration for Obsidian Vault Export

- **Objective:** Allow users to compile an entire Logseq graph into an Obsidian Vault via the KINETIC CLI.
- **Target Files:**
  - `src/logseq_matryca_parser/kinetic.py`
  - `tests/test_kinetic.py`
- **Implementation Specifications:**
  1. Add `OBSIDIAN = "obsidian"` to the `ExportFormat` Enum inside `kinetic.py`.
  2. Implement `_export_obsidian(graph: LogseqGraph, output_path: Path) -> int`.
  3. Iterate through `graph.pages`. For each page, use `ForgeExporter.to_obsidian_markdown` and write the result into a `.md` file inside the target `output_path`, respecting the namespace hierarchy (e.g., creating folders if the page is `Projects/AI/Matryca`).
  4. **Quality Gate:** Add a CLI test simulating the `export --format obsidian` command and verifying the output filesystem contains valid Obsidian Markdown files.

---

## ✅ Autonomous execution checklist (Wave 10)

Use this section during implementation; flip `[ ]` → `[x]` as each gate completes.

- [x] Task 1: `ObsidianForgeVisitor` in `forge.py` and tests in `tests/test_forge.py`
- [x] Local health: `make check` and `make test`
- [x] Task 2: `obsidian` format in `kinetic.py`, directory-preserving writer, CLI tests in `tests/test_kinetic.py`
- [x] Global verification: `make check`, ruff, mypy, pytest — all green
- [x] Architect notified (contract checklist fully `[x]`)

---

## Cursor 3 (Agents Window) — activation prompt (Composer-2)

Copy everything inside the fence below into Composer-2:

```
Act as an autonomous AI Agent in God-Mode following the H.S.E. engineering framework. Your objective is to fully implement the Obsidian integration detailed inside the contract file `ROADMAP_OBSIDIAN_ADAPTER.md` located in the root directory.

CRITICAL INSTRUCTIONS:
- In Task 1, you must accurately translate Logseq properties into standard YAML Frontmatter (`---`) at the top of the document. Convert Logseq block IDs to Obsidian's trailing `^block-id` syntax.
- In Task 2, ensure the CLI exporter creates nested directories if the Logseq page title contains namespaces (e.g., `Folder/Page.md`).

Operate in a strictly atomic, sequential loop:
1. Implement `ObsidianForgeVisitor` inside `src/logseq_matryca_parser/forge.py` and write the corresponding validation tests in `tests/test_forge.py`.
2. Run your local health validation via `make check` and `make test`.
3. Add the `obsidian` format switch to `src/logseq_matryca_parser/kinetic.py` and implement the directory-preserving file writer. Write the CLI mock tests.
4. Trigger the global verification suite (`make check`, ruff, mypy, pytest) to certify 100% green compliance.
5. Mark completed checkboxes inside `ROADMAP_OBSIDIAN_ADAPTER.md` changing `[ ]` to `[x]`, and notify the Architect.
```
