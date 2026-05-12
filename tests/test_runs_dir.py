"""Phase 3-Web T48 — run_id isolation + path traversal + streaming + TTL.

Covers the four security primitives ``web/_runs.py`` must satisfy:

- ``create_run_dir`` issues a uniquely-named directory under ``runs_root`` so
  concurrent invocations cannot collide (R3-C3 — `secrets.token_urlsafe`).
- ``validate_upload_path`` resolves the target and rejects (a) anything that
  escapes ``runs_root`` via ``..``, (b) any extension outside the allow-list
  (R1-C2).
- ``stream_save`` writes in chunks and aborts mid-stream when the running
  byte counter exceeds the per-file cap, cleaning up the partial file so no
  half-written input lingers (R1-H1, R1-H2).
- ``cleanup_expired_runs`` honours the lock file and the in-process
  ``_ACTIVE_RUNS`` set, preserving runs that are still active even when their
  ``mtime`` is older than the TTL window (R1-H4).
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from web._runs import (
    cleanup_expired_runs,
    create_run_dir,
    mark_active,
    mark_done,
    stream_save,
    validate_upload_path,
)


class _FakeUpload:
    """Minimal ``read(n)`` shim mirroring Streamlit's UploadedFile interface."""

    def __init__(self, data: bytes) -> None:
        self._data = data
        self._idx = 0

    def read(self, size: int) -> bytes:
        chunk = self._data[self._idx : self._idx + size]
        self._idx += size
        return chunk


def test_run_id_unique(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    a = create_run_dir(runs_root)
    b = create_run_dir(runs_root)
    assert a.name != b.name
    assert (a / "input").is_dir() and (a / "output").is_dir()
    assert (b / "input").is_dir() and (b / "output").is_dir()


def test_path_traversal_blocked(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    run_dir = create_run_dir(runs_root)
    with pytest.raises(ValueError, match="outside"):
        validate_upload_path(runs_root, run_dir / ".." / ".." / "etc" / "passwd")


def test_extension_allowlist(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    run_dir = create_run_dir(runs_root)
    with pytest.raises(ValueError, match="extension"):
        validate_upload_path(runs_root, run_dir / "input" / "malware.exe")


def test_stream_save_size_cap_during_write(tmp_path: Path) -> None:
    """R1-H1: mid-stream cap detection + partial-file cleanup."""
    runs_root = tmp_path / "runs"
    run_dir = create_run_dir(runs_root)
    target = run_dir / "input" / "big.xlsx"

    huge = b"x" * (51 * 1024 * 1024)
    with pytest.raises(ValueError, match="50MB"):
        stream_save(_FakeUpload(huge), target, per_file_mb=50)
    assert not target.exists()


def test_stream_save_total_cap_fail_early(tmp_path: Path) -> None:
    """R1-H2 fail-early: remaining_total cap aborts during write, partial cleaned."""
    runs_root = tmp_path / "runs"
    run_dir = create_run_dir(runs_root)
    target = run_dir / "input" / "second.xlsx"

    payload = b"z" * (5 * 1024 * 1024)
    with pytest.raises(ValueError, match="total upload"):
        stream_save(
            _FakeUpload(payload),
            target,
            per_file_mb=50,
            remaining_total=2 * 1024 * 1024,
        )
    assert not target.exists()


def test_stream_save_under_cap_succeeds(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    run_dir = create_run_dir(runs_root)
    target = run_dir / "input" / "ok.xlsx"

    payload = b"y" * (3 * 1024 * 1024)
    written = stream_save(_FakeUpload(payload), target, per_file_mb=50)
    assert written == len(payload)
    assert target.exists()
    assert target.read_bytes() == payload


def test_lock_file_prevents_cleanup(tmp_path: Path) -> None:
    """R1-H4: active run with stale mtime survives cleanup; done run is removed."""
    runs_root = tmp_path / "runs"
    run_dir = create_run_dir(runs_root)
    mark_active(run_dir)

    old = time.time() - 25 * 3600
    os.utime(run_dir, (old, old))

    cleanup_expired_runs(runs_root, ttl_hours=24)
    assert run_dir.exists()

    mark_done(run_dir)
    os.utime(run_dir, (old, old))
    cleanup_expired_runs(runs_root, ttl_hours=24)
    assert not run_dir.exists()


def test_cleanup_recent_run_untouched(tmp_path: Path) -> None:
    """Cleanup must never delete a run whose mtime is within the TTL window."""
    runs_root = tmp_path / "runs"
    run_dir = create_run_dir(runs_root)
    mark_done(run_dir)
    cleanup_expired_runs(runs_root, ttl_hours=24)
    assert run_dir.exists()
