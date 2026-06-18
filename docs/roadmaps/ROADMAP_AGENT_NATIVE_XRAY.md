# 📜 Architectural Contract: Agent-Native "Printing Press" & X-Ray Mode

**Contract Status:** Wave 11 — executed (suite green)
**Target Stack:** Python 3.12+ | Pydantic V2
**Inspiration Architectures:** "Printing Press" paradigm (steipete), Token-optimized dense AST mapping.

---

## 🎯 Task 1: The X-Ray Session Alias Registry

* **Objective:** Drastically reduce LLM context token consumption by replacing 36-character Logseq UUIDs with minimal sequential integer aliases (e.g., `[0]`, `[1]`) during agent reads, while keeping a translation map in memory.
* **Target Files:**
    * `src/logseq_matryca_parser/agent_press.py` (New File)
    * `tests/test_agent_press.py` (New File)
* **Implementation Specifications:**
    1. Create a new module `agent_press.py` dedicated to machine-native interactions.
    2. Implement a `SessionAliasRegistry` class. It must expose:
       * `generate_aliases(nodes: list[LogseqNode]) -> dict[int, str]`: Takes a list of nodes, assigns a unique sequential integer to each node's UUID, and returns the mapping (Alias -> Real UUID).
       * `resolve_alias(alias: int) -> str | None`: Reverses the translation.
    3. **Quality Gate:** Write a test asserting that passing 3 nodes generates aliases 0, 1, 2, and that resolving `1` returns the correct original UUID.

- [x] Task 1 complete

---

## 🎯 Task 2: Ultra-Dense Zero-Fluff Exporter (X-Ray AST)

* **Objective:** Serialize the AST into the absolute minimum amount of tokens required for an LLM to understand the outline topology. No metadata, no collapsed states, no empty lines.
* **Target Files:**
    * `src/logseq_matryca_parser/agent_press.py`
    * `tests/test_agent_press.py`
* **Implementation Specifications:**
    1. Inside `agent_press.py`, create a function `to_xray_markdown(nodes: list[LogseqNode], registry: SessionAliasRegistry) -> str`.
    2. For each node, it must output a strictly indented string representing only the alias and the `clean_text`.
    3. Format rule: `"{indent}[{alias}] {clean_text}"`. (e.g., `  [2] Database Phase`).
    4. Strip all markdown properties, drawers, and Logseq specific syntax that is irrelevant to the agent's immediate semantic understanding.
    5. **Quality Gate:** Test that a complex nested Logseq block with properties is reduced to a maximum of 2-3 lines of pure text with bracketed integer aliases.

- [x] Task 2 complete

---

## 🎯 Task 3: The Compound Agent CLI Command

* **Objective:** Expose a single, powerful CLI command that agents can use to instantly search the graph and get an ultra-dense X-Ray response back in stdout.
* **Target Files:**
    * `src/logseq_matryca_parser/kinetic.py`
* **Implementation Specifications:**
    1. Add a new Typer command to `kinetic.py`: `@app.command() def agent_read(graph_path: Path, tag: str = typer.Option(None), query: str = typer.Option(None))`
    2. The command must load the `LogseqGraph`. If `tag` is provided, use the fluent `GraphQuery().has_tag(tag).execute()`. If `query` is provided, use `search_content(query)`.
    3. Pass the results to `SessionAliasRegistry` and `to_xray_markdown`.
    4. Print the output directly to `stdout` in pure raw text (Zero Fluff, bypass Rich formatting entirely for this specific command so the agent doesn't read terminal color codes).
    5. **Quality Gate:** Ensure the CLI command can be invoked without errors and outputs plain text.

- [x] Task 3 complete
