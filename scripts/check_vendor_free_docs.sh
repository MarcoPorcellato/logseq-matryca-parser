#!/usr/bin/env bash
# Compatibility entry point; keep policy scanning in the Python implementation.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${script_dir}/check_vendor_free_docs.py" "$@"
