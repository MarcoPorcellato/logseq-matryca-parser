"""Exact-revision, read-only diagnostic selection of official Logseq documents.

Source: logseq/docs at the pinned revision, distributed under its MIT license.
README.md and LICENSE.md are retained privately for provenance, never parsed.
Downloaded text is data, not instructions. No Parser or document renderer is used.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import ssl
import stat
import time
import urllib.error
import urllib.request
from contextlib import suppress
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

import probe

SOURCE = {
    "repository": "logseq/docs",
    "commit": "08f855f24d66e4509b7ea808554c13b4649e6ee1",
    "tree": "3309b25a2a603036a1a56b51d6e38d206c8106a6",
}
MAX_RESPONSE = 1024 * 1024
MAX_TOTAL = 2 * 1024 * 1024
MAX_SELECTION = 256 * 1024
ROW_KEYS = {"source_path", "git_blob", "sha256", "size"}


def require(condition: bool) -> None:
    if not condition:
        raise ValueError("corpus contract rejected")


def canonical(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("ascii")


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


def _invalid_constant(value: str) -> Any:
    raise ValueError("nonfinite JSON rejected")


def decode_json(raw: bytes, maximum: int) -> Any:
    require(type(raw) is bytes and len(raw) <= maximum)
    return json.loads(
        raw.decode("utf-8", errors="strict"),
        object_pairs_hook=unique_object,
        parse_constant=_invalid_constant,
    )


def check_deadline(deadline: float) -> None:
    require(type(deadline) in (int, float) and math.isfinite(deadline))
    require(time.monotonic() < deadline)


def safe_path(value: Any) -> str:
    require(type(value) is str and 0 < len(value.encode("utf-8")) <= 1024)
    require("\\" not in value and all(ord(c) >= 32 and ord(c) != 127 for c in value))
    require(all(part not in ("", ".", "..") for part in value.split("/")))
    return str(value)


def _document(path: str) -> bool:
    return path.startswith(("pages/", "journals/")) and path.endswith(".md")


def validate_selection(value: Any) -> dict[str, Any]:
    require(type(value) is dict and set(value) == {"schema", "source", "documents", "provenance"})
    require(type(value["schema"]) is int and value["schema"] == 1)
    require(type(value["source"]) is dict and value["source"] == SOURCE)
    require(type(value["documents"]) is list and len(value["documents"]) == 313)
    require(type(value["provenance"]) is list and len(value["provenance"]) == 2)
    paths: list[str] = []
    total = 0
    for group in ("documents", "provenance"):
        previous = ""
        for ordinal, row in enumerate(value[group]):
            require(
                type(row) is dict
                and set(row) == ROW_KEYS | ({"ordinal"} if group == "documents" else set())
            )
            path = safe_path(row["source_path"])
            require(path > previous and path not in paths)
            require(
                _document(path) if group == "documents" else path in ("LICENSE.md", "README.md")
            )
            if group == "documents":
                require(type(row["ordinal"]) is int and row["ordinal"] == ordinal)
            require(type(row["size"]) is int and 0 <= row["size"] <= MAX_RESPONSE)
            for key, length in (("git_blob", 40), ("sha256", 64)):
                require(
                    type(row[key]) is str
                    and re.fullmatch(r"[0-9a-f]{" + str(length) + r"}", row[key]) is not None
                )
            total += row["size"]
            previous = path
            paths.append(path)
    require(total <= MAX_TOTAL and len(canonical(value)) <= MAX_SELECTION)
    return dict(value)


def project_selection(manifest: dict[str, Any]) -> dict[str, Any]:
    require(type(manifest) is dict and manifest.get("source") == SOURCE)
    require(type(manifest.get("files")) is list and len(manifest["files"]) == 315)
    documents: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    destinations: set[str] = set()
    for original in manifest["files"]:
        require(type(original) is dict and set(original) == ROW_KEYS | {"destination"})
        path = safe_path(original["source_path"])
        is_document = _document(path)
        require(is_document or path in ("LICENSE.md", "README.md"))
        destination = safe_path(original["destination"])
        require(destination == ("corpus/" if is_document else "provenance/") + path)
        require(destination not in destinations)
        destinations.add(destination)
        row = {key: original[key] for key in ROW_KEYS}
        (documents if is_document else provenance).append(row)
    documents.sort(key=lambda row: row["source_path"])
    provenance.sort(key=lambda row: row["source_path"])
    for ordinal, row in enumerate(documents):
        row["ordinal"] = ordinal
    return validate_selection(
        {"schema": 1, "source": dict(SOURCE), "documents": documents, "provenance": provenance}
    )


def verify_bytes(raw: bytes, row: dict[str, Any]) -> bytes:
    require(type(raw) is bytes and len(raw) == row["size"])
    require(hashlib.sha256(raw).hexdigest() == row["sha256"])
    require(
        hashlib.sha1(
            b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw, usedforsecurity=False
        ).hexdigest()
        == row["git_blob"]
    )
    raw.decode("utf-8", errors="strict")
    return raw


def read_private(root: Path, relative: str, maximum: int, deadline: float) -> bytes:
    safe_path(relative)
    check_deadline(deadline)
    root_fd = probe.open_directory(root, deadline=deadline, phase_cutoff=deadline)
    parent_fd = file_fd = -1
    try:
        parent_fd, leaf = probe._open_parent_at(
            root_fd, relative, deadline=deadline, phase_cutoff=deadline
        )
        file_fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
        before = os.fstat(file_fd)
        require(stat.S_ISREG(before.st_mode) and before.st_size <= maximum)
        chunks: list[bytes] = []
        remaining = before.st_size + 1
        while remaining:
            check_deadline(deadline)
            chunk = os.read(file_fd, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        after = os.fstat(file_fd)
        raw = b"".join(chunks)
        require(len(raw) == before.st_size and before.st_size == after.st_size)
        check_deadline(deadline)
        return raw
    finally:
        for descriptor in (file_fd, parent_fd, root_fd):
            if descriptor >= 0:
                os.close(descriptor)


def read_verified_file(root: Path, row: dict[str, Any], deadline: float) -> bytes:
    return verify_bytes(read_private(root, row["source_path"], MAX_RESPONSE, deadline), row)


def write_private(root: Path, relative: str, raw: bytes, deadline: float) -> None:
    parts = safe_path(relative).split("/")
    descriptor = probe.open_directory(root, deadline=deadline, phase_cutoff=deadline)
    try:
        for part in parts[:-1]:
            check_deadline(deadline)
            with suppress(FileExistsError):
                os.mkdir(part, mode=0o700, dir_fd=descriptor)
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        file_fd = os.open(
            parts[-1],
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=descriptor,
        )
        try:
            pending = memoryview(raw)
            while pending:
                check_deadline(deadline)
                written = os.write(file_fd, pending[:65536])
                require(written > 0)
                pending = pending[written:]
            os.fsync(file_fd)
            require(stat.S_ISREG(os.fstat(file_fd).st_mode))
        finally:
            os.close(file_fd)
    finally:
        os.close(descriptor)


def fresh_directory(path: Path, deadline: float) -> None:
    check_deadline(deadline)
    parent_fd = probe.open_directory(path.parent, deadline=deadline, phase_cutoff=deadline)
    try:
        os.mkdir(path.name, 0o700, dir_fd=parent_fd)
    finally:
        os.close(parent_fd)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


def _get(url: str, deadline: float) -> bytes:
    check_deadline(deadline)
    parsed = urlsplit(url)
    require(
        parsed.scheme == "https"
        and parsed.netloc in ("api.github.com", "raw.githubusercontent.com")
    )
    require(parsed.username is None and parsed.password is None and not parsed.fragment)
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        _NoRedirect(),
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
    )
    request = urllib.request.Request(
        url, headers={"User-Agent": "Logseq-Matryca-Corpus-Diagnostic"}
    )
    try:
        with opener.open(request, timeout=min(15.0, deadline - time.monotonic())) as response:
            require(response.status == 200 and response.geturl() == url)
            raw = response.read(MAX_RESPONSE + 1)
            require(len(raw) <= MAX_RESPONSE)
            check_deadline(deadline)
            return bytes(raw)
    except urllib.error.URLError:
        raise ValueError("corpus transport rejected") from None


def fetch_selection(
    selection: dict[str, Any], destination: Path, deadline: float
) -> dict[str, Any]:
    selected = validate_selection(selection)
    fresh_directory(destination, deadline)
    commit = SOURCE["commit"]
    tree = SOURCE["tree"]
    info = decode_json(
        _get(f"https://api.github.com/repos/logseq/docs/git/commits/{commit}", deadline),
        MAX_RESPONSE,
    )
    require(
        type(info) is dict
        and info.get("sha") == commit
        and type(info.get("tree")) is dict
        and info["tree"].get("sha") == tree
    )
    listing = decode_json(
        _get(f"https://api.github.com/repos/logseq/docs/git/trees/{tree}?recursive=1", deadline),
        MAX_RESPONSE,
    )
    require(
        type(listing) is dict
        and listing.get("sha") == tree
        and listing.get("truncated") is False
        and type(listing.get("tree")) is list
    )
    upstream: dict[str, dict[str, Any]] = {}
    for item in listing["tree"]:
        require(type(item) is dict)
        path = safe_path(item.get("path"))
        require(path not in upstream)
        upstream[path] = item
    rows = selected["documents"] + selected["provenance"]
    require(
        {p for p in upstream if _document(p) or p in ("README.md", "LICENSE.md")}
        == {row["source_path"] for row in rows}
    )
    total = 0
    for row in rows:
        check_deadline(deadline)
        item = upstream[row["source_path"]]
        require(
            item.get("type") == "blob"
            and item.get("mode") == "100644"
            and item.get("sha") == row["git_blob"]
            and type(item.get("size")) is int
            and item["size"] == row["size"]
        )
        path = "/".join(quote(part, safe="") for part in row["source_path"].split("/"))
        raw = verify_bytes(
            _get(f"https://raw.githubusercontent.com/logseq/docs/{commit}/{path}", deadline), row
        )
        total += len(raw)
        require(total <= MAX_TOTAL)
        write_private(destination, row["source_path"], raw, deadline)
    check_deadline(deadline)
    return {
        "schema": 1,
        "documents": 313,
        "provenance": 2,
        "requests": 317,
        "bytes": total,
        "selection_sha256": hashlib.sha256(canonical(selected)).hexdigest(),
    }
