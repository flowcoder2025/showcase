"""Phase 3-Web T48 — run isolation, path sanitization, streaming uploads, TTL.

Every Streamlit invocation receives a fresh ``runs/<token>/`` directory. The
helpers here keep that directory the only writable surface a user input can
reach (R1-C2 path traversal), bound each upload at the per-file cap during
write (R1-H1/H2 streaming), and let ``cleanup_expired_runs`` reclaim disk on
a TTL schedule without racing live executions (R1-H4 lock file).
"""

from __future__ import annotations

import secrets
import shutil
import time
from pathlib import Path
from typing import Protocol

ALLOWED_EXTS: frozenset[str] = frozenset(
    {
        ".xlsx",
        ".csv",
        ".pdf",
        ".docx",
        ".hwpx",
        ".png",
        ".jpg",
        ".jpeg",
        ".txt",
        ".md",
        ".json",
    }
)

_DEFAULT_PER_FILE_MB = 50
_DEFAULT_CHUNK_SIZE = 1024 * 1024
_DEFAULT_TTL_HOURS = 24

_ACTIVE_RUNS: set[Path] = set()


class _ChunkReader(Protocol):
    """Minimum surface for ``stream_save`` — Streamlit's ``UploadedFile`` and
    the test fixture both satisfy this."""

    def read(self, size: int) -> bytes: ...


def create_run_dir(runs_root: Path) -> Path:
    """Allocate a fresh ``runs_root/<token>/`` with ``input/`` and ``output/``."""
    runs_root.mkdir(parents=True, exist_ok=True)
    run_id = secrets.token_urlsafe(16)
    run_dir = runs_root / run_id
    (run_dir / "input").mkdir(parents=True)
    (run_dir / "output").mkdir(parents=True)
    return run_dir


def validate_upload_path(runs_root: Path, target: Path) -> Path:
    """Reject paths that escape ``runs_root`` or carry a disallowed extension."""
    resolved = target.resolve()
    root_resolved = runs_root.resolve()
    if not resolved.is_relative_to(root_resolved):
        raise ValueError(f"path traversal — {target} resolved outside {runs_root}")
    if resolved.suffix.lower() not in ALLOWED_EXTS:
        raise ValueError(
            f"extension {resolved.suffix!r} not allowed (allow-list: {sorted(ALLOWED_EXTS)})"
        )
    return resolved


def stream_save(
    uf: _ChunkReader,
    target: Path,
    *,
    per_file_mb: int = _DEFAULT_PER_FILE_MB,
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
    remaining_total: int | None = None,
) -> int:
    """Stream ``uf`` into ``target``; abort + cleanup if any cap is exceeded.

    Two limits apply during the write loop. ``per_file_mb`` caps the *single*
    upload, and ``remaining_total`` (when provided) caps how many additional
    bytes the caller can absorb across the whole batch (R1-H2 fail-early).
    Both are enforced *while* writing — the offending file is truncated and
    unlinked before the chunk that overruns the cap is committed to disk, so
    a partial blob never lingers.

    Returns total bytes written on success. Raises ``ValueError`` whose
    message contains either ``<N>MB`` (per-file) or ``total upload``
    (cross-file) so callers can disambiguate the two limits.
    """
    per_file_cap = per_file_mb * 1024 * 1024
    effective_cap = per_file_cap if remaining_total is None else min(per_file_cap, remaining_total)
    size = 0
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as fh:
        while True:
            chunk = uf.read(chunk_size)
            if not chunk:
                break
            size += len(chunk)
            if size > effective_cap:
                fh.close()
                target.unlink(missing_ok=True)
                if remaining_total is not None and size > remaining_total:
                    raise ValueError(f"total upload exceeds remaining {remaining_total} bytes")
                raise ValueError(f"file {target.name} exceeds {per_file_mb}MB cap")
            fh.write(chunk)
    return size


def mark_active(run_dir: Path) -> None:
    """Lock ``run_dir`` against TTL reclamation while a scenario is executing."""
    _ACTIVE_RUNS.add(run_dir.resolve())
    (run_dir / ".lock").write_text(str(time.time()), encoding="utf-8")


def mark_done(run_dir: Path) -> None:
    """Release the lock once execution has settled (success or failure)."""
    _ACTIVE_RUNS.discard(run_dir.resolve())
    lock = run_dir / ".lock"
    if lock.exists():
        lock.unlink()


def cleanup_expired_runs(runs_root: Path, *, ttl_hours: int = _DEFAULT_TTL_HOURS) -> int:
    """Remove run directories older than ``ttl_hours`` that are not active.

    Skips any directory still in ``_ACTIVE_RUNS`` or holding a ``.lock`` file
    so a concurrent process's run is not destroyed mid-flight (R1-H4).
    """
    if not runs_root.exists():
        return 0
    cutoff = time.time() - ttl_hours * 3600
    removed = 0
    for run_dir in runs_root.iterdir():
        if not run_dir.is_dir():
            continue
        if run_dir.resolve() in _ACTIVE_RUNS:
            continue
        if (run_dir / ".lock").exists():
            continue
        if run_dir.stat().st_mtime < cutoff:
            shutil.rmtree(run_dir)
            removed += 1
    return removed
