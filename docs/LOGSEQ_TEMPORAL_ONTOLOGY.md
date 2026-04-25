# **LOGSEQ\_TEMPORAL\_ONTOLOGY.md**

## **The Architecture of Temporal Representation in the Logseq Graph**

The foundational architecture of Logseq is predicated on the concept of a temporal graph where time is not merely a metadata attribute but a first-class citizen represented through specialized Page entities. In this paradigm, every journal entry is a node in a Datascript database, uniquely identified by a combination of its human-readable title and its internal integer representation.1 The system's reliance on ClojureScript and the DataScript library necessitates a highly structured approach to temporal data, leveraging the power of Datalog for efficient querying of chronological relationships.2 For a high-fidelity parser like LOGOS to successfully reconstruct a user’s life timeline, it must master the transition between the volatile Markdown representation of dates and the immutable internal state stored in the database.

Logseq operates as a block-oriented tool where the smallest unit of information, the block, inherits temporal context from its parent page.4 When a block resides on a journal page, it is implicitly associated with a specific date. This association is formalized in the database schema through the :block/journal-day attribute, which stores dates as YYYYMMDD integers.1 This integer-based storage is a critical design choice, as it allows Datalog queries to perform range comparisons (greater than, less than) using simple integer arithmetic rather than complex string parsing or heavy date-object instantiation.5 The efficacy of this system is evident in advanced queries where relative inputs like :today or :-7d are dynamically resolved into these integer formats to filter the graph.7

The challenge for the LOGOS parser lies in the fact that while the database is rigid, the Markdown files are highly localized and customizable. Users can define their preferred date formats in the config.edn file via keys such as :journal/page-title-format and :journal/file-name-format.10 This customization creates a layer of abstraction between the physical storage on disk and the logical entity in the graph. A date that appears as "Apr 25th, 2024" in the UI might be stored as 2024\_04\_25.md on the file system, but it must always resolve to the integer 20240425 within the :block/journal-day attribute.1

## **Official Date Format Specifications and Token Lexicon**

Logseq utilizes the cljs-time library, which is a ClojureScript wrapper for Joda-Time, to handle all date formatting and parsing operations.13 This provides a robust set of tokens that allow users to construct nearly any date representation. The parser must recognize these tokens to interpret the user’s config.edn settings and correctly identify date links within the Markdown content.

### **Mapping Table for Recognized Date Format Tokens**

The following table details the primary tokens supported by the Logseq core engine for defining journal page titles and file names. These tokens are case-sensitive and their behavior varies based on the number of repetitions.

| Token | Meaning | Presentation | Examples |
| :---- | :---- | :---- | :---- |
| y | Year | Number | 1996; 96 (if yy) |
| M | Month of year | Month | July; Jul; 07 |
| d | Day of month | Number | 10 |
| do | Day of month with ordinal | Text/Number | 25th, 1st, 2nd |
| E | Day of week | Text | Tuesday; Tue |
| a | Halfday of day | Text | PM |
| H | Hour of day (0-23) | Number | 0 |
| m | Minute of hour | Number | 30 |
| s | Second of minute | Number | 55 |
| S | Fraction of second | Number | 978 |
| z | Timezone | Text | Pacific Standard Time |
| Z | Timezone offset | Text | \-0800 |

The count of pattern letters determines the specific format used.13 For example, if the number of E characters is 4 or more, the full form of the day (e.g., "Wednesday") is used; otherwise, an abbreviated form (e.g., "Wed") is preferred.13 For months, 3 or more M characters trigger a textual representation, while fewer result in a numeric value.13 A unique addition in Logseq is the do token, which is not standard in all Joda-Time implementations but is frequently used in Logseq to provide ordinal suffixes like "st", "nd", "rd", and "th".8

### **Configuration and Localization Dynamics**

The localization of date formats is governed by two primary keys in the logseq/config.edn file. The :journal/page-title-format determines how the date appears at the top of a journal page and in internal links, while :journal/file-name-format dictates the string used to generate the .md file in the /journals directory.10 If a user sets :journal/page-title-format "EEEE, MMM do, yyyy", the system will render the date as "Friday, Aug 9th, 2024".13

A critical insight for the LOGOS parser is that while the display format can change, the internal resolution must remain consistent. Changing these formats in an existing graph is not retroactive; it only affects new journal pages.12 This often leads to a "fragmented graph" where older journal files follow one naming convention and newer ones follow another, potentially breaking the chronological link if the parser does not account for historical configuration states.11 The parser must therefore be capable of multi-pass format matching, attempting to resolve a date string against both current and common default formats.

## **Journal Page Linking and Resolution Logic**

Logseq employs a sophisticated resolution algorithm to map a string found in a Markdown file to a specific Journal Page entity. This process is complex because a date can be referenced as a standard page link \[\[2024-04-25\]\], as a localized string in a non-journal page, or as part of a property like created:: \[\[2024-04-25\]\].16

### **Filename vs. Display Name Mapping**

The physical filename is the source of truth for the journal's date during the initial indexing phase. By default, Logseq expects journal files to be named yyyy\_MM\_dd.md.10 When the graph is indexed, the system scans the /journals directory, parses the filenames, and creates page entities with the corresponding :block/journal-day integer.1

Once indexed, the "Display Name" (or Page Title) is generated based on the :journal/page-title-format. If a user writes \[\[Apr 25th, 2024\]\], the engine does not search for a file with that name; instead, it searches the Datascript database for a page where the :block/original-name or :block/name matches the string, or it attempts to parse the string into a date to find a matching :block/journal-day.2

### **Dynamic Linking and the Resolver Algorithm**

If a user references a date in a non-journal page, the engine must resolve that reference to the correct Journal Entity. This allows for features like "Linked References" where all mentions of a specific date across the entire graph are aggregated at the bottom of that day’s journal page.17 The resolution must be bi-directional: from string to entity and from entity to localized display string.

The following pseudocode represents the logic required for a Journal Name Resolver within the LOGOS parser.

Python

def resolve\_journal\_page(input\_string, config\_formats, graph\_database):  
    """  
    Resolves a string reference to a Journal Page ID and its ISO-8601 representation.  
    """  
    \# Step 1: Normalize input by removing brackets if present  
    clean\_string \= input\_string.strip("")  
      
    \# Step 2: Attempt to parse using the user's preferred formats from config.edn  
    for fmt in config\_formats:  
        try:  
            date\_obj \= parse\_date(clean\_string, fmt)  
            return map\_to\_entity(date\_obj, graph\_database)  
        except ParsingError:  
            continue  
              
    \# Step 3: Attempt parsing with common Logseq defaults  
    defaults \= \["yyyy-MM-dd", "MMM do, yyyy", "yyyy\_MM\_dd", "E, dd-MM-yyyy"\]  
    for fmt in defaults:  
        try:  
            date\_obj \= parse\_date(clean\_string, fmt)  
            return map\_to\_entity(date\_obj, graph\_database)  
        except ParsingError:  
            continue  
              
    \# Step 4: If parsing fails, treat as a standard page link (non-journal)  
    return resolve\_standard\_page(clean\_string, graph\_database)

def map\_to\_entity(date\_obj, db):  
    \# Convert date to the YYYYMMDD integer used for indexing  
    journal\_day \= int(date\_obj.strftime("%Y%m%d"))  
      
    \# Query the database for a page with this journal-day  
    entity \= db.query(f"\[:find?p :where \[?p :block/journal-day {journal\_day}\]\]")  
      
    if entity:  
        return {  
            "entity\_id": entity,  
            "iso\_8601": date\_obj.isoformat(),  
            "journal\_day": journal\_day  
        }  
    else:  
        \# If no entity exists, return the temporal metadata for potential page creation  
        return {  
            "entity\_id": None,  
            "iso\_8601": date\_obj.isoformat(),  
            "journal\_day": journal\_day  
        }

This resolver highlights a key architectural necessity: the parser must maintain a "temporal context" that includes not only the current system time but also the user's specific config.edn environment. Without this context, a string like "01-02-2024" is ambiguous, as it could represent January 2nd or February 1st depending on the user's locale.13

## **Scheduled, Deadlines, and Metadata Markers**

Temporal metadata in Logseq is primarily managed through three markers: SCHEDULED:, DEADLINE:, and CLOCK:.20 These markers are derived from Org-mode syntax and serve as the backbone for task management and time-tracking features.

### **Metadata vs. Content Distinctions**

It is crucial to distinguish between system-level timestamps and user-defined temporal markers. Every block in Logseq has a :block/created-at and :block/updated-at attribute, which are Unix Epoch timestamps in milliseconds.1 These are generated by the system and are generally not visible in the Markdown content.

Conversely, SCHEDULED: and DEADLINE: markers are part of the block's content string but are extracted by the parser into specialized attributes.8 When the parser encounters these markers, it removes them from the primary :block/content and populates the :block/scheduled or :block/deadline attributes in the database with the date represented as a YYYYMMDD integer.21

### **Regex Patterns for Marker Detection**

Logseq's detection of these markers relies on specific regex patterns that look for the marker keyword followed by a date string enclosed in angle brackets \<...\>.

| Marker | Regex Pattern (Conceptual) | Example Content |
| :---- | :---- | :---- |
| SCHEDULED | SCHEDULED:\\s\*\<(\\d{4}-\\d{2}-\\d{2}\[^\>\]\*)\> | SCHEDULED: \<2024-04-25 Thu\> |
| DEADLINE | DEADLINE:\\s\*\<(\\d{4}-\\d{2}-\\d{2}\[^\>\]\*)\> | DEADLINE: \<2024-05-01 Wed 17:00\> |
| CLOCK | CLOCK:\\s\*\\\[(\\d{4}-\\d{2}-\\d{2}\[^\\\]\]\*)\\\]\\s\*--\\s\*\\\[(\\d{4}-\\d{2}-\\d{2}\[^\\\]\]\*)\\\]\\s\*=\>\\s\*(\\d+:\\d+:\\d+) | CLOCK:-- \=\> 01:30:00 |

The CLOCK: marker is typically found within a :LOGBOOK: drawer, which is a specialized section of a block used to hide time-tracking data from the main view.22 The regex for clocks must account for the start timestamp, end timestamp, and the calculated duration.22

### **Timestamp Precision and Timezone Handling**

Timestamps in Logseq markers can include a time component (e.g., \<2024-04-25 Thu 17:00\>). When time is present, the core engine often treats it as a local time without an explicit timezone offset, inheriting the system's local time.14 However, for "Sovereign AI" purposes, this lack of timezone data is a liability. The LOGOS parser must normalize these to UTC by either assuming the graph's primary locale or using system-level offsets.

For CLOCK entries, the precision is typically to the minute, and the duration is calculated based on the difference between the two timestamps.22 In the database, the duration is often stored as the total number of minutes to facilitate aggregation in time-tracking reports.22

## **Recurrence and Repeater Logic**

One of the most complex aspects of Logseq’s temporal engine is the implementation of task repeaters. Logseq supports three types of repeaters, denoted by the symbols \+, \++, and .+.29 These repeaters follow the Org-mode convention but have specific behavioral nuances in the Logseq implementation.

### **Repeater Varieties and Logic**

The repeater symbol follows the date within the angle brackets, such as \<2024-04-25 Thu \+1d\>.

| Repeater | Name | logic | Expected Behavior |
| :---- | :---- | :---- | :---- |
| \+ | Simple Plus | Interval from last scheduled date | Repeats every X period. If completed late, it stays on the original interval cycle even if the new date is in the past. |
| \++ | Double Plus | Skip to future interval | Repeats every X period, but always results in a future date. It maintains the original day of the week or alignment. |
| .+ | Dotted Plus | Interval from completion date | The next occurrence is calculated by adding the interval to the current date (today). |

Technical investigations into the core source code (src/main/frontend/handler/repeated.cljs) reveal that the .+ repeater is often the most desired by users for habits like "water plants every 3 days," where the next event should be relative to the last time the action was performed.30 However, community feedback indicates that implementation bugs sometimes cause .+ to behave like \++.29 For an AI to accurately project a user's future schedule, it must identify these repeater markers and calculate the next "logical" occurrence based on the history of "DONE" state transitions recorded in the :LOGBOOK:.29

### **Repeater Calculation in Pseudocode**

The following logic illustrates how the parser should calculate the next date for a recurring task when it is marked as done.

Python

def calculate\_next\_repeat(last\_scheduled, completion\_date, interval\_str):  
    \# interval\_str example: "+1d", "++1w", ".+1m"  
    kind \= identify\_kind(interval\_str) \# Simple, Double, Dotted  
    delta \= parse\_interval(interval\_str) \# e.g., Timedelta(days=1)  
      
    if kind \== "SimplePlus":  
        return last\_scheduled \+ delta  
    elif kind \== "DoublePlus":  
        next\_date \= last\_scheduled \+ delta  
        while next\_date \<= completion\_date:  
            next\_date \+= delta  
        return next\_date  
    elif kind \== "DottedPlus":  
        return completion\_date \+ delta

The Sovereign AI must look at the :logbook history to see if the user consistently completes tasks late, which might suggest a need to adjust the interval or identify patterns of procrastination.27

## **Querying the Timeline and Datalog Temporal Predicates**

The ultimate utility of the temporal ontology is realized through Datalog queries. Logseq’s internal engine uses a series of predicates and attributes to index and retrieve time-based data. For the LOGOS parser to mimic this, it must understand how time is transformed from the graph into the database.

### **Key Temporal Attributes in the Schema**

The DataScript schema contains several attributes that are essential for chronological reconstruction 1:

* :block/journal-day: The date of the journal page the block resides on (Integer: YYYYMMDD).5  
* :block/journal?: A boolean flag indicating if the page is a journal.6  
* :block/scheduled: The scheduled date of a task (Integer: YYYYMMDD).21  
* :block/deadline: The deadline of a task (Integer: YYYYMMDD).21  
* :block/created-at: System timestamp of block creation (Epoch ms).1  
* :block/updated-at: System timestamp of the last modification (Epoch ms).33

### **Executing Range Queries**

Range queries are the most frequent temporal operations. A query to find all blocks from the "last week" typically looks like this in Datalog:

Clojure

\[:find (pull?b \[\*\])  
 :in $?start?today  
 :where  
 \[?b :block/page?p\]  
 \[?p :block/journal-day?d\]  
 \[(\>=?d?start)\]  
 \[(\<=?d?today)\]\]

In this context, :inputs like :-7d and :today are provided to the query engine.7 The engine resolves :-7d by taking the current system date and subtracting 7 days, then formatting the result as a YYYYMMDD integer.8 This demonstrates why the parser must maintain a real-time clock to resolve relative references during the AI Inference phase.

One significant insight into Logseq’s temporal querying is the "Journal Day Inheritance." If a block does not have its own :block/journal-day, it is often queried by looking up the :block/journal-day of its parent page.5 This recursive lookup is a core feature of Logseq's Datalog dialect and must be supported by any external parser aiming for high fidelity.22

## **Normalization for Sovereign AI: From Local to ISO-8601**

The primary objective of the LOGOS parser is to create a "Sovereign AI" capable of reconstructing a user's life timeline. This requires a rigorous normalization process where every temporal reference, regardless of its localized format or its position in the graph, is converted into a standard ISO-8601 string or a Unix Epoch timestamp.

### **The Normalization Pipeline**

The parser should implement a multi-stage normalization pipeline:

1. **Extraction**: Use the regex patterns identified for links, markers, and clock entries to pull raw strings from the Markdown content.16  
2. **Contextualization**: Identify the parent page’s date. If the block is on a journal page, its base date is the :block/journal-day of that page.1  
3. **Resolution**: Apply the Resolver Algorithm using the user's config.edn to turn localized strings into YYYYMMDD integers.10  
4. **Enrichment**: For tasks with times (e.g., 17:00), combine the date from the marker with the time to create a full ISO-8601 timestamp (e.g., 2024-04-25T17:00:00).23  
5. **Reconstruction**: Use the :logbook data to track the actual completion times, providing a ground-truth timeline of when actions were performed versus when they were scheduled.22

### **Chronicling Personal Focus Areas**

By normalizing all references to ISO-8601, the AI can perform longitudinal analysis. For example, to answer "What were my focus areas last October?", the AI does not just search for the word "October." Instead, it:

* Identifies the date range for October of the target year.  
* Converts this range to YYYYMMDD integers (e.g., 20231001 to 20231031).  
* Queries the graph for all blocks where :block/journal-day falls within this range.  
* Analyzes the content of those blocks and their linked pages (tags) to identify themes.

This approach transforms Logseq from a collection of text files into a structured database of human experience. The Sovereign AI thus gains the ability to "remember" with chronological precision, providing the user with an ordered, searchable, and insightful history of their digital life. The rigor of the temporal ontology is what enables this transition from a mere note-taking application to a true personal knowledge graph.

## **Comprehensive Analysis of Format Variations and mldoc Interactions**

The Logseq mldoc parser is the gatekeeper of temporal information within the graph. To ensure high-fidelity parsing for LOGOS, one must understand how mldoc handles the interplay between standard Markdown and the specific syntax required for Logseq's temporal features. Date format variations are not merely aesthetic; they represent different semantic intents within the user's workflow.11

In the context of mldoc, the detection of a "Date Link" is distinct from a standard page link. While a standard link might look like \[\[Project Logos\]\], a date link is recognized as a specific chronological entity. This distinction is vital because the core engine treats the latter as a trigger for journal-specific functionalities, such as the calendar view and temporal range querying.5 The detection logic within mldoc must be flexible enough to handle the wide array of tokens provided by the cljs-time library.13

| Feature | Description | mldoc/Core Interaction |
| :---- | :---- | :---- |
| **Token-Based Parsing** | Uses Joda-Time tokens (e.g., MMM do, yyyy) | Converts UI strings into internal date objects for the DB. |
| **Ordinal Handling** | Supports non-standard do suffix (1st, 2nd, etc.) | Requires custom regex logic to strip suffixes before conversion. |
| **Ambiguity Resolution** | Differentiates between DD/MM/YYYY and MM/DD/YYYY | Relies strictly on config.edn to determine the correct order. |
| **Multi-Format Support** | Permits multiple formats within a single graph | Re-indexing operations attempt to normalize all legacy dates. |

Localization further complicates this process. When the config.edn file is modified, the mldoc parser must be instructed on how to handle legacy data that may follow a previous format. Failure to do so results in "ghost pages" or broken links, where a date reference in a block no longer resolves to the intended journal page.11 The LOGOS parser must mimic this behavior by maintaining a registry of all date formats used throughout the history of the graph, ensuring that no temporal reference is lost during the reconstruction of the user's timeline.

## **Filename to Page Name Mapping and Indexing Strategies**

The bridge between the filesystem and the database is established through a strict indexing strategy. In Logseq, the physical filename of a journal entry acts as the initial metadata source. The default format, yyyy\_MM\_dd.md, is a deliberate choice intended to ensure that files are sorted chronologically by default on most operating systems.10 However, as users transition from other tools like Obsidian, they often bring different naming conventions (e.g., YYYY-MM-DD.md or MMM do, YYYY.md).11

The indexing engine handles these variations by attempting to parse the filename into a standard YYYYMMDD integer during the initial graph scan. This integer then populates the :block/journal-day and :page/journal-day attributes in the Datascript database.1 Once this mapping is established, the filename itself becomes secondary to the internal integer. The "Page Name" displayed in the UI is then dynamically generated using the :journal/page-title-format setting.11

| Internal Attribute | Data Type | Purpose | Example Value |
| :---- | :---- | :---- | :---- |
| :block/journal-day | Integer | Primary key for temporal indexing and sorting. | 20240425 |
| :block/original-name | String | The original title of the page as written on disk. | Apr 25th, 2024 |
| :block/name | String | Lowercase version of the name for fast lookups. | apr 25th, 2024 |
| :page/journal? | Boolean | Identifies if a page should be treated as a journal. | true |

The Dynamic Linking mechanism ensures that any mention of a date—whether as a bracketed link like \[\[2024-04-25\]\] or as a property value—is resolved to the correct Journal Entity. This resolution is not static; it is performed every time a block is rendered or a query is executed. For the Sovereign AI to be effective, it must understand this layer of abstraction. If a user writes a date in a non-journal page, the AI must be able to "hop" from that string to the corresponding journal entry to gather more context about what else occurred on that day.17

## **Deep Dive into Scheduled, Deadlines, and CLOCK Metadata**

The temporal metadata markers—SCHEDULED:, DEADLINE:, and CLOCK:—are the primary drivers of Logseq's utility as a task management system. Unlike journal page titles, which are high-level metadata, these markers are embedded directly within blocks and have a direct impact on the task's state and visibility within the system.20

A critical distinction must be made between the :block/created-at system timestamp and the user-defined markers. The former is a high-precision Unix Epoch timestamp (recorded in milliseconds) that tracks the exact moment a block was committed to the graph.6 The latter are "intentional" timestamps, representing when a task is meant to be performed or its final deadline.

| Marker Type | Precision | Timezone Handling | DB Representation |
| :---- | :---- | :---- | :---- |
| **System (created-at)** | Milliseconds | UTC (Normalized) | 1675479249000 |
| **SCHEDULED** | Date (optional time) | Local (No Offset) | 20240425 |
| **DEADLINE** | Date (optional time) | Local (No Offset) | 20240501 |
| **CLOCK** | Minutes | Local (Calculated) | 90 (minutes) |

For the \`\` syntax, the time precision is generally limited to minutes. Logseq lacks a formal mechanism for timezone handling within these markers, which can create discrepancies for users traveling across timezones. The LOGOS parser must address this by injecting timezone awareness based on the system's local settings at the time of parsing. This ensures that the Sovereign AI can correctly sequence events for a user who might be working across multiple geographic locations.

Furthermore, the CLOCK: marker's placement within the :LOGBOOK: drawer is essential for maintaining the readability of the Markdown file.22 These drawers act as a "hidden" metadata store, protecting the main content of the block from being cluttered by repetitive time-tracking entries. The LOGOS parser must be capable of identifying these drawers and extracting the CLOCK: data to build an accurate "Time Spent" report, which is a key component of understanding a user's focus areas over time.22

## **Technical Investigation of Recurrence and Repeater Logic**

Task repeaters represent the most complex logic within the Logseq temporal engine. While the concept of repeating tasks is common in productivity tools, Logseq's implementation provides a high degree of flexibility through the \+, \++, and .+ symbols.29 However, this flexibility also introduces potential for confusion and implementation bugs.

The \+ (Simple Plus) repeater is the most straightforward. It simply increments the scheduled date by the specified interval (e.g., \+1d for daily). If a user completes a task late, the next instance will still be scheduled relative to the original date, potentially creating a "backlog" of past-due tasks.30 This is useful for tasks that must be performed a specific number of times, regardless of when they are completed.

The \++ (Double Plus) repeater is designed to always push the next task into the future while maintaining a specific cycle (e.g., repeating every Monday). This ensures that a task completed on a Friday will skip ahead to the next Monday, rather than being scheduled for the previous Monday.29

The .+ (Dotted Plus) repeater is the most dynamic, as it calculates the next scheduled date relative to the "today" of completion.29 This is ideal for habits like "water plants every 3 days," where the interval should restart the moment the task is marked as done.

| Repeater | Syntax | Core Logic (Conceptual) | Use Case |
| :---- | :---- | :---- | :---- |
| **Simple** | \+1w | next\_date \= last\_scheduled \+ 7 days | Weekly meetings that occur on a fixed cycle. |
| **Double** | \++1w | next\_date \= last\_scheduled \+ (n \* 7 days) \> today | Fixed-day tasks where past instances are skipped. |
| **Dotted** | .+1w | next\_date \= today \+ 7 days | Habits or maintenance where interval matters. |

Analysis of community reports 29 indicates that the .+ repeater is often cited for behaving unexpectedly, sometimes skipping intervals or defaulting to the \++ logic. For the LOGOS parser, this means that simple keyword detection is insufficient. The parser must analyze the :LOGBOOK: history to determine the *actual* completion dates and then apply the intended repeater logic to verify the next scheduled date. This historical analysis is the only way to ensure the Sovereign AI can accurately project a user's future availability and habits.

## **Datalog Temporal Queries and Timeline Indexing**

The power of Logseq's temporal system is ultimately unlocked through Datalog queries. By transforming dates into integers (YYYYMMDD), Logseq allows for highly performant range queries that can span the entire graph.5 This is essential for features like the "journals overview" and advanced queries for overdue tasks.

The :block/journal-day attribute is the primary index for these queries. When a user asks for "all blocks from last week," the system does not need to parse every Markdown file. Instead, it performs a simple range check on the integer index.5 This approach is significantly faster than string-based searching and allows for complex combinations of temporal and non-temporal filters.

| Datalog Attribute | Purpose | Query Example |
| :---- | :---- | :---- |
| :block/journal-day | Chronological grouping | \[?p :block/journal-day 20240425\] |
| :block/scheduled | Task management | \[?b :block/scheduled?d\]\[(\<?d?today)\] |
| :block/deadline | Urgent priorities | \[?b :block/deadline?d\]\[(=?d?today)\] |
| :block/created-at | Audit/System history | \[?b :block/created-at?t\]\[(\>?t 1675479249000)\] |

One of the most powerful features of Logseq's query engine is the use of relative inputs like :today, :+7d, and :-30d.7 These inputs are resolved by the frontend before being passed to the Datalog engine, ensuring that queries are always relative to the current moment. For the Sovereign AI, this means that the LOGOS parser must be able to calculate these relative ranges in real-time, allowing the AI to answer questions like "What was I working on a month ago?" by dynamically constructing the appropriate Datalog query.

Furthermore, the "Inheritance Logic" in queries—where a block inherits the date of its parent page—is critical for organizing notes that are not explicitly dated.5 This allows the AI to reconstruct the context of a conversation or a project by looking at the journal page where it was recorded, even if the individual blocks lack specific timestamps.

## **Conclusion: The Road to Temporal Sovereignty**

The technical investigation into Logseq's temporal ontology reveals a system that is deeply rooted in the principles of graph-based knowledge management. By treating time as a first-class citizen and using integer-based indexing, Logseq provides a robust framework for chronological organization. However, the localized and customizable nature of the Markdown storage creates significant challenges for high-fidelity parsing.

The LOGOS parser must address these challenges by mastering the mldoc parser's date detection logic, the sophisticated Journal Name Resolver algorithm, and the complex rules governing task repeaters and metadata markers. By normalizing every temporal reference into a standard ISO-8601 string or Unix Epoch timestamp, LOGOS provides the essential foundation for a Sovereign AI. This AI can then move beyond mere text searching to achieve a true "World Model" of the user's data, answering chronological questions with precision and reconstructing a perfectly ordered timeline of the user's life. The mastery of this temporal ontology is not just a technical requirement; it is the key to unlocking the full potential of personal knowledge graphs for human-AI collaboration.

#### **Bibliografia**

1. General question about data structures to maximize benefits of datalog db and queries, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/general-question-about-data-structures-to-maximize-benefits-of-datalog-db-and-queries/20063](https://discuss.logseq.com/t/general-question-about-data-structures-to-maximize-benefits-of-datalog-db-and-queries/20063)  
2. How advanced queries work \- step-by-step explainer \- Queries \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/how-advanced-queries-work-step-by-step-explainer/30544](https://discuss.logseq.com/t/how-advanced-queries-work-step-by-step-explainer/30544)  
3. logseq/CODEBASE\_OVERVIEW.md at master \- GitHub, accesso eseguito il giorno aprile 25, 2026, [https://github.com/logseq/logseq/blob/master/CODEBASE\_OVERVIEW.md](https://github.com/logseq/logseq/blob/master/CODEBASE_OVERVIEW.md)  
4. Logseq from an Org-mode Point of View \- of Karl Voit, accesso eseguito il giorno aprile 25, 2026, [https://karl-voit.at/2024/01/28/logseq-from-org-pov/](https://karl-voit.at/2024/01/28/logseq-from-org-pov/)  
5. Logseq journal: On this day, accesso eseguito il giorno aprile 25, 2026, [https://manhtai.github.io/posts/logseq-journal-on-this-day/](https://manhtai.github.io/posts/logseq-journal-on-this-day/)  
6. Query to find blocks created today \- Questions & Help \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/query-to-find-blocks-created-today/15812](https://discuss.logseq.com/t/query-to-find-blocks-created-today/15812)  
7. How to query block property with a date? \- Questions & Help \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/how-to-query-block-property-with-a-date/11825](https://discuss.logseq.com/t/how-to-query-block-property-with-a-date/11825)  
8. How to show task's status, priority & deadlines in Table view mode \- Look what I built, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/how-to-show-tasks-status-priority-deadlines-in-table-view-mode/26924](https://discuss.logseq.com/t/how-to-show-tasks-status-priority-deadlines-in-table-view-mode/26924)  
9. A logseq plugin which counts how many days left until the deadline. \- GitHub, accesso eseguito il giorno aprile 25, 2026, [https://github.com/xxchan/logseq-deadline-countdown](https://github.com/xxchan/logseq-deadline-countdown)  
10. How to Change Logseq Journal File Name to YYYY-DD-MM Format \- Nesin.io, accesso eseguito il giorno aprile 25, 2026, [https://nesin.io/blog/change-logseq-journal-file-name-format](https://nesin.io/blog/change-logseq-journal-file-name-format)  
11. Journal file name format \- Questions & Help \- Logseq forum, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/journal-file-name-format/1590](https://discuss.logseq.com/t/journal-file-name-format/1590)  
12. Going back in time through Calendar creates and opens a page called Journal instead \#9923 \- GitHub, accesso eseguito il giorno aprile 25, 2026, [https://github.com/logseq/logseq/issues/9923](https://github.com/logseq/logseq/issues/9923)  
13. Looking for Customizing Date Formats in Logseq\! \- Customization ..., accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/looking-for-customizing-date-formats-in-logseq/28352](https://discuss.logseq.com/t/looking-for-customizing-date-formats-in-logseq/28352)  
14. cljs-time — com.andrewmcveigh/cljs-time 0.5.2 \- cljdoc, accesso eseguito il giorno aprile 25, 2026, [https://cljdoc.org/d/com.andrewmcveigh/cljs-time/0.5.2/api/cljs-time](https://cljdoc.org/d/com.andrewmcveigh/cljs-time/0.5.2/api/cljs-time)  
15. clj-time.format documentation, accesso eseguito il giorno aprile 25, 2026, [https://clj-time.github.io/clj-time/doc/clj-time.format.html](https://clj-time.github.io/clj-time/doc/clj-time.format.html)  
16. Modify date format in all existing docs \- Questions & Help \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/modify-date-format-in-all-existing-docs/30686](https://discuss.logseq.com/t/modify-date-format-in-all-existing-docs/30686)  
17. Proper way to specify block creation date? : r/logseq \- Reddit, accesso eseguito il giorno aprile 25, 2026, [https://www.reddit.com/r/logseq/comments/1k4suhe/proper\_way\_to\_specify\_block\_creation\_date/](https://www.reddit.com/r/logseq/comments/1k4suhe/proper_way_to_specify_block_creation_date/)  
18. Can I use a custom "date"/title format for journals and their titles? \- Questions & Help, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/can-i-use-a-custom-date-title-format-for-journals-and-their-titles/25983](https://discuss.logseq.com/t/can-i-use-a-custom-date-title-format-for-journals-and-their-titles/25983)  
19. Formatting date formats : r/logseq \- Reddit, accesso eseguito il giorno aprile 25, 2026, [https://www.reddit.com/r/logseq/comments/19cle0c/formatting\_date\_formats/](https://www.reddit.com/r/logseq/comments/19cle0c/formatting_date_formats/)  
20. What's the best practice for markers on recurring tasks? \- Questions & Help \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/whats-the-best-practice-for-markers-on-recurring-tasks/27455](https://discuss.logseq.com/t/whats-the-best-practice-for-markers-on-recurring-tasks/27455)  
21. Sorting by minimum of scheduled and deadline? \- Queries \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/sorting-by-minimum-of-scheduled-and-deadline/23613](https://discuss.logseq.com/t/sorting-by-minimum-of-scheduled-and-deadline/23613)  
22. How can I create a time-spent-on-tasks report for a tree of tasks or single page of tasks?, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/how-can-i-create-a-time-spent-on-tasks-report-for-a-tree-of-tasks-or-single-page-of-tasks/29541](https://discuss.logseq.com/t/how-can-i-create-a-time-spent-on-tasks-report-for-a-tree-of-tasks-or-single-page-of-tasks/29541)  
23. benjypng/logseq-dateutils \- GitHub, accesso eseguito il giorno aprile 25, 2026, [https://github.com/benjypng/logseq-dateutils](https://github.com/benjypng/logseq-dateutils)  
24. How do I get LogSeq page creation date to equal creation date of actual .md file?, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/how-do-i-get-logseq-page-creation-date-to-equal-creation-date-of-actual-md-file/13939](https://discuss.logseq.com/t/how-do-i-get-logseq-page-creation-date-to-equal-creation-date-of-actual-md-file/13939)  
25. How do I get the simplified block content as in regular logseq.table.version 1 of Advanced Queries in custom :view, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/how-do-i-get-the-simplified-block-content-as-in-regular-logseq-table-version-1-of-advanced-queries-in-custom-view/25192](https://discuss.logseq.com/t/how-do-i-get-the-simplified-block-content-as-in-regular-logseq-table-version-1-of-advanced-queries-in-custom-view/25192)  
26. Scheduled tasks on day of journal \- Queries \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/scheduled-tasks-on-day-of-journal/22441](https://discuss.logseq.com/t/scheduled-tasks-on-day-of-journal/22441)  
27. r/logseq \- Reddit, accesso eseguito il giorno aprile 25, 2026, [https://www.reddit.com/r/logseq/](https://www.reddit.com/r/logseq/)  
28. Home Report home for your next assignment Training Practice Complete challenging Kata to earn honor and ranks. Re-train to hone, accesso eseguito il giorno aprile 25, 2026, [https://www.terceiro.com.br/resolucoes-exercicios-codewars.pdf](https://www.terceiro.com.br/resolucoes-exercicios-codewars.pdf)  
29. Repeat tasks don't repeat as documented · Issue \#11260 \- GitHub, accesso eseguito il giorno aprile 25, 2026, [https://github.com/logseq/logseq/issues/11260](https://github.com/logseq/logseq/issues/11260)  
30. habits/repeating tasks scheduling reference date · Issue \#5645 ..., accesso eseguito il giorno aprile 25, 2026, [https://github.com/logseq/logseq/issues/5645](https://github.com/logseq/logseq/issues/5645)  
31. Repeating tasks don't behave as documented \- Bug Reports \- Logseq forum, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/repeating-tasks-dont-behave-as-documented/26631](https://discuss.logseq.com/t/repeating-tasks-dont-behave-as-documented/26631)  
32. Official, comprehensive list of \`config.edn\` options \- Archive \- Logseq, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/official-comprehensive-list-of-config-edn-options/4935](https://discuss.logseq.com/t/official-comprehensive-list-of-config-edn-options/4935)  
33. My GTD and slip box-ish workflow within logseq \- Look what I built, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/my-gtd-and-slip-box-ish-workflow-within-logseq/4626](https://discuss.logseq.com/t/my-gtd-and-slip-box-ish-workflow-within-logseq/4626)  
34. Use journal day instead of :today in advanced queries \- Logseq forum, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/use-journal-day-instead-of-today-in-advanced-queries/28121](https://discuss.logseq.com/t/use-journal-day-instead-of-today-in-advanced-queries/28121)  
35. Advanced queries for Logseq.md \- GitHub Gist, accesso eseguito il giorno aprile 25, 2026, [https://gist.github.com/jumski/ad9d9f952a263af35a06a7c6cfff0d04](https://gist.github.com/jumski/ad9d9f952a263af35a06a7c6cfff0d04)  
36. Sorting by journal-day and hiding the page name in advanced queries, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/sorting-by-journal-day-and-hiding-the-page-name-in-advanced-queries/24543](https://discuss.logseq.com/t/sorting-by-journal-day-and-hiding-the-page-name-in-advanced-queries/24543)  
37. Advanced Query that pulls all reference AND recursive name spaces \- Logseq forum, accesso eseguito il giorno aprile 25, 2026, [https://discuss.logseq.com/t/advanced-query-that-pulls-all-reference-and-recursive-name-spaces/21275](https://discuss.logseq.com/t/advanced-query-that-pulls-all-reference-and-recursive-name-spaces/21275)