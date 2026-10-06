"""Synthetic corpus contracts: no real corpus, network, workers or sleeps."""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.parse import quote

import pytest

HERE = Path(__file__).resolve().parent
COMMIT = "08f855f24d66e4509b7ea808554c13b4649e6ee1"
TREE = "3309b25a2a603036a1a56b51d6e38d206c8106a6"
PAYLOAD = b"- Synthetic fixture\n"


def module(name: str) -> Any:
    path = HERE / f"{name}.py"
    assert path.is_file(), f"missing approved corpus helper: {name}"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec is not None and spec.loader is not None
        loaded = importlib.util.module_from_spec(spec)
        sys.modules[name] = loaded
        spec.loader.exec_module(loaded)
    return sys.modules[name]


def synthetic_manifest() -> dict[str, Any]:
    names = [f"pages/Page{i:03}.md" for i in range(311)]
    names += ["pages/Literal%3F.md", "journals/Second%3F.md", "README.md", "LICENSE.md"]
    return {
        "source": {"repository": "logseq/docs", "commit": COMMIT, "tree": TREE},
        "private_runtime_field": "must-not-project",
        "files": [
            {
                "source_path": name,
                "destination": ("corpus/" + name if "/" in name else "provenance/" + name),
                "size": len(PAYLOAD),
                "sha256": hashlib.sha256(PAYLOAD).hexdigest(),
                "git_blob": hashlib.sha1(
                    b"blob " + str(len(PAYLOAD)).encode() + b"\0" + PAYLOAD
                ).hexdigest(),
            }
            for name in names
        ],
    }


def selection() -> dict[str, Any]:
    return module("corpus_inputs").project_selection(synthetic_manifest())


def fake_transport(monkeypatch: pytest.MonkeyPatch, selected: dict[str, Any]) -> list[str]:
    calls: list[str] = []
    responses: dict[str, bytes] = {
        f"https://api.github.com/repos/logseq/docs/git/commits/{COMMIT}": json.dumps(
            {"sha": COMMIT, "tree": {"sha": TREE}}
        ).encode(),
        f"https://api.github.com/repos/logseq/docs/git/trees/{TREE}?recursive=1": json.dumps(
            {
                "sha": TREE,
                "truncated": False,
                "tree": [
                    {
                        "path": row["source_path"],
                        "type": "blob",
                        "mode": "100644",
                        "sha": row["git_blob"],
                        "size": row["size"],
                    }
                    for row in selected["documents"] + selected["provenance"]
                ],
            }
        ).encode(),
    }
    for row in selected["documents"] + selected["provenance"]:
        path = "/".join(quote(p, safe="") for p in row["source_path"].split("/"))
        responses[f"https://raw.githubusercontent.com/logseq/docs/{COMMIT}/{path}"] = PAYLOAD

    def get(url: str, deadline: float) -> bytes:
        assert deadline == 270.0
        calls.append(url)
        return responses[url]

    helper = module("corpus_inputs")
    monkeypatch.setattr(helper, "_get", get)
    monkeypatch.setattr(helper.time, "monotonic", lambda: 0.0)
    return calls


def test_projection_preserves_313_ordinals_and_only_public_schema() -> None:
    result = selection()
    assert set(result) == {"schema", "source", "documents", "provenance"}
    assert result["schema"] == 1
    assert [row["ordinal"] for row in result["documents"]] == list(range(313))
    assert len(result["provenance"]) == 2
    assert set(result["documents"][0]) == {"ordinal", "source_path", "git_blob", "sha256", "size"}
    assert result["documents"][0]["source_path"] == "journals/Second%3F.md"
    assert "must-not-project" not in json.dumps(result)


@pytest.mark.parametrize("mutation", ["missing", "extra", "duplicate", "destination", "revision"])
def test_projection_rejects_changed_selection(mutation: str) -> None:
    manifest = synthetic_manifest()
    if mutation == "missing":
        manifest["files"].pop(0)
    elif mutation == "extra":
        manifest["files"].append(
            {
                **manifest["files"][0],
                "source_path": "pages/Extra.md",
                "destination": "corpus/pages/Extra.md",
            }
        )
    elif mutation == "duplicate":
        manifest["files"][1] = copy.deepcopy(manifest["files"][0])
    elif mutation == "destination":
        manifest["files"][0]["destination"] = "corpus/pages/Other.md"
    else:
        manifest["source"]["commit"] = "0" * 40
    with pytest.raises(ValueError):
        module("corpus_inputs").project_selection(manifest)


@pytest.mark.parametrize(
    "path",
    [
        "/absolute.md",
        "pages/../secret.md",
        "pages/./Page.md",
        "pages//Page.md",
        "pages/Bad\n.md",
        "pages/Bad\\.md",
    ],
)
def test_selection_rejects_unsafe_paths(path: str) -> None:
    result = selection()
    result["documents"][0]["source_path"] = path
    with pytest.raises(ValueError):
        module("corpus_inputs").validate_selection(result)


@pytest.mark.parametrize(
    "field,value",
    [
        ("size", True),
        ("size", -1),
        ("ordinal", True),
        ("sha256", "x"),
        ("git_blob", "0" * 39),
        ("unexpected", "private"),
    ],
)
def test_selection_rejects_bad_public_row_schema(field: str, value: Any) -> None:
    result = selection()
    result["documents"][0][field] = value
    with pytest.raises(ValueError):
        module("corpus_inputs").validate_selection(result)


def test_transfer_uses_317_fixed_requests_and_literal_percent_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    selected = selection()
    calls = fake_transport(monkeypatch, selected)
    destination = tmp_path / "fresh"
    result = module("corpus_inputs").fetch_selection(selected, destination, 270.0)
    assert result["documents"] == 313 and result["provenance"] == 2
    assert result["requests"] == len(calls) == 317
    assert f"https://raw.githubusercontent.com/logseq/docs/{COMMIT}/pages/Literal%253F.md" in calls
    assert (destination / "pages/Literal%3F.md").read_bytes() == PAYLOAD
    assert (destination.stat().st_mode & 0o777) == 0o700
    assert ((destination / "pages/Literal%3F.md").stat().st_mode & 0o777) == 0o600


@pytest.mark.parametrize("problem", ["size", "blob", "sha", "utf8", "symlink", "directory"])
def test_verified_read_rejects_substitution_or_non_regular_input(
    tmp_path: Path, problem: str
) -> None:
    helper = module("corpus_inputs")
    row = selection()["documents"][0]
    file = tmp_path / row["source_path"]
    file.parent.mkdir()
    if problem == "symlink":
        target = tmp_path / "target"
        target.write_bytes(PAYLOAD)
        file.symlink_to(target)
    elif problem == "directory":
        file.mkdir()
    else:
        data = PAYLOAD if problem != "utf8" else b"\xff" * len(PAYLOAD)
        file.write_bytes(data)
        if problem == "size":
            row["size"] += 1
        elif problem == "blob":
            row["git_blob"] = "0" * 40
        elif problem == "sha":
            row["sha256"] = "0" * 64
        else:
            row["sha256"] = hashlib.sha256(data).hexdigest()
            row["git_blob"] = hashlib.sha1(
                b"blob " + str(len(data)).encode() + b"\0" + data
            ).hexdigest()
    with pytest.raises((ValueError, OSError)):
        helper.read_verified_file(tmp_path, row, 270.0)


def test_transfer_does_not_reuse_an_existing_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    selected = selection()
    calls = fake_transport(monkeypatch, selected)
    with pytest.raises((ValueError, FileExistsError)):
        module("corpus_inputs").fetch_selection(selected, tmp_path, 270.0)
    assert not calls


def synthetic_bindings() -> dict[str, Any]:
    return {
        "repository": "MarcoPorcellato/logseq-matryca-parser",
        "event": "workflow_dispatch",
        "ref": "refs/heads/ci/fixture",
        "commit": "a" * 40,
        "workflow_sha256": "b" * 64,
        "selection_sha256": hashlib.sha256(
            module("corpus_inputs").canonical(selection())
        ).hexdigest(),
        "source_aggregate_sha256": "c" * 64,
        "parser_source_aggregate_sha256": "d" * 64,
        "run_id": 123,
        "run_attempt": 1,
        "runtime": {
            "version": "3.12.13",
            "assertions": True,
            "binary_sha256": "e" * 64,
            "packages": [{"name": "pytest", "version": "9.0.3"}],
        },
    }


SAFE_SUPERVISOR = {
    "child_exit_status": 0,
    "reason": "complete",
    "leader_reaped": True,
    "cleanup_confirmed": True,
    "live_descendant_after_normal_exit": False,
    "stdout_bytes": 0,
    "xml_bytes": 0,
    "xml_drained": None,
}


def campaign_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, first: dict[str, Any] | None = None
) -> tuple[Any, list[int], Path, dict[str, Any]]:
    campaign = module("corpus_campaign")
    selected = selection()
    corpus = tmp_path / "synthetic"
    corpus.mkdir()
    for row in selected["documents"]:
        path = corpus / row["source_path"]
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(PAYLOAD)
    calls: list[int] = []
    bindings = synthetic_bindings()
    monkeypatch.setattr(campaign, "live_bindings", lambda: copy.deepcopy(bindings))
    monkeypatch.setattr(campaign, "_stage", lambda name, operation, **kwargs: operation())
    monkeypatch.setattr(campaign.time, "monotonic", lambda: 0.0)

    def worker(
        payload: bytes, digest: str, title: str, *, timeout: float, deadline: float
    ) -> dict[str, Any]:
        assert payload == PAYLOAD and digest == hashlib.sha256(PAYLOAD).hexdigest()
        assert title and timeout == 3.0 and deadline == 285.0
        calls.append(len(calls))
        if first is not None and len(calls) == 1:
            return copy.deepcopy(first)
        return {
            "classification": "parsed_invariants_pass",
            "root_count": 1,
            "node_count": 1,
            "invariant_result": "pass",
            "cleanup_confirmed": True,
            "return_code": 0,
        }

    monkeypatch.setattr(campaign, "_worker", worker)
    return campaign, calls, corpus, bindings


def test_fixed_ranges_cover_last_and_both_edges() -> None:
    campaign = module("corpus_campaign")
    assert campaign.batch_ranges(313) == (
        (0, 40),
        (40, 79),
        (79, 118),
        (118, 157),
        (157, 196),
        (196, 235),
        (235, 274),
        (274, 313),
    )
    for count in (312, 314, True):
        with pytest.raises(ValueError):
            campaign.batch_ranges(count)


def test_all_313_receive_one_result_and_complete_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign, calls, corpus, bindings = campaign_fixture(tmp_path, monkeypatch)
    selected = selection()
    batches = [
        {
            "packet": campaign.run_batch(selected, i, corpus, tmp_path, 290.0),
            "supervisor": dict(SAFE_SUPERVISOR),
        }
        for i in range(8)
    ]
    result = campaign.aggregate_batches(selected, batches, bindings)
    assert len(calls) == 313 and result["outcome"] == "PASS"
    assert result["coverage"] == {
        "selected": 313,
        "attempted": 313,
        "terminal": 313,
        "excluded": 0,
        "skipped": 0,
        "duplicates": 0,
        "unattempted": [],
        "complete": True,
    }
    assert [row["ordinal"] for row in result["results"]] == list(range(313))
    assert result["results"][312]["classification"] == "parsed_invariants_pass"
    assert len(module("corpus_inputs").canonical(result)) <= 192 * 1024


@pytest.mark.parametrize(
    "classification,outcome",
    [
        ("expected_domain_rejection", "FAIL"),
        ("unexpected_exception", "FAIL"),
        ("raw_content_mismatch", "FAIL"),
        ("tree_invariants", "FAIL"),
        ("timeout", "INCOMPLETE"),
    ],
)
def test_early_parser_finding_does_not_drop_later_documents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, classification: str, outcome: str
) -> None:
    first: dict[str, Any] = {
        "classification": classification,
        "cleanup_confirmed": True,
        "return_code": 0,
    }
    if classification in ("expected_domain_rejection", "unexpected_exception"):
        first["exception_type"] = "ValueError"
    campaign, calls, corpus, bindings = campaign_fixture(tmp_path, monkeypatch, first)
    selected = selection()
    batches = [
        {
            "packet": campaign.run_batch(selected, i, corpus, tmp_path, 290.0),
            "supervisor": dict(SAFE_SUPERVISOR),
        }
        for i in range(8)
    ]
    result = campaign.aggregate_batches(selected, batches, bindings)
    assert len(calls) == 313 and result["coverage"]["complete"] is True
    assert result["outcome"] == outcome and result["outcomes"][classification] == 1


@pytest.mark.parametrize(
    "first",
    [
        {"classification": "timeout", "cleanup_confirmed": True},
        {"classification": "worker_start_failure", "cleanup_confirmed": True},
        {"classification": "cleanup_unconfirmed", "cleanup_confirmed": False, "return_code": 0},
        {"classification": "binding_failure", "cleanup_confirmed": True, "return_code": 0},
        {"classification": "output_overflow", "cleanup_confirmed": True, "return_code": 0},
        {"classification": "invalid_child_result", "cleanup_confirmed": True, "return_code": 0},
        {"classification": "unknown", "cleanup_confirmed": True, "return_code": 0},
    ],
)
def test_unsafe_or_unlaunched_worker_stops_with_explicit_unattempted_ordinals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, first: dict[str, Any]
) -> None:
    campaign, calls, corpus, bindings = campaign_fixture(tmp_path, monkeypatch, first)
    selected = selection()
    packet = campaign.run_batch(selected, 0, corpus, tmp_path, 290.0)
    result = campaign.aggregate_batches(
        selected, [{"packet": packet, "supervisor": dict(SAFE_SUPERVISOR)}], bindings
    )
    assert len(calls) == 1 and packet["complete"] is False
    assert result["outcome"] == "INCOMPLETE" and result["coverage"]["complete"] is False
    assert 1 in result["coverage"]["unattempted"] and 312 in result["coverage"]["unattempted"]


def test_prelaunch_timeout_does_not_count_as_attempt() -> None:
    assert not module("corpus_campaign").worker_launch_confirmed(
        {"classification": "timeout", "cleanup_confirmed": True}
    )


def test_finalized_worker_launch_is_confirmed() -> None:
    campaign = module("corpus_campaign")
    assert campaign.worker_launch_confirmed(
        {"classification": "timeout", "cleanup_confirmed": True, "return_code": -9}
    )
    for value in (True, None, "0", -129, 256):
        assert not campaign.worker_launch_confirmed({"return_code": value})


@pytest.mark.parametrize(
    "mutation", ["ordinal", "hash", "bool_count", "exception", "binding", "missing", "duplicate"]
)
def test_aggregate_rejects_substituted_or_forged_batch_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    campaign, _, corpus, bindings = campaign_fixture(tmp_path, monkeypatch)
    selected = selection()
    packet = campaign.run_batch(selected, 0, corpus, tmp_path, 290.0)
    if mutation == "ordinal":
        packet["rows"][0]["ordinal"] = 312
    elif mutation == "hash":
        packet["rows"][0]["input_sha256"] = "0" * 64
    elif mutation == "bool_count":
        packet["rows"][0]["node_count"] = True
    elif mutation == "exception":
        packet["rows"][0]["exception_type"] = "unsafe\nmessage"
    elif mutation == "binding":
        packet["bindings"]["runtime"]["binary_sha256"] = "0" * 64
    elif mutation == "missing":
        packet["rows"].pop()
    else:
        packet["rows"][1] = copy.deepcopy(packet["rows"][0])
    with pytest.raises(ValueError):
        campaign.aggregate_batches(
            selected, [{"packet": packet, "supervisor": dict(SAFE_SUPERVISOR)}], bindings
        )


@pytest.mark.parametrize(
    "key,value",
    [
        ("reason", "timeout"),
        ("leader_reaped", False),
        ("cleanup_confirmed", False),
        ("live_descendant_after_normal_exit", True),
        ("stdout_bytes", 262145),
        ("child_exit_status", True),
    ],
)
def test_exit_zero_with_unsafe_supervisor_cannot_continue(key: str, value: Any) -> None:
    supervisor = {**SAFE_SUPERVISOR, key: value}
    assert not module("corpus_campaign").supervisor_safe(supervisor)


def test_deadline_exhaustion_launches_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign, calls, corpus, bindings = campaign_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(campaign.time, "monotonic", lambda: 274.0)
    selected = selection()
    packet = campaign.run_batch(selected, 0, corpus, tmp_path, 290.0)
    report = campaign.aggregate_batches(
        selected, [{"packet": packet, "supervisor": dict(SAFE_SUPERVISOR)}], bindings
    )
    assert not calls and report["coverage"]["attempted"] == 0
    assert report["coverage"]["unattempted"] == list(range(313))


def test_changed_runtime_after_batch_cannot_be_published(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign, _, corpus, bindings = campaign_fixture(tmp_path, monkeypatch)
    changed = {**bindings, "commit": "f" * 40}
    snapshots = iter([bindings, changed])
    monkeypatch.setattr(campaign, "live_bindings", lambda: next(snapshots))
    with pytest.raises(ValueError):
        campaign.run_batch(selection(), 0, corpus, tmp_path, 290.0)
    assert not (tmp_path / "batch-0.json").exists()


@pytest.mark.parametrize(
    "problem", ["commit", "tree", "truncated", "duplicate", "missing", "mode", "raw"]
)
def test_transport_rejects_remote_substitution_without_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, problem: str
) -> None:
    helper = module("corpus_inputs")
    selected = selection()
    calls = fake_transport(monkeypatch, selected)
    original = helper._get

    def changed(url: str, deadline: float) -> bytes:
        raw = original(url, deadline)
        if "api.github.com" in url:
            data = json.loads(raw)
            if "/commits/" in url and problem == "commit":
                data["sha"] = "0" * 40
            if "/trees/" in url:
                if problem == "tree":
                    data["sha"] = "0" * 40
                elif problem == "truncated":
                    data["truncated"] = True
                elif problem == "duplicate":
                    data["tree"].append(copy.deepcopy(data["tree"][0]))
                elif problem == "missing":
                    data["tree"].pop()
                elif problem == "mode":
                    data["tree"][0]["mode"] = "120000"
            return json.dumps(data).encode()
        return b"wrong" if problem == "raw" else raw

    monkeypatch.setattr(helper, "_get", changed)
    with pytest.raises(ValueError):
        helper.fetch_selection(selected, tmp_path / "fresh", 270.0)
    assert len(calls) <= 3 and len(set(calls)) == len(calls)


def identity_environment() -> dict[str, str]:
    return {
        "GITHUB_REPOSITORY": "MarcoPorcellato/logseq-matryca-parser",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "CORPUS_ENABLED": "true",
        "QUALIFICATION_ENABLED": "false",
        "EXPECTED_REF": "refs/heads/ci/fixture",
        "GITHUB_REF": "refs/heads/ci/fixture",
        "EXPECTED_COMMIT": "a" * 40,
        "GITHUB_SHA": "a" * 40,
        "EXPECTED_WORKFLOW_SHA256": "b" * 64,
        "EXPECTED_SELECTION_SHA256": "c" * 64,
        "GITHUB_RUN_ID": "123",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_WORKFLOW_REF": "MarcoPorcellato/logseq-matryca-parser/.github/workflows/parser-adversarial.yml@refs/heads/ci/fixture",
    }


def test_identity_binds_dispatch_ref_commit_workflow_and_selection() -> None:
    campaign = module("corpus_campaign")
    assert hasattr(campaign, "expected_identity"), "missing hosted identity gate"
    result = campaign.expected_identity(identity_environment())
    assert result["ref"] == "refs/heads/ci/fixture" and result["run_id"] == 123
    assert result["selection_sha256"] == "c" * 64


@pytest.mark.parametrize(
    "key,value",
    [
        ("GITHUB_REPOSITORY", "other/repo"),
        ("GITHUB_EVENT_NAME", "push"),
        ("CORPUS_ENABLED", "false"),
        ("QUALIFICATION_ENABLED", "true"),
        ("GITHUB_REF", "refs/heads/main"),
        ("GITHUB_SHA", "f" * 40),
        ("GITHUB_WORKFLOW_REF", "wrong"),
        ("GITHUB_RUN_ATTEMPT", "2"),
        ("EXPECTED_SELECTION_SHA256", ""),
        ("GITHUB_RUN_ID", "0"),
    ],
)
def test_identity_rejects_wrong_or_combined_mode_binding(key: str, value: str) -> None:
    campaign = module("corpus_campaign")
    assert hasattr(campaign, "expected_identity"), "missing hosted identity gate"
    env = {**identity_environment(), key: value}
    with pytest.raises(ValueError):
        campaign.expected_identity(env)


@pytest.mark.parametrize("unsafe", [False, True])
def test_wrapper_continuation_checks_packet_and_supervisor_before_next_batch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, unsafe: bool
) -> None:
    campaign, _, corpus, bindings = campaign_fixture(
        tmp_path,
        monkeypatch,
        {"classification": "raw_content_mismatch", "cleanup_confirmed": True, "return_code": 0},
    )
    assert hasattr(campaign, "run_all_batches"), "missing wrapper continuation gate"
    visited: list[int] = []

    def run_one(index: int) -> dict[str, Any]:
        visited.append(index)
        packet = campaign.run_batch(selection(), index, corpus, tmp_path, 290.0)
        supervisor = dict(SAFE_SUPERVISOR)
        if unsafe:
            supervisor["cleanup_confirmed"] = False
        return {"packet": packet, "supervisor": supervisor}

    report = campaign.run_all_batches(selection(), bindings, run_one)
    assert visited == ([0] if unsafe else list(range(8)))
    assert report["outcome"] == ("INCOMPLETE" if unsafe else "FAIL")


def test_corpus_workflow_opt_in_does_not_disable_existing_modes() -> None:
    workflow = (HERE.parents[2] / ".github/workflows/parser-adversarial.yml").read_text()
    assert "official-corpus-qualification:" in workflow, "missing manual corpus job"
    reader = module("corpus_campaign")
    assert hasattr(reader, "mode_jobs"), "missing mode selection contract"
    assert reader.mode_jobs("schedule", False, False) == (True, False, False)
    assert reader.mode_jobs("workflow_dispatch", False, False) == (True, False, False)
    assert reader.mode_jobs("workflow_dispatch", True, False) == (False, True, False)
    assert reader.mode_jobs("workflow_dispatch", False, True) == (False, False, True)
    with pytest.raises(ValueError):
        reader.mode_jobs("workflow_dispatch", True, True)


@pytest.mark.parametrize(
    "case", ["valid", "version", "package", "development", "boolean", "duplicate", "missing"]
)
def test_uv_version_proof_rejects_unqualified_builds(case: str) -> None:
    value: dict[str, Any] = {"package_name": "uv", "version": "0.11.7", "commit_info": None}
    if case == "version":
        value["version"] = "0.12.16"
    elif case == "package":
        value["package_name"] = "other"
    elif case == "development":
        value["commit_info"] = {"commits_since_last_tag": 1}
    elif case == "boolean":
        value["commit_info"] = {"commits_since_last_tag": False}
    elif case == "missing":
        value.pop("commit_info")
    raw = json.dumps(value).encode()
    if case == "duplicate":
        raw = b'{"package_name":"uv","version":"wrong","version":"0.11.7"}'
    campaign = module("corpus_campaign")
    if case == "valid":
        campaign.validate_uv_version(raw)
    else:
        with pytest.raises(ValueError):
            campaign.validate_uv_version(raw)


@pytest.mark.parametrize("problem", ["none", "prefix", "origin", "version", "extra", "duplicate"])
def test_runtime_proof_checks_origins_and_every_installed_lock_version(
    monkeypatch: pytest.MonkeyPatch, problem: str
) -> None:
    campaign = module("corpus_campaign")
    monkeypatch.setattr(campaign.sys, "version_info", (3, 12, 13))
    monkeypatch.setattr(
        campaign.sys, "prefix", str(campaign.ROOT / ("wrong" if problem == "prefix" else ".venv"))
    )
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    monkeypatch.setenv("PYTEST_ADDOPTS", "")
    monkeypatch.delenv("PYTEST_PLUGINS", raising=False)

    def find_spec(name: str) -> Any:
        if name in ("probe", "extract_results", "corpus_inputs", "corpus_campaign"):
            path = campaign.QUAL / (name + ".py")
        elif name in ("pytest", "_pytest"):
            path = campaign.ROOT / ".venv/lib/python3.12/site-packages" / name / "__init__.py"
        elif name == "logseq_matryca_parser":
            path = campaign.ROOT / "src/logseq_matryca_parser/__init__.py"
        elif name == "tests.parser_assurance.invariants":
            path = campaign.ROOT / "tests/parser_assurance/invariants.py"
        else:
            path = campaign.ROOT / name.replace(".", "/") / "__init__.py"
        if problem == "origin" and name == "probe":
            path = campaign.ROOT / "other.py"
        return SimpleNamespace(origin=str(path))

    monkeypatch.setattr(campaign.importlib.util, "find_spec", find_spec)
    distributions = [SimpleNamespace(metadata={"Name": "pytest"}, version="9.0.3")]
    if problem == "version":
        distributions[0].version = "0.0.1"
    elif problem == "extra":
        distributions.append(SimpleNamespace(metadata={"Name": "undeclared"}, version="1.0"))
    elif problem == "duplicate":
        distributions.append(SimpleNamespace(metadata={"Name": "PYTEST"}, version="9.0.3"))
    monkeypatch.setattr(campaign.importlib.metadata, "distributions", lambda: distributions)
    monkeypatch.setattr(campaign, "extractor", SimpleNamespace(sha=lambda path: "e" * 64))
    if problem == "none":
        result = campaign.runtime_facts()
        assert result == synthetic_bindings()["runtime"]
    else:
        with pytest.raises(ValueError):
            campaign.runtime_facts()


@pytest.mark.parametrize(
    "problem",
    ["none", "expression", "skip", "duplicate", "missing", "count", "class", "entity", "decorator"],
)
def test_synthetic_control_xml_proves_bound_test_selection_not_only_exit_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, problem: str
) -> None:
    campaign = module("corpus_campaign")
    source = (
        "def test_plain(): pass\n"
        "@pytest.mark.parametrize('value', [0, 1])\n"
        "def test_parameter(value): pass\n"
    )
    if problem == "decorator":
        source = "@pytest.mark.skip\ndef test_plain(): pass\n"
    elif problem == "expression":
        source = source.replace("[0, 1]", "['x' * 64, {'value': 1}]")
    (tmp_path / "test_corpus_campaign.py").write_text(source)
    monkeypatch.setattr(campaign, "QUAL", tmp_path)
    monkeypatch.setattr(campaign.time, "monotonic", lambda: 0.0)
    (tmp_path / "synthetic.result").write_text(
        json.dumps({**SAFE_SUPERVISOR, "xml_bytes": 100, "xml_drained": True})
    )
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite", tests="3", failures="0", errors="0", skipped="0")
    names = ["test_plain", "test_parameter[0]", "test_parameter[1]"]
    if problem == "missing":
        names.pop()
        suite.set("tests", "2")
    elif problem == "duplicate":
        names[-1] = names[1]
    elif problem == "count":
        suite.set("tests", "4")
    for name in names:
        case = ET.SubElement(
            suite,
            "testcase",
            classname=".github.qualification.offline-probe.test_corpus_campaign",
            name=name,
        )
        if problem == "class":
            case.set("classname", "substituted")
        if problem == "skip":
            ET.SubElement(case, "skipped")
    raw = ET.tostring(root)
    if problem == "entity":
        raw = b'<!DOCTYPE x [<!ENTITY x "hidden">]>' + raw
    (tmp_path / "synthetic.xml").write_bytes(raw)
    if problem in ("none", "expression"):
        assert campaign.validate_controls(tmp_path, "synthetic", 20.0) == {
            "selected": 3,
            "passed": 3,
            "skipped": 0,
            "failed": 0,
            "errors": 0,
        }
    else:
        with pytest.raises(ValueError):
            campaign.validate_controls(tmp_path, "synthetic", 20.0)


@pytest.mark.parametrize("control,count", [("strict", 1), ("remaining", 91)])
def test_frozen_control_xml_is_only_synthetically_validated_locally(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, control: str, count: int
) -> None:
    campaign = module("corpus_campaign")
    expected = (
        campaign.extractor.STRICT_TEST_IDS
        if control == "strict"
        else campaign.extractor.REMAINING_TEST_IDS
    )
    monkeypatch.setattr(campaign.time, "monotonic", lambda: 0.0)
    (tmp_path / (control + ".result")).write_text(
        json.dumps({**SAFE_SUPERVISOR, "xml_bytes": 100, "xml_drained": True})
    )
    root = ET.Element("testsuites")
    suite = ET.SubElement(
        root, "testsuite", tests=str(count), failures="0", errors="0", skipped="0"
    )
    for classname, name in sorted(expected):
        ET.SubElement(suite, "testcase", classname=classname, name=name)
    (tmp_path / (control + ".xml")).write_bytes(ET.tostring(root))
    assert campaign.validate_controls(tmp_path, control, 20.0)["passed"] == count
    suite.remove(suite[0])
    suite.set("tests", str(count - 1))
    (tmp_path / (control + ".xml")).write_bytes(ET.tostring(root))
    with pytest.raises(ValueError):
        campaign.validate_controls(tmp_path, control, 20.0)


@pytest.mark.parametrize(
    "arguments",
    [
        [],
        ["transfer", "extra"],
        ["batch", "--index", "8"],
        ["batch", "--index", "01"],
        ["run"],
        ["report", "extra"],
    ],
)
def test_cli_rejects_unapproved_invocations_without_transport_or_worker(
    monkeypatch: pytest.MonkeyPatch, arguments: list[str]
) -> None:
    campaign = module("corpus_campaign")
    calls: list[str] = []
    monkeypatch.setattr(campaign, "identity_record", lambda: {"deadline": 30.0})
    monkeypatch.setattr(campaign, "private_root", lambda: Path("/synthetic"))
    monkeypatch.setattr(campaign, "read_selection", lambda deadline: selection())
    monkeypatch.setattr(campaign, "live_bindings", synthetic_bindings)
    monkeypatch.setattr(campaign, "phase_safe", lambda *args: True)
    monkeypatch.setattr(campaign, "validate_controls", lambda *args: {})
    monkeypatch.setattr(
        campaign.inputs,
        "read_private",
        lambda *args: b'{"strict":{},"remaining":{},"synthetic":{}}',
    )
    monkeypatch.setattr(campaign.inputs, "fetch_selection", lambda *args: calls.append("transfer"))
    monkeypatch.setattr(campaign, "run_batch", lambda *args: calls.append("batch"))
    monkeypatch.setattr(campaign, "final_report", lambda: calls.append("report"))
    assert campaign.main(arguments) == 1 and calls == []


def _condition(expression: str, event: str, synthetic: bool, corpus: bool) -> bool:
    for variable, value in (
        ("github.event_name", event),
        ("inputs.hosted_cleanup_qualification", synthetic),
        ("inputs.official_corpus_probe", corpus),
    ):
        expression = expression.replace(variable, repr(value))
    expression = (
        re.sub(r"\btrue\b", "True", expression).replace("&&", " and ").replace("||", " or ")
    )

    def read(node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.BoolOp):
            values = [bool(read(value)) for value in node.values]
            return all(values) if isinstance(node.op, ast.And) else any(values)
        assert isinstance(node, ast.Compare) and len(node.ops) == len(node.comparators) == 1
        left, right = read(node.left), read(node.comparators[0])
        assert isinstance(node.ops[0], (ast.Eq, ast.NotEq))
        return left == right if isinstance(node.ops[0], ast.Eq) else left != right

    return bool(read(ast.parse(expression, mode="eval").body))


@pytest.mark.parametrize(
    "event,synthetic,corpus,expected",
    [
        ("schedule", False, False, (True, False, False)),
        ("workflow_dispatch", False, False, (True, False, False)),
        ("workflow_dispatch", True, False, (False, True, False)),
        ("workflow_dispatch", False, True, (False, False, True)),
        ("workflow_dispatch", True, True, (False, False, True)),
    ],
)
def test_actual_job_expressions_select_one_route_and_reject_combined_identity(
    event: str, synthetic: bool, corpus: bool, expected: tuple[bool, bool, bool]
) -> None:
    workflow = (HERE.parents[2] / ".github/workflows/parser-adversarial.yml").read_text()
    conditions = re.findall(r"^  [a-z-]+:\n(?:    #[^\n]*\n)*    if: (.+)$", workflow, re.MULTILINE)
    assert len(conditions) == 3
    assert tuple(_condition(value, event, synthetic, corpus) for value in conditions) == expected
    if synthetic and corpus:
        with pytest.raises(ValueError):
            module("corpus_campaign").expected_identity(
                identity_environment() | {"QUALIFICATION_ENABLED": "true"}
            )
    assert "pull_request:" not in workflow and "  push:" not in workflow


def test_corpus_launcher_keeps_uv_cache_and_python_downloads_private() -> None:
    script = (HERE / "run_corpus_campaign.sh").read_text()
    assert 'UV_CACHE_DIR="${private_dir}/uv-cache"' in script
    assert 'UV_PYTHON_INSTALL_DIR="${private_dir}/uv-python"' in script
    workflow = (
        (HERE.parents[2] / ".github/workflows/parser-adversarial.yml")
        .read_text()
        .split("  official-corpus-qualification:", 1)[1]
    )
    assert "enable-cache: false" in workflow
    assert "upload-artifact" not in workflow and "actions/cache" not in workflow


@pytest.mark.parametrize(
    "problem", ["none", "missing", "changed", "aggregate", "duplicate", "substitution"]
)
def test_source_map_binds_exact_union_without_self_reference(
    monkeypatch: pytest.MonkeyPatch, problem: str
) -> None:
    campaign = module("corpus_campaign")
    base = [{"path": f"src/contract_{index:02}.py", "sha256": "f" * 64} for index in range(36)]
    names = sorted({row["path"] for row in base} | campaign.NEW_FILES)
    assert len(names) == 43 and not any(
        name.endswith("corpus-source-manifest.json") for name in names
    )
    digest = hashlib.sha256(PAYLOAD).hexdigest()
    rows = [{"path": name, "sha256": digest} for name in names]
    aggregate = hashlib.sha256(
        b"".join(row["path"].encode() + b"\0" + row["sha256"].encode() + b"\n" for row in rows)
    ).hexdigest()
    value = {"files": rows, "source_aggregate_sha256": aggregate}
    if problem == "missing":
        rows.pop()
    elif problem == "changed":
        rows[0]["sha256"] = "a" * 64
    elif problem == "aggregate":
        value["source_aggregate_sha256"] = "a" * 64
    elif problem == "duplicate":
        rows[1] = copy.deepcopy(rows[0])
    elif problem == "substitution":
        rows[0]["path"] = "src/undeclared.py"
    monkeypatch.setattr(
        campaign, "extractor", SimpleNamespace(manifest_rows=lambda: (base, "f" * 64))
    )

    def read(root: Path, name: str, maximum: int, deadline: float) -> bytes:
        assert deadline == 20.0
        return (
            campaign.inputs.canonical(value) if name == "corpus-source-manifest.json" else PAYLOAD
        )

    monkeypatch.setattr(campaign.inputs, "read_private", read)
    if problem == "none":
        assert campaign.source_bindings(20.0) == ("f" * 64, aggregate)
    else:
        with pytest.raises(ValueError):
            campaign.source_bindings(20.0)


@pytest.mark.parametrize("operation", ["read", "write", "directory", "identity", "phase", "uv"])
def test_short_deadline_descriptor_operations_use_caller_owned_cutoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    helper = module("corpus_inputs")
    campaign = module("corpus_campaign")
    monkeypatch.setattr(helper.time, "monotonic", lambda: 0.0)
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested/input").write_bytes(PAYLOAD)
    if operation == "read":
        assert helper.read_private(tmp_path, "nested/input", 1024, 4.0) == PAYLOAD
    elif operation == "write":
        helper.write_private(tmp_path, "nested/output", PAYLOAD, 4.0)
        assert (tmp_path / "nested/output").read_bytes() == PAYLOAD
    elif operation == "directory":
        helper.fresh_directory(tmp_path / "new", 4.0)
        assert (tmp_path / "new").is_dir()
    elif operation == "identity":
        env = identity_environment()
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        monkeypatch.setattr(campaign, "private_root", lambda: tmp_path)
        record = {
            "identity": campaign.expected_identity(env),
            "parser_source_aggregate_sha256": "a" * 64,
            "source_aggregate_sha256": "b" * 64,
            "deadline": 100.0,
        }
        (tmp_path / "identity.json").write_text(json.dumps(record))
        assert campaign.identity_record() == record
    elif operation == "phase":
        (tmp_path / "identity.result").write_text(json.dumps(SAFE_SUPERVISOR))
        assert campaign.phase_safe(tmp_path, "identity", 10.0)
    else:
        raw = b'{"package_name":"uv","version":"0.11.7","commit_info":null}'
        (tmp_path / "install.capture").write_bytes(raw)
        campaign.validate_uv_version(helper.read_private(tmp_path, "install.capture", 16384, 4.0))


@pytest.mark.parametrize(
    "failure_index,problem", [(0, "exception"), (1, "exception"), (7, "packet"), (1, "entry")]
)
def test_interrupted_batch_evidence_retains_only_validated_prefix_and_all_ordinals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_index: int, problem: str
) -> None:
    campaign, _, corpus, bindings = campaign_fixture(
        tmp_path,
        monkeypatch,
        {"classification": "raw_content_mismatch", "cleanup_confirmed": True, "return_code": 0},
    )
    visited: list[int] = []

    def run_one(index: int) -> dict[str, Any]:
        visited.append(index)
        if index == failure_index:
            if problem == "exception":
                raise OSError("synthetic unavailable packet")
            return (
                {"packet": None, "supervisor": dict(SAFE_SUPERVISOR)} if problem == "packet" else {}
            )
        packet = campaign.run_batch(selection(), index, corpus, tmp_path, 290.0)
        return {"packet": packet, "supervisor": dict(SAFE_SUPERVISOR)}

    report = campaign.run_all_batches(selection(), bindings, run_one)
    count = campaign.RANGES[failure_index][0]
    assert visited == list(range(failure_index + 1))
    assert report["outcome"] == "INCOMPLETE"
    assert report["coverage"]["attempted"] == report["coverage"]["terminal"] == count
    assert report["coverage"]["unattempted"] == list(range(count, 313))
    assert len(report["results"]) == 313 and len(report["batches"]) == failure_index
    assert report["outcomes"].get("raw_content_mismatch", 0) == (1 if count else 0)
    assert campaign.report_child_permitted(report) is False


def test_reporting_failure_downgrades_complete_prefix_without_losing_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign, _, corpus, bindings = campaign_fixture(tmp_path, monkeypatch)
    report = campaign.run_all_batches(
        selection(),
        bindings,
        lambda index: {
            "packet": campaign.run_batch(selection(), index, corpus, tmp_path, 290.0),
            "supervisor": dict(SAFE_SUPERVISOR),
        },
    )
    assert campaign.report_child_permitted(report) is True
    interrupted = campaign.interrupted_report(report)
    assert report["outcome"] == "PASS" and interrupted["outcome"] == "INCOMPLETE"
    assert interrupted["coverage"]["complete"] is True
    assert (
        interrupted["coverage"]["attempted"] == 313 and interrupted["coverage"]["unattempted"] == []
    )
    assert interrupted["results"] == report["results"]
