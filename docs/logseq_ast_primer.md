# 🧠 Logseq AST Primer: Understanding Spatial Markdown and the Logos Protocol

To contribute to or understand the **Logos Protocol**, you must first understand the idiosyncratic nature of Logseq's data structure. 

Logseq does not use standard Markdown; it uses an **Outliner-based Spatial Markdown**. 
Standard NLP text splitters and RAG chunkers destroy Logseq data because they parse text linearly. Logseq must be parsed **topologically**.

Here is the domain logic that the Logos FSM (Finite State Machine) is built to handle.

---

## 1. The Outliner Paradigm (Spatial Indentation)

In standard Markdown, lists are just formatting. In Logseq, **indentation dictates the Abstract Syntax Tree (AST)**. The physical space defines the semantic parent-child relationship.

**Example:**

```markdown
- Strategy Meeting
  - Discussed Q3 goals
    - Marketing budget needs approval
  - Fired the PR agency
```

### The AST Translation

- **"Strategy Meeting" (Level 0)** is the Parent.
- **"Discussed Q3 goals" (Level 1)** is a Child. 

If you delete the parent, this child loses its context. Standard chunkers will split these lines into different vector embeddings, destroying the semantic link. Logos preserves it via `parent_id`.

---

## 2. Block Properties (The Metadata Layer)

Logseq allows injecting metadata directly into blocks. These are not standard Markdown frontmatter, but inline key-value pairs that must immediately follow the block's first line.

**Example:**

```markdown
- Advanced RAG Architecture #[[AI]]
  id:: 6628ec8c-5544-486a-8d77-62860c239851
  collapsed:: true
  custom_state:: verified
  - First principle of data extraction...
```

### Parsing Rules for Logos

1. Properties (like `id::`) belong to the block above them.
2. They must be stripped from the raw text content to avoid polluting the AI's context window.
3. The `id::` property is sacred: it overrides any deterministic UUID generation because it is the native anchor for Logseq's internal block-references.

---

## 3. Soft Breaks vs. Hard Breaks (Multiline Blocks)

A single block in Logseq can contain multiple lines of text without creating a new node. This is represented by `Shift+Enter` (soft breaks).

**Example:**

```markdown
- This is the first line of the block.
  This is the second line of the SAME block.
  - This is a new child block.
```

### Parsing Rules for Logos

If a line does not start with a bullet (`-` or `*`), and is not a property (`key:: value`), it is treated as a multiline continuation of the `current_node`.

---

## 4. The Matryca Moat: Why Standard RAG Fails

If you feed Logseq Markdown into `RecursiveCharacterTextSplitter` (LangChain) or similar naive chunkers:

- It splits blocks mid-sentence based on character count.
- It completely loses the parent-child indentation context.
- It ingests system properties (e.g., `collapsed:: true`) as semantic text, confusing the LLM.

The **Logos Protocol** solves this by walking the AST deterministically, isolating properties, and exporting "Clean-RAG" formatted data (`ForgeExporter`) where every node retains its hierarchical lineage.
