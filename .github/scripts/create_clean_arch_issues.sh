#!/usr/bin/env bash
# Bootstrap Clean Architecture v1.6 milestone, epic, and phase issues.
# Run from repo root: bash .github/scripts/create_clean_arch_issues.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

REPO="${GITHUB_REPOSITORY:-MarcoPorcellato/logseq-matryca-parser}"
MILESTONE_TITLE="v1.6 — Clean Architecture & Code Quality"
OUT="$ROOT/.github/clean_arch_issue_numbers.txt"
: > "$OUT"

milestone_number() {
  gh api "repos/${REPO}/milestones" --paginate \
    --jq ".[] | select(.title==\"${MILESTONE_TITLE}\") | .number" | head -1
}

ensure_milestone() {
  local num
  num=$(milestone_number || true)
  if [[ -n "${num}" ]]; then
    echo "Milestone exists: #${num} (${MILESTONE_TITLE})"
    echo "milestone=${num}" >> "$OUT"
    return
  fi
  num=$(gh api "repos/${REPO}/milestones" -f title="${MILESTONE_TITLE}" \
    -f description="Uncle Bob rings, layer CI, KINETIC/SYNAPSE SRP-OCP slices. SSOT: docs/CLEAN_CODE_ARCHITECTURE.md. Target: v1.6.0." \
    --jq '.number')
  echo "Created milestone #${num}: ${MILESTONE_TITLE}"
  echo "milestone=${num}" >> "$OUT"
}

create_issue() {
  local id="$1"
  local title="$2"
  local labels="$3"
  local body_file="$4"
  local url
  url=$(gh issue create --title "$title" --label "$labels" --body-file "$body_file")
  local num="${url##*/}"
  local ms
  ms=$(milestone_number)
  if [[ -n "${ms}" ]]; then
    gh api -X PATCH "repos/${REPO}/issues/${num}" -f milestone="${ms}" >/dev/null
  fi
  echo "$id=${num}" >> "$OUT"
  echo "Created ${id} -> #${num}"
}

BODY_DIR=$(mktemp -d)
trap 'rm -rf "$BODY_DIR"' EXIT

ensure_milestone

# Epic
cat > "$BODY_DIR/epic.md" <<'EOF'
## Goal

Ship the v1.6 Clean Architecture contract: SSOT documentation, import-boundary CI, KINETIC export extraction, SYNAPSE embed OCP, graph ISP public API, and a KINETIC command slice.

## Clean Architecture lens

| Ring | Modules touched |
|------|-----------------|
| Entities | `logos_core` (unchanged in v1) |
| Use cases | `graph`, `logos_parser` (no FSM refactor) |
| Adapters | `synapse`, `forge`, `kinetic_export` |
| Drivers | `kinetic`, `kinetic_commands` |

## Phases (child issues)

Update checkboxes when each phase merges:

- [ ] Phase 0 — docs SSOT + layer CI + vendor-name-check
- [ ] Phase 1 — `kinetic_export.py` (DEBT-005)
- [ ] Phase 2 — SYNAPSE embed OCP (DEBT-006) — #70
- [ ] Phase 3 — `iter_attached_nodes()` + `kinetic_commands.py`
- [ ] Phase 4 — hardening + v1 closure

## SSOT

- [`docs/CLEAN_CODE_ARCHITECTURE.md`](https://github.com/MarcoPorcellato/logseq-matryca-parser/blob/main/docs/CLEAN_CODE_ARCHITECTURE.md)
- [`docs/quality/CLEAN_ARCH_BACKLOG.md`](https://github.com/MarcoPorcellato/logseq-matryca-parser/blob/main/docs/quality/CLEAN_ARCH_BACKLOG.md)
- [`docs/quality/GITHUB_CLEAN_ARCH_ROADMAP.md`](https://github.com/MarcoPorcellato/logseq-matryca-parser/blob/main/docs/quality/GITHUB_CLEAN_ARCH_ROADMAP.md)

## Out of scope (v2 epic)

- `logos_parser.py` split (1439 lines, CRITICAL hub — do not refactor in v1.6)
- Hexagonal `domain/ports.py`
- Vendor AST indexer in CI (Ghost Tooling policy)

## Definition of Done

- [ ] All phase issues closed
- [ ] `make all` green on `main`
- [ ] `CHANGELOG.md` ready for v1.6.0
- [ ] Milestone closed after tag `v1.6.0`
EOF
create_issue "EPIC" "Epic: Clean Architecture v1.6 — documentation, layer CI, and SRP/OCP slices" "architecture,enhancement" "$BODY_DIR/epic.md"

# Phase 0
cat > "$BODY_DIR/phase0.md" <<'EOF'
## Problem

Contributors lack a single Uncle Bob SSOT, automated layer-boundary tests, and a vendor-free code-audit runbook. Two small DIP/SRP slices are already implemented locally but not tracked on `main`.

## Clean Architecture lens

| Ring | SOLID | Dependency rule |
|------|-------|-----------------|
| Drivers / use cases | SRP, DIP | Public graph API for watcher; remove dead kinetic helper |
| CI (tests) | — | Inner rings must not import frameworks |

## Deliverables

- [ ] `docs/CLEAN_CODE_ARCHITECTURE.md` — rings, SOLID, module map
- [ ] `tests/test_layer_boundary.py` — import-boundary gate
- [ ] `scripts/check_vendor_free_docs.sh` + `make vendor-name-check`
- [ ] `docs/internal/LOCAL_CODE_STUDY.md` — maintainer runbook (generic terminology)
- [ ] Public `LogseqGraph.is_tracked_markdown_path()` (closes #68)
- [ ] Remove dead `_parse_graph` from `kinetic.py` (closes #67)

## Reproduction

```bash
uv run pytest tests/test_layer_boundary.py -q
make vendor-name-check
```

## Expected vs actual

- **Expected:** `make all` passes; zero vendor tool names in public docs.
- **Actual (pre-merge):** slices exist only in working tree.

## Definition of Done

- [ ] `make all` passes
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] PR body: `Fixes #67`, `Fixes #68`, links epic
EOF
create_issue "PHASE0" "docs: Clean Architecture SSOT, layer CI, and code-audit runbook" "architecture,clean-code,documentation" "$BODY_DIR/phase0.md"

# Phase 1
cat > "$BODY_DIR/phase1.md" <<'EOF'
## Problem

`kinetic.py` mixes Typer wiring with five `_export_*` handlers (~700 lines). Export formats cannot be extended without editing the driver module (SRP / OCP violation).

## Clean Architecture lens

| Ring | SOLID | Dependency rule |
|------|-------|-----------------|
| Drivers | SRP, OCP | `kinetic.py` orchestrates; `kinetic_export.py` owns format handlers |
| Adapters | — | Handlers may call `forge`, `synapse` via public APIs |

## Suggested fix

1. Create `src/logseq_matryca_parser/kinetic_export.py`
2. Move `_export_json`, `_export_markdown`, `_export_obsidian`, `_export_langchain`, etc.
3. Registry or dispatcher in `kinetic.export()` — no behavior change
4. Extend `tests/test_layer_boundary.py` for the new module

## Reproduction

```bash
uv run matryca-parse export --help
make check
```

## Expected vs actual

- **Expected:** identical CLI output and exit codes; `kinetic.py` shrinks materially.
- **Actual:** all export logic inline in `kinetic.py`.

## Definition of Done

- [ ] `make all` passes
- [ ] `tests/test_kinetic.py` unchanged behavior
- [ ] `docs/quality/CLEAN_ARCH_BACKLOG.md` — DEBT-005 closed
- [ ] `CHANGELOG.md` if operator-visible

**Tracking:** DEBT-005
EOF
create_issue "PHASE1" "refactor(kinetic): extract export handlers to kinetic_export.py (SRP)" "architecture,clean-code,cli,enhancement" "$BODY_DIR/phase1.md"

# Phase 3a — iter_attached_nodes
cat > "$BODY_DIR/phase3a.md" <<'EOF'
## Problem

`LogseqGraph._iter_attached_nodes()` is private but is the correct ISP surface for consumers that must skip orphan ghost nodes. Callers risk using `graph.pages` or `_node_registry` directly.

## Clean Architecture lens

| Ring | SOLID | Dependency rule |
|------|-------|-----------------|
| Use cases | ISP | Public iterator; private implementation unchanged |
| Adapters | DIP | `agent_read`, LENS, SYNAPSE should prefer public API |

## Suggested fix

- Add `LogseqGraph.iter_attached_nodes() -> Iterator[LogseqNode]` (public)
- Delegate from existing private method
- Deprecation comment on leaky patterns in docstring only

## Reproduction

```python
from logseq_matryca_parser.graph import LogseqGraph
g = LogseqGraph.load_directory("path/to/vault")
list(g.iter_attached_nodes())
```

## Definition of Done

- [ ] Public method documented in `CLEAN_CODE_ARCHITECTURE.md` module map
- [ ] `make all` passes
- [ ] No new `graph.pages` iteration in drivers without `iter_canonical_pages()`
EOF
create_issue "PHASE3A" "refactor(graph): public iter_attached_nodes() (ISP)" "architecture,clean-code,enhancement" "$BODY_DIR/phase3a.md"

# Phase 3b — kinetic_commands
cat > "$BODY_DIR/phase3b.md" <<'EOF'
## Problem

After Phase 1 export extraction, `kinetic.py` still hosts many Typer subcommands (scan, visualize, agent-write, demo). The driver module remains above the ~550-line SRP threshold.

## Clean Architecture lens

| Ring | SOLID | Dependency rule |
|------|-------|-----------------|
| Drivers | SRP | `kinetic.py` = app factory + shared helpers; `kinetic_commands.py` = command handlers |

## Suggested fix

- Extract command groups to `kinetic_commands.py`
- `kinetic.py` registers commands via imports
- Extend `tests/test_layer_boundary.py` if needed

## Related

- #61 — replace production `assert` in `agent_write` (include in same PR if still present)

## Definition of Done

- [ ] `make all` passes
- [ ] `tests/test_kinetic.py` green
- [ ] `kinetic.py` line count ≤ 550 post-extraction
EOF
create_issue "PHASE3B" "refactor(kinetic): extract subcommands to kinetic_commands.py (SRP)" "architecture,clean-code,cli,enhancement" "$BODY_DIR/phase3b.md"

# Phase 4
cat > "$BODY_DIR/phase4.md" <<'EOF'
## Problem

v1.6 documentation and backlog need final cross-links; epic checklist must close; README/COOKBOOK should point to the Uncle Bob SSOT.

## Deliverables

- [ ] README + COOKBOOK links to `docs/CLEAN_CODE_ARCHITECTURE.md`
- [ ] `docs/quality/CLEAN_ARCH_BACKLOG.md` — v1 structural items marked complete
- [ ] Close epic issue
- [ ] `CHANGELOG.md` release notes draft for v1.6.0 (no autonomous tag)

## Definition of Done

- [ ] `make all` passes
- [ ] Epic checklist complete
- [ ] Milestone ready to close after release tag
EOF
create_issue "PHASE4" "chore: Clean Architecture v1 hardening + README/COOKBOOK links" "architecture,clean-code,documentation" "$BODY_DIR/phase4.md"

echo ""
echo "=== Issue numbers written to ${OUT} ==="
cat "$OUT"
echo ""
echo "Next: assign milestone to existing #70, #71, #61 via gh issue edit"
echo "Create GitHub Project: gh project create --title 'Logseq Parser — Clean Architecture v1.6' --owner MarcoPorcellato"
