#!/usr/bin/env bash
# Re-index logseq-matryca-parser with GitNexus (code graph + semantic embeddings).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export HF_HOME="${HF_HOME:-$HOME/.cache/huggingface}"
mkdir -p "$HF_HOME"

if command -v gitnexus >/dev/null 2>&1; then
  GITNEXUS=gitnexus
else
  GITNEXUS="npx"
  NPX_ARGS=(-y gitnexus@latest)
fi

if [[ "$GITNEXUS" == "npx" ]]; then
  exec npx "${NPX_ARGS[@]}" analyze --embeddings --skip-agents-md --skip-skills "$@"
else
  exec "$GITNEXUS" analyze --embeddings --skip-agents-md --skip-skills "$@"
fi
