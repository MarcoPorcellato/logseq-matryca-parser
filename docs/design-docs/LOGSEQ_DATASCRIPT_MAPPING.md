# **LOGSEQ\_DATASCRIPT\_MAPPING.md**

The architectural integrity of the LOGOS parser depends upon a precise reverse-engineering of the Logseq Datascript schema. Logseq represents a departure from traditional Markdown-based note-taking applications by implementing an Entity-Attribute-Value (EAV) model, where the Markdown file serves as a serialized representation of a persistent in-memory Datalog graph database.1 To achieve 100% semantic parity, the Python-based LOGOS objects must mirror the internal logic that transposes plaintext syntax into specific database attributes. This report provides a technical specification for that mapping, detailing the keywords, data structures, and relationship logic utilized within Logseq’s core.

## **The Foundation of the EAV Model in Logseq**

Logseq utilizes Datascript, a ClojureScript implementation of the Datalog query language, to manage its internal graph. The database treats every distinct element—whether a page or a block—as an entity identified by a unique numeric :db/id.1 These entities are defined by a series of facts, known as datoms, which consist of an entity ID, an attribute (a namespaced keyword), and a value. For the LOGOS developer, it is critical to understand that the Markdown file is essentially a transaction log that the Logseq app parses to populate this graph.4

The schema is not strictly enforced in the same manner as a relational database, but it relies on a set of core attributes that define the behavior of blocks and pages. These attributes determine how information is indexed, how hierarchies are navigated, and how metadata is surfaced through the UI and the advanced query engine.6

## **Page Entity Specification**

In the Logseq graph, a page is fundamentally a special type of block entity that possesses a :page/name attribute.8 While blocks are typically anonymous and identified by position, pages provide named entry points into the graph. The mapping of a Markdown file to a page entity involves several critical attributes that manage identity, file association, and temporal metadata.

### **Page Identification and Normalization**

The primary identifier for a page is the :page/name. Logseq employs a strict normalization protocol for this attribute. Every page name is converted to lowercase for indexing purposes.1 This normalization is what enables case-insensitive linking across the graph. For instance, \] and \[\[research\]\] resolve to the same entity. However, Logseq also maintains the :page/original-name to preserve the user's preferred casing for display in the UI.10

| Datascript Attribute | Data Type | Markdown/System Source | Description |
| :---- | :---- | :---- | :---- |
| :page/name | String | File name or title:: | Normalized lowercase identifier for the page entity.10 |
| :page/original-name | String | File name or title:: | The casing of the page name as originally defined by the user.10 |
| :page/file | Ref | File system path | A reference to the entity representing the underlying .md or .org file.10 |
| :page/alias | Ref (Many) | alias:: property | A collection of references to other page entities serving as synonyms for this page.10 |
| :page/tags | Ref (Many) | tags:: property | References to pages that categorize this page entity.10 |

For a Python parser, managing the relationship between :page/name and :page/original-name is vital. When serializing a LogseqPage object back to Markdown, using the normalized name would lead to a loss of the user's aesthetic preferences, whereas failing to use it during lookup would break the graph’s internal linking consistency.

### **Journal Metadata**

Journal pages are a specialized subset of page entities. They are identified by the :page/journal? boolean flag.6 The core of the journal system is the :page/journal-day attribute, which stores the date as an integer in YYYYMMDD format (e.g., ![][image1] for May 20, 2024).6 This integer-based storage is mathematically efficient for range-based Datalog queries, allowing the app to quickly aggregate blocks across a specific timeframe.

| Datascript Attribute | Data Type | Markdown/System Source | Description |
| :---- | :---- | :---- | :---- |
| :page/journal? | Boolean | File location/name | Indicates if the page is a daily journal entry.6 |
| :page/journal-day | Integer | File name (e.g., 2024\_05\_20.md) | The date of the journal entry as a sortable integer.10 |

The LOGOS parser must be able to derive these attributes from the file name patterns typically found in the journals/ directory. Without correctly mapping :page/journal-day, the temporal context that powers Logseq’s "Journals" view will be inaccessible to any downstream RAG system.

## **Block Entity Specification**

The block is the atomic unit of the Logseq graph. Almost every element in a Markdown file—every bullet, paragraph, and heading—is transacted as a :block entity.17 Unlike pages, which are often file-level objects, blocks are granular and carry a significant amount of positional and state data.

### **Core Block Attributes**

Every block is assigned a unique :block/uuid.6 This UUID is the immutable address of the block, allowing it to be referenced from any other part of the graph. When a user creates a block reference using ((uuid)), Logseq looks up the entity associated with this specific keyword.

| Datascript Attribute | Data Type | Description |
| :---- | :---- | :---- |
| :block/uuid | UUID | Universally unique identifier; corresponds to the id:: property in Markdown.6 |
| :block/content | String | The raw text content of the block, including markers and property strings.6 |
| :block/page | Ref | A reference to the ID of the page entity containing the block.6 |
| :block/parent | Ref | A reference to the ID of the block's immediate parent (either another block or a page).6 |
| :block/left | Ref | A reference to the sibling block immediately preceding this block.6 |
| :block/format | Keyword | The syntax format, typically :markdown.6 |

The :block/content attribute stores the "source of truth" for the block's text. However, for efficient querying, Logseq "explodes" specific parts of this content into other attributes, such as :block/marker for tasks and :block/properties for metadata.11

### **The Mapping of Task States (Markers)**

Task management is a native feature of the Logseq database. When a block starts with a recognized keyword like TODO or DONE, Logseq extracts this into the :block/marker attribute.16 This allows the database to index tasks separately from regular text.

The following markers are hardcoded within the Logseq core logic and recognized by the database:

* TODO, LATER: Representing pending tasks.  
* DOING, NOW: Representing active tasks.  
* DONE: Representing completed tasks.  
* WAITING, WAIT: Representing tasks stalled by external dependencies.  
* CANCELED, CANCELLED: Representing tasks that have been aborted.19

If a block possesses a marker, it may also have a :block/priority, typically stored as a single character ("A", "B", or "C").10 These are not just part of the content string; they are distinct attributes that enable the sorting and filtering required for high-performance task dashboards.

## **Hierarchy and Topological Mapping**

One of the most critical aspects of the LOGOS parser is the reconstruction of the outliner hierarchy. Logseq does not use a simple array of children to represent nesting. Instead, it employs a pointer-based system that allows for efficient graph traversal and block movement.6

### **Parent and Sibling Logic**

The hierarchy is defined by two primary pointers: :block/parent and :block/left.

* **:block/parent**: This attribute points to the database ID of the entity directly above the current block. If a block is at the root level of a page, its parent is the page entity itself.6  
* **:block/left**: This attribute manages the sequence of blocks at the same level of indentation. It points to the block immediately "to the left" (i.e., preceding it). The first block under a parent will have a :block/left value that is either null or, in some internal transactions, points back to the parent to signal the start of a list.6

This structure is effectively a linked list for siblings, combined with a parent pointer for the tree structure. To reconstruct a page in Python, the LOGOS parser must follow the :block/parent references to establish the tree and then use the :block/left references to sort each level of the tree. This is a departure from standard Markdown parsers that treat indentation as a simple depth integer.

### **The Path-Refs Indexing Mechanism**

Logseq implements a specialized attribute called :block/path-refs to handle context inheritance in the graph.23 While :block/refs contains only the pages and blocks explicitly mentioned in a block’s content, :block/path-refs is a transitive collection that includes:

1. All direct references in the block.  
2. All references made by the block's parent.  
3. All references made by every ancestor up to the page level.  
4. The ID of the page itself.6

This inheritance logic is the engine behind Logseq’s powerful search capabilities. It allows a query for \#research to return a specific bullet point even if that bullet does not contain the tag, provided that one of its parent blocks or the page itself is tagged with \#research.20 For the LOGOS parser, calculating :block/path-refs is essential for ensuring that Python-serialized objects can support the same level of discoverability as the original Logseq app.

## **Property System Engineering**

Properties in Logseq (key:: value) are the primary mechanism for adding structured data to the outliner. These are stored in a specialized :block/properties map and an accompanying :block/properties-order vector.10

### **The Properties Map and Normalization**

The :block/properties attribute is a map where keys are stored as keywords. Logseq performs normalization on these keys, often converting underscores to hyphens and ensuring they are lowercase.11

The storage of values within this map is determined by the content type:

* **Plain Text**: Stored as a simple string.  
* **Page References**: If a value is enclosed in brackets \[\[ref\]\] or prefixed with \#, it is stored in the database as a **Clojure Set** of strings.11 This allows a single property to point to multiple entities. For example, tags:: \[\[work\]\]\[\[urgent\]\] is stored as \#{"work" "urgent"}.

### **Maintaining Document Order**

Because maps in Clojure/Datascript are inherently unordered, Logseq uses the :block/properties-order attribute—a vector of keywords—to remember the exact sequence in which the user wrote the properties.10 Without this attribute, the LOGOS parser would randomly reorder properties every time a file is saved, which would be unacceptable for a high-fidelity tool.

| Attribute | Data Type | Example Value |
| :---- | :---- | :---- |
| :block/properties | Map | {:status "active", :type \#{"project"}} |
| :block/properties-order | Vector | \[:status :type\] |

The parser must also account for "hidden" properties used by the system, such as :collapsed (boolean) and :heading (boolean), which govern the UI representation of the block.13

## **Relationship Mapping: Refs, Tags, and Block Refs**

Connectivity in the Logseq graph is achieved through three primary syntactic structures. While they appear different in Markdown, their mapping to the Datascript database follows a highly unified logic.

### **Wikilinks and Hashtags**

In the current "Logseq MD" implementation, there is no functional difference between a wikilink \[\[Page Name\]\] and a hashtag \#PageName. Both are parsed and stored in the :block/refs attribute as references to a page entity.15 The choice between them is primarily an aesthetic one made by the user to indicate whether the link is part of a sentence or a categorization metadata.15

However, the Python developer must be aware of the "Logseq DB" transition, where hashtags act as "NewTags" (similar to Supertags in Tana). In this emerging model, a tag is not just a link but a template that can automatically apply properties to the block it is attached to.30

### **Block References and Reverse-Lookup**

Block references ((uuid)) are mapped to the target block’s :db/id in the :block/refs collection.6 Logseq does not store the text of the referenced block; it dynamically resolves the reference at render time.

The reverse-lookup (backlinking) for blocks is indexed by querying the :block/refs attribute across the entire database to find all entities that point to a specific block's ID.32 This is a computationally intensive task, which is why Logseq also maintains a :block/path-refs index to speed up these lookups in the context of specific pages or hierarchies.23

## **Metadata and Temporal State Mapping**

Logseq tracks the lifecycle of every block and page using temporal attributes. For the LOGOS parser, maintaining these timestamps is critical for sync and history features.

### **Timestamps and Performance**

The attributes :block/created-at and :block/updated-at store Unix timestamps (in milliseconds). While these are standard for pages, Logseq sometimes omits them for individual blocks to improve performance on large graphs.10 If a block lacks these attributes, the parser should assume they are inherited from the parent page or the file's modification time.

| Datascript Attribute | Data Type | Source |
| :---- | :---- | :---- |
| :block/created-at | Integer | System creation time.10 |
| :block/updated-at | Integer | Last modification time.10 |

If the LOGOS parser is used to build a RAG system, these timestamps are essential for implementing "recency bias" in retrieval, ensuring the AI prioritizes information that the user has recently engaged with.

## **JSON Specification: A Complex Block Example**

To guide the development of the Python LogseqNode object, the following JSON represents a fully-featured block as it exists inside the Datascript database. This example includes a task marker, properties, tags, and a child block.

### **Markdown Source**

* TODO Deliver the\] technical report \#urgent  
  id:: 64909c2c-2838-405f-8c02-4a0d53356518  
  type::\]  
  priority:: A  
  scheduled:: 20240520  
  * Ensure 100% semantic parity with the graph

### **Datascript JSON Mapping**

JSON

\] technical report \#urgent\\n  type::\]\\n  priority:: A\\n  scheduled:: 20240520",  
    "block/marker": "TODO",  
    "block/priority": "A",  
    "block/scheduled": 20240520,  
    "block/page": { "db/id": 100 },  
    "block/parent": { "db/id": 100 },  
    "block/left": { "db/id": 5000 },  
    "block/format": "markdown",  
    "block/properties": {  
      "type":,  
      "priority": "A",  
      "scheduled": 20240520  
    },  
    "block/properties-order": \["type", "priority", "scheduled"\],  
    "block/refs": \[  
      { "db/id": 101, "block/name": "logos" },  
      { "db/id": 102, "block/name": "urgent" },  
      { "db/id": 103, "block/name": "documentation" }  
    \],  
    "block/path-refs": \[  
      { "db/id": 100 },  
      { "db/id": 101 },  
      { "db/id": 102 },  
      { "db/id": 103 }  
    \],  
    "block/created-at": 1716200000000,  
    "block/updated-at": 1716210000000  
  },  
  {  
    "db/id": 5002,  
    "block/uuid": "9b12c3d4-e567\-890a-bc1d\-2e3f4a5b6c7d",  
    "block/content": "Ensure 100% semantic parity with the graph",  
    "block/page": { "db/id": 100 },  
    "block/parent": { "db/id": 5001 },  
    "block/left": null,  
    "block/format": "markdown",  
    "block/path-refs": \[  
      { "db/id": 100 },  
      { "db/id": 5001 },  
      { "db/id": 101 },  
      { "db/id": 102 },  
      { "db/id": 103 }  
    \]  
  }  
\]

## **Logic for Serializing Python Objects to Datascript**

To build the LOGOS parser, the serialization logic must handle the "lifting" of Markdown text into these structured triples. The process is not a linear read-and-write but a multi-pass graph construction.

### **Phase 1: Identity Extraction**

The parser must first scan for the id:: property. If found, this is transacted as the :block/uuid. If not, a V4 UUID is generated and the property is injected back into the Markdown to ensure persistence. This identity is the primary key for the LogseqNode object in Python.

### **Phase 2: Positional Resolution**

As the outliner is parsed, each block’s indentation level determines its :block/parent. The parser must maintain a "current sibling" state for each level of the tree. When a new block is encountered at depth ![][image2], its :block/left pointer is set to the previous block found at depth ![][image2] under the same parent. This correctly maps the sequence of the document to the graph topology.

### **Phase 3: Reference Explosion**

The parser must iterate through the :block/content and extract wikilinks, tags, and block refs. Each extracted string is normalized (lowercased) and checked against the :page/name index. If a match is found, a reference triple \[block-id :block/refs page-id\] is created. For block refs, the UUID is resolved to its corresponding :db/id.

### **Phase 4: Property Map Construction**

The parser must extract the property block (the lines immediately following the first line of content).

1. Keys are converted to keywords (e.g., Type:: \-\> :type).  
2. Values are inspected for brackets. If present, the value is wrapped in a set.  
3. The original order of keys is recorded in the :block/properties-order vector.

## **Conclusion**

The mapping between Logseq Markdown and Datascript is a sophisticated transformation that turns a hierarchical text file into a contextual graph. Achieving semantic parity requires the LOGOS parser to meticulously manage normalized page identities, linked-list hierarchy pointers, and set-based property values. By following the schema specifications outlined in this technical document, the LOGOS project can ensure that its Python objects are mathematically equivalent to the data structures used in Logseq, providing a solid foundation for advanced graph-based applications and RAG systems. This specification serves as the authoritative guide for the implementation of the LogseqPage and LogseqNode classes, ensuring that the "sovereign" parser maintains the integrity of the user's graph data.

#### **Bibliografia**

1. How advanced queries work \- step-by-step explainer \- Queries \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/how-advanced-queries-work-step-by-step-explainer/30544](https://discuss.logseq.com/t/how-advanced-queries-work-step-by-step-explainer/30544)  
2. LogSeq: Personal Knowledge Graphs with DB power | by Volodymyr Pavlyshyn \- Medium, accesso eseguito il giorno aprile 25, 2026, [https://volodymyrpavlyshyn.medium.com/logseq-personal-knowledge-graphs-with-db-power-85687d17cc4a](https://volodymyrpavlyshyn.medium.com/logseq-personal-knowledge-graphs-with-db-power-85687d17cc4a)  
3. How to create page with properties? Page templates? \- Questions & Help \- Logseq forum, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/how-to-create-page-with-properties-page-templates/26029](https://discuss.logseq.com/t/how-to-create-page-with-properties-page-templates/26029)  
4. nbb with features enabled for logseq \- GitHub, accesso eseguito il giorno aprile 25, 2026, [https://github.com/logseq/nbb-logseq](https://github.com/logseq/nbb-logseq)  
5. nbb-logseq/examples/from-js/README.md at main \- GitHub, accesso eseguito il giorno aprile 25, 2026, [https://github.com/logseq/nbb-logseq/blob/main/examples/from-js/README.md](https://github.com/logseq/nbb-logseq/blob/main/examples/from-js/README.md)  
6. General question about data structures to maximize benefits of ..., accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/general-question-about-data-structures-to-maximize-benefits-of-datalog-db-and-queries/20063](https://discuss.logseq.com/t/general-question-about-data-structures-to-maximize-benefits-of-datalog-db-and-queries/20063)  
7. Data structure in logseq \- Questions & Help, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/data-structure-in-logseq/21179](https://discuss.logseq.com/t/data-structure-in-logseq/21179)  
8. Where I can know the detail schema of logseq db \- Questions & Help, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/where-i-can-know-the-detail-schema-of-logseq-db/6053](https://discuss.logseq.com/t/where-i-can-know-the-detail-schema-of-logseq-db/6053)  
9. Option to treat specific blocks as pages \- Feature Requests \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/option-to-treat-specific-blocks-as-pages/13203](https://discuss.logseq.com/t/option-to-treat-specific-blocks-as-pages/13203)  
10. Logseq datascript schema · GitHub, accesso eseguito il giorno aprile 25, 2026, [https://gist.github.com/tiensonqin/9a40575827f8f63eec54432443ecb929](https://gist.github.com/tiensonqin/9a40575827f8f63eec54432443ecb929)  
11. A Little Guy and His Blog \- Investing and Technical ExcellenceA ..., accesso eseguito il giorno aprile 25, 2026, [https://www.eriksuniverse.com/](https://www.eriksuniverse.com/)  
12. Advanced query for sorted tasks with custom table view \- Look what I built \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/advanced-query-for-sorted-tasks-with-custom-table-view/29101](https://discuss.logseq.com/t/advanced-query-for-sorted-tasks-with-custom-table-view/29101)  
13. Official, comprehensive list of \`config.edn\` options \- Archive \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/official-comprehensive-list-of-config-edn-options/4935](https://discuss.logseq.com/t/official-comprehensive-list-of-config-edn-options/4935)  
14. Different ways to structure data \- Page 4 \- Queries \- Logseq forum, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/different-ways-to-structure-data/8819?page=4](https://discuss.logseq.com/t/different-ways-to-structure-data/8819?page=4)  
15. The difference between \[\[page links\]\], \#tags, and properties:: \- Documentation \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/the-difference-between-page-links-tags-and-properties/8393](https://discuss.logseq.com/t/the-difference-between-page-links-tags-and-properties/8393)  
16. Queries for task management \- Look what I built \- Logseq forum, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/queries-for-task-management/14937](https://discuss.logseq.com/t/queries-for-task-management/14937)  
17. Different ways to structure data \- Queries \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/different-ways-to-structure-data/8819](https://discuss.logseq.com/t/different-ways-to-structure-data/8819)  
18. Pages vs Blocks \- General \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/pages-vs-blocks/205](https://discuss.logseq.com/t/pages-vs-blocks/205)  
19. Custom workflows/TODO markers via plugins? \- Questions & Help \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/custom-workflows-todo-markers-via-plugins/18630](https://discuss.logseq.com/t/custom-workflows-todo-markers-via-plugins/18630)  
20. Queries for task management \- Page 6 \- Look what I built \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/queries-for-task-management/14937?page=6](https://discuss.logseq.com/t/queries-for-task-management/14937?page=6)  
21. Pinning active projects to journal page \- Questions & Help \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/pinning-active-projects-to-journal-page/25374](https://discuss.logseq.com/t/pinning-active-projects-to-journal-page/25374)  
22. Just realized the difference between page properties and block properties \- please double check, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/just-realized-the-difference-between-page-properties-and-block-properties-please-double-check/30433](https://discuss.logseq.com/t/just-realized-the-difference-between-page-properties-and-block-properties-please-double-check/30433)  
23. Automatic Query based on the parent block reference, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/automatic-query-based-on-the-parent-block-reference/16023](https://discuss.logseq.com/t/automatic-query-based-on-the-parent-block-reference/16023)  
24. Advanced Query that pulls all reference AND recursive name spaces \- Logseq forum, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/advanced-query-that-pulls-all-reference-and-recursive-name-spaces/21275](https://discuss.logseq.com/t/advanced-query-that-pulls-all-reference-and-recursive-name-spaces/21275)  
25. Tag based task aggregator \- Look what I built \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/tag-based-task-aggregator/21378](https://discuss.logseq.com/t/tag-based-task-aggregator/21378)  
26. Using 'contains?' on bracketed vs non-bracketed property values \- Queries \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/using-contains-on-bracketed-vs-non-bracketed-property-values/27221](https://discuss.logseq.com/t/using-contains-on-bracketed-vs-non-bracketed-property-values/27221)  
27. Lesson 5: How to Power Your Workflows Using Properties and Dynamic Variables \- Queries, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/lesson-5-how-to-power-your-workflows-using-properties-and-dynamic-variables/10173](https://discuss.logseq.com/t/lesson-5-how-to-power-your-workflows-using-properties-and-dynamic-variables/10173)  
28. Logseq makes \#tags and \[\[pages\]\] the same construct. How has that worked for you? \- Reddit, accesso eseguito il giorno aprile 25, 2026, [https://www.reddit.com/r/logseq/comments/1mkhxqz/logseq\_makes\_tags\_and\_pages\_the\_same\_construct/](https://www.reddit.com/r/logseq/comments/1mkhxqz/logseq_makes_tags_and_pages_the_same_construct/)  
29. Difference between \[\[\]\] and \# : r/logseq \- Reddit, accesso eseguito il giorno aprile 25, 2026, [https://www.reddit.com/r/logseq/comments/t41f6b/difference\_between\_and/](https://www.reddit.com/r/logseq/comments/t41f6b/difference_between_and/)  
30. Introducing NewTags (with examples) \- Look what I built \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/introducing-newtags-with-examples/32310](https://discuss.logseq.com/t/introducing-newtags-with-examples/32310)  
31. Tags vs Pages in the New Logseq DB: A Missed Chance for Unification?, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/tags-vs-pages-in-the-new-logseq-db-a-missed-chance-for-unification/33684](https://discuss.logseq.com/t/tags-vs-pages-in-the-new-logseq-db-a-missed-chance-for-unification/33684)  
32. Help Navigating & Converting Extensive Block References, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/help-navigating-converting-extensive-block-references/32051](https://discuss.logseq.com/t/help-navigating-converting-extensive-block-references/32051)  
33. Logseq query to find all references to a block \- Hugo Ideler, accesso eseguito il giorno aprile 25, 2026, [https://hugoideler.com/2024/01/logseq-query-to-find-all-references-to-a-block/](https://hugoideler.com/2024/01/logseq-query-to-find-all-references-to-a-block/)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAE0AAAAXCAYAAABOHMIhAAADKklEQVR4Xu2XS8hNURTHlzcDCX0og6skBkoMPAp9UwYirygTUoYkAykyIV8xMjE1IUUmkpQBKYVEKY9EnqG85RnW/+y1fOv8v73v1R3q/Orf3eu/19lnn3323mdfkYaGhob/l0GqZfbbjlmqJWwSo1XLVaO4okBLdZFNY6qktgZzhTGbDWUCG4b3qxOLVXPYZF6pHqvOqH6rvtSrKyZLqjuoWmTlXMPwL6luWBnqROmex1SnVHNVt1Vv6tUVfo+ot7UMkXHmx35dr2Uktkqq26hao/ophUmEpHkZLz7sJIvjG8Sbh9cbvHeS3mbkh7QfOL8XDxoeiq87kvEQ42VflvSwDB4aObFf08yLbR2iGKzLeBV+cRzRr+bttviaxQy8BxRz3i7zhpMPsCRnSqrnQYP3lDzMbG6fY8YfnPPc837lcgC8DWxiaX4k75mk5H0Wt2sw+idVV0IMNkvK4f0NexVeBkB9HLQh5mH2RMabH+E4B3K4X9537xc/iwPvJZs5vIEWxUzJj9yUfE70UI6D1msell1kqPkRxFh63pct9eoi3HeUP4fY4bws8yUlvQ5e6cKSH0H9AfKwFeAr7CAnDtpq804Hz+H7Ib4X4l+qJyHOcVYG9gsx9mTmX56xSvie8XIXlnznvuTrP1DMg7bKvNKgjQjxjlAG6yXlrCQ/gnp8SdnratCwlGawKeULSz6A73tiBMeBYeTxoE0071zwwEjz2+FLuJQHP3eMgP+NTWnflhyX+gFzrGqblUsXlvxPqrUh3q4aY2W/piQH5VshBlPMdy5Y3Aqef0S67RcD7w6bYKekg2QE036plfdLuUGeDQ9VC8nj5cigndyRA4fLyArzHexfiOPqQBne3eCBTv3yY1YEEwfeAvKrgcHN8fnHZxmHSmysSI5/XRDHfWK6eT3Bw5nnheqqpLbwi5M8d4ZBPS+N3EGW98g90n+WdM5Lyon7HmZk7Bf+FTySelt+nsNMdY6aNwCYJUX2mueDhPKJ/uq/Xkk5/Dzoel6vrmaf/1XbJCkHbz/yXtUn6bx1WFJOXIL+JS4pgr+ScfahHqeJhoaGhoaGhq75A2ztO31XlLFcAAAAAElFTkSuQmCC>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABEAAAAXCAYAAADtNKTnAAAAs0lEQVR4Xu2SOwoCQRBECzFTY0Nv4gE8iJmXMDDxBGaewFMJIn5AUAM/aPX2DDs0s9Pm7oNKuqqbGhigxaNL7ag39aEe1Ik6Utcwu1GDuFBiBl3IcYd67qEttE2ODvSItCsioaUdJojf1LRiBCeA+oi0yrLG70ca8QI9+Bk3sIL6G2tEptDAwhoB+UfiP62RsoeG+tYIvFBuWVF6yhjqDa0hTKgD6gOiM/S7X5LZPC60/B1f03I3IioklxcAAAAASUVORK5CYII=>