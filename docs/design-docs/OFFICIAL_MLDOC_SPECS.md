# **LOGSEQ\_OFFICIAL\_TESTS.md**

The parsing architecture underpinning the Logseq platform represents a highly specialized synthesis of standard Markdown principles and Org-mode hierarchical directives. This dual lineage is implemented via a dedicated, OCaml-based functional parsing engine known as mldoc, which is an evolution of the mlorg parser originally designed by Simon Castellan.1 Operating in an ecosystem that demands local-first text editing coupled with a highly structured Datalog graph database, the mldoc parser is tasked with an exceptionally difficult lexical objective. It must continuously ingest relatively unstructured, plain-text character streams and deterministically compile them into a strictly typed Abstract Syntax Tree (AST).2 This AST is subsequently serialized into JSON or Extensible Data Notation (EDN) for ingestion by Clojure/ClojureScript backend processes, which manage the graph schema, Malli validations, and Real-Time Collaboration (RTC) synchronization logic.4

Because Logseq functions fundamentally as an outliner rather than a traditional document renderer, the standard rules of CommonMark or GitHub Flavored Markdown (GFM) frequently conflict with the application's required data topology. Consequently, the mldoc engine—utilizing the Angstrom parser combinator library—has been heavily customized to process a wide array of esoteric textual edge cases. The parser must simultaneously track absolute spatial indentation layouts, isolate legacy system metadata drawers, map complex key-value property associations, and recursively resolve deeply nested graph references without triggering infinite loops or catastrophic backtracking.2

The exhaustive documentation provided herein details the official syntax edge cases, structural anomaly tests, and deterministic AST behavior targets synthesized directly from the logseq/mldoc testing framework. The insights are derived from the logic encapsulated within test/test\_markdown.ml and the corresponding Clojure schema validators located in the deps/graph-parser directory.5 The analysis spans four primary focus areas critical to the reverse-engineering of the graph parser: Broken and Extreme Indentation topologies, System Noise isolation, Property and Metadata mapping, and complex Reference and Tag entity resolution.

## ---

**Part 1: Topological Layout and Broken Indentation Dynamics**

In a conventional Markdown specification, document hierarchy is predominantly established via explicit heading markers, where the parser's primary responsibility is to construct a flat sequence of block-level elements. In these traditional models, nesting is generally reserved for list items and is dictated by sequential two-space or four-space indentations. However, the Logseq parsing paradigm fundamentally subverts this standard model. The application views every discrete paragraph or user entry as an independent "block" arranged within a rigid tree structure.3

To support this outliner paradigm, the mldoc parser utilizes absolute whitespace indentation levels as the overriding source of truth for the parent-child topology, regardless of the semantic depth indicated by traditional heading markers.3 The Angstrom scanner within mldoc maintains a stateful layout context, conceptually tracking virtual indentation and dedentation tokens based purely on the character count of leading whitespace at the commencement of a new line.2 The parser associates zero spaces with the root level, while incremental offsets dictate deeper tree nesting.3

This absolute indentation rule introduces profound complexities during the lexing phase, particularly when users introduce malformed text. Copy-pasting text from external sources, switching between devices with mismatched space-to-tab editor settings, or interleaving heading markers with unexpected whitespace blocks forces the parser to deploy aggressive error-recovery heuristics. When a new heading block is introduced at a specific indentation level, the parser must calculate a relative offset, adjusting all subsequent child levels against the newly established baseline.3 The tables and scenarios below dictate exactly how the AST resolves these geometric textual fractures.

| Leading Whitespace Condition | Lexical Interpretation | AST Parent-Child Assignment Rule |
| :---- | :---- | :---- |
| Zero spaces (Root) | Baseline established at Level 0\. | Node is assigned as a root block in the JSON AST array. |
| Consistent positive delta (e.g., \+2 spaces) | Virtual INDENT token emitted. | Node is nested as a direct child of the preceding block. |
| Inconsistent positive delta (e.g., \+4 spaces skipping \+2) | Baseline shift without intermediate node creation. | Node is nested as a direct child, with layout state updated to the new delta. |
| Mixed tab/space siblings | Deduplication and normalization fallback. | Sibling status granted if the column alignment falls within the established tolerance threshold. |
| Negative delta (e.g., \-2 spaces) | Virtual DEDENT token emitted. | Parser ascends the layout stack until a matching baseline column is found, appending as a sibling to the matched node. |

## **Scenario: Absolute Indentation Overriding Heading Semantics**

**Context:** The mldoc parser rigorously tests the primacy of absolute whitespace indentation over standard Markdown heading depth algorithms. In this scenario, lower-level headings (such as H3) are physically placed at the root level, while top-level headings (such as H1) are indented to appear as children. The parser must demonstrate that the AST hierarchy is constructed strictly from the whitespace prefix state, thereby relegating the heading markers to mere inline formatting or metadata variables attached to the AST node, rather than dictating the structural tree depth.3 **Input Markdown:**

### **Root Level H3**

\- Level 1 Bullet  
	\# Level 2 H1  
		\- Level 3 Bullet

**Expected Output / AST Behavior:** The Abstract Syntax Tree deterministically ignores the conventional semantic meaning of the hash markers for hierarchy construction. The Angstrom parser initializes its indentation tracking stack at column zero. The initial string \#\#\# Root Level H3 is parsed with zero indentation, resulting in its assignment as a root node of type Heading with a metadata parameter of :level 3\.6 As the scanner proceeds to the next line, it detects a single tab character, which introduces a positive indentation delta. The parser emits a virtual indentation token, and the text Level 1 Bullet is instantiated as the first child of the root node.

Subsequently, the parser encounters \\t\\t\# Level 2 H1. This introduces a second positive spatial delta. The parser binds this block as a direct child of the Level 1 Bullet node. Even though the string contains a primary \# marker, the AST registers the node topologically at depth two (as a grandchild of the root), while storing the heading formatting within the node's properties as a Heading object with :level 1\. Finally, the string \\t\\t\\t- Level 3 Bullet is evaluated and nested beneath the Level 2 H1 node. If this document is exported via a tool like logseq-file-ast, the resulting JSON structure heavily favors structural nesting over heading parameters, yielding a strictly unified tree that mathematically corresponds to the physical tabs rather than the markdown semantics.3

## **Scenario: The Zero-to-Four Space Fracture**

**Context:** A critical failure point in standard markdown parsers occurs when text contains broken indentation sequences—specifically, a sudden geometric jump from a zero-space prefix directly to a four-space prefix, entirely bypassing an intermediate two-space or single-tab level. The mldoc engine must decide whether to treat the heavily indented text as a grandchild (which would necessitate the creation of a phantom, empty intermediate child node), a direct child with a non-standard spatial baseline, or an indented code block as dictated by standard CommonMark specifications.3 **Input Markdown:**

* Root Node  
  * Sudden Four Space Node  
    * Normal Two Space Delta  
      **Expected Output / AST Behavior:**  
      To resolve this anomaly, the mldoc lexer employs a specialized whitespace unification pass designed to preserve user intent within the context of an outliner database. The parser initially reads the Root Node string at column zero. Upon scanning the subsequent line, it detects four consecutive spaces. While a strict standard Markdown parser might interpret four spaces following a list item as either a block continuation or an erroneously formatted string, the Logseq outliner paradigm mandates that this represents a nested level.

Because the intermediate two-space level is entirely missing from the character stream, mldoc does not generate a phantom or empty intermediate node to bridge the gap. Instead, it dynamically binds the Sudden Four Space Node as a direct child of the Root Node, internally recording the new spatial baseline delta for this specific subtree as four spaces. When the parser moves to the third line and encounters six spaces, it calculates a delta of two spaces relative to the parent node. The parser seamlessly accepts this as a valid child of the Sudden Four Space Node. When the AST normalizes these relationships into JSON or EDN formats, the inconsistent visual spacing is entirely stripped. The final hierarchical array transforms the physical character variations into purely logical datalog relationships, linking the blocks cleanly without retaining the spatial anomalies.3

## **Scenario: Sibling Mismatch and Dedent Calculation**

**Context:** Within the layout state machine, sibling nodes are structurally mandated to share the exact same indentation prefix string. If siblings present with mismatched white spaces—for instance, one node utilizing a physical tab character while another utilizes four individual space characters—the mldoc parser's scanner must execute character reconciliation heuristics to prevent the layout stack from prematurely issuing a block termination command.3 **Input Markdown:**

* Parent Block  
  * Sibling One (1 Tab)  
  * Sibling Two (4 Spaces)  
  * Sibling Three (2 Spaces) **Expected Output / AST Behavior:** The OCaml parsing logic applies an aggressive character-equivalence heuristic during the layout scanning phase. In the Logseq ecosystem, a physical tab is generally mapped to equivalent space geometry depending on the user's overarching graph configuration, though the internal mldoc engine frequently defaults to a rigid two-space parity for Markdown lists.3 The Sibling One string establishes the first child indentation baseline utilizing a \\t character. When the scanner evaluates the subsequent string, Sibling Two, it processes the four space characters.

If the internal parity configuration equates one tab to two spaces, the four-space prefix dictates that Sibling Two is actually a child of Sibling One, pushing it to a grandchild depth. However, if the parity equates a tab to four spaces, the layout state machine recognizes Sibling Two as a direct sibling of Sibling One. The standard fallback behavior isolates the relative delta. Because Sibling Three uses only two spaces, the layout tracker determines that the spatial column is less than the active stack depth for Sibling Two, forcing the emission of a DEDENT token. The AST dynamically flattens these misalignments into the closest logical levels, grouping the siblings beneath the Parent Block if their calculated column depths fall within the bounds of a single logical level. This strict spatial alignment is crucial for preventing graph corruption during real-time collaborative editing sessions, where disparate client environments may inject conflicting whitespace characters into the shared sequence.3

## ---

**Part 2: System Noise Isolation and Legacy Drawer Processing**

The Logseq desktop and web applications do not operate strictly as passive text renderers; they simultaneously function as state engines for task management, scheduled time tracking, and application-specific metadata configurations. To achieve this embedded functionality without permanently polluting the readable document body, Logseq borrows extensive syntax from the Emacs Org-mode ecosystem.2 This legacy implementation relies on designated hierarchical "drawers" and system noise markers. Strings such as :LOGBOOK:, CLOCK:, PROPERTIES:, and custom double-colon directive booleans like collapsed:: true must be successfully identified at the lexical level, parsed into discrete metadata objects, and subsequently discarded from the primary visual text rendering pipeline.13

The mldoc parser achieves this through specialized Angstrom combinators designed to sniff the opening sequences of a block for these specific markers.2 When a line commences with a colon character, followed immediately by a recognized system keyword and a terminating colon, the parser executes a hard state transition. It temporarily suspends the standard Markdown block parsing logic and shifts into a dedicated "drawer-consumption" mode. Within this state, the scanner blindly reads all subsequent lines as opaque strings or timestamp objects until it encounters the explicit closing tag :END:.13

This sequestration mechanism is absolutely critical for database integrity. The data held within these drawers, such as task state transition timestamps or Pomodoro tracking times, is structurally alien to standard paragraph content. A failure to correctly identify the termination token—or mishandling an empty drawer initialization—can lead to catastrophic cascading failures within the parser, where the entire remainder of a document is swallowed into an invisible AST metadata node.14 The parser must also gracefully resolve single-line system noise directives that dictate frontend UI behavior but hold zero semantic weight in the user's textual note.13

| System Noise Token | Combinator State Shift | Target AST Destination |
| :---- | :---- | :---- |
| :LOGBOOK: | Enters multi-line opaque drawer consumption mode. | Appends strings to the :logbook array within the node's :meta dictionary. |
| :PROPERTIES: | Enters multi-line dictionary mapping mode. | Parses key-value pairs into the :properties map within the :meta dictionary. |
| :END: | Terminates drawer mode. | Restores primary block parsing state machine. |
| CLOCK: | Triggers timestamp regex evaluation. | Translates temporal bounds into the time-tracking index; stripped from visible text. |
| collapsed:: true | Single-line directive stripping. | Injects a boolean :collapsed flag into the block's AST definition; stripped from visible text. |

## **Scenario: Standard System Drawer Encapsulation**

**Context:** This scenario strictly evaluates the parser's capacity to enter and exit the Org-mode drawer state without corrupting adjacent block structures. It validates the foundational requirement that the CLOCK: tracking sequence and state change strings nested inside a :LOGBOOK: drawer are mapped directly to metadata AST structures rather than rendered text blocks, ensuring that the parent block's textual output remains pristine.2 **Input Markdown:**

* TODO Implement the new AST parser  
  :LOGBOOK:  
  CLOCK:-- \=\> 01:00  
  :END:  
  * Sub-task continuing after the drawer **Expected Output / AST Behavior:** The AST generation sequence begins with the parser identifying the TODO keyword at the start of the block, which immediately flags the node for task state formatting. As the scanner transitions to the next line, which is spatially indented to become a child or property of the root TODO block, it encounters the string :LOGBOOK:. The Angstrom combinator consumes this specific token and forces the lexer into drawer mode.14 The subsequent CLOCK: line is read as raw string data by the base parser, knowing that downstream logic (specifically frontend.util.clock) will translate these temporal boundaries into the database.15

The scanner continues until it matches the :END: token, which successfully terminates the drawer mode and releases the lock. In the resulting JSON AST structure, the primary node representing the TODO block contains only the textual string Implement the new AST parser within its title array. All LOGBOOK data is completely sequestered into a non-rendered :meta or :drawer object attached to the block's programmatic definition. Crucially, the string \- Sub-task continuing after the drawer is parsed normally and nested as a standard child block of the TODO block. This structural outcome proves that the drawer parser successfully and cleanly returned control to the main block-level combinator stack without consuming adjacent siblings.6

## **Scenario: Empty Drawer and Malformed Noise Anomaly**

**Context:** Software regression reports, specifically GitHub Pull Request \#138 and Issue \#3823, explicitly highlight the parser's failure state when encountering an initialized but immediately terminated :LOGBOOK: drawer.14 Historically, if a drawer was completely empty, the lexer failed to recognize the state change, leading to severe synchronization issues where the underlying markdown file updated its state but the user interface did not accurately reflect the database modification.14 **Input Markdown:**

* TODO Clean SCHEDULED: \<2022-01-08 Sat.+2d\>  
  :LOGBOOK:  
  :END:  
  **Expected Output / AST Behavior:**  
  The OCaml combinator responsible for executing the take\_until ":END:" directive must exhibit high tolerance for zero-length payloads. The parser matches the opening :LOGBOOK: token and prepares for sequential reading. However, as it peeks at the very next token in the stream, it encounters :END:, resulting in a payload length of absolute zero.

To maintain database integrity, the AST must construct a valid but empty logbook meta-object for the block rather than faulting. The parser strictly forbids throwing a fatal exception or swallowing the subsequent document structure due to the empty array. The expected AST behavior yields an output array containing the block text TODO Clean SCHEDULED... alongside a structural :meta dictionary where the :logbook key maps directly to an empty array \`\` or nil.6 This deliberate handling ensures that the application frontend can safely clear task timers and reconcile the graph database without experiencing a desynchronization event.

## **Scenario: Inline UI Directives and System Booleans**

**Context:** Logseq heavily leverages a double-colon syntax (e.g., collapsed:: true) inline within the Markdown stream to persist user interface state variables or block behavior toggles across distinct sessions. Because these variables do not utilize standard property blocks or drawer encapsulation, the parser must rely on localized geometric scanning to recognize these specifically defined reserved keys and dynamically strip them from the visible paragraph text.13 **Input Markdown:**

* A massive block of text that the user wants to hide.  
  collapsed:: true  
  **Expected Output / AST Behavior:**  
  As the lexer evaluates the block lines, it scans for trailing directive strings appended to the paragraph nodes. The string collapsed:: true is identified against an internal dictionary of reserved noise directives. When the AST object is constructed for the string A massive block of text..., the parsing logic actively mutates the textual payload by stripping the collapsed:: true line entirely from the visible inline text tuple.

In its place, the AST generation sequence injects a boolean flag directly into the block's root property definition or metadata dictionary, establishing the key-value pair :collapsed true. This guarantees that the front-end rendering engine automatically folds the block upon initialization. Conversely, if a non-reserved or user-defined keyword is utilized with the double-colon syntax in this exact same geometric position, the parser automatically routes the character stream to the secondary Properties parser instead, treating it as user-defined metadata.6

## ---

**Part 3: Properties and Metadata Extraction**

Beyond the isolation of legacy system noise, the Logseq parsing engine implements a highly sophisticated key-value property system. These dynamically mapped properties enable users to assign specific database identifiers to individual blocks, construct complex Datalog queries, and define reusable programmatic templates.13 The syntax driving this feature relies on the double-colon operator (e.g., key:: value), a convention uniquely adapted to the Logseq Markdown dialect. The parser must distinguish flawlessly between built-in special properties that dictate system behavior (such as id:: for block referencing, tags:: for automated indexing, or title:: for page aliasing) and arbitrary, user-defined custom properties.13

Within the mldoc execution pipeline, the block property parsing phase typically triggers immediately following the resolution of block boundaries but before the initiation of deep inline text tokenization. When a discrete block is scanned, any trailing lines or immediately nested lines featuring the :: delimiter are aggregated into a temporary buffer.17 The resulting data structure cleanly partitions the core textual payload of the block from its metadata schema. This partition is structurally imperative, ensuring that Datalog queries can rapidly filter millions of nodes based on property keys without executing computationally expensive string-matching operations against the entire graphical document body.18

An exceptionally complex edge case emerges when the properties themselves contain nested block references, page links, or inline markdown formatting strings, such as id:: \[id:\](\] "...") or author::\].12 The property value parser cannot default to ingesting these variables as raw, unformatted strings; it must recursively invoke a subset of the inline Markdown parser to build a secondary AST specifically for the property values. This recursive parsing requirement imposes strict constraints on calculation depth to prevent stack overflow vulnerabilities during massive graph compilation cycles.

| Property Key Type | Lexical Target | AST Extraction Output |
| :---- | :---- | :---- |
| Built-in identifier (id::) | Matches universally unique identifier regex. | Extracted as a core string and injected into the block's top-level database identifier field. |
| System routing (tags::) | Matches comma-separated string literals. | Tokenized into an array of Tag nodes and injected into the :tags object schema. |
| User-defined (custom::) | Matches arbitrary string to arbitrary string. | Passed through recursive inline parsing; output as nested tuples in the :properties map. |
| Inline textual anomaly | Fails block-boundary geometric heuristic. | Bypasses property parsing entirely; rendered visually as a Plain text node. |

## **Scenario: Universally Unique Identifier (UUID) Binding**

**Context:** The entirety of Logseq's block referencing capability relies on highly stable, universally unique identifiers assigned automatically or manually via the id:: property.9 This diagnostic test ensures that the parser strictly extracts the UUID string, purges it from the visible block body to prevent visual clutter, and binds it permanently to the node's top-level metadata definition. Furthermore, it validates the parser's capacity to maintain integrity when specialized Anki spaced-repetition cloze syntax is mixed dynamically with identifier generation.20 **Input Markdown:**

* test anki cloze 2 {{c1 ![][image1]}} id:: 5defb049-56eb-4cc8-a391-3d9cdd74c907 **Expected Output / AST Behavior:** The execution flow dictates that the parser first isolates the main block text from the layout stream. During the secondary scan, it detects the explicit string id:: immediately followed by a structurally valid UUID sequence. In the AST generation phase, the entire id::... line is forcefully stripped from the Paragraph or Label node's string tuple, ensuring it will never be printed to the user interface.6

The serialization output structure—whether JSON or EDN—takes the isolated identifier string and injects it directly into the block's top-level identifiers, yielding an object geometry similar to :meta {:properties {"id" "5defb049-56eb-4cc8-a391-3d9cdd74c907"}}.6 Crucially, the parser ensures that the primary text tuple containing \["Plain" "test anki cloze 2 "\] and the highly specialized cloze tuple containing \["Cloze"...\] remain perfectly intact and geometrically accurate, entirely free from the trailing identifier noise that previously occupied the same physical text block.20

## **Scenario: Complex Value Tokenization within Properties**

**Context:** Advanced users frequently nest active graph links, index tags, or rich formatting within the property values to create dynamic dashboards. Consequently, the property value parser must not treat the extracted value as an opaque literal string; it must recursively tokenize the value payload for active links to ensure the Datalog database registers the backlink and updates the node graph accordingly.16 **Input Markdown:**

* Primary research statement.  
  source::\]  
  related-tags:: \#theory, \[\[physics\]\]  
  **Expected Output / AST Behavior:**  
  The initial parsing phase for the double-colon properties splits the input string precisely at the first valid occurrence of ::. The extracted keys, source and related-tags, are converted into sanitized, machine-readable dictionary keys. Rather than halting execution, the extracted values are passed back into the inline combinator engine. The string \] is successfully parsed and converted into a PageReference AST node.

The related-tags string is far more complex, requiring tokenization into two distinct reference nodes: a Tag node representing \#theory and a secondary PageReference node representing \[\[physics\]\].6 The final AST architecture populates the :meta {:properties...} object with complex arrays of these parsed inline nodes rather than basic raw strings. By representing properties as nested AST tuples, the graph database engine can flawlessly traverse the bidirectional relationships implicitly defined within the metadata schema, enabling complex queries against nested properties.6

## **Scenario: Property Blocks vs. Standard Text Ambiguity**

**Context:** If the double-colon syntax appears inadvertently in the middle of a continuous text paragraph rather than at the geometric beginning of a line or as a distinct, trailing metadata block, the parser must deploy spatial heuristics to determine if it is a genuine property declaration or merely standard text (such as a code snippet demonstrating the syntax).13 **Input Markdown:**

* This is a standard sentence that contains a weird string like key:: value inside it.  
  actual-prop:: true  
  **Expected Output / AST Behavior:**  
  To prevent catastrophic false positives, the parser rigidly restricts property recognition to specific geometric bounds within the spatial block—typically localized to the end of the block and strictly delimited by line breaks. As the scanner evaluates the first sentence, the internal string key:: value is bypassed by the property engine and treated entirely as a literal inline text tuple \["Plain" "key:: value"\] because it does not follow a mandatory line break.

Conversely, the string actual-prop:: true resides on a discrete new line at the terminus of the block, perfectly conforming to the spatial property boundary rules. This line is aggressively stripped from the visible text output and injected into the :properties AST map as a boolean or string pair. This strict boundary enforcement is the primary defense mechanism preventing arbitrary prose from inadvertently corrupting the block's hidden metadata schema during unstructured journaling.6

## ---

**Part 4: Complex Graph Connectivity via References and Tags**

The foundational value proposition of a networked thought environment is its capacity for bidirectional linking and knowledge traversal. Logseq implements this architecture via a tri-modal syntax: standard page references delineated by \[\[Page Name\]\], indexing tags delineated by \#Tag, and highly specific block references delineated by ((uuid)).9 The inline parser within the mldoc ecosystem must traverse the text stream sequentially, character by character, to identify these specific delimiters. Because the system allows for an extraordinarily high prevalence of nested references—such as referencing a specific block that internally contains a page link, or placing a page link visual representation inside another page link alias—the inline parsing engine must support deep recursive descent without stalling the main thread.9

Block references using the ((uuid)) syntax present a highly unique lexing challenge. Unlike standard page references which can contain arbitrary and highly variable strings, block references must contain exactly formatted Universally Unique Identifiers (or their string equivalents in older databases).18 The parser must extract this UUID, validate its structural integrity, and generate a specific BlockReference AST node.6 When the ClojureScript frontend eventually receives this specific node type, it utilizes the embedded UUID to execute a direct Datalog pull query, retrieving the target block's complete AST and seamlessly rendering it inline within the user interface.9

Furthermore, standard hashing utilizing the \# symbol is deployed for inline tagging. However, in Markdown specifications, a \# symbol physically located at the beginning of a line inherently denotes a heading. Therefore, the parser must maintain contextual awareness to differentiate between a structural heading marker (which requires a trailing space) and an indexing tag (which directly precedes alphanumeric characters, e.g., \#tag).6 If a tag necessitates the use of spaces, the syntax borrows the page reference architecture, resulting in \#\]. The precedence rules between these overlapping tokens dictate the final geometric topology of the inline AST elements.2

| Reference Syntax | Recursive Parsing Depth | Resulting AST Node Type |
| :---- | :---- | :---- |
| \[\[Page Name\]\] | Standard inline tokenization. | PageReference |
| \#Tag | Single-word strict tokenization. | Tag |
| \#\] | Dual-state tokenization (Tag wrapper over PageReference). | Tag node containing a PageReference child array. |
| ((UUID)) | Strict UUID regex validation. | BlockReference |
| \[Alias\](((UUID))) | Deep recursion (Alias wrapper over BlockReference). | Link node where the target URL parameter is defined as a BlockReference. |

## **Scenario: Pure Block Reference Extraction**

**Context:** The parsing engine must successfully isolate the double-parenthesis syntax indicating a hard block reference. It is required to strip the wrapping parenthesis, validate the internal string payload as an active identifier string, and separate it cleanly from any surrounding punctuation or inline text strings.9 **Input Markdown:**

* The foundational argument is presented here: ((64c752b0-d33b-4448-a261-e4dc2bbe12d3)).  
  **Expected Output / AST Behavior:**  
  The inline scanner marches across the string until it matches the (( sequence, which immediately initiates a specialized take\_until "))" sequence combinator. The internal payload, 64c752b0-d33b-4448-a261-e4dc2bbe12d3, is extracted and passed to the validation engine. Upon success, the AST generation sequence constructs a highly structured tuple array representing the block's entire text geometry.

The resulting structure is defined as: \["Plain" "."\]\].6 The ability of the parser to successfully isolate the trailing period and capture it as an entirely separate Plain node proves that the block reference combinator successfully and cleanly yielded execution control back to the standard text scanner after consuming the exact boundaries of the reference.6

## **Scenario: Complex Tag Aliasing and Multi-word Indexing**

**Context:** Logseq officially allows hashtags to function symbiotically with page links, creating a mechanism where links can act as tags, and tags can encompass complex strings containing spaces. The syntax \[\[\#tag\]\] or \#\] forces the parser to subvert the standard rule where the \# character immediately terminates upon encountering a space.17 **Input Markdown:**

* An analysis of quantum mechanics via \#\[\[Quantum Physics\]\]. **Expected Output / AST Behavior:** This complex token sequence heavily stresses the parser's state-switching capabilities. The scanner encounters the \# symbol, which typically triggers a basic tag state designed to consume a single alphanumeric word. However, the immediate presence of \]\].6 By structurally prioritizing the bracket encapsulation over the standard space-delimiting rule of the hash symbol, the parsing engine successfully registers complex, multi-word indexing phrases without breaking the graphical backlink database.6

## **Scenario: Nested Link References and Aliased Blocks**

**Context:** Users frequently require the aliasing of links using standard Markdown URL syntax combined recursively with graph references, resulting in complex geometrical arrays such as (((uuid))).17 The AST must recursively build a node hierarchy where the link target is recognized as an internal graphical entity rather than a standard HTTP URL. **Input Markdown:**

* Check out this crucial definition related to the subject.  
  **Expected Output / AST Behavior:**  
  This string introduces severe stress to the depth-first recursive tokenizer within the Angstrom library. The scanner encounters the \`

## **Scenario: Complex Lexical Precedence \- Headings vs. Tags**

**Context:** A hash \# acts structurally as a heading marker if located at the absolute beginning of a line and followed by a space, but functions as a tag when utilized inline without trailing whitespace. This test specifically evaluates the lexical precedence rules enforced by the parse\_marker configurations deployed within the mldoc source code.2 **Input Markdown:**

# **\#heading-tag at the start of a heading**

**Expected Output / AST Behavior:** The parser approaches the line and identifies the first \# symbol. Because it is physically located at column zero and followed immediately by a space character, the block-level layout combinator consumes it. This action flags the entire subsequent block string as a structural Heading node populated with the metadata :level 1\.3

Following this structural assignment, the inline text scanner begins processing the remainder of the string: \#heading-tag at the.... The second \# symbol is processed. Because it features no trailing space, the inline combinator correctly consumes it as a standard Tag object. The AST output strictly respects this dual-nature parsing, generating the array: \]\]\["Plain" " at the start of a heading"\]\]}\].6 This absolute differentiation prevents early tagging characters from inadvertently upgrading text into heading block structures.

## ---

**Part 5: Lexical Collisions and Inline Boundary Resolution**

The most volatile and computationally complex area of textual parsing involves the resolution of inline formatting—specifically bolding, italics, inline code, and mathematical LaTeX formulas.2 Because these stylistic choices utilize overlapping token markers (e.g., \* for italic, \*\* for bold, \_ for italic, \_\_ for underline, $ for math), the mldoc lexer must implement highly specific, optimized lookahead and lookbehind assertions. As thoroughly documented within the test\_markdown.ml testing suite, certain environmental limits (such as the Safari browser engine's historical lack of support for JavaScript regex lookbehinds) dictate that the core OCaml engine must resolve these boundaries structurally before emitting the final AST payload to the JavaScript or ClojureScript clients.8

Historical bug reports and issues documented across the Logseq repository (such as Issue \#9266 and Issue \#8790) highlight recurring, critical failures in these specific overlapping zones. For instance, when a user pastes heavily formatted text from external applications like Microsoft Teams, it frequently yields malformed geometric strings such as \*\*bold text: \*\*.7 A naive parser observing the space before the closing asterisks will fail to match the bold pair entirely, instead matching the inner single asterisks and erroneously rendering the text as italics surrounded by literal asterisks.7 Similarly, subscripts and superscripts containing spaces (e.g., 1 \<sup\>st\</sup\> or 1^{st}) frequently fracture the AST string arrays if HTML elements aren't robustly handled alongside standard Markdown boundaries.7 Furthermore, escaping multi-tick code blocks inherently stresses the verbatim node calculation limits, requiring precise delimiter length tracking.24

## **Scenario: Bold vs. Italic Boundary Overlap (Trailing Space Anomaly)**

**Context:** Extracted directly from the diagnostics of GitHub Issue \#9266, when bold markers surround text that ends inadvertently with a space (a highly common artifact resulting from clipboard pasting from rich-text enterprise editors), the parser must decide whether to rigorously enforce strict CommonMark flanking rules (which reject the closing marker entirely if preceded by a space) or employ a permissive, specialized fallback behavior.7 **Input Markdown:**

* \*\*Inclusion of Dell and Cisco Partnerships: \*\* **Expected Output / AST Behavior:** Strict CommonMark flanking rules mathematically dictate that a closing \*\* marker sequence cannot be preceded by a whitespace character. The parser reads the opening \*\* and scans forward, finding the closing \*\* at the end of the string, but preceded by a space. According to the foundational bug report, earlier legacy versions of the Logseq parser fell back to matching the innermost \* markers, treating the string geometrically as \* (literal character) \+ \*Inclusion...: \* (italic formatting) \+ \* (literal character). This caused the AST to emit an Italic node sandwiched awkwardly between Plain text asterisks.7

To rectify this, the corrected, expected behavior implemented in the updated mldoc logic mandates an overriding trim operation or a specialized Logseq-flavor permissive bold match. The AST is now required to emit a singular Bold node containing the string Inclusion of Dell and Cisco Partnerships: , proactively stripping the trailing space to prevent the visual downgrade to italics and preserving the original rich-text intent.7

## **Scenario: HTML Superscript and Whitespace Fracturing**

**Context:** Logseq officially supports the injection of arbitrary HTML tags via the mldoc fallback parser pipeline. However, mixing HTML tags with adjacent whitespace and numerical data can cause unexpected text fragmentation, severely damaging the visual output, as seen extensively with superscript formatting bugs.7 **Input Markdown:**

* Normally it is 1st but what about 1 st? **Expected Output / AST Behavior:** The parser cleanly tokenizes the first instance, 1\<sup\>st\</sup\>. The resulting AST geometry represents this correctly as a \["Plain" "1"\] node, immediately followed by an HTML/Entity node for the superscript containing the string st.2 For the second instance, 1 \<sup\>st\</sup\>, the space disrupts the strict character binding.

The parser generates a \["Plain" "1 "\] node, followed independently by the superscript node. The AST correctly isolates the space into the Plain text node. The error noted by users where the output "renders as 1 st" is typically diagnosed as a downstream rendering CSS anomaly, but strictly at the parser level, the AST must maintain the highly structured HTML node definition rather than dropping the \<sup\> tags entirely and rendering them as raw text.7 This exact parsing behavior ensures that data loss does not occur when moving between platforms.

## **Scenario: Nested Verbatim Code Block Escaping**

**Context:** When a user wishes to document precisely how to write a code block within their notes, they must geometrically wrap a standard three-backtick string entirely inside a four-backtick string.24 This scenario rigorously tests the greedy nature of the Angstrom take\_until combinator assigned to verbatim syntax parsing. **Input Markdown:** \-\`

Snippet di codice

code

\`\`\`  
\*\*Expected Output / AST Behavior:\*\*  
The lexer matches the initial \`\`\`\`\` string as the opening marker sequence for a \`CodeBlock\` or \`Verbatim\` node.\[2, 24\] Critically, it must store the mathematical length of this opening delimiter (which is 4\) into its active state tracking buffer. As the scanner consumes the internal payload, it encounters \`\`\`\`lang\`. 

Because the delimiter length of the internal string is 3 (which is strictly less than the state-tracked delimiter of 4), the parser engine treats it entirely as a literal string payload rather than a termination sequence. The parser only halts when it encounters the closing \`\`\`\`\` sequence matching the exact length of 4, successfully terminating the block. The AST output is a highly clean \`CodeBlock\` node containing the exact internal string \`\`\`\`lang\\ncode\\n\`\`\`\` without prematurely closing, thus mathematically verifying the dynamic delimiter-length tracking integrity within the OCaml lexer state.

\#\# Scenario: Anki Cloze and LaTeX Math Boundaries  
\*\*Context:\*\* The Logseq user base heavily integrates spaced repetition study methodologies and advanced mathematical documentation. Therefore, the parser must cleanly and flawlessly distinguish between standard curly braces, LaTeX math boundary markers (\`$\`), and specific Anki spaced-repetition cloze structures such as \`{{c1...}}\` when they are interleaved within the exact same geometric string.  
\*\*Input Markdown:\*\*  
\- test anki cloze 1 {{c1 $\\mathrm{K}$}}  
\*\*Expected Output / AST Behavior:\*\*  
The inline parser reads the initial string sequence \`test anki cloze 1 \`. Upon encountering the sequence \`{{c1 \`, it triggers a hard transition into the specialized Cloze node combinator pipeline. Deep inside the cloze execution state, it encounters the \`$\` symbol, which immediately triggers a sub-transition into the LaTeX inline math combinator. 

The Math combinator consumes the internal string \`\\mathrm{K}\` and elegantly closes its state upon encountering the secondary \`$\`. Subsequently, the Cloze combinator resumes and closes successfully at the \`}}\` delimiter sequence. The resulting AST array is highly nested but geometrically perfect: \`\["Cloze" {:id "c1", :content \[\["Math" "\\\\mathrm{K}"\]\]}\]\`. The parser correctly proves its deep recursive descent capabilities, allowing complex LaTeX AST nodes to exist dynamically inside spaced-repetition Cloze nodes without the \`{}\` structural braces of the LaTeX syntax maliciously confusing the closing \`}}\` sequence of the overarching Cloze tag.

#### **Bibliografia**

1. mldoc/mlorg at master \- GitHub, accesso eseguito il giorno aprile 25, 2026, [https://github.com/logseq/mldoc/blob/master/mlorg](https://github.com/logseq/mldoc/blob/master/mlorg)  
2. Mldoc \- Another Emacs Org-mode and Markdown parser. \- GitHub, accesso eseguito il giorno aprile 25, 2026, [https://github.com/logseq/mldoc](https://github.com/logseq/mldoc)  
3. Allow non-outline (freeform) text \- \#45 by cannibalox \- Feature Requests \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/allow-non-outline-freeform-text/172/45](https://discuss.logseq.com/t/allow-non-outline-freeform-text/172/45)  
4. logseq/logseq: A privacy-first, open-source platform for knowledge management and collaboration. Download link: http://github.com/logseq/logseq/releases. roadmap: https://logseq.io/p/NX4mc\_ggEV · GitHub \- GitHub, accesso eseguito il giorno aprile 25, 2026, [https://github.com/logseq/logseq](https://github.com/logseq/logseq)  
5. logseq/.i18n-lint.toml at master \- GitHub, accesso eseguito il giorno aprile 25, 2026, [https://github.com/logseq/logseq/blob/master/.i18n-lint.toml](https://github.com/logseq/logseq/blob/master/.i18n-lint.toml)  
6. GitHub \- cldwalker/logseq-clis, accesso eseguito il giorno aprile 25, 2026, [https://github.com/cldwalker/logseq-clis](https://github.com/cldwalker/logseq-clis)  
7. Use a proper markdown Standard such as GFM or Commonmark. · Issue \#9266 \- GitHub, accesso eseguito il giorno aprile 25, 2026, [https://github.com/logseq/logseq/issues/9266](https://github.com/logseq/logseq/issues/9266)  
8. updating page name doesn't update tags prefixed with ... \- GitHub, accesso eseguito il giorno aprile 25, 2026, [https://github.com/logseq/logseq/issues/6611](https://github.com/logseq/logseq/issues/6611)  
9. The basics of Logseq block references \- Documentation, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/the-basics-of-logseq-block-references/8458](https://discuss.logseq.com/t/the-basics-of-logseq-block-references/8458)  
10. Different ways to structure data \- Queries \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/different-ways-to-structure-data/8819](https://discuss.logseq.com/t/different-ways-to-structure-data/8819)  
11. Option to Make Parser Respect Standard Markdown \- General \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/option-to-make-parser-respect-standard-markdown/640](https://discuss.logseq.com/t/option-to-make-parser-respect-standard-markdown/640)  
12. References with specific tag or task \- Queries \- Logseq forum, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/references-with-specific-tag-or-task/27734](https://discuss.logseq.com/t/references-with-specific-tag-or-task/27734)  
13. List of special properties and tags \- Documentation \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/list-of-special-properties-and-tags/25821](https://discuss.logseq.com/t/list-of-special-properties-and-tags/25821)  
14. LOGBOOK doesn't display state changes of repeating tasks · Issue \#3823 \- GitHub, accesso eseguito il giorno aprile 25, 2026, [https://github.com/logseq/logseq/issues/3823](https://github.com/logseq/logseq/issues/3823)  
15. logseq/src/main/frontend/components/block.cljs at master \- GitHub, accesso eseguito il giorno aprile 25, 2026, [https://github.com/logseq/logseq/blob/master/src/main/frontend/components/block.cljs](https://github.com/logseq/logseq/blob/master/src/main/frontend/components/block.cljs)  
16. Logseq's Export Formats \- Random Geekery, accesso eseguito il giorno aprile 25, 2026, [https://randomgeekery.org/post/2022/03/logseqs-export-formats/](https://randomgeekery.org/post/2022/03/logseqs-export-formats/)  
17. An idea for a more standard-Markdown property syntax \- General \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/an-idea-for-a-more-standard-markdown-property-syntax/20073](https://discuss.logseq.com/t/an-idea-for-a-more-standard-markdown-property-syntax/20073)  
18. Help Navigating & Converting Extensive Block References, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/help-navigating-converting-extensive-block-references/32051](https://discuss.logseq.com/t/help-navigating-converting-extensive-block-references/32051)  
19. Query to format structured blocks into table, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/query-to-format-structured-blocks-into-table/26733](https://discuss.logseq.com/t/query-to-format-structured-blocks-into-table/26733)  
20. cloze with latex doesn't work · Issue \#5087 \- GitHub, accesso eseguito il giorno aprile 25, 2026, [https://github.com/logseq/logseq/issues/5087](https://github.com/logseq/logseq/issues/5087)  
21. Why You Should Use Block References in Logseq: A Beginner's Introduction \- YouTube, accesso eseguito il giorno aprile 25, 2026, [https://www.youtube.com/watch?v=g66G2ThmC7M](https://www.youtube.com/watch?v=g66G2ThmC7M)  
22. Block References Issues and Ideas for Improvements \- Feature Requests, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/block-references-issues-and-ideas-for-improvements/15784](https://discuss.logseq.com/t/block-references-issues-and-ideas-for-improvements/15784)  
23. How can I get a folder hierachy on logseq? Pics of what I mean \- Reddit, accesso eseguito il giorno aprile 25, 2026, [https://www.reddit.com/r/logseq/comments/wibfz6/how\_can\_i\_get\_a\_folder\_hierachy\_on\_logseq\_pics\_of/](https://www.reddit.com/r/logseq/comments/wibfz6/how_can_i_get_a_folder_hierachy_on_logseq_pics_of/)  
24. Option to Make Parser Respect Standard Markdown \- \#9 by lewisia \- General \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/option-to-make-parser-respect-standard-markdown/640/9](https://discuss.logseq.com/t/option-to-make-parser-respect-standard-markdown/640/9)  
25. Markdown: cannot put bold words inside italic sentence · Issue \#8790 \- GitHub, accesso eseguito il giorno aprile 25, 2026, [https://github.com/logseq/logseq/issues/8790](https://github.com/logseq/logseq/issues/8790)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABoAAAAXCAYAAAAV1F8QAAAA9ElEQVR4XmNgGAVDDXAA8XMg/o+E3wFxKJKaY2jyRUhyJAOYIdiAGANEzhJdghyAy6JMIL6NLkgJAFmyD03sIhCXoYlRBJQYIBaxQPmiUD7VwRIGhMG5UDZNLIKltKtAnA3E96BiVAcwH4hA+YJQPkXJGB3Aggod7GfALk42eM+A3UBQwgCJT0GXgAJDIOaBsjmBmAlJDivAF/G45EAZF2Q4SO48EIsD8S8gtkNWBAJhQPyGAWEQCD8BYjYkNQ/R5F8iyekAMTNUHAZAbJA41QEoI99H4mPzOVXAZyCOReLfhdJULUlAAN0HeUB8EE1sFAxyAAAvTEOc/K2MwAAAAABJRU5ErkJggg==>