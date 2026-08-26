#!/usr/bin/env bash
set -euo pipefail

readonly EXPECTED_SHA256="b8d26013800c99ba806506a0539a9ddc781bfab52f95c8f1dbdff1b65c2fcd4c"

ccp_candidate="$(command -v commit-ci-preflight || true)"
if [[ -z "$ccp_candidate" || "$ccp_candidate" != /* || ! -x "$ccp_candidate" ]]; then
  printf 'A qualified absolute commit-ci-preflight executable is unavailable on PATH.\n' >&2
  exit 1
fi
readonly CCP_BINARY="$ccp_candidate"

actual_sha256="$(shasum -a 256 "$CCP_BINARY" | awk '{print $1}')"
if [[ "$actual_sha256" != "$EXPECTED_SHA256" ]]; then
  printf 'CCP executable digest mismatch: expected %s, found %s\n' \
    "$EXPECTED_SHA256" "$actual_sha256" >&2
  exit 1
fi

printf 'CCP executable: %s\nCCP SHA-256: %s\n' "$CCP_BINARY" "$actual_sha256" >&2
exec "$CCP_BINARY" "$@"
