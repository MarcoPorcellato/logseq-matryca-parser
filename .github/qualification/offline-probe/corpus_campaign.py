"""Bounded all-document diagnostic; Parser success is not semantic completeness."""

from __future__ import annotations

import ast
import hashlib
import importlib.metadata
import importlib.util
import os
import re
import subprocess
import sys
import time
import tomllib
import xml.etree.ElementTree as ET
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import corpus_inputs as inputs
import extract_results as extractor
import probe

_stage = probe._bounded_stage
_worker = probe.run_worker
FINDINGS = {
    "expected_domain_rejection",
    "unexpected_exception",
    "raw_content_mismatch",
    "tree_invariants",
}
CONTINUABLE = FINDINGS | {"parsed_invariants_pass", "timeout"}
INFRASTRUCTURE = {
    "binding_failure",
    "invalid_child_result",
    "output_overflow",
    "cleanup_unconfirmed",
    "worker_start_failure",
    "worker_io_failure",
    "worker_descendant_detected",
    "worker_interrupted",
    "runner_rejected_optimized_python",
    "runner_platform_unsupported",
    "input_failure",
    "malformed_worker",
    "budget_exhausted",
    "unattempted",
}
ROW_KEYS = {
    "ordinal",
    "input_sha256",
    "attempted",
    "classification",
    "cleanup_confirmed",
    "root_count",
    "node_count",
    "invariant_result",
    "exception_type",
}
RANGES = ((0, 40), (40, 79), (79, 118), (118, 157), (157, 196), (196, 235), (235, 274), (274, 313))
ROOT = Path(__file__).resolve().parents[3]
QUAL = ROOT / ".github/qualification/offline-probe"
NEW_FILES = {
    f".github/qualification/offline-probe/{name}"
    for name in (
        "corpus-selection.json",
        "corpus_inputs.py",
        "corpus_campaign.py",
        "test_corpus_campaign.py",
        "run_corpus_campaign.sh",
        "source-manifest.json",
    )
}
NEW_FILES.add("tests/test_quality_gate_contract.py")


def batch_ranges(count: int) -> tuple[tuple[int, int], ...]:
    inputs.require(type(count) is int and count == 313)
    return RANGES


def worker_launch_confirmed(result: dict[str, Any]) -> bool:
    code = result.get("return_code") if type(result) is dict else None
    return type(code) is int and -128 <= code <= 255


def mode_jobs(event: str, synthetic: bool, corpus: bool) -> tuple[bool, bool, bool]:
    inputs.require(type(synthetic) is bool and type(corpus) is bool and not (synthetic and corpus))
    return (
        event != "workflow_dispatch" or not (synthetic or corpus),
        event == "workflow_dispatch" and synthetic,
        event == "workflow_dispatch" and corpus,
    )


def expected_identity(env: Mapping[str, str]) -> dict[str, Any]:
    inputs.require(env.get("GITHUB_REPOSITORY") == "MarcoPorcellato/logseq-matryca-parser")
    inputs.require(
        env.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
        and env.get("CORPUS_ENABLED") == "true"
        and env.get("QUALIFICATION_ENABLED") == "false"
    )
    ref = env.get("EXPECTED_REF", "")
    inputs.require(
        re.fullmatch(r"refs/heads/[!-~]{1,244}", ref) is not None and ref == env.get("GITHUB_REF")
    )
    commit = env.get("EXPECTED_COMMIT", "")
    inputs.require(
        re.fullmatch(r"[0-9a-f]{40}", commit) is not None and commit == env.get("GITHUB_SHA")
    )
    inputs.require(
        env.get("GITHUB_WORKFLOW_REF")
        == f"MarcoPorcellato/logseq-matryca-parser/.github/workflows/parser-adversarial.yml@{ref}"
    )
    inputs.require(env.get("GITHUB_RUN_ATTEMPT") == "1")
    run_id = env.get("GITHUB_RUN_ID", "")
    inputs.require(run_id.isascii() and run_id.isdecimal() and 1 <= int(run_id) <= 9007199254740991)
    result = {
        "repository": env["GITHUB_REPOSITORY"],
        "event": "workflow_dispatch",
        "ref": ref,
        "commit": commit,
        "run_id": int(run_id),
        "run_attempt": 1,
    }
    for key, variable in (
        ("workflow_sha256", "EXPECTED_WORKFLOW_SHA256"),
        ("selection_sha256", "EXPECTED_SELECTION_SHA256"),
    ):
        digest = env.get(variable, "")
        inputs.require(re.fullmatch(r"[0-9a-f]{64}", digest) is not None)
        result[key] = digest
    return result


def private_root() -> Path:
    root = Path(os.environ["RUNNER_TEMP"])
    inputs.require(root.is_absolute())
    return root / "official-corpus-qualification"


def read_selection(deadline: float) -> dict[str, Any]:
    raw = inputs.read_private(QUAL, "corpus-selection.json", inputs.MAX_SELECTION, deadline)
    selection = inputs.validate_selection(inputs.decode_json(raw, inputs.MAX_SELECTION))
    inputs.require(raw == inputs.canonical(selection))
    return selection


def _head() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        timeout=5,
        check=False,
    )
    inputs.require(
        result.returncode == 0 and len(result.stdout) <= 128 and len(result.stderr) <= 4096
    )
    return result.stdout.decode("ascii", errors="strict").strip()


def source_bindings(deadline: float) -> tuple[str, str]:
    base, original = extractor.manifest_rows()
    names = {row["path"] for row in base} | NEW_FILES
    value = inputs.decode_json(
        inputs.read_private(QUAL, "corpus-source-manifest.json", 256 * 1024, deadline), 256 * 1024
    )
    inputs.require(type(value) is dict and set(value) == {"files", "source_aggregate_sha256"})
    rows = value["files"]
    inputs.require(type(rows) is list and len(rows) == len(names) == 43)
    observed: list[str] = []
    digest = hashlib.sha256()
    for row in rows:
        inputs.require(type(row) is dict and set(row) == {"path", "sha256"})
        name = inputs.safe_path(row["path"])
        inputs.require(
            type(row["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is not None
        )
        raw = inputs.read_private(ROOT, name, 1024 * 1024, deadline)
        inputs.require(hashlib.sha256(raw).hexdigest() == row["sha256"])
        observed.append(name)
        digest.update(name.encode("utf-8") + b"\0" + row["sha256"].encode("ascii") + b"\n")
    inputs.require(
        observed == sorted(names) and value["source_aggregate_sha256"] == digest.hexdigest()
    )
    return original, digest.hexdigest()


def prepare_identity() -> None:
    inputs.require(__debug__)
    identity = expected_identity(os.environ)
    deadline = time.monotonic() + 25.0
    selection = read_selection(deadline)
    inputs.require(
        hashlib.sha256(inputs.canonical(selection)).hexdigest() == identity["selection_sha256"]
    )
    workflow = inputs.read_private(
        ROOT, ".github/workflows/parser-adversarial.yml", 256 * 1024, deadline
    )
    inputs.require(
        hashlib.sha256(workflow).hexdigest() == identity["workflow_sha256"]
        and _head() == identity["commit"]
    )
    original, aggregate = source_bindings(deadline)
    root = private_root()
    inputs.fresh_directory(root, deadline)
    value = {
        "identity": identity,
        "parser_source_aggregate_sha256": original,
        "source_aggregate_sha256": aggregate,
        "deadline": time.monotonic() + 3900.0,
    }
    inputs.write_private(root, "identity.json", inputs.canonical(value), deadline)


def identity_record() -> dict[str, Any]:
    deadline = time.monotonic() + 10.0
    record = inputs.decode_json(
        inputs.read_private(private_root(), "identity.json", 16 * 1024, deadline), 16 * 1024
    )
    inputs.require(
        type(record) is dict
        and set(record)
        == {"identity", "parser_source_aggregate_sha256", "source_aggregate_sha256", "deadline"}
    )
    inputs.require(record["identity"] == expected_identity(os.environ))
    inputs.check_deadline(record["deadline"])
    return dict(record)


def runtime_facts() -> dict[str, Any]:
    inputs.require(
        __debug__
        and sys.version_info[:3] == (3, 12, 13)
        and Path(sys.prefix).resolve() == (ROOT / ".venv").resolve()
    )
    inputs.require(
        os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD") == "1"
        and os.environ.get("PYTEST_ADDOPTS") == ""
        and not os.environ.get("PYTEST_PLUGINS")
    )
    expected = {
        "probe": QUAL / "probe.py",
        "extract_results": QUAL / "extract_results.py",
        "corpus_inputs": QUAL / "corpus_inputs.py",
        "corpus_campaign": QUAL / "corpus_campaign.py",
        "tests": ROOT / "tests/__init__.py",
        "tests.parser_assurance": ROOT / "tests/parser_assurance/__init__.py",
        "tests.parser_assurance.invariants": ROOT / "tests/parser_assurance/invariants.py",
        "logseq_matryca_parser": ROOT / "src/logseq_matryca_parser/__init__.py",
    }
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    for name, origin in expected.items():
        spec = importlib.util.find_spec(name)
        inputs.require(
            spec is not None
            and spec.origin is not None
            and Path(spec.origin).resolve() == origin.resolve()
        )
    site = (ROOT / ".venv/lib/python3.12/site-packages").resolve()
    for name in ("pytest", "_pytest"):
        spec = importlib.util.find_spec(name)
        inputs.require(
            spec is not None
            and spec.origin is not None
            and site in Path(spec.origin).resolve().parents
        )
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))

    def normalize(name: str) -> str:
        return re.sub(r"[-_.]+", "-", name).lower()

    pins = {normalize(row["name"]): row["version"] for row in lock["package"] if "version" in row}
    packages: dict[str, str] = {}
    for distribution in importlib.metadata.distributions():
        name = normalize(distribution.metadata["Name"])
        if name == "logseq-matryca-parser":
            continue
        inputs.require(name not in packages and pins.get(name) == distribution.version)
        packages[name] = distribution.version
    executable = Path(sys.executable).resolve(strict=True)
    return {
        "version": "3.12.13",
        "assertions": True,
        "binary_sha256": extractor.sha(executable),
        "packages": [
            {"name": name, "version": version} for name, version in sorted(packages.items())
        ],
    }


def live_bindings() -> dict[str, Any]:
    record = identity_record()
    selection = read_selection(record["deadline"])
    original, aggregate = source_bindings(record["deadline"])
    inputs.require(
        original == record["parser_source_aggregate_sha256"]
        and aggregate == record["source_aggregate_sha256"]
    )
    workflow = inputs.read_private(
        ROOT, ".github/workflows/parser-adversarial.yml", 256 * 1024, record["deadline"]
    )
    inputs.require(
        _head() == record["identity"]["commit"]
        and hashlib.sha256(workflow).hexdigest() == record["identity"]["workflow_sha256"]
    )
    return validate_bindings(
        {
            **record["identity"],
            "source_aggregate_sha256": aggregate,
            "parser_source_aggregate_sha256": original,
            "runtime": runtime_facts(),
        },
        selection,
    )


def qualify_runtime() -> None:
    record = identity_record()
    value = live_bindings()
    inputs.write_private(
        private_root(), "bindings.json", inputs.canonical(value), record["deadline"]
    )
    inputs.write_private(
        private_root(), "pytest.ini", b"[pytest]\npythonpath = .\naddopts =\n", record["deadline"]
    )


def validate_bindings(value: Any, selection: dict[str, Any]) -> dict[str, Any]:
    keys = {
        "repository",
        "event",
        "ref",
        "commit",
        "workflow_sha256",
        "selection_sha256",
        "source_aggregate_sha256",
        "parser_source_aggregate_sha256",
        "run_id",
        "run_attempt",
        "runtime",
    }
    inputs.require(type(value) is dict and set(value) == keys)
    inputs.require(
        value["repository"] == "MarcoPorcellato/logseq-matryca-parser"
        and value["event"] == "workflow_dispatch"
    )
    inputs.require(
        type(value["ref"]) is str
        and re.fullmatch(r"refs/heads/[!-~]{1,244}", value["ref"]) is not None
    )
    for key, length in (
        ("commit", 40),
        ("workflow_sha256", 64),
        ("selection_sha256", 64),
        ("source_aggregate_sha256", 64),
        ("parser_source_aggregate_sha256", 64),
    ):
        inputs.require(
            type(value[key]) is str
            and re.fullmatch(r"[0-9a-f]{" + str(length) + r"}", value[key]) is not None
        )
    inputs.require(
        value["selection_sha256"] == hashlib.sha256(inputs.canonical(selection)).hexdigest()
    )
    inputs.require(type(value["run_id"]) is int and 1 <= value["run_id"] <= 9007199254740991)
    inputs.require(type(value["run_attempt"]) is int and value["run_attempt"] == 1)
    runtime = value["runtime"]
    inputs.require(
        type(runtime) is dict
        and set(runtime) == {"version", "assertions", "binary_sha256", "packages"}
    )
    inputs.require(runtime["version"] == "3.12.13" and runtime["assertions"] is True)
    inputs.require(
        type(runtime["binary_sha256"]) is str
        and re.fullmatch(r"[0-9a-f]{64}", runtime["binary_sha256"]) is not None
    )
    inputs.require(type(runtime["packages"]) is list and 0 < len(runtime["packages"]) <= 200)
    names: list[str] = []
    for row in runtime["packages"]:
        inputs.require(type(row) is dict and set(row) == {"name", "version"})
        inputs.require(
            all(
                type(row[key]) is str
                and re.fullmatch(r"[A-Za-z0-9._+!-]{1,128}", row[key]) is not None
                for key in ("name", "version")
            )
        )
        names.append(row["name"])
    inputs.require(names == sorted(set(names)))
    return dict(value)


def empty_row(
    row: dict[str, Any], classification: str = "unattempted", cleanup: bool = False
) -> dict[str, Any]:
    return {
        "ordinal": row["ordinal"],
        "input_sha256": row["sha256"],
        "attempted": False,
        "classification": classification,
        "cleanup_confirmed": cleanup,
        "root_count": None,
        "node_count": None,
        "invariant_result": "not_checked",
        "exception_type": None,
    }


def worker_row(row: dict[str, Any], raw: Any) -> dict[str, Any]:
    inputs.require(
        type(raw) is dict
        and set(raw)
        <= {
            "classification",
            "cleanup_confirmed",
            "return_code",
            "root_count",
            "node_count",
            "invariant_result",
            "exception_type",
        }
    )
    classification = raw.get("classification")
    inputs.require(type(classification) is str and classification in CONTINUABLE | INFRASTRUCTURE)
    inputs.require(type(raw.get("cleanup_confirmed")) is bool)
    result = empty_row(row, classification, raw["cleanup_confirmed"])
    result["attempted"] = worker_launch_confirmed(raw)
    if classification == "parsed_invariants_pass":
        inputs.require(
            result["attempted"]
            and raw.get("return_code") == 0
            and raw.get("invariant_result") == "pass"
        )
        for key in ("root_count", "node_count"):
            inputs.require(type(raw.get(key)) is int and 0 <= raw[key] <= 1000000)
            result[key] = raw[key]
        inputs.require(result["node_count"] >= result["root_count"])
        result["invariant_result"] = "pass"
    elif classification == "tree_invariants":
        result["invariant_result"] = "fail"
    if "exception_type" in raw:
        inputs.require(
            type(raw["exception_type"]) is str
            and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", raw["exception_type"]) is not None
        )
        result["exception_type"] = raw["exception_type"]
    if classification in FINDINGS:
        inputs.require(result["attempted"] and raw.get("return_code") == 0)
    return result


def validate_row(row: Any, selected: dict[str, Any]) -> None:
    inputs.require(type(row) is dict and set(row) == ROW_KEYS)
    inputs.require(
        type(row["ordinal"]) is int
        and row["ordinal"] == selected["ordinal"]
        and row["input_sha256"] == selected["sha256"]
    )
    inputs.require(type(row["attempted"]) is bool and type(row["cleanup_confirmed"]) is bool)
    inputs.require(
        type(row["classification"]) is str and row["classification"] in CONTINUABLE | INFRASTRUCTURE
    )
    inputs.require(row["invariant_result"] in ("pass", "fail", "not_checked"))
    for key in ("root_count", "node_count"):
        inputs.require(row[key] is None or (type(row[key]) is int and 0 <= row[key] <= 1000000))
    exception = row["exception_type"]
    inputs.require(
        exception is None
        or (
            type(exception) is str
            and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", exception) is not None
        )
    )
    if row["classification"] == "parsed_invariants_pass":
        inputs.require(
            row["attempted"] and row["cleanup_confirmed"] and row["invariant_result"] == "pass"
        )
        inputs.require(
            type(row["root_count"]) is int
            and type(row["node_count"]) is int
            and row["node_count"] >= row["root_count"]
        )
    inputs.require(len(inputs.canonical(row)) <= 512)


def run_batch(
    selection: dict[str, Any],
    batch_index: int,
    corpus_root: Path,
    output_root: Path,
    deadline: float,
) -> dict[str, Any]:
    selected = inputs.validate_selection(selection)
    inputs.require(type(batch_index) is int and 0 <= batch_index < 8 and __debug__)
    bindings = validate_bindings(live_bindings(), selected)
    inputs.check_deadline(deadline)
    deadline = min(deadline, time.monotonic() + 290.0)
    work_cutoff = deadline - 15.0
    start, end = RANGES[batch_index]
    rows: list[dict[str, Any]] = []
    stopped = False
    for source in selected["documents"][start:end]:
        if stopped:
            rows.append(empty_row(source))
            continue
        if time.monotonic() + 6.0 >= work_cutoff:
            rows.append(empty_row(source, "budget_exhausted", True))
            stopped = True
            continue
        try:
            payload = _stage(
                "corpus_read",
                lambda source=source: inputs.read_verified_file(corpus_root, source, work_cutoff),
                deadline=work_cutoff,
                reserve_final=False,
                max_payload_bytes=inputs.MAX_RESPONSE,
            )
            inputs.verify_bytes(payload, source)
        except Exception as exc:
            rows.append(
                empty_row(source, "input_failure", getattr(exc, "cleanup_confirmed", False) is True)
            )
            stopped = True
            continue
        raw = _worker(
            payload,
            source["sha256"],
            source["source_path"].rsplit("/", 1)[-1][:-3],
            timeout=3.0,
            deadline=deadline - 5.0,
        )
        try:
            result = worker_row(source, raw)
            validate_row(result, source)
        except (ValueError, TypeError, KeyError):
            result = empty_row(source, "malformed_worker", False)
        rows.append(result)
        stopped = not (
            result["attempted"]
            and result["cleanup_confirmed"]
            and result["classification"] in CONTINUABLE
        )
        if time.monotonic() >= work_cutoff:
            stopped = True
    inputs.require(live_bindings() == bindings)
    packet = {
        "schema": 1,
        "batch_index": batch_index,
        "bindings": bindings,
        "rows": rows,
        "complete": not stopped,
    }
    inputs.require(len(inputs.canonical(packet)) <= 64 * 1024)
    inputs.write_private(
        output_root, f"batch-{batch_index}.json", inputs.canonical(packet), deadline
    )
    return packet


def supervisor_safe(value: Any) -> bool:
    try:
        result = extractor.validate_run_result(value)
    except (ValueError, TypeError, KeyError):
        return False
    return bool(
        result["reason"] == "complete"
        and type(result["child_exit_status"]) is int
        and result["child_exit_status"] == 0
        and result["leader_reaped"] is True
        and result["cleanup_confirmed"] is True
        and result["live_descendant_after_normal_exit"] is False
    )


def validate_batch(
    packet: Any, selection: dict[str, Any], bindings: dict[str, Any], index: int
) -> None:
    inputs.require(
        type(packet) is dict
        and set(packet) == {"schema", "batch_index", "bindings", "rows", "complete"}
    )
    inputs.require(
        type(packet["schema"]) is int
        and packet["schema"] == 1
        and type(packet["batch_index"]) is int
        and packet["batch_index"] == index
    )
    inputs.require(
        packet["bindings"] == bindings
        and type(packet["complete"]) is bool
        and type(packet["rows"]) is list
    )
    start, end = RANGES[index]
    inputs.require(len(packet["rows"]) == end - start)
    unsafe = False
    for row, source in zip(packet["rows"], selection["documents"][start:end], strict=True):
        validate_row(row, source)
        inputs.require(not (unsafe and row["attempted"]))
        unsafe = unsafe or not (
            row["attempted"] and row["cleanup_confirmed"] and row["classification"] in CONTINUABLE
        )
    inputs.require(not packet["complete"] or not unsafe)


def next_batch_permitted(
    packet: Any, supervisor: Any, selection: dict[str, Any], bindings: dict[str, Any], index: int
) -> bool:
    try:
        validate_batch(packet, selection, bindings, index)
    except (ValueError, TypeError, KeyError):
        return False
    return bool(packet["complete"] and supervisor_safe(supervisor))


def aggregate_batches(
    selection: dict[str, Any], results: list[dict[str, Any]], bindings: dict[str, Any]
) -> dict[str, Any]:
    selected = inputs.validate_selection(selection)
    validate_bindings(bindings, selected)
    inputs.require(type(results) is list and len(results) <= 8)
    rows = [empty_row(source) for source in selected["documents"]]
    batches: list[dict[str, Any]] = []
    safe = True
    for index, entry in enumerate(results):
        inputs.require(safe and type(entry) is dict and set(entry) == {"packet", "supervisor"})
        packet = entry["packet"]
        validate_batch(packet, selected, bindings, index)
        start, end = RANGES[index]
        rows[start:end] = packet["rows"]
        safe = next_batch_permitted(packet, entry["supervisor"], selected, bindings, index)
        batches.append(
            {
                "index": index,
                "complete": packet["complete"],
                "supervisor_safe": supervisor_safe(entry["supervisor"]),
                "packet_sha256": hashlib.sha256(inputs.canonical(packet)).hexdigest(),
            }
        )
    unattempted = [row["ordinal"] for row in rows if not row["attempted"]]
    complete = not unattempted
    frequencies: dict[str, int] = {}
    for row in rows:
        frequencies[row["classification"]] = frequencies.get(row["classification"], 0) + 1
    infrastructure = (
        not safe
        or not complete
        or any(
            row["classification"] in INFRASTRUCTURE | {"timeout"} or not row["cleanup_confirmed"]
            for row in rows
        )
    )
    outcome = (
        "INCOMPLETE"
        if infrastructure
        else ("FAIL" if any(row["classification"] in FINDINGS for row in rows) else "PASS")
    )
    metadata = {
        "schema": 1,
        "source": dict(inputs.SOURCE),
        "bindings": bindings,
        "batches": batches,
        "coverage": {
            "selected": 313,
            "attempted": 313 - len(unattempted),
            "terminal": 313 - len(unattempted),
            "excluded": 0,
            "skipped": 0,
            "duplicates": 0,
            "unattempted": unattempted,
            "complete": complete,
        },
        "outcome": outcome,
        "outcomes": frequencies,
    }
    inputs.require(len(inputs.canonical(metadata)) <= 32 * 1024)
    report = {**metadata, "results": rows}
    inputs.require(len(inputs.canonical(report)) <= 192 * 1024)
    return report


def run_all_batches(
    selection: dict[str, Any], bindings: dict[str, Any], run_one: Callable[[int], dict[str, Any]]
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for index in range(8):
        try:
            entry = run_one(index)
            inputs.require(type(entry) is dict and set(entry) == {"packet", "supervisor"})
            validate_batch(entry["packet"], selection, bindings, index)
        except Exception:
            # Missing evidence is not proof that the current worker never launched.
            # Retain only prior validated batches; never start another child.
            break
        results.append(entry)
        if not next_batch_permitted(
            entry["packet"], entry["supervisor"], selection, bindings, index
        ):
            break
    return aggregate_batches(selection, results, bindings)


def report_child_permitted(report: dict[str, Any]) -> bool:
    batches = report.get("batches")
    return bool(
        type(batches) is list
        and len(batches) == 8
        and all(
            type(batch) is dict
            and batch.get("complete") is True
            and batch.get("supervisor_safe") is True
            for batch in batches
        )
    )


def interrupted_report(report: dict[str, Any]) -> dict[str, Any]:
    """Preserve validated accounting without qualifying unfinished final checks."""
    return {**report, "outcome": "INCOMPLETE"}


def _emit_report(report: dict[str, Any]) -> None:
    raw = inputs.canonical(report)
    inputs.require(len(raw) + len(b"CORPUS_RESULT ") <= 192 * 1024)
    metadata = {key: value for key, value in report.items() if key != "results"}
    inputs.require(len(inputs.canonical(metadata)) <= 32 * 1024)
    sys.stdout.buffer.write(b"CORPUS_RESULT " + raw)


def validate_uv_version(raw: bytes) -> None:
    value = inputs.decode_json(raw, 16 * 1024)
    inputs.require(
        type(value) is dict
        and value.get("package_name") == "uv"
        and value.get("version") == "0.11.7"
        and "commit_info" in value
    )
    commit = value.get("commit_info")
    inputs.require(
        commit is None
        or (
            type(commit) is dict
            and type(commit.get("commits_since_last_tag")) is int
            and commit["commits_since_last_tag"] == 0
        )
    )


def phase_safe(root: Path, name: str, deadline: float, status: int = 0, xml: bool = False) -> bool:
    try:
        result = inputs.decode_json(
            inputs.read_private(root, name + ".result", 4096, deadline), 4096
        )
        checked = extractor.validate_run_result(result)
        return bool(
            type(checked["child_exit_status"]) is int
            and checked["child_exit_status"] == status
            and checked["reason"] == "complete"
            and checked["leader_reaped"] is True
            and checked["cleanup_confirmed"] is True
            and checked["live_descendant_after_normal_exit"] is False
            and (not xml or checked["xml_drained"] is True)
        )
    except (ValueError, OSError, TypeError, KeyError):
        return False


def _phase(name: str, seconds: int, command: list[str], xml: bool = False, status: int = 0) -> None:
    record = identity_record()
    root = private_root()
    remaining = int(record["deadline"] - time.monotonic())
    inputs.require(remaining > 5)
    limit = min(seconds, remaining)
    code = extractor.run_supervised(
        root / (name + ".capture"),
        root / (name + ".result"),
        limit,
        command,
        root / (name + ".xml") if xml else None,
    )
    inputs.require(code == status and phase_safe(root, name, record["deadline"], status, xml))


def validate_controls(root: Path, name: str, deadline: float) -> dict[str, int]:
    inputs.require(phase_safe(root, name, deadline, xml=True))
    if name in ("strict", "remaining"):
        expected = extractor.STRICT_TEST_IDS if name == "strict" else extractor.REMAINING_TEST_IDS
        value = extractor.parse_xml(root / (name + ".xml"), expected)
        inputs.require(
            value["_ids"] == expected
            and value["selected"] == len(expected)
            and value["passed"] == len(expected)
            and value["skipped"] == value["failed"] == value["errors"] == 0
        )
        return {
            "selected": len(expected),
            "passed": len(expected),
            "skipped": 0,
            "failed": 0,
            "errors": 0,
        }
    inputs.require(name == "synthetic")
    raw = inputs.read_private(root, "synthetic.xml", 1024 * 1024, deadline)
    inputs.require(b"<!DOCTYPE" not in raw.upper() and b"<!ENTITY" not in raw.upper())
    document = ET.fromstring(raw)
    inputs.require(document.tag == "testsuites" and len(document.findall("testsuite")) == 1)
    expected_counts: dict[str, int] = {}
    tree = ast.parse(inputs.read_private(QUAL, "test_corpus_campaign.py", 256 * 1024, deadline))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            count = 1
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call):
                    raise ValueError("unsupported test decorator")
                inputs.require(
                    isinstance(decorator.func, ast.Attribute)
                    and decorator.func.attr == "parametrize"
                    and len(decorator.args) >= 2
                )
                values = decorator.args[1]
                inputs.require(isinstance(values, (ast.List, ast.Tuple)) and len(values.elts) > 0)
                if not isinstance(values, (ast.List, ast.Tuple)):
                    raise ValueError("unsupported parametrization")
                count *= len(values.elts)
            expected_counts[node.name] = count
    actual: dict[str, int] = {}
    identities: set[tuple[str, str]] = set()
    cases = document.findall("testsuite/testcase")
    for case in cases:
        classname, name = case.get("classname", ""), case.get("name", "")
        inputs.require(
            classname == ".github.qualification.offline-probe.test_corpus_campaign"
            and (classname, name) not in identities
        )
        inputs.require(
            not any(case.find(tag) is not None for tag in ("failure", "error", "skipped"))
        )
        base = name.split("[", 1)[0]
        inputs.require(base in expected_counts)
        identities.add((classname, name))
        actual[base] = actual.get(base, 0) + 1
    inputs.require(actual == expected_counts and len(cases) > 0)
    suite = document.find("testsuite")
    inputs.require(
        suite is not None
        and suite.get("tests") == str(len(cases))
        and suite.get("failures") == suite.get("errors") == suite.get("skipped") == "0"
    )
    return {"selected": len(cases), "passed": len(cases), "skipped": 0, "failed": 0, "errors": 0}


def _uv_python(*command: str) -> list[str]:
    return ["uv", "run", "--locked", "--no-sync", "python", *command]


def _python_call(expression: str) -> list[str]:
    return _uv_python(
        "-c",
        "import sys; sys.path.insert(0, '.github/qualification/offline-probe'); import corpus_campaign as c; "
        + expression,
    )


def hosted_controller() -> int:
    """Fixed hosted phases; this function must never be called by local tests."""
    preliminary: dict[str, Any] | None = None
    controls: dict[str, Any] | None = None
    try:
        root = private_root()
        record = identity_record()
        _phase("verify", 60, _python_call("c.qualify_runtime()"))
        selection = read_selection(record["deadline"])
        bindings = live_bindings()
        ini = str(root / "pytest.ini")
        base = [
            "uv",
            "run",
            "--locked",
            "--no-sync",
            "pytest",
            "--noconftest",
            "-p",
            "no:cacheprovider",
            "-c",
            ini,
            "-q",
            "--rootdir=.",
        ]
        _phase(
            "strict",
            60,
            base
            + [
                "--junitxml=" + str(root / "strict.xml"),
                ".github/qualification/offline-probe/test_probe.py::test_completed_worker_with_live_descendant_is_not_success",
            ],
            xml=True,
        )
        strict = validate_controls(root, "strict", record["deadline"])
        _phase(
            "remaining",
            180,
            base
            + [
                "--junitxml=" + str(root / "remaining.xml"),
                ".github/qualification/offline-probe/test_probe.py",
                "-k",
                "not test_completed_worker_with_live_descendant_is_not_success",
            ],
            xml=True,
        )
        remaining = validate_controls(root, "remaining", record["deadline"])
        _phase(
            "synthetic",
            180,
            base
            + [
                "--junitxml=" + str(root / "synthetic.xml"),
                ".github/qualification/offline-probe/test_corpus_campaign.py",
            ],
            xml=True,
        )
        synthetic = validate_controls(root, "synthetic", record["deadline"])
        controls = {"strict": strict, "remaining": remaining, "synthetic": synthetic}
        inputs.write_private(root, "controls.json", inputs.canonical(controls), record["deadline"])
        _phase("transfer", 300, _uv_python(str(QUAL / "corpus_campaign.py"), "transfer"))

        def run_one(index: int) -> dict[str, Any]:
            seconds = min(300, int(record["deadline"] - time.monotonic()))
            inputs.require(seconds >= 10)
            code = extractor.run_supervised(
                root / f"batch-{index}.capture",
                root / f"batch-{index}.result",
                seconds,
                _uv_python(str(QUAL / "corpus_campaign.py"), "batch", "--index", str(index)),
            )
            packet = inputs.decode_json(
                inputs.read_private(root, f"batch-{index}.json", 64 * 1024, record["deadline"]),
                64 * 1024,
            )
            supervisor = inputs.decode_json(
                inputs.read_private(root, f"batch-{index}.result", 4096, record["deadline"]), 4096
            )
            inputs.require(
                code == supervisor.get("child_exit_status") or not supervisor_safe(supervisor)
            )
            return {"packet": packet, "supervisor": supervisor}

        preliminary = run_all_batches(selection, bindings, run_one)
        if not report_child_permitted(preliminary):
            # No further child is started when continuation ownership is unsafe.
            preliminary["controls"] = controls
            _emit_report(interrupted_report(preliminary))
            return 1
        # Report is the only stage that maps Parser findings to CI failure.
        status = 0 if preliminary["outcome"] == "PASS" else 1
        _phase("report", 90, _uv_python(str(QUAL / "corpus_campaign.py"), "report"), status=status)
        raw = inputs.read_private(root, "report.capture", 192 * 1024, record["deadline"])
        expected = final_report()
        inputs.require(raw == b"CORPUS_RESULT " + inputs.canonical(expected))
        sys.stdout.buffer.write(raw)
        return status
    except Exception:
        if preliminary is not None:
            fallback = interrupted_report(preliminary)
            if controls is not None:
                fallback["controls"] = controls
            try:
                _emit_report(fallback)
                return 1
            except Exception:
                pass
        sys.stdout.write(
            'CORPUS_RESULT {"schema":1,"outcome":"INCOMPLETE","evidence":"unqualified"}\n'
        )
        return 1


def final_report() -> dict[str, Any]:
    record = identity_record()
    root = private_root()
    selection = read_selection(record["deadline"])
    bindings = live_bindings()
    saved = inputs.decode_json(
        inputs.read_private(root, "bindings.json", 32 * 1024, record["deadline"]), 32 * 1024
    )
    inputs.require(saved == bindings)
    results: list[dict[str, Any]] = []
    for index in range(8):
        path = root / f"batch-{index}.json"
        if not path.exists():
            break
        packet = inputs.decode_json(
            inputs.read_private(root, path.name, 64 * 1024, record["deadline"]), 64 * 1024
        )
        supervisor = inputs.decode_json(
            inputs.read_private(root, f"batch-{index}.result", 4096, record["deadline"]), 4096
        )
        results.append({"packet": packet, "supervisor": supervisor})
        if not next_batch_permitted(packet, supervisor, selection, bindings, index):
            break
    report = aggregate_batches(selection, results, bindings)
    controls = {
        name: validate_controls(root, name, record["deadline"])
        for name in ("strict", "remaining", "synthetic")
    }
    transfer = inputs.decode_json(
        inputs.read_private(root, "transfer.json", 4096, record["deadline"]), 4096
    )
    inputs.require(
        phase_safe(root, "transfer", record["deadline"])
        and transfer
        == {
            "schema": 1,
            "documents": 313,
            "provenance": 2,
            "requests": 317,
            "bytes": sum(row["size"] for row in selection["documents"] + selection["provenance"]),
            "selection_sha256": bindings["selection_sha256"],
        }
    )
    report["controls"] = controls
    inputs.require(len(inputs.canonical(report)) + len(b"CORPUS_RESULT ") <= 192 * 1024)
    inputs.require(
        len(inputs.canonical({key: value for key, value in report.items() if key != "results"}))
        <= 32 * 1024
    )
    return report


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    try:
        record = identity_record()
        root = private_root()
        selection = read_selection(record["deadline"])
        live_bindings()
        inputs.require(phase_safe(root, "sync", record["deadline"]))
        controls = {
            name: validate_controls(root, name, record["deadline"])
            for name in ("strict", "remaining", "synthetic")
        }
        saved_controls = inputs.decode_json(
            inputs.read_private(root, "controls.json", 4096, record["deadline"]), 4096
        )
        inputs.require(controls == saved_controls)
        if arguments == ["transfer"]:
            deadline = min(time.monotonic() + 270.0, record["deadline"] - 15.0)
            result = inputs.fetch_selection(selection, root / "corpus", deadline)
            inputs.write_private(
                root, "transfer.json", inputs.canonical(result), record["deadline"]
            )
            return 0
        if (
            len(arguments) == 3
            and arguments[:2] == ["batch", "--index"]
            and arguments[2] in tuple(str(index) for index in range(8))
        ):
            inputs.require(phase_safe(root, "transfer", record["deadline"]))
            transfer = inputs.decode_json(
                inputs.read_private(root, "transfer.json", 4096, record["deadline"]), 4096
            )
            inputs.require(
                transfer
                == {
                    "schema": 1,
                    "documents": 313,
                    "provenance": 2,
                    "requests": 317,
                    "bytes": sum(
                        row["size"] for row in selection["documents"] + selection["provenance"]
                    ),
                    "selection_sha256": record["identity"]["selection_sha256"],
                }
            )
            result = run_batch(
                selection,
                int(arguments[2]),
                root / "corpus",
                root,
                min(time.monotonic() + 290.0, record["deadline"]),
            )
            return 0 if result["complete"] else 1
        if arguments == ["report"]:
            report = final_report()
            sys.stdout.buffer.write(b"CORPUS_RESULT " + inputs.canonical(report))
            return 0 if report["outcome"] == "PASS" else 1
        raise ValueError("unsupported corpus invocation")
    except Exception:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
