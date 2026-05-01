# Logseq Matryca Parser — Architecture (The Logos Protocol)

## 1. Title & High-Level Philosophy

### 1.1 The LLM operating system metaphor

Treat the intelligent stack not as an isolated language model but as **an operating system**:

| Layer              | Analogue in this architecture |
| ------------------ | ----------------------------- |
| **CPU**            | The LLM (reasoning, planning, generation). |
| **RAM**            | The **context window** — bounded, volatile working memory loaded from structured retrieval. |
| **Hard disk**      | The **Logseq graph** — durable, hierarchical, sovereign knowledge stored as outliner **Spatial Markdown** on disk. |

The Matryca Parser is the **deterministic translation layer**: it reads the hierarchical “filesystem” representation of thought (blocks, indentation, identities) without corrupting topology, so retrieval and prompting can assemble **faithful subgraphs** into RAM rather than brittle text shards.

### 1.2 “Blender RAG” vs. a topological file-system driver

**Naive / standard RAG** routinely applies **recursive or fixed-size chunkers** to raw Markdown. For Logseq-style graphs this behaves like dropping the disk into a blender: contiguous bytes are diced by character budgets, sibling blocks are fused with unrelated parents, and indentation semantics are erased. The result is embeddings of **ambiguous fragments** disconnected from lineage — a lossy projection of structured storage into unstructured bags of text.

The **Matryca (Logos) approach** rejects that erosion of structure. Implementation-wise, **`StackMachineParser` (alias `LogosParser`)** performs **O(N) deterministic parsing** using spatial indentation as the sole arbiter of parent–child linkage, yielding a rigorous **Abstract Syntax Tree (AST)** (`LogseqPage`, `LogseqNode`). **`SYNAPSE`** acts as driver-level output: adapters emit **LangChain `Document`** and **LlamaIndex `TextNode`** objects whose **metadata encodes lineage** (`parent_id`, `path`, `left_id`, graph tokens), preserving the **exact topological semantics** expected by Sovereign AI and local pipelines.

Together, LOGOS + SYNAPSE implement **Document-Driven Development** principles. Historical specifications and blueprints are preserved in [`/docs/design-docs/`](./design-docs/) to constrain behavior, while the runtime code enforces deterministic invariants matching those documents.

---

## 2. System Context Diagram

The following pipeline is the authoritative context view for enterprise readers: ingestion from raw graph markdown, deterministic AST construction, adapter emission, then downstream **vector store indexing** / **LLM OS** retrieval.

```mermaid
---
title: Matryca — End-to-End Data Plane (Topological Preservation)
---
flowchart LR
  %% Styles
  classDef source fill:#0f172a,stroke:#38bdf8,color:#e2e8f0;
  classDef logos fill:#14532d,stroke:#22c55e,color:#ecfccb;
  classDef synapse fill:#431407,stroke:#fb923c,color:#ffedd5;
  classDef sink fill:#1e1b4b,stroke:#a78bfa,color:#ede9fe;
  classDef lens fill:#0c4a6e,stroke:#38bdf8,color:#e0f2fe;

  subgraph SRC["SOURCE — Sovereign Knowledge"]
    G[("Logseq graph root")]:::source
    MD["Markdown under pages / journals"]:::source
  end

  subgraph LOGOS["LOGOS — AST engine (deterministic stack-machine)"]
    P["StackMachineParser / LogosParser"]:::logos
    AST["LogseqPage + LogseqNode AST"]:::logos
    REG["PageRegistry (UUID ⇄ Node)"]:::logos
  end

  subgraph SYN["SYNAPSE — Framework-native adapters"]
    LC["LangChain Document visitor"]:::synapse
    LI["LlamaIndex TextNode + NodeRelationship"]:::synapse
  end

  subgraph OUT["DESTINATION — LLM OS plane"]
    VS[("Vector store / index")]:::sink
    RAG["RAG retrieval + prompt assembly"]:::sink
    LLM[("LLM runtime (CPU)")]:::sink
  end

  subgraph LENS_SIDE["LENS — Human topology inspector (orthogonal)"]
    NX["NetworkX graph build"]:::lens
    PV["PyVis HTML export"]:::lens
  end

  G --> MD --> P --> AST
  P --- REG
  AST --> LC
  AST --> LI
  AST --> NX --> PV
  LC --> VS
  LI --> VS
  VS --> RAG --> LLM
```

Auxiliary exporters (**FORGE** for JSON / flat Markdown, **KINETIC** CLI orchestration) consume the same AST and are orthogonal to SYNAPSE; they are intentionally omitted above to emphasize the sovereign RAG path.

---

## 3. Core Components Detail

### 3.1 LOGOS — deterministic stack-machine parsing

**LOGOS** is the strict parser core ([`StackMachineParser`](../src/logseq_matryca_parser/logos_parser.py)).

- **Stack-machine semantics.** For each line, indentation is quantized (spaces plus tab-width scaling) into a discrete **logical level**. The parser maintains parallel stacks (`stack`, `stack_columns`, `stack_indents`). When a new bullet or heading block appears:
  - **Pop** ancestors while `stack_columns[-1] >= indent_level` (exit deeper subtrees).
  - **Maintain or nest** relative to the remaining top-of-stack (`stack[-1]`).
  - **Push** the freshly built `LogseqNode` onto the stack and register its UUID with `PageRegistry` for deterministic identity and future block-reference linkage.
  This yields **finite-state, linear-time** traversal with explicit ascend/descend behavior — not regex-driven whole-document guessing.

- **Spatial indentation rules.** In Logseq, **indentation defines the AST**, not list decoration. Heading blocks and bullets both participate as first-class structural lines. Levels are **normalized post-pass** to tree depth (`_normalize_indent_levels`) so persisted `indent_level` reflects hierarchical depth independent of authoring quirks after stack repair.

- **Block properties & `id::`.** Subsequent lines matching `key:: value` attach to **`current_node`** (or accumulate into **frontmatter-derived page properties** when no node exists yet). Parsed properties live in **`LogseqNode.properties`**. **`id::`** establishes the authoritative block UUID (`uuid` overridden from property `id` when present — the native anchor for `((uuid))` references inside Logseq).

- **`clean_text` isolation.** Embedding-facing text (`clean_text`) is produced by stripping property lines, timelines, markup noise appropriate to vector use, bullet prefixes, etc. **`content`** retains richer raw semantics; **`clean_text`** prevents **collapsed::**, SCHEDULED/DEADLINE noise, and similar system surface from poisoning semantic retrieval.

### 3.2 SYNAPSE — AST → LangChain / LlamaIndex with lineage injection

**SYNAPSE** (`logseq_matryca_parser.synapse`) implements **`ASTVisitor`** harnesses rather than brittle string serializers.

- **LangChain.** [`LangChainVisitor`](../src/logseq_matryca_parser/synapse.py) emits one **`Document`** per node with `page_content=node.clean_text` and metadata unioning **`node.properties`** with lineage fields (`uuid`, `parent_id`, `indent_level`, `source`, **`path`** — the UUID ancestry chain — `left_id`, `refs`, task/repeater/temporal cues). This preserves **parent context** explicitly in retrieval filters and re-ranking.

- **LlamaIndex.** [`LlamaIndexVisitor`](../src/logseq_matryca_parser/synapse.py) constructs **`TextNode`** instances keyed by **`id_=node.uuid`**. It wires **`NodeRelationship.PARENT`** and **`CHILD`** via **`RelatedNodeInfo`**, back-linking when the parent appears earlier in preorder traversal — encoding **topology as first-class edges** beyond flat metadata dictionaries.

Together, adapters guarantee that **embedding units align with intentional block boundaries**, not splitter accidents.

### 3.3 LENS — NetworkX topology + PyVis interactive visualization

**LENS** (`logseq_matryca_parser.lens.GraphVisualizer`) builds a **`networkx.Graph`** over **page ⇄ wiki/tag reference** projections using `NetworkXVisitor` during AST preorder walks. Nodes receive **degree-based sizing** (“sun” hotspots) and subgroup classification (`page`, `tag`, `journal`, etc.).

Visualization export uses **`pyvis`** with **`force_atlas_2based`** physics, fullscreen canvas, HUD filters, glassmorphism control chrome, and stabilized layout configuration suitable for **large graphs at interactive frame rates** in the browser (product positioning targets fluid exploration of graphs on the order of **10⁴ nodes**).

---

## 4. Data Flow Sequence

Lifecycle of introducing **one structural block line** after prior context established (bullet path; heading path symmetrically analogous).

```mermaid
---
title: LOGOS — Lifecycle of Parsing One Structural Block Line
---
sequenceDiagram
  autonumber
  participant LR as Line Reader
  participant INV as Indent & Line Classifier<br/>(bullet / heading / property / continuation)
  participant PSI as Content & UUID Builder<br/>_build_node (+ clean_text derivation)
  participant STK as Stack Machine<br/>pop · push · attach
  participant AST as Immutable LogseqNode<br/>(registered in PageRegistry)

  LR->>INV: Deliver raw_line (spatial text + leading whitespace)

  alt Structural bullet or heading prefix
    INV->>INV: Compute indentation level<br/>(_compute_indent_level)
    INV->>STK: While deeper/equal indentation exhausted → pop ascend
    PSI->>PSI: Resolve UUID (id:: / deterministic hash fallback)
    PSI->>PSI: Harvest inline tokens (wikilinks, tags, SCHEDULED/DEADLINE, headings)
    PSI->>PSI: Produce clean_text excluding property/key noise
    PSI->>AST: Instantiate LogseqNode shell
    STK->>STK: _initialize_node_graph_fields (path, left_id)
    alt Stack non-empty after pops
      STK->>AST: Attach as child<br/>model_copy(update parent_id)
      STK->>AST: Ripple immutable parent chain updates into stack tiers
    else Empty stack ⇒ root-level block
      STK->>AST: Append to LogseqPage.root_nodes
    end
    STK->>STK: push(node, indent_level)
    AST-->>LR: Become current_node for continuation lines / properties

  else key:: value property line following a block
    INV->>PSI: Parse property key/value
    PSI->>AST: Refresh current_node (+ optional uuid bridge for id property)
    Note over PSI: clean_text regenerated via clean_node_content
    PSI->>STK: _replace_stack_tail_node (immutable replace child slot)

  else Neither structural nor property
    INV->>PSI: Treat as soft-continuation merge into current_node
    PSI->>AST: Expand content (+ code fence / drawers per state)
    PSI->>STK: Replace tail references for nested immutables
  end
```

---

## 5. The Matryca Moat — Why Standard RAG Fails on Outliner Markdown

Recursive and character-budget chunkers assume **approximately flat prose**. Logseq violates that assumption fundamentally:

| Failure mode                         | Impact on sovereign knowledge |
| ------------------------------------ | ------------------------------ |
| **Mid-block splits**                  | Fragments multimodal bullets; orphans soft-line continuations. |
| **Loss of indentation topology**      | Child insights appear unrelated to hypotheses in parent bullets. |
| **Property ingestion as prose**       | `collapsed:: true`, SCHEDULED markers, drawer noise degrade embedding geometry. |
| **UUID / reference desynchronization**| Block anchors no longer correspond to embeddings; graph-native references `((uuid))` become orphaned strings. |

**Deterministic AST parsing plus SYNAPSE metadata** restores **semantic sovereignty**: each retrieval unit inherits explicit **ancestor identity** (`parent_id`, cumulative `path`) and optional graph-native LlamaIndex **edges**, enabling **topology-aware augmentation** aligned with Andrej Karpathy’s mental model — the LLM “CPU” issues reads against a hierarchical disk through a **faithful driver**, not a stochastic blender.

---

*This document reflects the implementations in `src/logseq_matryca_parser/logos_parser.py`, `synapse.py`, `lens.py`, and `logos_core.py`, and complements narrative primers such as [`logseq_ast_primer.md`](logseq_ast_primer.md).* 
