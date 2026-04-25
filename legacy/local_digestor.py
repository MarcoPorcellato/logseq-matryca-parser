import asyncio
import json
import os
import re
import shutil
import urllib.request
from datetime import datetime
from typing import Any, Dict, Literal, TypeVar

from pydantic import BaseModel, ValidationError

from smart_router.core.ingestion_engine import IngestionEngine
from smart_router.core.librarian_models import (
    EntityNodeSchema,
    SovereignNotePackage,
)

INBOX_DIR = "raw_sources/inbox"
PROCESSED_DIR = "raw_sources/processed"
DOCS_DIR = "docs"
ARCHIVE_DIR = "docs/archives/logseq"
LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
WORKSPACE_UID = "default"

NodeType = Literal[
    "Map", "Area", "Project", "Resource", "Archive",
    "Victory", "Result", "Alignment", "Improvement", "Observation"
]

async def emit_note_package(
    slug: str,
    content: str,
    ontology_class: NodeType,
    metadata: Dict[str, str],
    indentation_level: int,
) -> None:
    package = SovereignNotePackage(
        slug=slug,
        content=content,
        ontology_class=ontology_class,
        metadata=metadata,
        indentation_level=indentation_level,
    )
    engine = IngestionEngine(WORKSPACE_UID)
    await engine.ingest(package)
    await engine.close()

SCOUT_PROMPT = """
You are the Matryca Zettelkasten Scout.
Map out dense methodological frameworks and specific projects.
"""

SURGEON_PROMPT = """
Sei l'Esoscheletro Cognitivo (Motore ViRiAMO-T) di un utente AuDHD. Il tuo compito è analizzare il testo in input (Logseq Markdown).
Utilizza il Diagnostic Scanner con le seguenti definizioni per l'estrazione:
MAPRA (Gerarchia Strutturale):
- Mappa: Core identity, long-term vision, or V2MOM. The 'Why'.
- Area: A sphere of activity with a standard to be maintained over time. Continuous maintenance. Example: Health, Finances.
- Progetto: A series of tasks linked to a goal, with a specific deadline and end state.
- Risorsa: Topics of ongoing interest. Fluid Zettelkasten knowledge.
- Archivio: Completed or inactive items for cold storage.

ViRiAMO-T (Vettori di Diario Giornaliero):
- Vittoria: Focus on mindset and nervous system resilience. Detect: executive dysfunction bypass, 'done is better than perfect' mindset, successful state transitions (e.g., from hyper-arousal to rest), and invisible resilience in the face of AuDHD paralysis.
- Risultato: Focus on concrete output and cash flow. Strictly distinguish between 'Movement' (planning/organizing) and 'Action' (shipping, invoicing, closing deals). Extract hard metrics, ROI, and completed loops.
- Allineamento: Focus on values vs. actions. Detect cognitive dissonance. Compare declared values with actual time spent (calendar logic). Identify 'Engineer vs. Entrepreneur' role conflicts.
- Miglioramento: Focus on systems, not effort. Identify bottlenecks (sensory overload, decision fatigue, process gaps). Apply Pareto 80/20 to stress vs. profit. Suggest high-leverage systemic interventions.
- Osservazione: Deep pattern recognition. Connect temporal threads (e.g., Tuesday's stress causing Thursday's procrastination). Map energy curves based on timestamps and biological factors (sleep, food).

- Se il testo è strutturale, classificalo nella gerarchia MAPRA.
- Se il testo è un Diario Giornaliero (Daily Note), estrai SPIETATAMENTE i 5 Vettori ViRiAMO (V, R, A, M, O). Non fare 'Bypass Spirituale'. Se c'è troppa astrazione e zero 'Risultati' materiali, segnala l'assenza di Grounding. Restituisci JSON validato secondo lo schema Pydantic.
"""

class ScoutNote(BaseModel):
    filename: str
    original_exact_match: str
    ontology_class: NodeType

class ScoutResponse(BaseModel):
    scouted_notes: list[ScoutNote]

class LogseqASTParser:
    @staticmethod
    def parse_trees(text: str) -> list[str]:
        trees: list[str] = []
        current_tree: list[str] = []
        for line in text.splitlines():
            if line.startswith("- ") or line.startswith("# "):
                if current_tree:
                    trees.append("\n".join(current_tree))
                current_tree = [line]
            else:
                if current_tree:
                    current_tree.append(line)
                elif line.strip():
                    current_tree.append(line)
        if current_tree:
            trees.append("\n".join(current_tree))
        return trees

    @staticmethod
    def chunk_into_buckets(text: str, max_chars: int = 12000) -> list[str]:
        buckets: list[str] = []
        current_bucket: list[str] = []
        current_length = 0
        trees = LogseqASTParser.parse_trees(text)
        for tree in trees:
            tree_len = len(tree)
            if current_length + tree_len > max_chars and current_bucket:
                buckets.append("\n".join(current_bucket))
                current_bucket = [tree]
                current_length = tree_len
            else:
                current_bucket.append(tree)
                current_length += tree_len + 1
        if current_bucket:
            buckets.append("\n".join(current_bucket))
        return [b.strip() for b in buckets if b.strip()]

T = TypeVar("T", bound=BaseModel)

def call_local_llm(
    system_prompt: str, user_content: str, response_model: type[T]
) -> T | None:
    payload: Dict[str, Any] = {
        "model": "local-model",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.0,
        "stop": ["}\n}", "```\n"],
    }
    req = urllib.request.Request(
        LM_STUDIO_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            wiki_content = result["choices"][0]["message"]["content"]
            match = re.search(r"\{.*\}", wiki_content, re.DOTALL)
            if match:
                json_str = match.group(0)
                try:
                    return response_model.model_validate_json(json_str)
                except (json.JSONDecodeError, ValidationError):
                    return None
            else:
                return None
    except Exception:
        return None

def find_matching_line_index(
    match_str: str, lines: list[str]
) -> tuple[int, str | None]:
    stripped = match_str.strip()
    safe_match = re.escape(stripped).replace(r"\ ", r"\s+").replace(r"\t", r"\s+")
    for i, line in enumerate(lines):
        if re.search(safe_match, line):
            return i, "strict"
    core_match = re.sub(r"^[\-\*\+\s]+", "", stripped)
    is_valid_fallback = len(core_match) >= 10
    if is_valid_fallback:
        core_lower = core_match.lower()
        for i, line in enumerate(lines):
            if core_lower in line.lower() and "🕸️" not in line:
                return i, "fuzzy"
    return -1, None

def isolate_exact_subtree(
    global_text: str, match_str: str
) -> tuple[str | None, str | None]:
    lines = global_text.split("\n")
    start_idx, match_type = find_matching_line_index(match_str, lines)
    if start_idx == -1:
        return None, None
    first_line = lines[start_idx]
    base_indent = len(first_line) - len(first_line.lstrip(" \t"))
    subtree_lines = [first_line]
    for line in lines[start_idx + 1 :]:
        if not line.strip():
            subtree_lines.append(line)
            continue
        current_indent = len(line) - len(line.lstrip(" \t"))
        if current_indent <= base_indent:
            break
        subtree_lines.append(line)
    return "\n".join(subtree_lines), match_type

def compute_indent(match_str: str, global_text: str) -> int:
    lines = global_text.split("\n")
    start_idx, _ = find_matching_line_index(match_str, lines)
    if start_idx == -1:
        return -1
    line = lines[start_idx]
    return len(line) - len(line.lstrip(" \t"))

async def main() -> None:
    if not os.path.exists(INBOX_DIR) or not os.listdir(INBOX_DIR):
        return
    for filename in os.listdir(INBOX_DIR):
        if filename.startswith("."):
            continue
        filepath = os.path.join(INBOX_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            global_skeleton = f.read()
        macro_buckets = LogseqASTParser.chunk_into_buckets(
            global_skeleton, max_chars=15000
        )
        all_success = True
        for macro_bucket in macro_buckets:
            scout_result = call_local_llm(
                SCOUT_PROMPT, f"Map this chunk:\n\n{macro_bucket}", ScoutResponse
            )
            if not scout_result:
                all_success = False
                continue
            scouted_notes_with_indent: list[tuple[int, Any]] = []
            for note_map in scout_result.scouted_notes:
                indent = compute_indent(note_map.original_exact_match, global_skeleton)
                scouted_notes_with_indent.append((indent, note_map))
            def get_indent(x: tuple[int, Any]) -> int:
                return x[0]
            scouted_notes_with_indent.sort(key=get_indent, reverse=True)
            for indent, note_map in scouted_notes_with_indent:
                match_str: str = note_map.original_exact_match
                note_filename = os.path.basename(note_map.filename)
                target_tree, match_type = isolate_exact_subtree(
                    global_skeleton, match_str
                )
                if not target_tree:
                    all_success = False
                    continue

                ontology_class = note_map.ontology_class
                
                extracted_base = call_local_llm(
                    SURGEON_PROMPT,
                    f"Transform this isolated tree:\n\n{target_tree}",
                    EntityNodeSchema,
                )
                
                if extracted_base:
                    wiki_content = extracted_base.content
                    if not note_filename.endswith(".md"):
                        note_filename += ".md"
                    try:
                        metadata: Dict[str, str] = {
                            "source_filename": filename,
                            "confidence": str(extracted_base.confidence),
                            "extracted_at": datetime.now().isoformat(),
                        }
                        await emit_note_package(
                            slug=note_filename,
                            content=wiki_content,
                            ontology_class=ontology_class,
                            metadata=metadata,
                            indentation_level=indent,
                        )
                        pattern_str = re.escape(target_tree.strip())
                        pattern_str = (
                            pattern_str.replace(r"\ ", r"\s+")
                            .replace(r"\t", r"\s+")
                            .replace(r"\n", r"\s+")
                        )
                        first_line = target_tree.split("\n")[0]
                        leading_ws = first_line[
                            : len(first_line) - len(first_line.lstrip(" \t"))
                        ]
                        try:
                            global_skeleton = re.sub(
                                pattern_str,
                                lambda _: (
                                    f"{leading_ws}🕸️ [[ESTRATTO: {note_filename}]]"
                                ),
                                global_skeleton,
                                count=1,
                            )
                        except Exception:
                            global_skeleton = global_skeleton.replace(
                                target_tree,
                                f"{leading_ws}🕸️ [[ESTRATTO: {note_filename}]]",
                            )
                    except Exception:
                        all_success = False
                else:
                    all_success = False

        global_skeleton = re.sub(r"\n{3,}", "\n\n", global_skeleton)
        if all_success and macro_buckets:
            compressed_filename = f"Compressed_{filename}"
            if not compressed_filename.endswith(".md"):
                compressed_filename += ".md"
            os.makedirs(ARCHIVE_DIR, exist_ok=True)
            compressed_path = os.path.join(ARCHIVE_DIR, compressed_filename)
            final_text = global_skeleton.strip()
            try:
                with open(compressed_path, "w", encoding="utf-8") as f:
                    f.write(final_text)
                os.makedirs(PROCESSED_DIR, exist_ok=True)
                shutil.move(filepath, os.path.join(PROCESSED_DIR, filename))
            except Exception:
                all_success = False

if __name__ == "__main__":
    asyncio.run(main())
