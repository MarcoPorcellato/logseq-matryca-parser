# **LOGSEQ\_ASSET\_RESOLUTION\_SPEC.md**

## **The Philosophical and Architectural Underpinnings of the Logseq Filesystem**

The development of the LOGOS parser necessitates a foundational understanding of the Logseq ecosystem, which is fundamentally predicated on a decentralized, local-first philosophy. Unlike centralized knowledge management systems that rely on proprietary databases or opaque blob storage, Logseq treats the user's local filesystem as the primary source of truth. This design choice implies that the application's internal state—managed via a Datascript database—is essentially a high-performance index or cache of the physical Markdown and Org-mode files residing on the disk.1 For the Senior Filesystem Architect, the core challenge lies in the "dual-truth" nature of Logseq: the logical graph represented in the database and the physical hierarchy represented in the OS directory structure.

The architecture of a Logseq graph is built around a root directory, often referred to as the "graph root." Within this root, the structure is standardized into several key subdirectories: /pages for standard notes, /journals for daily entries, /assets for binary files, and /logseq for configuration metadata, including config.edn and custom.css.1 The resolution of any asset or page reference is always calculated relative to this root, which ensures portability of the graph across different machines and operating systems, provided the entire folder is synced as a unit. However, the implementation of this resolution logic is non-standard, particularly in how it handles relative path traversal and the escaping of illegal characters in page titles.3

The block-oriented nature of Logseq further complicates this filesystem mapping. Every bullet point in a Markdown file is a "block" with a unique identity in the database, yet it lacks a physical counterpart on the disk unless it is a "page" block (the root of a file). This abstraction requires the LOGOS parser to bridge the gap between a sequential text file and a graph-based data structure where assets can be referenced at any level of the hierarchy. The following specification delineates the exact mechanisms Logseq employs to maintain this synchronization, focusing on asset resolution, namespace mapping, and the deep-linking capabilities of the PDF annotation engine.

## **Asset Path Resolution Logic: Algorithmic Translation**

Logseq's Asset Resolution Engine is designed to handle media files, PDFs, and other attachments while maintaining link stability during file renames or moves. The resolution logic deviates from standard Markdown editors because Logseq prioritizes the "Graph Root" as the primary reference point over the current file's directory.3

### **Relative Path Mechanics and Root-Centric Resolution**

In a typical Markdown environment, a relative path like ../assets/image.png would resolve relative to the directory containing the Markdown file. In Logseq, while the syntax remains the same, the internal resolver frequently defaults to the graph root to ensure that assets remain accessible even when pages are virtually nested within namespaces. This is a critical distinction for the LOGOS parser: the physical location of the file in the /pages or /journals folder does not necessarily determine the base for path resolution.4

| Path Type | Syntax Pattern | Resolution Strategy | System Behavior |
| :---- | :---- | :---- | :---- |
| Relative Asset | ../assets/file.png | Graph-Root Relative | Standard for dragged-and-dropped assets; resolves to \[graph-root\]/assets/file.png. 5 |
| Local Asset | assets/file.png | Root-Relative | Often used in older graphs or specific plugins; assumes the root as the base. 4 |
| Absolute System | file:///C:/Users/Graph/assets/a.png | OS Path | Fragile and non-portable; bypassed by Logseq's internal relative logic during sync. 5 |
| External URI | https://example.com/a.png | Remote URL | Handled by the browser/Electron layer; not considered a local asset. 7 |

One of the significant points of friction in the current implementation is the inconsistent handling of the double-dot .. notation in file:// links. Research indicates that Logseq sometimes ignores leading .. segments, incorrectly resolving them to logseq/assets/ instead of stepping up to the parent directory of the graph.4 For the LOGOS parser, the primary resolution algorithm must prioritize a search path that begins at the graph root. If an asset reference begins with assets/ or ../assets/, the parser should immediately prepend the graph root path, effectively normalizing the reference.

### **Namespace Complexity and Virtual Nesting**

Logseq implements a sophisticated namespace system (e.g., \]) that creates a virtual hierarchy within the UI. However, this hierarchy is not mirrored in the physical filesystem by default. Most pages reside in a flat structure within the /pages directory.8 When a page is "deeply nested," the physical Markdown file is still located at /pages/Projects\_\_Alpha\_\_Task.md (using the modern double-underscore separator).10

Because the physical depth of the file on the disk does not change regardless of the namespace depth, the resolution of ../assets/file.png remains constant. Logseq looks for assets relative to the physical graph root, not the virtual namespace hierarchy.8 This "flat-file hierarchy" paradox means that even if a user views a page as being several levels deep, the asset resolution logic is identical to that of a top-level page. The LOGOS parser must ignore the logical namespace depth when calculating system paths and focus strictly on the physical directory structure of the /pages folder.

### **Global vs. Local Assets: Portability and Identity**

Logseq makes a sharp distinction between "Local Assets"—those stored within the graph's own /assets directory—and "Global Assets" or external files. Local assets are treated as internal components of the knowledge graph and are indexed by the Datascript database with specific metadata.11

1. **Local Assets**: These are typically referenced using relative paths (../assets/). They are essential for graph portability. When the graph is moved to another computer, these relative links continue to function because they are resolved against the new graph root.3  
2. **Absolute Paths**: References using file:/// or absolute Windows/POSIX paths are considered external. These are not portable and will break if the graph is synchronized to a different device or if the external folder structure changes.5  
3. **Zotero and Symbolic Links**: Advanced users often manage large PDF libraries via Zotero. Because Logseq's relative path handling for external directories can be unreliable, the community often employs symbolic links within the /assets folder to trick Logseq into treating external folders as local ones.4

## **Namespace and Hierarchy Mapping: Filesystem Translation**

The mapping of page titles to filenames is governed by a set of escaping rules designed to maintain cross-platform compatibility while allowing the use of characters that are traditionally reserved by operating systems.

### **Physical vs. Virtual Translation**

The translation of logical page titles (e.g., Work.Projects.2024) into physical filenames has evolved significantly. Initially, Logseq used the URL-encoded %2F as the separator for namespaces (e.g., Work%2FProjects%2F2024.md).8 However, this led to "ugly" filenames and issues with filename length limits on Windows systems, where the %2F characters contributed to the 260-character MAX\_PATH limit.10

In modern versions of Logseq (starting around 0.8.9), the system transitioned to a new set of escaping rules.10 The primary change was the adoption of the double lowbar (\_\_) as the separator for namespaces, replacing both %2F and the previous problematic parsing of dots (.) into slashes.10

| Logical Character | Physical Filename Translation (Modern) | Reasoning |
| :---- | :---- | :---- |
| / (Namespace) | \_\_ (Double Underscore) | Avoids OS path reserved characters; improves readability outside Logseq. 10 |
| . (Dot) | Preserved as . | Historically parsed as a slash; now treated as a literal character to avoid breaking file extensions. 10 |
| (Space) | Preserved as | Standard Markdown editors and OSes handle spaces well; avoids the "clutter" of %20. 10 |
| : (Reserved) | HTML entity or Hex encoding | Prevents issues on Windows where colons are reserved for drive letters. 10 |

The LOGOS parser must be capable of bidirectional translation: it must be able to convert a user's search query for \[\[Projects/Alpha\]\] into the filename Projects\_\_Alpha.md, and conversely, it must be able to take a list of files in the /pages directory and reconstruct the logical namespace hierarchy for the LLM.

### **Namespace Aliasing and Rename Integrity**

When a user renames a parent namespace, Logseq does not perform a directory-level rename (as there are no actual directories for namespaces). Instead, it performs a bulk rename of all files in the /pages folder that share the affected prefix.12 For example, renaming the namespace Work to Job would trigger the following transformations:

* Work\_\_Tasks.md becomes Job\_\_Tasks.md  
* Work\_\_Projects\_\_Alpha.md becomes Job\_\_Projects\_\_Alpha.md

Because asset references are relative to the graph root (e.g., ../assets/file.png), they remain functional after the rename. The relative distance between the page file (in /pages) and the asset file (in /assets) is preserved.10 The database maintains the integrity of internal links by updating the :block/content and :block/path-refs attributes in Datascript.11 This mechanism ensures that child page links and their asset references do not break during organizational refactoring.

## **PDF Annotations and the HLS Deep-Linking Protocol**

Logseq's PDF annotation engine is one of its most technologically complex components, utilizing the hls:// (Highlight Link System) protocol to bridge the gap between structured notes and unstructured binary PDFs.

### **PDF Highlight Syntax and Coordination Data**

The hls:// syntax (e.g., \[\[hls://zotero\_link\_id\]\]) serves as a unique identifier for a specific annotation event. When a user creates a highlight, Logseq does not modify the original PDF file. Instead, it creates a "sidecar" annotation record.14 The link between a block in a note and a region in a PDF is mediated by an annotation page, typically prefixed with hls\_\_.

The (offset, position) data for a highlight is stored as a vector of coordinates within the properties of a block or in an associated .edn metadata file.14 These coordinates represent the bounding box of the highlight on the PDF canvas.

| Coordinate Metadata | Description | Technical Format |
| :---- | :---- | :---- |
| page | The literal PDF page number. | Integer |
| Rect | The bounding box (x1, y1, x2, y2). | \[float, float, float, float\] 15 |
| C | The RGB color of the highlight. | \[r, g, b\] (0.0 to 1.0 scale) 15 |
| type | The annotation subtype (e.g., /Highlight, /Rect). | EDN Keyword 15 |

The mapping back to the physical PDF is achieved through the file:: property in the first block of the annotation page. This property contains a relative path to the PDF in the /assets folder: file::../assets/research\_paper.pdf.16 When the user clicks an hls:// link, Logseq retrieves the coordinate data, opens the PDF viewer at the specified page, and renders an overlay on the PDF.js canvas at the stored coordinates.17

### **Annotation File Storage and Linking Logic**

Logseq's strategy for storing annotations is designed to keep them searchable and linkable.

1. **Markdown Annotation Pages**: For every annotated PDF, Logseq generates a Markdown file in the /pages directory named hls\_\_\<pdf\_filename\_without\_extension\>.md.16 This file contains all highlights for that PDF as individual blocks.  
2. **EDN Metadata**: While the text of the highlight is in Markdown, the technical metadata (coordinates, colors) is often stored in a companion .edn file within the /assets directory or embedded as hidden properties in the annotation blocks.14  
3. **The Link Chain**: The LOGOS parser can resolve a highlight link by following this chain:  
   * Identify ((block-ref)) in a user's note.  
   * Look up the block in Datascript to find its source page (the hls\_\_ page).  
   * Retrieve the hl-page and ls-pos properties from the block or sidecar file.  
   * Use the file:: property of the hls\_\_ page to find the absolute path to the PDF asset. 11

## **Resource Indexing in the Database: Datascript Attributes**

For the LOGOS parser to provide absolute system paths to an LLM, it must query the Datascript database, which acts as the relational map for the entire filesystem.

### **Internal Attributes for Assets and Files**

Logseq's Datascript schema defines specific attributes that link logical entities (blocks and pages) to physical resources.11

| Attribute | Entity Type | Function |
| :---- | :---- | :---- |
| :block/file | Block | A reference to the file entity where the block is stored. 11 |
| :page/file | Page | A reference to the file entity associated with the page. 11 |
| :file/path | File | The unique system path to the file, relative to the graph root. 11 |
| :block/page | Block | Links a block to its parent page entity. 11 |
| :block/ref-pages | Block | A set of references to pages (or assets) mentioned in the block. 11 |

When an asset is dragged into Logseq, a block is created with a content string like \!\[Label\](../assets/image.png). The database does not necessarily store a dedicated :asset entity. Instead, it indexes the file reference within the block content. The LOGOS parser must parse this content string and then use the :file/path of the containing page to resolve the absolute system path.

### **MIME Type Handling and Classification**

Logseq's internal classification of assets determines the rendering component used (e.g., image vs. video vs. PDF). This classification is primarily extension-driven but involves underlying system calls in the Electron environment to probe content types.18

Logseq classifies resources into several buckets:

* **Images**: Rendered via the frontend.extensions.lightbox and standard \<img\> tags. Supported formats include .png, .jpg, .jpeg, .gif, .svg, and .webp.19  
* **Videos**: Rendered via an internal player component (e.g., frontend.extensions.video.youtube or a local HTML5 video tag). Supported formats include .mp4, .webm, and .ogv.  
* **Audio**: Handled via the :audio renderer, which supports .mp3, .wav, and .m4a.5  
* **Documents**: Specifically .pdf files, which trigger the specialized frontend.extensions.pdf module.19

The classification logic is crucial for the LOGOS parser's "AI-Ready" objective. For a multimodal RAG system, the parser must identify the MIME type and route the asset to the appropriate model (e.g., a vision model for images or a text extraction pipeline for PDFs).

## **LOGOS Technical Specification: Blueprints for Implementation**

This section provides the concrete technical patterns and algorithms required for the LOGOS Python parser to replicate Logseq's internal resolution logic.

### **Regex Patterns for Asset Link Detection**

Logseq supports both Markdown and Org-mode syntax. The parser must utilize the following regex patterns to detect asset links and hls:// references accurately.

**Markdown Asset Links**:

Python

\# Captures:\!\[Label\](../assets/file.png) or \[Label\](../assets/file.pdf)  
MARKDOWN\_ASSET\_REGEX \= r'\!?(?:\\\[.\*?\\\])\\(((?:\\.\\.\\/)\*assets\\/\[^ \\)\]+)\\)'

\# Captures: file::../assets/file.pdf (Page/Block Properties)  
PROPERTY\_ASSET\_REGEX \= r'^\\s\*file::\\s\*((?:\\.\\.\\/)\*assets\\/\[^\\s\]+)'

7

**Org-mode Asset Links**:

Python

\# Captures: \[\[../assets/file.png\]\]  
ORG\_ASSET\_REGEX \= r'\\\[\\\[(?:\\.\\.\\/)\*assets\\/(\[^\\\]\]+)\\\]\\\]'

1

**HLS Highlight Links**:

Python

\# Captures: \[\[hls://1698059081568\_0\]\]  
HLS\_PROTOCOL\_REGEX \= r'\\\[\\\[(hls:\\/\\/\[^\\\]\]+)\\\]\\\]'

14

### **Asset Path Resolver: Pseudocode Algorithm**

The following algorithm provides a step-by-step resolution of a Logseq link to an absolute system path.

Python

def ResolveAssetPath(graphRoot, currentFilePath, linkContent):  
    """  
    Standardizes the resolution of a Logseq asset link to an absolute system path.  
    """  
    \# 1\. Normalize the link string  
    normalizedLink \= linkContent.replace('\\\\', '/')  
      
    \# 2\. Check for absolute file protocol  
    if normalizedLink.startswith("file://"):  
        \# Handle Electron/Windows path inconsistencies  
        path \= normalizedLink.replace("file://", "")  
        if path.startswith("/") and os.name \== 'nt':  
            path \= path\[1:\] \# Strip leading slash for Windows paths like /C:/  
        return os.path.abspath(path)  
      
    \# 3\. Handle Relative Assets (The Logseq Core Logic)  
    \# Logseq resolves '../assets/' and 'assets/' relative to the graph root.  
    if normalizedLink.startswith("../assets/") or normalizedLink.startswith("assets/"):  
        \# Remove any leading '../' to get the root-relative path  
        rootRelativePath \= normalizedLink.replace("../assets/", "assets/")  
        absolutePath \= os.path.join(graphRoot, rootRelativePath)  
        return os.path.normpath(absolutePath)  
          
    \# 4\. Handle Namespace-specific resolution (Edge Case)  
    \# If the current page is a namespace with physical folders (rare/manual)  
    \# we would look relative to currentFilePath.  
    localPath \= os.path.join(os.path.dirname(currentFilePath), normalizedLink)  
    if os.path.exists(localPath):  
        return os.path.normpath(localPath)  
          
    \# 5\. Fallback: Search the entire /assets folder for the filename (Logseq's soft resolution)  
    filename \= os.path.basename(normalizedLink)  
    globalAssetPath \= os.path.join(graphRoot, "assets", filename)  
    if os.path.exists(globalAssetPath):  
        return globalAssetPath

    return None \# Link could not be resolved

4

### **PDF Highlight Extraction: Data Structure Specification**

The extraction of PDF highlights requires parsing the sidecar .edn files or page properties and mapping them to the specific coordinate system of the PDF.

**Annotation Block Structure (JSON Output for LLM)**:

JSON

{  
  "protocol": "hls://",  
  "annotation\_id": "1698059081568\_0",  
  "source\_pdf": {  
    "logical\_name": "how\_to\_take\_smart\_notes.pdf",  
    "absolute\_path": "/home/user/graph/assets/how\_to\_take\_smart\_notes.pdf",  
    "mime\_type": "application/pdf"  
  },  
  "highlight\_data": {  
    "page\_number": 12,  
    "coordinates": {  
      "x1": 52.9556,  
      "y1": 728.343,  
      "x2": 191.196,  
      "y2": 743.218  
    },  
    "color\_rgb": \[1.0, 1.0, 0.0\],  
    "text": "Writing is not the outcome of thinking; it is the medium in which thinking takes place."  
  }  
}

14

**Technical Mapping Logic**:

1. When the parser encounters \], it queries the database for a block where :block/content or a custom property matches \<ID\>.  
2. The parser retrieves the parent page (e.g., hls\_\_how\_to\_take\_smart\_notes).  
3. It resolves the file:: property of that page to locate the physical PDF in /assets.  
4. It extracts the ls-pos (coordinates) and hl-page (page number) from the annotation block properties.  
5. These coordinates are passed to the RAG system, allowing a visual processing agent to crop the specific region of the PDF for the LLM to "see." 14

## **Evolution and Future Trajectory of the Logseq Filesystem**

The transition toward a "Database Version" of Logseq marks a potential shift in how assets and namespaces are managed. While the current specification focuses on the stable Markdown-based filesystem, the future architecture may rely more heavily on SQLite or a similar relational storage engine.26 However, the core logic for asset resolution is expected to remain backwards compatible to support the existing multi-platform synchronization model.

### **Towards Physical Directory Support**

There is a long-standing proposal within the Logseq community to move from encoded filenames (e.g., A\_\_B.md) to a physical directory structure (e.g., A/B.md).9 Proponents argue this would improve compatibility with standard Markdown tools and avoid filename length limits. If Logseq adopts this "Virtual Hierarchy" or "Folder-based Namespace" model, the LOGOS parser's ResolveAssetPath algorithm will need to be updated to handle variable directory depths. In such a scenario, the ../assets/ relative path would become a literal traversal relative to the Markdown file's location, rather than a shorthand for the graph root.

### **Implications for AI and Multimodal RAG**

The primary motivation for the LOGOS parser—making Logseq "AI-Ready"—requires a level of filesystem precision that goes beyond standard note-taking apps. By mastering the Asset Resolution Engine, the LOGOS parser can provide an LLM with a comprehensive context window that includes:

* **Spatial Context**: Exactly where on a PDF page a highlight was made.  
* **Hierarchical Context**: How a specific asset fits into the larger namespace taxonomy.  
* **Relational Context**: How an image or video is linked across different blocks via block references.

This technical specification provides the roadmap for building a high-fidelity bridge between the unstructured filesystem and the structured data needs of modern artificial intelligence. The ability to resolve any hls:// link or ../assets/ reference to an absolute system path is the final piece of the puzzle for a fully integrated, multimodal knowledge retrieval system.3

#### **Bibliografia**

1. Logseq from an Org-mode Point of View \- of Karl Voit, accesso eseguito il giorno aprile 25, 2026, [https://karl-voit.at/2024/01/28/logseq-from-org-pov/](https://karl-voit.at/2024/01/28/logseq-from-org-pov/)  
2. Just realized the difference between page properties and block properties \- please double check, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/just-realized-the-difference-between-page-properties-and-block-properties-please-double-check/30433](https://discuss.logseq.com/t/just-realized-the-difference-between-page-properties-and-block-properties-please-double-check/30433)  
3. The relative path for files in "assets" folder · logseq logseq ... \- GitHub, accesso eseguito il giorno aprile 25, 2026, [https://github.com/logseq/logseq/discussions/4582](https://github.com/logseq/logseq/discussions/4582)  
4. Relative Paths in file links don't work (incorrect handling of double-dot ..) \- Bug Reports, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/relative-paths-in-file-links-dont-work-incorrect-handling-of-double-dot/8952](https://discuss.logseq.com/t/relative-paths-in-file-links-dont-work-incorrect-handling-of-double-dot/8952)  
5. Support relative path in audio component \- Feature Requests \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/support-relative-path-in-audio-component/5518](https://discuss.logseq.com/t/support-relative-path-in-audio-component/5518)  
6. Understanding the proper way to handle attachements ("assets") \- \#7 by gax, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/understanding-the-proper-way-to-handle-attachements-assets/8910/7](https://discuss.logseq.com/t/understanding-the-proper-way-to-handle-attachements-assets/8910/7)  
7. logseq/.i18n-lint.toml at master \- GitHub, accesso eseguito il giorno aprile 25, 2026, [https://github.com/logseq/logseq/blob/master/.i18n-lint.toml](https://github.com/logseq/logseq/blob/master/.i18n-lint.toml)  
8. How to use Logseq Namespaces, accesso eseguito il giorno aprile 25, 2026, [https://www.logseqmastery.com/blog/logseq-namespaces](https://www.logseqmastery.com/blog/logseq-namespaces)  
9. Proposal: Changing How Namespaces Function in Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/proposal-changing-how-namespaces-function-in-logseq/3727](https://discuss.logseq.com/t/proposal-changing-how-namespaces-function-in-logseq/3727)  
10. Cleaner file names \- Feature Requests \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/cleaner-file-names/11014](https://discuss.logseq.com/t/cleaner-file-names/11014)  
11. Logseq datascript schema · GitHub, accesso eseguito il giorno aprile 25, 2026, [https://gist.github.com/tiensonqin/9a40575827f8f63eec54432443ecb929](https://gist.github.com/tiensonqin/9a40575827f8f63eec54432443ecb929)  
12. Support subdirs for namespace hierarchy \- Page 4 \- Feature Requests \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/support-subdirs-for-namespace-hierarchy/9763?page=4](https://discuss.logseq.com/t/support-subdirs-for-namespace-hierarchy/9763?page=4)  
13. General question about data structures to maximize benefits of datalog db and queries, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/general-question-about-data-structures-to-maximize-benefits-of-datalog-db-and-queries/20063](https://discuss.logseq.com/t/general-question-about-data-structures-to-maximize-benefits-of-datalog-db-and-queries/20063)  
14. Export PDF with Highlights / Save highlights to PDF file \- Feature Requests \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/export-pdf-with-highlights-save-highlights-to-pdf-file/6076](https://discuss.logseq.com/t/export-pdf-with-highlights-save-highlights-to-pdf-file/6076)  
15. PDF annotation in Logseq \- Feature Requests, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/pdf-annotation-in-logseq/1427](https://discuss.logseq.com/t/pdf-annotation-in-logseq/1427)  
16. Inconsistent behavior when using built-in PDF reader & annotator \- General \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/inconsistent-behavior-when-using-built-in-pdf-reader-annotator/22305](https://discuss.logseq.com/t/inconsistent-behavior-when-using-built-in-pdf-reader-annotator/22305)  
17. Feature Request: PDF annotations link jumps back to corresponding location in the PDF file, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/feature-request-pdf-annotations-link-jumps-back-to-corresponding-location-in-the-pdf-file/4518](https://discuss.logseq.com/t/feature-request-pdf-annotations-link-jumps-back-to-corresponding-location-in-the-pdf-file/4518)  
18. HTTP server in cljs.browser.repl doesn't serve files with extensions other than specified in ext-\>mime-type \- Clojure Q\&A, accesso eseguito il giorno aprile 25, 2026, [https://ask.clojure.org/index.php/5893/server-browser-doesnt-serve-files-extensions-other-specified](https://ask.clojure.org/index.php/5893/server-browser-doesnt-serve-files-extensions-other-specified)  
19. logseq/src/main/frontend/components/block.cljs at master \- GitHub, accesso eseguito il giorno aprile 25, 2026, [https://github.com/logseq/logseq/blob/master/src/main/frontend/components/block.cljs](https://github.com/logseq/logseq/blob/master/src/main/frontend/components/block.cljs)  
20. logseq/src/main/frontend/modules/shortcut/config.cljs at master \- GitHub, accesso eseguito il giorno aprile 25, 2026, [https://github.com/logseq/logseq/blob/master/src/main/frontend/modules/shortcut/config.cljs](https://github.com/logseq/logseq/blob/master/src/main/frontend/modules/shortcut/config.cljs)  
21. Macros to improve assets management \- Look what I built \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/macros-to-improve-assets-management/13606](https://discuss.logseq.com/t/macros-to-improve-assets-management/13606)  
22. Logseq doesn't seem to support Markdown Reference Links\!? \- Questions & Help, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/logseq-doesnt-seem-to-support-markdown-reference-links/19245](https://discuss.logseq.com/t/logseq-doesnt-seem-to-support-markdown-reference-links/19245)  
23. Creating Link Aliases in Logseq \- by Preslav Rachev \- Medium, accesso eseguito il giorno aprile 25, 2026, [https://medium.com/@p5v/creating-link-aliases-in-logseq-fe321d38fd7b](https://medium.com/@p5v/creating-link-aliases-in-logseq-fe321d38fd7b)  
24. Markdown vs Orgmode \- Which format should one choose? : r/logseq \- Reddit, accesso eseguito il giorno aprile 25, 2026, [https://www.reddit.com/r/logseq/comments/1by05ql/markdown\_vs\_orgmode\_which\_format\_should\_one\_choose/](https://www.reddit.com/r/logseq/comments/1by05ql/markdown_vs_orgmode_which_format_should_one_choose/)  
25. 0.8.18 · Milestone \#12 · logseq/logseq \- GitHub, accesso eseguito il giorno aprile 25, 2026, [https://github.com/logseq/logseq/milestone/12?closed=1](https://github.com/logseq/logseq/milestone/12?closed=1)  
26. Creating Link Aliases in Logseq \- Preslav Rachev, accesso eseguito il giorno aprile 25, 2026, [https://preslav.me/2022/04/10/create-link-aliases-in-logseq/](https://preslav.me/2022/04/10/create-link-aliases-in-logseq/)  
27. Support subdirs for namespace hierarchy \- Feature Requests \- Logseq forum, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/support-subdirs-for-namespace-hierarchy/9763](https://discuss.logseq.com/t/support-subdirs-for-namespace-hierarchy/9763)