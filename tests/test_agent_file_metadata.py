from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from logseq_matryca_parser._agent_file_io import _write_agent_file


def _run(*args: str) -> bytes:
    result = subprocess.run(args, capture_output=True, check=False, timeout=10)
    assert result.returncode == 0, "required metadata operation failed"
    return result.stdout


def _set_attribute(path: Path) -> None:
    if sys.platform == "darwin":
        _run("/usr/bin/xattr", "-wx", "org.matryca.test", "006162ff", str(path))
    else:
        os.setxattr(path, "user.matryca_test", b"\x00ab\xff")


def _attribute(path: Path) -> bytes:
    if sys.platform == "darwin":
        return bytes.fromhex(_run("/usr/bin/xattr", "-px", "org.matryca.test", str(path)).decode())
    return os.getxattr(path, "user.matryca_test")


@pytest.mark.skipif(
    sys.platform != "darwin" and not (hasattr(os, "setxattr") and hasattr(os, "getxattr")),
    reason="extended attribute APIs are unavailable on this platform",
)
@pytest.mark.parametrize("append", [False, True])
def test_existing_extended_attribute_survives_write(tmp_path: Path, append: bool) -> None:
    target = tmp_path / "target"
    target.write_bytes(b"old")
    _set_attribute(target)
    before = target.stat()
    assert _attribute(target) == b"\x00ab\xff"

    _write_agent_file(target, "new", append=append)

    assert target.read_bytes() == (b"oldnew" if append else b"new")
    assert (target.stat().st_dev, target.stat().st_ino) == (before.st_dev, before.st_ino)
    assert _attribute(target) == b"\x00ab\xff"


def _acl(path: Path) -> bytes:
    if sys.platform == "darwin":
        return b"\n".join(_run("/bin/ls", "-le", str(path)).splitlines()[1:])
    if os.name == "nt":
        return _run("icacls", str(path))
    return _run("getfacl", "-cpn", str(path))


def _set_acl(path: Path) -> None:
    if sys.platform == "darwin":
        _run("/bin/chmod", "+a", "everyone allow readattr", str(path))
    elif os.name == "nt":
        _run("icacls", str(path), "/grant", "*S-1-5-32-545:(RA)")
    else:
        _run("setfacl", "-m", "u:65534:r--", str(path))


def _reset_acl(path: Path) -> None:
    if sys.platform == "darwin":
        _run("/bin/chmod", "-N", str(path))
    elif os.name == "nt":
        _run("icacls", str(path), "/reset")
    else:
        _run("setfacl", "-b", str(path))


def _require_acl_platform() -> None:
    if sys.platform == "darwin" or os.name == "nt":
        return
    if sys.platform != "linux":
        pytest.skip("native ACL fixture is defined only for Darwin, Windows, and Linux")
    if not shutil.which("setfacl") or not shutil.which("getfacl"):
        pytest.skip("Linux ACL utilities setfacl and getfacl are not both installed")


@pytest.mark.parametrize("append", [False, True])
def test_existing_native_acl_survives_write(tmp_path: Path, append: bool) -> None:
    _require_acl_platform()
    target = tmp_path / "target"
    target.write_bytes(b"old")
    default_acl = _acl(target)
    _set_acl(target)
    before_acl = _acl(target)
    assert before_acl != default_acl
    before = target.stat()

    _write_agent_file(target, "new", append=append)

    assert target.read_bytes() == (b"oldnew" if append else b"new")
    assert (target.stat().st_dev, target.stat().st_ino) == (before.st_dev, before.st_ino)
    assert _acl(target) == before_acl


def test_acl_fixture_detects_deliberate_metadata_reset(tmp_path: Path) -> None:
    _require_acl_platform()
    target = tmp_path / "target"
    target.write_bytes(b"old")
    _set_acl(target)
    before = _acl(target)
    _reset_acl(target)
    assert _acl(target) != before


_INHERITED_SID = "S-1-5-32-546"
_READ_ATTRIBUTES = 128


def _has_inherited_fixture_ace(records: object) -> bool:
    assert isinstance(records, list)
    for record in records:
        assert isinstance(record, dict)
        assert isinstance(record.get("sid"), str)
        assert type(record.get("rights")) is int
        assert type(record.get("inherited")) is bool
        assert record.get("kind") in ("Allow", "Deny")
    return any(
        record["sid"] == _INHERITED_SID
        and record["rights"] & _READ_ATTRIBUTES == _READ_ATTRIBUTES
        and record["inherited"] is True
        and record["kind"] == "Allow"
        for record in records
    )


@pytest.mark.parametrize(
    "record",
    [
        {"sid": "S-1-5-32-546", "rights": 128, "inherited": False, "kind": "Allow"},
        {"sid": "S-1-5-32-545", "rights": 128, "inherited": True, "kind": "Allow"},
        {"sid": "S-1-5-32-546", "rights": 8, "inherited": True, "kind": "Allow"},
        {"sid": "S-1-5-32-546", "rights": 128, "inherited": True, "kind": "Deny"},
    ],
)
def test_inherited_ace_oracle_rejects_nonmatching_records(record: dict[str, object]) -> None:
    assert not _has_inherited_fixture_ace([record])


def test_inherited_ace_oracle_rejects_malformed_record() -> None:
    with pytest.raises(AssertionError):
        _has_inherited_fixture_ace([{"sid": _INHERITED_SID}])
    assert _has_inherited_fixture_ace(
        [{"sid": "S-1-5-32-546", "rights": 128, "inherited": True, "kind": "Allow"}]
    )


def _windows_acl_records(path: Path) -> object:
    script = (
        "$ErrorActionPreference = 'Stop'; "
        "$acl = Get-Acl -LiteralPath $env:MATRyCA_TEST_ACL_PATH; "
        "$rules = @($acl.GetAccessRules($true, $true, "
        "[System.Security.Principal.SecurityIdentifier]) | ForEach-Object { "
        "@{ sid = $_.IdentityReference.Value; rights = [int]$_.FileSystemRights; "
        "inherited = $_.IsInherited; kind = $_.AccessControlType.ToString() } }); "
        "ConvertTo-Json -InputObject $rules -Compress"
    )
    environment = os.environ.copy()
    environment["MATRyCA_TEST_ACL_PATH"] = str(path)
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        check=False,
        timeout=10,
        env=environment,
    )
    assert result.returncode == 0, "required Windows DACL inspection failed"
    return json.loads(result.stdout)


@pytest.mark.skipif(os.name != "nt", reason="native Windows DACL inheritance requires Windows")
@pytest.mark.parametrize("append", [False, True])
def test_new_file_inherits_distinctive_windows_dacl(tmp_path: Path, append: bool) -> None:
    parent = tmp_path / "owned-parent"
    parent.mkdir()
    baseline = _windows_acl_records(parent)
    assert isinstance(baseline, list)
    assert all(record["sid"] != _INHERITED_SID for record in baseline)
    _run("icacls", str(parent), "/grant", "*S-1-5-32-546:(OI)(CI)(IO)(RA)")
    target = parent / "new-file"
    assert not target.exists()

    _write_agent_file(target, "new", append=append)

    assert target.read_bytes() == b"new"
    assert _has_inherited_fixture_ace(_windows_acl_records(target))


@pytest.mark.skipif(
    sys.platform != "darwin" and not (hasattr(os, "setxattr") and hasattr(os, "getxattr")),
    reason="extended attribute APIs are unavailable on this platform",
)
def test_fresh_replacement_lacks_fixture_attribute_and_original_inode(tmp_path: Path) -> None:
    target = tmp_path / "target"
    replacement = tmp_path / "replacement"
    target.write_bytes(b"old")
    _set_attribute(target)
    before = target.stat()
    replacement.write_bytes(b"new")
    replacement.replace(target)
    assert (target.stat().st_dev, target.stat().st_ino) != (before.st_dev, before.st_ino)
    if sys.platform == "darwin":
        assert b"org.matryca.test" not in _run("/usr/bin/xattr", str(target)).splitlines()
    else:
        assert "user.matryca_test" not in os.listxattr(target)
