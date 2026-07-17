#!/usr/bin/env bash
# Fail when forbidden vendor AST indexer names appear in the tracked tree.
# Patterns are base64-encoded so the checker itself stays vendor-agnostic in source.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

pattern="$(printf '%s' 'Z2l0bmV4dXN8dXNlci1naXRuZXh1c3xcLmdpdG5leHVzcmN8XC5naXRuZXh1cy8=' | base64 -d)"

if rg -i "${pattern}" \
  --glob '!.git' \
  --glob '!uv.lock' \
  --glob '!scripts/check_vendor_free_docs.sh' \
  . ; then
  echo "ERROR: forbidden vendor tool name found in tracked tree (audit code / Ghost Tooling policy)" >&2
  exit 1
fi

echo "vendor-name-check: OK"
