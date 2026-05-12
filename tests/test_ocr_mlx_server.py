"""mlx_vlm.server subprocess manager — 좀비 0 보장 검증."""

from __future__ import annotations

import signal
from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock

import pytest
from flowcoder_office_tools.ocr import _mlx_server


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """각 테스트 시작 시 모듈 상태 초기화 + AX_OCR_BASE_URL 격리."""
    for k in (
        "AX_OCR_BASE_URL_E2B",
        "AX_OCR_BASE_URL_E4B",
        "AX_MLX_BIN",
        "AX_GEMMA_E2B_MODEL_PATH",
        "AX_GEMMA_E4B_MODEL_PATH",
    ):
        monkeypatch.delenv(k, raising=False)
    _mlx_server._PROCS.clear()
    _mlx_server._CLEANUP_REGISTERED = False
    _mlx_server._PRIOR_HANDLERS.clear()
    yield
    _mlx_server._PROCS.clear()


# -- base_url / model_path / is_external -----------------------------------


def test_base_url_default_e2b() -> None:
    assert _mlx_server.base_url("gemma4:e2b") == "http://127.0.0.1:11437/v1"


def test_base_url_default_e4b() -> None:
    assert _mlx_server.base_url("gemma4:e4b") == "http://127.0.0.1:11438/v1"


def test_base_url_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AX_OCR_BASE_URL_E2B", "http://other:9999/v1")
    assert _mlx_server.base_url("gemma4:e2b") == "http://other:9999/v1"
    # E4B 미영향
    assert _mlx_server.base_url("gemma4:e4b") == "http://127.0.0.1:11438/v1"


def test_model_path_defaults() -> None:
    assert _mlx_server.model_path("gemma4:e2b").endswith("gemma-4-e2b-mlx")
    assert _mlx_server.model_path("gemma4:e4b").endswith("gemma-4-e4b-mlx")


def test_model_path_env_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    monkeypatch.setenv("AX_GEMMA_E2B_MODEL_PATH", str(tmp_path))
    assert _mlx_server.model_path("gemma4:e2b") == str(tmp_path)


def test_is_external_false_when_no_env() -> None:
    assert _mlx_server.is_external("gemma4:e2b") is False
    assert _mlx_server.is_external("gemma4:e4b") is False


def test_is_external_true_when_base_url_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AX_OCR_BASE_URL_E2B", "http://x/v1")
    assert _mlx_server.is_external("gemma4:e2b") is True
    assert _mlx_server.is_external("gemma4:e4b") is False


# -- ensure_running: skip when external -----------------------------------


def test_ensure_running_skips_when_external(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AX_OCR_BASE_URL_E2B", "http://other:9999/v1")
    spawned: list[Any] = []
    monkeypatch.setattr(_mlx_server.subprocess, "Popen", lambda *a, **k: spawned.append((a, k)))
    _mlx_server.ensure_running("gemma4:e2b")
    assert spawned == [], "AX_OCR_BASE_URL_E2B 설정 시 spawn 안 함"


def test_ensure_running_idempotent(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """이미 spawn된 PID가 살아있으면 두 번째 호출은 no-op."""
    bin_path = tmp_path / "mlx_vlm.server"
    bin_path.write_text("#!/bin/sh\nsleep 1\n")
    bin_path.chmod(0o755)
    model_dir = tmp_path / "model"
    model_dir.mkdir()

    monkeypatch.setenv("AX_MLX_BIN", str(bin_path))
    monkeypatch.setenv("AX_GEMMA_E2B_MODEL_PATH", str(model_dir))

    fake_proc = MagicMock()
    fake_proc.poll.return_value = None  # 살아있음
    fake_proc.pid = 99999

    spawn_count = {"n": 0}

    def fake_popen(*a: Any, **k: Any) -> MagicMock:
        spawn_count["n"] += 1
        return fake_proc

    monkeypatch.setattr(_mlx_server.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(_mlx_server, "_wait_health", lambda *a, **k: None)
    monkeypatch.setattr(_mlx_server, "_port_open", lambda *a, **k: False)

    _mlx_server.ensure_running("gemma4:e2b")
    _mlx_server.ensure_running("gemma4:e2b")
    assert spawn_count["n"] == 1, "두 번째 호출은 no-op (살아있는 PID)"


def test_ensure_running_uses_start_new_session(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    """spawn 시 start_new_session=True 강제 — process group 격리."""
    bin_path = tmp_path / "mlx_vlm.server"
    bin_path.write_text("#!/bin/sh\nsleep 1\n")
    bin_path.chmod(0o755)
    model_dir = tmp_path / "model"
    model_dir.mkdir()

    monkeypatch.setenv("AX_MLX_BIN", str(bin_path))
    monkeypatch.setenv("AX_GEMMA_E2B_MODEL_PATH", str(model_dir))

    captured: dict[str, Any] = {}

    def fake_popen(*a: Any, **k: Any) -> MagicMock:
        captured["args"] = a
        captured["kwargs"] = k
        m = MagicMock()
        m.poll.return_value = None
        m.pid = 99998
        return m

    monkeypatch.setattr(_mlx_server.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(_mlx_server, "_wait_health", lambda *a, **k: None)
    monkeypatch.setattr(_mlx_server, "_port_open", lambda *a, **k: False)

    _mlx_server.ensure_running("gemma4:e2b")
    assert captured["kwargs"].get("start_new_session") is True


def test_ensure_running_passes_correct_cli_args(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    """spawn 시 --model + --port가 별칭에 맞게 전달된다."""
    bin_path = tmp_path / "mlx_vlm.server"
    bin_path.write_text("#!/bin/sh\nsleep 1\n")
    bin_path.chmod(0o755)
    model_dir = tmp_path / "e4b-model"
    model_dir.mkdir()

    monkeypatch.setenv("AX_MLX_BIN", str(bin_path))
    monkeypatch.setenv("AX_GEMMA_E4B_MODEL_PATH", str(model_dir))

    captured: dict[str, Any] = {}

    def fake_popen(*a: Any, **k: Any) -> MagicMock:
        captured["cmd"] = a[0]
        m = MagicMock()
        m.poll.return_value = None
        m.pid = 99997
        return m

    monkeypatch.setattr(_mlx_server.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(_mlx_server, "_wait_health", lambda *a, **k: None)
    monkeypatch.setattr(_mlx_server, "_port_open", lambda *a, **k: False)

    _mlx_server.ensure_running("gemma4:e4b")
    cmd = captured["cmd"]
    assert "--model" in cmd
    assert str(model_dir) in cmd
    assert "--port" in cmd
    assert "11438" in cmd  # E4B port


def test_ensure_running_skips_if_port_already_open(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    """누가 이미 11437을 점유 중이면 spawn 건너뛴다 (ex: plist 모드 + AX_OCR_BASE_URL 미설정)."""
    bin_path = tmp_path / "mlx_vlm.server"
    bin_path.write_text("#!/bin/sh\nsleep 1\n")
    bin_path.chmod(0o755)
    model_dir = tmp_path / "model"
    model_dir.mkdir()

    monkeypatch.setenv("AX_MLX_BIN", str(bin_path))
    monkeypatch.setenv("AX_GEMMA_E2B_MODEL_PATH", str(model_dir))

    spawn_count = {"n": 0}

    def fake_popen(*a: Any, **k: Any) -> MagicMock:
        spawn_count["n"] += 1
        return MagicMock()

    monkeypatch.setattr(_mlx_server.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(_mlx_server, "_port_open", lambda *a, **k: True)
    monkeypatch.setattr(_mlx_server, "_wait_health", lambda *a, **k: None)

    _mlx_server.ensure_running("gemma4:e2b")
    assert spawn_count["n"] == 0, "포트 점유 시 spawn 안 함"


def test_ensure_running_raises_on_missing_bin(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    monkeypatch.setenv("AX_MLX_BIN", str(tmp_path / "does-not-exist"))
    with pytest.raises(FileNotFoundError, match="AX_MLX_BIN"):
        _mlx_server.ensure_running("gemma4:e2b")


def test_ensure_running_raises_on_missing_model_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    bin_path = tmp_path / "mlx_vlm.server"
    bin_path.write_text("#!/bin/sh\nsleep 1\n")
    bin_path.chmod(0o755)
    monkeypatch.setenv("AX_MLX_BIN", str(bin_path))
    monkeypatch.setenv("AX_GEMMA_E2B_MODEL_PATH", str(tmp_path / "no-model"))
    with pytest.raises(FileNotFoundError, match="model dir"):
        _mlx_server.ensure_running("gemma4:e2b")


# -- shutdown_all: SIGTERM → SIGKILL escalation ----------------------------


def test_shutdown_all_sends_sigterm_to_process_group(monkeypatch: pytest.MonkeyPatch) -> None:
    proc = MagicMock()
    proc.pid = 12345
    # 첫 poll은 None(살아있음 → killpg SIGTERM 보냄), 그 후 0(죽음 → polling 종료)
    poll_seq = iter([None, 0, 0, 0])
    proc.poll.side_effect = lambda: next(poll_seq)
    _mlx_server._PROCS["gemma4:e2b"] = proc

    killed: list[tuple[int, int]] = []
    monkeypatch.setattr(_mlx_server.os, "getpgid", lambda pid: pid)
    monkeypatch.setattr(_mlx_server.os, "killpg", lambda pgid, sig: killed.append((pgid, sig)))

    _mlx_server.shutdown_all(timeout=0.1)
    assert (12345, signal.SIGTERM) in killed
    assert all(sig != signal.SIGKILL for _, sig in killed), "즉시 응답 시 SIGKILL 안 보냄"


def test_shutdown_all_escalates_to_sigkill_on_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proc = MagicMock()
    proc.pid = 12346
    proc.poll.return_value = None  # 끝까지 안 죽음
    proc.wait.side_effect = lambda timeout=None: None
    _mlx_server._PROCS["gemma4:e2b"] = proc

    killed: list[tuple[int, int]] = []
    monkeypatch.setattr(_mlx_server.os, "getpgid", lambda pid: pid)
    monkeypatch.setattr(_mlx_server.os, "killpg", lambda pgid, sig: killed.append((pgid, sig)))

    _mlx_server.shutdown_all(timeout=0.2)
    assert (12346, signal.SIGTERM) in killed
    assert (12346, signal.SIGKILL) in killed, "SIGTERM 무응답 → SIGKILL escalate"


def test_shutdown_all_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    proc = MagicMock()
    proc.pid = 12347
    poll_seq = iter([None, 0, 0])
    proc.poll.side_effect = lambda: next(poll_seq)
    _mlx_server._PROCS["gemma4:e2b"] = proc

    killed: list[tuple[int, int]] = []
    monkeypatch.setattr(_mlx_server.os, "getpgid", lambda pid: pid)
    monkeypatch.setattr(_mlx_server.os, "killpg", lambda pgid, sig: killed.append((pgid, sig)))

    _mlx_server.shutdown_all(timeout=0.1)
    first = list(killed)
    _mlx_server.shutdown_all(timeout=0.1)
    assert killed == first, "두 번째 호출은 no-op"


def test_shutdown_all_handles_already_dead_process(monkeypatch: pytest.MonkeyPatch) -> None:
    """프로세스가 이미 죽어있으면 killpg 호출 자체를 건너뛴다."""
    proc = MagicMock()
    proc.pid = 12348
    proc.poll.return_value = 0  # 이미 종료
    _mlx_server._PROCS["gemma4:e2b"] = proc

    killed: list[Any] = []
    monkeypatch.setattr(_mlx_server.os, "getpgid", lambda pid: pid)
    monkeypatch.setattr(_mlx_server.os, "killpg", lambda pgid, sig: killed.append((pgid, sig)))

    _mlx_server.shutdown_all(timeout=0.05)
    assert killed == [], "이미 죽은 프로세스에 killpg 안 보냄"


def test_shutdown_all_swallows_process_lookup_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """PGID 조회 실패(이미 reap됨) 시 silently skip."""
    proc = MagicMock()
    proc.pid = 12349
    proc.poll.return_value = None
    _mlx_server._PROCS["gemma4:e2b"] = proc

    def raise_lookup(_pid: int) -> int:
        raise ProcessLookupError

    monkeypatch.setattr(_mlx_server.os, "getpgid", raise_lookup)
    # 예외가 새어나오지 않아야 한다.
    _mlx_server.shutdown_all(timeout=0.05)


# -- cleanup hook registration ---------------------------------------------


def test_register_cleanup_once_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    atexit_calls: list[Any] = []
    monkeypatch.setattr(_mlx_server.atexit, "register", lambda fn: atexit_calls.append(fn))
    monkeypatch.setattr(_mlx_server.signal, "signal", lambda sig, h: None)
    monkeypatch.setattr(_mlx_server.signal, "getsignal", lambda sig: signal.SIG_DFL)

    _mlx_server._register_cleanup_once()
    _mlx_server._register_cleanup_once()
    assert len(atexit_calls) == 1, "atexit.register는 한 번만"


def test_register_cleanup_registers_signal_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_mlx_server.atexit, "register", lambda fn: None)
    sigs_set: list[int] = []
    monkeypatch.setattr(
        _mlx_server.signal,
        "signal",
        lambda sig, h: sigs_set.append(int(sig)),
    )
    monkeypatch.setattr(_mlx_server.signal, "getsignal", lambda sig: signal.SIG_DFL)

    _mlx_server._register_cleanup_once()
    assert int(signal.SIGTERM) in sigs_set
    assert int(signal.SIGINT) in sigs_set
    assert int(signal.SIGHUP) in sigs_set


def test_ensure_running_registers_cleanup_on_first_spawn(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    bin_path = tmp_path / "mlx_vlm.server"
    bin_path.write_text("#!/bin/sh\nsleep 1\n")
    bin_path.chmod(0o755)
    model_dir = tmp_path / "model"
    model_dir.mkdir()

    monkeypatch.setenv("AX_MLX_BIN", str(bin_path))
    monkeypatch.setenv("AX_GEMMA_E2B_MODEL_PATH", str(model_dir))

    fake_proc = MagicMock()
    fake_proc.poll.return_value = None
    fake_proc.pid = 88888

    monkeypatch.setattr(_mlx_server.subprocess, "Popen", lambda *a, **k: fake_proc)
    monkeypatch.setattr(_mlx_server, "_wait_health", lambda *a, **k: None)
    monkeypatch.setattr(_mlx_server, "_port_open", lambda *a, **k: False)

    register_calls: list[Any] = []
    monkeypatch.setattr(_mlx_server, "_register_cleanup_once", lambda: register_calls.append(None))

    _mlx_server.ensure_running("gemma4:e2b")
    assert len(register_calls) == 1


# -- integration: real port_open check (loopback) --------------------------


def test_port_open_returns_false_for_unused_port() -> None:
    # 49152 이상 ephemeral 포트 중 고정값은 점유 가능성 있어, 매우 큰 값 사용.
    assert _mlx_server._port_open(54329) is False
