---
name: logseq-read
description: "Read and query the user's personal Logseq knowledge base (notes, journals, tasks). The graph path is configured via the LOGSEQ_GRAPH_PATH environment variable or the default placeholder in the script (see below). Always use this skill before answering questions about personal notes, knowledge, projects, or tasks—never hallucinate missing data. Activate it when the user asks about a person, project, or topic in the notes (\"read notes about X\", \"what do I know about Y\", \"who is X\"); asks for tasks (\"what do I need to do\", \"open TODOs\", \"tasks in progress\"); asks for today's or historical journal (\"today's journal\", \"what I did yesterday\"); wants to search notes (\"search notes\", \"where did I write about X\"); wants to list pages or graph. Also use it for questions about work, customers, projects, or personal plans."
---

# Logseq Read

Skill for reading the user's Logseq graph while preserving hierarchy, wikilinks, tags, properties, and task state.

**Graph path:** `/path/to/your/logseq/graph` (or set the `LOGSEQ_GRAPH_PATH` environment variable to the absolute path of your Logseq graph before running the script)
- `pages/` → notes about people, projects, and topics
- `journals/` → daily journals (`YYYY_MM_DD.md`)

---

## Execution

The base path for this skill is shown in the header `Base directory for this skill:` at the top of this document in Claude Desktop. Use that path in the script:

```bash
python "/SKILL_BASE_DIR/scripts/parse_logseq.py" <ARGS>
```

Replace `/SKILL_BASE_DIR` with the base path extracted from the header.

---

## Available commands

| Topic | When to use |
|-----------|--------------|
| `--page "Name"` | Read one page (person, project, topic) |
| `--journal today` | Today's journal |
| `--journal 2026-05-15` | Journal for a specific date (ISO) |
| `--todos` | All open tasks (TODO/DOING/LATER) across all notes |
| `--search "term"` | Full-text search across all notes |
| `--list` | List all available pages and journals |

---

## How to map user requests

- *"read notes about [person/project]"* → `--page "[name]"`
- *"what do I need to do / open tasks / TODO"* → `--todos`
- *"today's journal / what I did today"* → `--journal today`
- *"journal for [spoken date or ISO]"* → `--journal YYYY-MM-DD`
- *"search [term] in notes"* → `--search "[term]"`
- *"which pages do I have / list notes"* → `--list`
- Question about a specific person or project → `--page "[name]"`

If the request is ambiguous, start with `--list` to show available pages, then read the relevant one.

---

## Output structure

The script returns structured markdown containing:
- **Properties** of the page (`title::`, `tags::`, `type::`, `status::`, etc.)
- **Hierarchy** of bullet points preserved (indentation = depth)
- **Tasks** with state: `TODO`, `DOING`, `DONE`, `LATER`
- **Wikilink** as `[[Page Name]]`
- **Scheduled** items and timeline annotations

---

## How to use the output

1. Read notes with the appropriate command
2. Respond to the user question by summarizing relevant information
3. Always include open tasks if they are present and relevant
4. If output includes `[[Wikilink]]` to related pages, offer to read those pages too with `--page`
5. Never invent information not present in the notes—cite it or say it is missing

---

## Automatic setup

The script installs `logseq-matryca-parser` automatically if missing.
If installation fails, install manually with:

```bash
uv pip install logseq-matryca-parser
```
