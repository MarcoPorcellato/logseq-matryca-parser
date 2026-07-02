#!/usr/bin/env bash
# Fail when forbidden vendor AST indexer names appear in the tracked tree.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

if rg -i 'gitnexus|user-gitnexus|\.gitnexusrc|\.gitnexus/' \
  --glob '!.git' \
  --glob '!scripts/check_vendor_free_docs.sh' \
  . ; then
  echo "ERROR: forbidden vendor tool name found in tracked tree" >&2
  exit 1
fi

echo "vendor-name-check: OK"
