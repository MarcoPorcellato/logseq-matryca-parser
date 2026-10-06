#!/usr/bin/env bash
set -euo pipefail
umask 077

readonly helper_dir=".github/qualification/offline-probe"
readonly extractor="${helper_dir}/extract_results.py"
readonly temp_root="${RUNNER_TEMP:?RUNNER_TEMP missing}"
readonly private_dir="${temp_root}/hosted-cleanup-qualification"
readonly mode="${1:-run}"

if [[ "$mode" == "--identity-only" ]]; then
  capture_dir="${temp_root}/hosted-cleanup-identity-capture"
  mkdir -m 700 "$capture_dir"
  chmod 700 "$capture_dir"
  capture="${capture_dir}/identity.capture"
  status_file="${capture_dir}/identity.status"
  set +e
  python3 "$extractor" run --capture "$capture" --result "${capture_dir}/identity.result" \
    --timeout 30 -- python3 "$extractor" identity \
    >"$status_file" 2>&1
  runner_status=$?
  set -e
  status="$(<"$status_file")"
  if (( runner_status != 0 )) || [[ ! "$status" =~ ^[0-9]{1,3}$ ]] || (( status != 0 )); then
    printf '{"outcome":"INCOMPLETE"}\n'
    exit 1
  fi
  exit 0
fi

if [[ "$mode" != "run" || ! -d "$private_dir" || -L "$private_dir" ]]; then
  printf '{"outcome":"INCOMPLETE"}\n'
  exit 1
fi
chmod 700 "$private_dir"

record_status() {
  printf '%b\n' "$1" > "${private_dir}/statuses.txt"
  chmod 600 "${private_dir}/statuses.txt"
}

run_capped() {
  local name="$1" seconds="$2" capture status_file runner_status status
  shift 2
  capture="${private_dir}/${name}.capture"
  status_file="${private_dir}/${name}.status"
  : > "$status_file"
  chmod 600 "$status_file"
  set +e
  if [[ "$name" == strict || "$name" == remaining ]]; then
    python3 "$extractor" run --capture "$capture" --result "${private_dir}/${name}.result" \
      --timeout "$seconds" --xml-capture "${private_dir}/${name}.xml" -- "$@" \
      >"$status_file" 2>&1
  else
    python3 "$extractor" run --capture "$capture" --result "${private_dir}/${name}.result" \
      --timeout "$seconds" -- "$@" >"$status_file" 2>&1
  fi
  runner_status=$?
  set -e
  status="$(<"$status_file")"
  if (( runner_status != 0 )) || [[ ! "$status" =~ ^[0-9]{1,3}$ ]] || (( status > 255 )); then
    status=125
  fi
  printf '%s' "$status"
}

identity_status=0
install_status="$(run_capped install 30 uv --version)"
if (( install_status == 0 )) && ! grep -qx 'uv 0.11.7' "${private_dir}/install.capture"; then
  install_status=1
fi
record_status "identity\t${identity_status}\ninstall\t${install_status}"

sync_status="null"
verify_status="null"
strict_status="null"
remaining_status="null"
if (( install_status == 0 )); then
  sync_status="$(run_capped sync 300 uv sync --locked --all-extras)"
  record_status "identity\t${identity_status}\ninstall\t${install_status}\nsync\t${sync_status}"
fi

export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
export PYTEST_ADDOPTS=
export PYTHONPATH=
if [[ -n "${PYTEST_PLUGINS:-}" ]]; then
  printf '{"outcome":"INCOMPLETE"}\n'
  exit 1
fi
if [[ "$sync_status" == "0" ]]; then
  verify_status="$(run_capped verify 30 uv run --locked --no-sync python "$extractor" verify)"
  record_status "identity\t${identity_status}\ninstall\t${install_status}\nsync\t${sync_status}\nverify\t${verify_status}"
fi

if [[ "$verify_status" == "0" ]]; then
  verify_status="$(run_capped verify-strict 30 uv run --locked --no-sync python "$extractor" verify)"
  record_status "identity\t${identity_status}\ninstall\t${install_status}\nsync\t${sync_status}\nverify\t${verify_status}"
fi
if [[ "$verify_status" == "0" ]]; then
  strict_status="$(run_capped strict 60 uv run --locked --no-sync pytest --noconftest \
    -p no:cacheprovider -c "${temp_root}/pytest.ini" -q \
    --rootdir=. \
    --junitxml="${private_dir}/strict.xml" \
    .github/qualification/offline-probe/test_probe.py::test_completed_worker_with_live_descendant_is_not_success)"
  record_status "identity\t${identity_status}\ninstall\t${install_status}\nsync\t${sync_status}\nverify\t${verify_status}\nstrict\t${strict_status}"
fi

strict_gate_status=125
if [[ "$strict_status" == "0" ]]; then
  strict_gate_status="$(run_capped strict-report 30 uv run --locked --no-sync python "$extractor" strict)"
fi

if [[ "$strict_status" == "0" && "$strict_gate_status" == "0" ]]; then
  verify_status="$(run_capped verify-remaining 30 uv run --locked --no-sync python "$extractor" verify)"
  record_status "identity\t${identity_status}\ninstall\t${install_status}\nsync\t${sync_status}\nverify\t${verify_status}\nstrict\t${strict_status}"
fi

if [[ "$strict_status" == "0" && "$strict_gate_status" == "0" && "$verify_status" == "0" ]]; then
  remaining_status="$(run_capped remaining 180 uv run --locked --no-sync pytest --noconftest \
    -p no:cacheprovider -c "${temp_root}/pytest.ini" -q -x \
    --rootdir=. \
    --junitxml="${private_dir}/remaining.xml" \
    .github/qualification/offline-probe/test_probe.py \
    -k 'not test_completed_worker_with_live_descendant_is_not_success')"
fi

record_status "identity\t${identity_status}\ninstall\t${install_status}\nsync\t${sync_status}\nverify\t${verify_status}\nstrict\t${strict_status}\nremaining\t${remaining_status}"
extract_status="$(run_capped extract 30 uv run --locked --no-sync python "$extractor" report)"
capture="${private_dir}/extract.capture"
bytes=$(wc -c < "$capture")
if (( bytes > 16384 )) || (( extract_status != 0 )); then
  printf '{"outcome":"INCOMPLETE"}\n'
  exit 1
fi
cat "$capture"
if grep -qx '{"outcome":"PASS"}' "$capture"; then
  exit 0
fi
if grep -q '"outcome":"PASS"' "$capture"; then
  exit 0
fi
exit 1
