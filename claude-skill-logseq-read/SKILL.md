---
name: logseq-read
description: "Legge e interroga la knowledge base Logseq personale dell'utente (appunti, note, journal, task). Il percorso del graph si configura con la variabile d'ambiente LOGSEQ_GRAPH_PATH oppure con il placeholder predefinito nello script (vedi sotto). USA sempre questa skill prima di rispondere a domande sulle note personali, la conoscenza, i progetti o i task — non inventare dalla memoria. Attivala quando l'utente chiede di una persona, progetto o argomento nelle note (\"leggi le note su X\", \"cosa so su Y\", \"chi è X\"); chiede cosa ha da fare (\"cosa ho da fare\", \"TODO aperti\", \"task in sospeso\"); chiede il journal di oggi o del passato (\"journal di oggi\", \"cosa ho fatto ieri\"); vuole cercare nelle note (\"cerca nelle note\", \"dove ho scritto di X\"); vuole elencare pagine o graph. Attivala anche per domande su lavoro, clienti, progetti o piani personali."
---

# Logseq Read

Skill per leggere il graph Logseq dell'utente mantenendo gerarchia, wikilink, tag, proprietà e stato dei task.

**Graph path:** `/path/to/your/logseq/graph` (oppure imposta la variabile d'ambiente `LOGSEQ_GRAPH_PATH` sul percorso assoluto del tuo graph Logseq prima di eseguire lo script)
- `pages/` → note su persone, progetti, argomenti
- `journals/` → diari giornalieri (`YYYY_MM_DD.md`)

---

## Esecuzione

Il percorso base di questa skill è indicato nell'intestazione "Base directory for this skill:" all'inizio di questo documento in Claude Desktop. Usa quel percorso per lo script:

```bash
python "/SKILL_BASE_DIR/scripts/parse_logseq.py" <ARGS>
```

Sostituisci `/SKILL_BASE_DIR` con il percorso base estratto dall'intestazione.

---

## Comandi disponibili

| Argomento | Quando usarlo |
|-----------|--------------|
| `--page "Nome"` | Leggi una pagina (persona, progetto, argomento) |
| `--journal today` | Journal di oggi |
| `--journal 2026-05-15` | Journal di una data specifica (ISO) |
| `--todos` | Tutti i task aperti (TODO/DOING/LATER) da tutte le note |
| `--search "termine"` | Ricerca full-text in tutte le note |
| `--list` | Lista tutte le pagine e i journal disponibili |

---

## Come mappare la richiesta dell'utente

- *"leggi le note su [nome/progetto]"* → `--page "[nome]"`
- *"cosa ho da fare / task aperti / TODO"* → `--todos`
- *"journal di oggi / cosa ho fatto oggi"* → `--journal today`
- *"journal del [data verbale o ISO]"* → `--journal YYYY-MM-DD`
- *"cerca [termine] nelle note"* → `--search "[termine]"`
- *"quali pagine ho / lista note"* → `--list`
- Domanda su una persona o progetto specifico → `--page "[nome]"`

Se la richiesta è ambigua, inizia con `--list` per mostrare le pagine disponibili, poi leggi quella pertinente.

---

## Struttura dell'output

Lo script restituisce markdown strutturato con:
- **Proprietà** della pagina (`title::`, `tags::`, `type::`, `status::`, ecc.)
- **Gerarchia** dei bullet point preservata (indentazione = profondità)
- **Task** con stato: `TODO`, `DOING`, `DONE`, `LATER`
- **Wikilink** come `[[Nome Pagina]]`
- **Scheduled** e annotazioni temporali

---

## Come usare l'output

1. Leggi le note con il comando appropriato
2. Rispondi alla domanda dell'utente sintetizzando le informazioni rilevanti
3. Cita sempre task aperti se presenti e pertinenti alla domanda
4. Se nell'output ci sono `[[Wikilink]]` a pagine correlate, offriti di leggerle anche quelle con `--page`
5. Non inventare mai informazioni non presenti nelle note — citale o ammetti che non ci sono

---

## Setup automatico

Lo script installa `logseq-matryca-parser` automaticamente se mancante.
In caso di errore di installazione, esegui manualmente:

```bash
pip install logseq-matryca-parser
```
