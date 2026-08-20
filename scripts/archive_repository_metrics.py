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
import tempfile
import time
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
_API_VERSION = "2026-03-10"
_API_TIMEOUT_SECONDS = 30
_MAX_RESPONSE_BYTES = 2_000_000
_MAX_FETCH_ATTEMPTS = 3
_RETRYABLE_HTTP_STATUS = {408, 429, 500, 502, 503, 504}

MetricsPayload = dict[str, Any]


class MetricsFetchError(RuntimeError):
    """Raised when a complete, bounded GitHub metrics snapshot cannot be fetched."""


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
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(json.dumps(payload, indent=2) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


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
    for _quarter, payload in sorted(in_memory.items()):
        written.append(save_quarter_payload(metrics_dir, payload))

    legacy_path.unlink()
    all_quarters = sorted(set(list_quarter_files(metrics_dir)))
    write_index(metrics_dir, quarters=all_quarters, legacy_migrated=True)
    logger.info("Migrated legacy history.json into %d quarterly file(s)", len(written))
    return written


def fetch_api(url: str, token: str) -> MetricsPayload | list[Any]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": _API_VERSION,
        "User-Agent": "logseq-matryca-parser-metrics",
    }
    request = Request(url, headers=headers)
    last_error = "unknown failure"
    for attempt in range(1, _MAX_FETCH_ATTEMPTS + 1):
        retryable = True
        try:
            with urlopen(request, timeout=_API_TIMEOUT_SECONDS) as response:
                raw = response.read(_MAX_RESPONSE_BYTES + 1)
            if len(raw) > _MAX_RESPONSE_BYTES:
                raise MetricsFetchError(
                    f"GitHub API response exceeds {_MAX_RESPONSE_BYTES} bytes for {url}"
                )
            loaded = json.loads(raw.decode("utf-8"))
            if not isinstance(loaded, (dict, list)):
                raise MetricsFetchError(f"GitHub API returned a non-container payload for {url}")
            return loaded
        except HTTPError as exc:
            retryable = exc.code in _RETRYABLE_HTTP_STATUS
            last_error = f"HTTP {exc.code}: {exc.reason}"
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            last_error = str(exc)

        if not retryable or attempt == _MAX_FETCH_ATTEMPTS:
            break
        time.sleep(attempt)
    raise MetricsFetchError(f"GitHub API fetch failed for {url}: {last_error}")


def _validate_snapshot_shapes(
    views: object,
    clones: object,
    referrers: object,
    paths: object,
    releases: object,
) -> None:
    def nonnegative_int(value: object) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and value >= 0

    def valid_day_timestamp(value: object) -> bool:
        if not isinstance(value, str) or len(value) < 10:
            return False
        try:
            dt.date.fromisoformat(value[:10])
        except ValueError:
            return False
        return True

    def valid_count_row(row: dict[str, object], *, label_field: str) -> bool:
        return (
            isinstance(row.get(label_field), str)
            and nonnegative_int(row.get("count", 0))
            and nonnegative_int(row.get("uniques", 0))
        )

    if not isinstance(views, dict) or not isinstance(views.get("views"), list):
        raise MetricsFetchError("GitHub traffic payload is missing list field 'views'")
    if not isinstance(clones, dict) or not isinstance(clones.get("clones"), list):
        raise MetricsFetchError("GitHub traffic payload is missing list field 'clones'")
    if not isinstance(referrers, list):
        raise MetricsFetchError("GitHub referrers payload must be a list")
    if not isinstance(paths, list):
        raise MetricsFetchError("GitHub popular paths payload must be a list")
    if not isinstance(releases, list):
        raise MetricsFetchError("GitHub releases payload must be a list")

    row_sets = (
        ("views", views["views"]),
        ("clones", clones["clones"]),
        ("referrers", referrers),
        ("popular paths", paths),
        ("releases", releases),
    )
    for label, rows in row_sets:
        if any(not isinstance(row, dict) for row in rows):
            raise MetricsFetchError(f"GitHub {label} payload contains a non-object row")

    for label, rows in (("views", views["views"]), ("clones", clones["clones"])):
        if any(
            not valid_day_timestamp(row.get("timestamp"))
            or not nonnegative_int(row.get("count", 0))
            or not nonnegative_int(row.get("uniques", 0))
            for row in rows
        ):
            raise MetricsFetchError(f"GitHub {label} payload contains malformed fields")

    if any(not valid_count_row(row, label_field="referrer") for row in referrers):
        raise MetricsFetchError("GitHub referrers payload contains malformed fields")
    if any(
        not valid_count_row(row, label_field="path") or not isinstance(row.get("title"), str)
        for row in paths
    ):
        raise MetricsFetchError("GitHub popular paths payload contains malformed fields")

    for release in releases:
        assert isinstance(release, dict)
        assets = release.get("assets", [])
        if not isinstance(assets, list) or any(not isinstance(asset, dict) for asset in assets):
            raise MetricsFetchError("GitHub releases payload contains malformed assets")
        if not isinstance(release.get("tag_name"), str) or any(
            not isinstance(asset.get("name"), str)
            or not nonnegative_int(asset.get("download_count", 0))
            for asset in assets
        ):
            raise MetricsFetchError("GitHub releases payload contains malformed fields")


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
    base = f"https://api.github.com/repos/{repo_slug}"
    views_data = fetch_api(f"{base}/traffic/views", token)
    clones_data = fetch_api(f"{base}/traffic/clones", token)
    referrers_data = fetch_api(f"{base}/traffic/popular/referrers", token)
    paths_data = fetch_api(f"{base}/traffic/popular/paths", token)
    releases_data = fetch_api(f"{base}/releases", token)
    _validate_snapshot_shapes(
        views_data,
        clones_data,
        referrers_data,
        paths_data,
        releases_data,
    )

    metrics_dir.mkdir(parents=True, exist_ok=True)
    quarters_dir(metrics_dir).mkdir(parents=True, exist_ok=True)

    modified = migrate_legacy_history(metrics_dir)
    touched_quarters: dict[str, MetricsPayload] = {}

    def touch_quarter(quarter: str) -> MetricsPayload:
        return touched_quarters.setdefault(quarter, load_quarter_payload(metrics_dir, quarter))

    view_days = 0
    assert isinstance(views_data, dict)
    for row in views_data["views"]:
        timestamp = str(row.get("timestamp", ""))
        if len(timestamp) < 10:
            continue
        day = timestamp[:10]
        quarter = quarter_key_from_date(day)
        payload = touch_quarter(quarter)
        view_days += _apply_views_or_clones(payload, "views", [row])

    clone_days = 0
    assert isinstance(clones_data, dict)
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

    assert isinstance(referrers_data, list)
    current_payload["referrers"][today] = [
        {
            "referrer": item.get("referrer"),
            "count": item.get("count", 0),
            "uniques": item.get("uniques", 0),
        }
        for item in referrers_data
    ]

    assert isinstance(paths_data, list)
    current_payload["popular_content"][today] = [
        {
            "path": item.get("path"),
            "title": item.get("title"),
            "count": item.get("count", 0),
            "uniques": item.get("uniques", 0),
        }
        for item in paths_data
    ]

    assert isinstance(releases_data, list)
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

    for _quarter, payload in sorted(touched_quarters.items()):
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
        "--log-level",
        default=os.environ.get("LOG_LEVEL", "INFO"),
        help="Python logging level (default: INFO)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=args.log_level.upper(), format="%(levelname)s: %(message)s")

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        logger.error("GITHUB_TOKEN is required")
        return 1
    if not args.repo:
        logger.error("REPO_SLUG (or --repo) is required")
        return 1

    try:
        archive_repository_metrics(args.metrics_dir, args.repo, token)
    except MetricsFetchError as error:
        logger.error("Metrics snapshot aborted: %s", error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
