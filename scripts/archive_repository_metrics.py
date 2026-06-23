#!/usr/bin/env python3
"""Archive GitHub repository traffic metrics into quarterly JSON files.

Each calendar quarter is stored as ``metrics/quarters/YYYY-QN.json`` so the
archive stays bounded and easy to ingest. A legacy monolithic ``history.json``
is split once on first run and then removed.

Usage (CI):
    GITHUB_TOKEN=... REPO_SLUG=owner/repo python scripts/archive_repository_metrics.py
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_METRICS_DIR = _REPO_ROOT / "metrics"
_QUARTERS_DIR_NAME = "quarters"
_LEGACY_HISTORY_NAME = "history.json"
_INDEX_NAME = "index.json"
_SCHEMA_VERSION = 1
_METRIC_SECTIONS = ("views", "clones", "releases", "referrers", "popular_content")

MetricsPayload = dict[str, Any]


def quarter_key_from_date(date_str: str) -> str:
    """Return calendar quarter id ``YYYY-QN`` for an ISO date ``YYYY-MM-DD``."""
    year_str, month_str, _day = date_str.split("-", 2)
    quarter = (int(month_str) - 1) // 3 + 1
    return f"{year_str}-Q{quarter}"


def empty_quarter_payload(quarter: str) -> MetricsPayload:
    return {"quarter": quarter, **{section: {} for section in _METRIC_SECTIONS}}


def quarters_dir(metrics_dir: Path) -> Path:
    return metrics_dir / _QUARTERS_DIR_NAME


def quarter_file_path(metrics_dir: Path, quarter: str) -> Path:
    return quarters_dir(metrics_dir) / f"{quarter}.json"


def index_path(metrics_dir: Path) -> Path:
    return metrics_dir / _INDEX_NAME


def legacy_history_path(metrics_dir: Path) -> Path:
    return metrics_dir / _LEGACY_HISTORY_NAME


def _read_json(path: Path) -> MetricsPayload | None:
    if not path.is_file() or path.stat().st_size == 0:
        return None
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return None
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Ignoring invalid JSON at %s", path)
        return None
    return loaded if isinstance(loaded, dict) else None


def _write_json(path: Path, payload: MetricsPayload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def load_quarter_payload(metrics_dir: Path, quarter: str) -> MetricsPayload:
    path = quarter_file_path(metrics_dir, quarter)
    loaded = _read_json(path)
    if loaded is None:
        return empty_quarter_payload(quarter)
    loaded.setdefault("quarter", quarter)
    for section in _METRIC_SECTIONS:
        loaded.setdefault(section, {})
    return loaded


def save_quarter_payload(metrics_dir: Path, payload: MetricsPayload) -> Path:
    quarter = str(payload["quarter"])
    path = quarter_file_path(metrics_dir, quarter)
    _write_json(path, payload)
    return path


def list_quarter_files(metrics_dir: Path) -> list[str]:
    root = quarters_dir(metrics_dir)
    if not root.is_dir():
        return []
    return sorted(path.stem for path in root.glob("*.json"))


def load_index(metrics_dir: Path) -> MetricsPayload:
    loaded = _read_json(index_path(metrics_dir))
    if loaded is None:
        return {
            "schema_version": _SCHEMA_VERSION,
            "partition": "calendar_quarter",
            "quarters": [],
            "legacy_migrated": False,
        }
    loaded.setdefault("schema_version", _SCHEMA_VERSION)
    loaded.setdefault("partition", "calendar_quarter")
    loaded.setdefault("quarters", [])
    loaded.setdefault("legacy_migrated", False)
    return loaded


def write_index(metrics_dir: Path, *, quarters: list[str], legacy_migrated: bool) -> Path:
    payload: MetricsPayload = {
        "schema_version": _SCHEMA_VERSION,
        "partition": "calendar_quarter",
        "quarters": sorted(set(quarters)),
        "legacy_migrated": legacy_migrated,
        "updated_at": dt.datetime.now(dt.UTC).strftime("%Y-%m-%d"),
    }
    path = index_path(metrics_dir)
    _write_json(path, payload)
    return path


def _route_date_section(
    store: dict[str, MetricsPayload],
    metrics_dir: Path,
    section: str,
    section_data: Any,
) -> None:
    if not isinstance(section_data, dict):
        return
    for day, value in section_data.items():
        if not isinstance(day, str) or len(day) < 10:
            continue
        quarter = quarter_key_from_date(day[:10])
        payload = store.setdefault(quarter, load_quarter_payload(metrics_dir, quarter))
        payload[section][day[:10]] = value


def migrate_legacy_history(metrics_dir: Path) -> list[Path]:
    """Split ``history.json`` into quarterly files. Returns written paths."""
    legacy_path = legacy_history_path(metrics_dir)
    index = load_index(metrics_dir)
    if index.get("legacy_migrated"):
        return []
    if not legacy_path.is_file():
        index["legacy_migrated"] = True
        write_index(
            metrics_dir,
            quarters=list_quarter_files(metrics_dir),
            legacy_migrated=True,
        )
        return []

    legacy = _read_json(legacy_path)
    if legacy is None:
        legacy_path.unlink(missing_ok=True)
        write_index(
            metrics_dir,
            quarters=list_quarter_files(metrics_dir),
            legacy_migrated=True,
        )
        return []

    in_memory: dict[str, MetricsPayload] = {}
    for section in _METRIC_SECTIONS:
        _route_date_section(in_memory, metrics_dir, section, legacy.get(section, {}))

    written: list[Path] = []
    for quarter, payload in sorted(in_memory.items()):
        written.append(save_quarter_payload(metrics_dir, payload))

    legacy_path.unlink()
    all_quarters = sorted(set(list_quarter_files(metrics_dir)))
    write_index(metrics_dir, quarters=all_quarters, legacy_migrated=True)
    logger.info("Migrated legacy history.json into %d quarterly file(s)", len(written))
    return written


def fetch_api(url: str, token: str) -> MetricsPayload | list[Any] | None:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    try:
        request = Request(url, headers=headers)
        with urlopen(request) as response:
            return json.loads(response.read().decode())
    except HTTPError as exc:
        logger.error("GitHub API HTTP %s for %s: %s", exc.code, url, exc.reason)
        return None
    except OSError as exc:
        logger.error("Failed to fetch %s: %s", url, exc)
        return None


def _apply_views_or_clones(
    payload: MetricsPayload,
    section: str,
    rows: list[MetricsPayload] | None,
) -> int:
    if not rows:
        return 0
    count = 0
    bucket = payload.setdefault(section, {})
    for row in rows:
        timestamp = str(row.get("timestamp", ""))
        if len(timestamp) < 10:
            continue
        day = timestamp[:10]
        bucket[day] = {"count": row.get("count", 0), "uniques": row.get("uniques", 0)}
        count += 1
    return count


def archive_repository_metrics(
    metrics_dir: Path,
    repo_slug: str,
    token: str,
    *,
    now: dt.datetime | None = None,
) -> list[Path]:
    """Fetch GitHub traffic APIs and persist updates into quarterly JSON files."""
    metrics_dir.mkdir(parents=True, exist_ok=True)
    quarters_dir(metrics_dir).mkdir(parents=True, exist_ok=True)

    modified = migrate_legacy_history(metrics_dir)
    touched_quarters: dict[str, MetricsPayload] = {}

    def touch_quarter(quarter: str) -> MetricsPayload:
        return touched_quarters.setdefault(quarter, load_quarter_payload(metrics_dir, quarter))

    base = f"https://api.github.com/repos/{repo_slug}"
    views_data = fetch_api(f"{base}/traffic/views", token)
    clones_data = fetch_api(f"{base}/traffic/clones", token)
    referrers_data = fetch_api(f"{base}/traffic/popular/referrers", token)
    paths_data = fetch_api(f"{base}/traffic/popular/paths", token)
    releases_data = fetch_api(f"{base}/releases", token)

    view_days = 0
    if isinstance(views_data, dict) and isinstance(views_data.get("views"), list):
        for row in views_data["views"]:
            timestamp = str(row.get("timestamp", ""))
            if len(timestamp) < 10:
                continue
            day = timestamp[:10]
            quarter = quarter_key_from_date(day)
            payload = touch_quarter(quarter)
            view_days += _apply_views_or_clones(payload, "views", [row])

    clone_days = 0
    if isinstance(clones_data, dict) and isinstance(clones_data.get("clones"), list):
        for row in clones_data["clones"]:
            timestamp = str(row.get("timestamp", ""))
            if len(timestamp) < 10:
                continue
            day = timestamp[:10]
            quarter = quarter_key_from_date(day)
            payload = touch_quarter(quarter)
            clone_days += _apply_views_or_clones(payload, "clones", [row])

    moment = now or dt.datetime.now(dt.UTC)
    today = moment.strftime("%Y-%m-%d")
    current_quarter = quarter_key_from_date(today)
    current_payload = touch_quarter(current_quarter)

    if isinstance(referrers_data, list):
        current_payload["referrers"][today] = [
            {
                "referrer": item.get("referrer"),
                "count": item.get("count", 0),
                "uniques": item.get("uniques", 0),
            }
            for item in referrers_data
        ]

    if isinstance(paths_data, list):
        current_payload["popular_content"][today] = [
            {
                "path": item.get("path"),
                "title": item.get("title"),
                "count": item.get("count", 0),
                "uniques": item.get("uniques", 0),
            }
            for item in paths_data
        ]

    if isinstance(releases_data, list):
        current_payload["releases"][today] = [
            {
                "tag": release.get("tag_name"),
                "assets": [
                    {asset.get("name", "asset"): asset.get("download_count", 0)}
                    for asset in release.get("assets", [])
                    if isinstance(asset, dict)
                ],
            }
            for release in releases_data
            if isinstance(release, dict)
        ]

    for quarter, payload in sorted(touched_quarters.items()):
        modified.append(save_quarter_payload(metrics_dir, payload))

    all_quarters = sorted(set(list_quarter_files(metrics_dir)))
    modified.append(
        write_index(
            metrics_dir,
            quarters=all_quarters,
            legacy_migrated=True,
        )
    )

    logger.info("Archived views for %d day(s) and clones for %d day(s)", view_days, clone_days)
    logger.info("Updated quarterly files: %s", ", ".join(all_quarters) or "(none)")
    return modified


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metrics-dir",
        type=Path,
        default=_DEFAULT_METRICS_DIR,
        help="Directory that stores metrics/index.json and metrics/quarters/",
    )
    parser.add_argument(
        "--repo",
        default=os.environ.get("REPO_SLUG"),
        help="GitHub repository slug (owner/name); defaults to REPO_SLUG env var",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("GITHUB_TOKEN"),
        help="GitHub API token; defaults to GITHUB_TOKEN env var",
    )
    parser.add_argument(
        "--log-level",
        default=os.environ.get("LOG_LEVEL", "INFO"),
        help="Python logging level (default: INFO)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=args.log_level.upper(), format="%(levelname)s: %(message)s")

    if not args.token:
        logger.error("GITHUB_TOKEN (or --token) is required")
        return 1
    if not args.repo:
        logger.error("REPO_SLUG (or --repo) is required")
        return 1

    archive_repository_metrics(args.metrics_dir, args.repo, args.token)
    return 0


if __name__ == "__main__":
    sys.exit(main())
