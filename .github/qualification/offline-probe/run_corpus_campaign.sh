#!/usr/bin/env bash
set -euo pipefail
umask 077

readonly helper_dir=".github/qualification/offline-probe"
readonly extractor="${helper_dir}/extract_results.py"
readonly temp_root="${RUNNER_TEMP:?RUNNER_TEMP missing}"
readonly private_dir="${temp_root}/official-corpus-qualification"

incomplete() {
  printf '%s\n' 'CORPUS_RESULT {"schema":1,"outcome":"INCOMPLETE","evidence":"unqualified"}'
  exit 1
}

if [[ "${1:-run}" == "--identity-only" && $# == 1 ]]; then
  readonly identity_dir="${temp_root}/official-corpus-identity"
  mkdir -m 700 "$identity_dir" || incomplete
  set +e
  python3 "$extractor" run --capture "${identity_dir}/identity.capture" \
    --result "${identity_dir}/identity.result" --timeout 30 -- python3 -c \
    'import sys; sys.path.insert(0, ".github/qualification/offline-probe"); import corpus_campaign as c; c.prepare_identity()' \
    >"${identity_dir}/identity.status" 2>&1
  outer_status=$?
  set -e
  [[ "$outer_status" == 0 && "$(<"${identity_dir}/identity.status")" == 0 ]] || incomplete
  python3 -c 'import sys,time; from pathlib import Path; sys.path.insert(0, ".github/qualification/offline-probe"); import corpus_campaign as c; sys.exit(0 if c.phase_safe(Path(sys.argv[1]), "identity", time.monotonic()+10) else 1)' \
    "$identity_dir" >"${identity_dir}/validate.status" 2>&1 || incomplete
  exit 0
fi

[[ $# == 0 && -d "$private_dir" && ! -L "$private_dir" ]] || incomplete

export UV_CACHE_DIR="${private_dir}/uv-cache"
export UV_PYTHON_INSTALL_DIR="${private_dir}/uv-python"

run_capped() {
  local name="$1" seconds="$2" outer_status status
  shift 2
  set +e
  python3 "$extractor" run --capture "${private_dir}/${name}.capture" \
    --result "${private_dir}/${name}.result" --timeout "$seconds" -- "$@" \
    >"${private_dir}/${name}.status" 2>&1
  outer_status=$?
  set -e
  status="$(<"${private_dir}/${name}.status")"
  [[ "$outer_status" == 0 && "$status" == 0 ]] || incomplete
  python3 -c 'import sys,time; sys.path.insert(0, ".github/qualification/offline-probe"); import corpus_campaign as c; r=c.identity_record(); sys.exit(0 if c.phase_safe(c.private_root(), sys.argv[1], r["deadline"]) else 1)' \
    "$name" >"${private_dir}/${name}.validate" 2>&1 || incomplete
}

run_capped install 30 uv self version --output-format json
run_capped install-version 5 python3 -c \
  'import sys,time; sys.path.insert(0, ".github/qualification/offline-probe"); import corpus_campaign as c; c.validate_uv_version(c.inputs.read_private(c.private_root(), "install.capture", 16384, time.monotonic()+4))'
run_capped sync 300 uv sync --locked --all-extras

export UV_NO_SYNC=1 UV_OFFLINE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTEST_ADDOPTS= PYTHONPATH=
[[ -z "${PYTEST_PLUGINS:-}" ]] || incomplete

# The selected Python driver owns sequential phases, not a nested supervisor.
# Its only authored public output is validated ASCII JSON with a fixed prefix.
uv run --locked --no-sync python -c \
  'import sys; sys.path.insert(0, ".github/qualification/offline-probe"); import corpus_campaign as c; sys.exit(c.hosted_controller())' \
  2>"${private_dir}/controller.stderr"
