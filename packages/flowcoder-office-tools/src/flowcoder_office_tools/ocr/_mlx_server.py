"""mlx_vlm.server subprocess lifecycle manager — 좀비 0 보장.

핵심 계약
- ``ensure_running(model_alias)``: E2B/E4B 서버가 안 떠 있으면 띄운다. 이미 떠 있으면
  no-op. ``AX_OCR_BASE_URL_E2B`` / ``AX_OCR_BASE_URL_E4B``가 설정돼있으면 외부 서버
  사용으로 간주하고 spawn 자체를 건너뛴다 (plist 등 영구 운영 모드).
- 첫 spawn 시 ``atexit`` + ``SIGTERM`` / ``SIGINT`` / ``SIGHUP`` cleanup hook을 등록한다.
- ``shutdown_all()``: 모든 spawn된 서버를 process group 단위로 종료한다.
  ``os.killpg(pgid, SIGTERM)`` → ``wait_timeout`` 동안 polling → 살아있으면 ``SIGKILL``.

좀비 방지
- ``Popen(..., start_new_session=True)``로 새 프로세스 그룹 생성 → 자식의 자식
  (uvicorn worker 등)까지 일괄 회수.
- atexit + 3개 signal handler로 비정상 종료(Ctrl+C, kill, SIGHUP)에도 cleanup 보장.
- handler 안에서 cleanup 후 원래 default 동작 emulate: SIGINT는 KeyboardInterrupt
  raise, 그 외는 ``sys.exit(128 + signum)``. 이미 등록된 다른 handler가 있으면
  그걸 호출 (chained).
"""

from __future__ import annotations

import atexit
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any, Final, Literal

ModelAlias = Literal["gemma4:e2b", "gemma4:e4b"]

_DEFAULT_MLX_BIN: Final[str] = "/Users/jerome/mlx-env/bin/mlx_vlm.server"
_DEFAULT_E2B_MODEL: Final[str] = "/Users/jerome/models/gemma-4-e2b-mlx"
_DEFAULT_E4B_MODEL: Final[str] = "/Users/jerome/models/gemma-4-e4b-mlx"
_E2B_PORT: Final[int] = 11437
_E4B_PORT: Final[int] = 11438
_HEALTH_TIMEOUT_DEFAULT: Final[float] = 90.0
_SHUTDOWN_GRACE_SEC: Final[float] = 5.0

# Module-level state. Re-entry guarded so double calls are no-ops and cleanup
# runs at most once. ``_PROCS`` keys are the model alias.
_PROCS: dict[str, subprocess.Popen[bytes]] = {}
_CLEANUP_REGISTERED: bool = False
_CLEANUP_DONE: bool = False
# 시그널 핸들러 슬롯 — typeshed 상 ``Callable[[int, FrameType|None], Any] | int |
# Handlers | None`` 가 가능해 union이 복잡하므로 Any로 단순화한다 (라이브러리 경계).
_PRIOR_HANDLERS: dict[int, Any] = {}


# -- public API -------------------------------------------------------------


def base_url(model_alias: ModelAlias) -> str:
    """OpenAI client용 base_url. env override 우선."""
    port = _E2B_PORT if model_alias == "gemma4:e2b" else _E4B_PORT
    env_key = "AX_OCR_BASE_URL_E2B" if model_alias == "gemma4:e2b" else "AX_OCR_BASE_URL_E4B"
    return os.environ.get(env_key) or f"http://127.0.0.1:{port}/v1"


def model_path(model_alias: ModelAlias) -> str:
    """mlx_vlm.server에 넘길 모델 디렉토리. env override 우선."""
    if model_alias == "gemma4:e2b":
        return os.environ.get("AX_GEMMA_E2B_MODEL_PATH") or _DEFAULT_E2B_MODEL
    return os.environ.get("AX_GEMMA_E4B_MODEL_PATH") or _DEFAULT_E4B_MODEL


def is_external(model_alias: ModelAlias) -> bool:
    """``AX_OCR_BASE_URL_*``가 설정돼있으면 외부 서버 사용으로 간주."""
    env_key = "AX_OCR_BASE_URL_E2B" if model_alias == "gemma4:e2b" else "AX_OCR_BASE_URL_E4B"
    return bool(os.environ.get(env_key))


def ensure_running(
    model_alias: ModelAlias, *, wait_health: float = _HEALTH_TIMEOUT_DEFAULT
) -> None:
    """E2B/E4B 서버가 떠 있도록 보장한다 (idempotent).

    AX_OCR_BASE_URL_<E2B|E4B>가 설정돼있으면 spawn 건너뛴다 (외부 서버 모드).
    이미 spawn된 PID가 살아있으면 no-op. 죽었으면 다시 띄운다.
    첫 spawn 시 cleanup hook 등록.

    Args:
        model_alias: ``gemma4:e2b`` 또는 ``gemma4:e4b``.
        wait_health: ``/health`` polling 최대 대기 (초). 기본 90s — 모델 로딩이
            cold start 시 30~60s 소요 가능.

    Raises:
        RuntimeError: ``wait_health`` 초과해도 ``/health`` 응답 없을 때.
        FileNotFoundError: ``AX_MLX_BIN`` 또는 모델 경로 부재.
    """
    if is_external(model_alias):
        return

    existing = _PROCS.get(model_alias)
    if existing is not None and existing.poll() is None:
        return  # 살아있음

    bin_path = os.environ.get("AX_MLX_BIN") or _DEFAULT_MLX_BIN
    if not os.path.isfile(bin_path):
        raise FileNotFoundError(f"AX_MLX_BIN not found: {bin_path}")

    mpath = model_path(model_alias)
    if not os.path.isdir(mpath):
        raise FileNotFoundError(f"MLX model dir not found: {mpath}")

    port = _E2B_PORT if model_alias == "gemma4:e2b" else _E4B_PORT

    # 포트 선점 검사 — 이미 다른 프로세스가 점유했으면 그 서버를 신뢰하고 spawn 스킵.
    # (사용자가 plist 등으로 미리 띄운 경우 + AX_OCR_BASE_URL은 설정 안 한 상태).
    if _port_open(port):
        return

    cmd = [
        bin_path,
        "--model",
        mpath,
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--prefill-step-size",
        "2048",
    ]
    proc = subprocess.Popen(  # noqa: S603 - bin_path is validated above
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    _PROCS[model_alias] = proc
    _register_cleanup_once()

    # /health polling — 첫 콜드스타트는 모델 로딩 30~60s 소요.
    _wait_health(port, timeout=wait_health, proc=proc)


def shutdown_all(timeout: float = _SHUTDOWN_GRACE_SEC) -> None:
    """모든 spawn된 서버를 process group 단위로 종료. idempotent."""
    global _CLEANUP_DONE
    if _CLEANUP_DONE:
        return
    _CLEANUP_DONE = True

    for alias, proc in list(_PROCS.items()):
        try:
            if proc.poll() is not None:
                continue  # 이미 죽음
            try:
                pgid = os.getpgid(proc.pid)
            except ProcessLookupError:
                continue
            os.killpg(pgid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError, OSError):
            continue
        del alias  # silence linter

    deadline = time.monotonic() + timeout
    pending = list(_PROCS.values())
    while pending and time.monotonic() < deadline:
        pending = [p for p in pending if p.poll() is None]
        if pending:
            time.sleep(0.1)

    # SIGTERM 무응답 → SIGKILL escalate.
    for proc in pending:
        try:
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            continue

    # Final reap — 좀비 방지 (Popen.wait이 wait4 호출).
    for proc in _PROCS.values():
        try:
            proc.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            pass
        except OSError:
            pass


# -- internal helpers -------------------------------------------------------


def _register_cleanup_once() -> None:
    """atexit + SIGTERM/SIGINT/SIGHUP 핸들러 등록 — 모듈 라이프타임 1회만."""
    global _CLEANUP_REGISTERED
    if _CLEANUP_REGISTERED:
        return
    _CLEANUP_REGISTERED = True

    atexit.register(shutdown_all)

    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        try:
            prior = signal.getsignal(sig)
        except (ValueError, OSError):
            continue
        _PRIOR_HANDLERS[int(sig)] = prior

        def _make_handler(s: int) -> Callable[[int, object], None]:
            def _handler(signum: int, frame: object) -> None:
                shutdown_all()
                # Re-raise default behavior. SIGINT → KeyboardInterrupt for
                # interactive feedback. Otherwise exit with conventional
                # 128+signum status.
                prev = _PRIOR_HANDLERS.get(s)
                # SIG_DFL / SIG_IGN은 enum 값이라 callable()이 False — 이 가드만으로
                # 사용자 정의 핸들러만 chain된다.
                if callable(prev):
                    try:
                        prev(signum, frame)
                        return
                    except SystemExit:
                        raise
                    except BaseException:
                        # 외부 핸들러 예외는 무시하고 default 동작으로 fallback
                        pass
                if signum == int(signal.SIGINT):
                    raise KeyboardInterrupt
                sys.exit(128 + signum)

            return _handler

        try:
            signal.signal(sig, _make_handler(int(sig)))
        except (ValueError, OSError):
            # background thread에서 import되면 signal.signal이 실패할 수 있다.
            # cleanup은 atexit으로 충분히 보장된다.
            continue


def _port_open(port: int, host: str = "127.0.0.1") -> bool:
    """``host:port``에 누가 이미 LISTEN 중인지 즉시 확인 (1초 connect timeout)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        try:
            s.connect((host, port))
        except (TimeoutError, OSError):
            return False
        return True


def _wait_health(port: int, *, timeout: float, proc: subprocess.Popen[bytes]) -> None:
    """``/health`` 200을 받을 때까지 polling. 프로세스가 도중에 죽으면 즉시 에러."""
    url = f"http://127.0.0.1:{port}/health"
    deadline = time.monotonic() + timeout
    last_err: str = ""
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(
                f"mlx_vlm.server (port {port}) exited early with code {proc.returncode}"
            )
        try:
            with urllib.request.urlopen(url, timeout=2.0) as resp:  # noqa: S310
                if resp.status == 200:
                    return
                last_err = f"status={resp.status}"
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = str(e)
        time.sleep(0.5)
    raise RuntimeError(f"mlx_vlm.server (port {port}) /health timeout after {timeout}s; {last_err}")
