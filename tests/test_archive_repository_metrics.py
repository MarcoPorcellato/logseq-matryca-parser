from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from scripts.archive_repository_metrics import (
    archive_repository_metrics,
    empty_quarter_payload,
    migrate_legacy_history,
    quarter_file_path,
    quarter_key_from_date,
)


def test_quarter_key_from_date() -> None:
    assert quarter_key_from_date("2026-01-15") == "2026-Q1"
    assert quarter_key_from_date("2026-03-31") == "2026-Q1"
    assert quarter_key_from_date("2026-04-01") == "2026-Q2"
    assert quarter_key_from_date("2026-12-31") == "2026-Q4"


def test_migrate_legacy_history_splits_by_quarter(tmp_path: Path) -> None:
    metrics_dir = tmp_path / "metrics"
    metrics_dir.mkdir()
    legacy = {
        "views": {
            "2026-02-10": {"count": 1, "uniques": 1},
            "2026-05-20": {"count": 2, "uniques": 2},
        },
        "clones": {
            "2026-02-10": {"count": 3, "uniques": 1},
        },
        "referrers": {
            "2026-05-21": [{"referrer": "github.com", "count": 4, "uniques": 2}],
        },
        "popular_content": {},
        "releases": {},
    }
    (metrics_dir / "history.json").write_text(json.dumps(legacy), encoding="utf-8")

    written = migrate_legacy_history(metrics_dir)

    assert not (metrics_dir / "history.json").exists()
    assert quarter_file_path(metrics_dir, "2026-Q1") in written
    assert quarter_file_path(metrics_dir, "2026-Q2") in written

    q1 = json.loads(quarter_file_path(metrics_dir, "2026-Q1").read_text(encoding="utf-8"))
    q2 = json.loads(quarter_file_path(metrics_dir, "2026-Q2").read_text(encoding="utf-8"))
    assert q1["views"]["2026-02-10"]["count"] == 1
    assert q1["clones"]["2026-02-10"]["count"] == 3
    assert q2["views"]["2026-05-20"]["count"] == 2
    assert q2["referrers"]["2026-05-21"][0]["referrer"] == "github.com"

    index = json.loads((metrics_dir / "index.json").read_text(encoding="utf-8"))
    assert index["legacy_migrated"] is True
    assert index["quarters"] == ["2026-Q1", "2026-Q2"]


def test_archive_repository_metrics_routes_14_day_window_across_quarters(
    tmp_path: Path,
    monkeypatch,
) -> None:
    metrics_dir = tmp_path / "metrics"

    def fake_fetch(url: str, token: str):
        if url.endswith("/traffic/views"):
            return {
                "views": [
                    {"timestamp": "2026-03-30T00:00:00Z", "count": 1, "uniques": 1},
                    {"timestamp": "2026-04-02T00:00:00Z", "count": 2, "uniques": 2},
                ]
            }
        if url.endswith("/traffic/clones"):
            return {"clones": []}
        if url.endswith("/popular/referrers"):
            return [{"referrer": "example.com", "count": 1, "uniques": 1}]
        if url.endswith("/popular/paths"):
            return [{"path": "/README.md", "title": "README", "count": 1, "uniques": 1}]
        if url.endswith("/releases"):
            return [{"tag_name": "v1.0.0", "assets": [{"name": "wheel", "download_count": 5}]}]
        return None

    monkeypatch.setattr("scripts.archive_repository_metrics.fetch_api", fake_fetch)

    archive_repository_metrics(
        metrics_dir,
        "owner/repo",
        "token",
        now=dt.datetime(2026, 4, 2, tzinfo=dt.UTC),
    )

    q1 = json.loads(quarter_file_path(metrics_dir, "2026-Q1").read_text(encoding="utf-8"))
    q2 = json.loads(quarter_file_path(metrics_dir, "2026-Q2").read_text(encoding="utf-8"))
    assert q1["views"]["2026-03-30"]["count"] == 1
    assert q2["views"]["2026-04-02"]["count"] == 2
    assert q2["referrers"]["2026-04-02"][0]["referrer"] == "example.com"
    assert q2["releases"]["2026-04-02"][0]["tag"] == "v1.0.0"


def test_empty_quarter_payload_shape() -> None:
    payload = empty_quarter_payload("2026-Q3")
    assert payload["quarter"] == "2026-Q3"
    assert set(payload) == {"quarter", "views", "clones", "releases", "referrers", "popular_content"}
