"""T37 — safe_mode_v2 (contextvars + force_safe Token + thread isolation).

R1-H3: os.environ mutation 0건.
R2-M3: force_safe() returns Token for caller-controlled reset.
"""

from __future__ import annotations

import os
import threading

import pytest

from core.common.safe_mode_v2 import (
    _SAFE_VAR,
    force_safe,
    is_safe,
    safe_mode_scope,
)


def test_thread_isolation() -> None:
    """ContextVar는 thread 간 격리 — 한 thread의 set이 다른 thread에 영향 0."""
    results: dict[str, bool] = {}

    def in_thread(name: str, enabled: bool) -> None:
        with safe_mode_scope(enabled):
            results[name] = is_safe()

    t1 = threading.Thread(target=in_thread, args=("t1", True))
    t2 = threading.Thread(target=in_thread, args=("t2", False))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    assert results["t1"] is True
    assert results["t2"] is False


def test_force_safe_returns_token_for_reset(monkeypatch: pytest.MonkeyPatch) -> None:
    """R2-M3: force_safe 후 token으로 복귀 가능."""
    monkeypatch.delenv("DEMO_SAFE", raising=False)
    assert is_safe() is False
    token = force_safe()
    try:
        assert is_safe() is True
    finally:
        _SAFE_VAR.reset(token)
    assert is_safe() is False


def test_force_safe_does_not_mutate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """R1-H3: os.environ mutation 0."""
    monkeypatch.delenv("DEMO_SAFE", raising=False)
    token = force_safe()
    try:
        assert os.environ.get("DEMO_SAFE") is None
    finally:
        _SAFE_VAR.reset(token)


def test_safe_mode_scope_yields_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    """safe_mode_scope 컨텍스트 종료 시 자동 reset."""
    monkeypatch.delenv("DEMO_SAFE", raising=False)
    assert is_safe() is False
    with safe_mode_scope(True):
        assert is_safe() is True
    assert is_safe() is False


def test_safe_mode_scope_disable(monkeypatch: pytest.MonkeyPatch) -> None:
    """safe_mode_scope(False) 명시적 disable."""
    monkeypatch.setenv("DEMO_SAFE", "1")
    assert is_safe() is True
    with safe_mode_scope(False):
        assert is_safe() is False
    assert is_safe() is True


def test_is_safe_falls_back_to_env_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    """sentinel default — ContextVar 미설정 시 DEMO_SAFE env 참조."""
    monkeypatch.setenv("DEMO_SAFE", "1")
    assert is_safe() is True
    monkeypatch.setenv("DEMO_SAFE", "0")
    assert is_safe() is False
    monkeypatch.delenv("DEMO_SAFE", raising=False)
    assert is_safe() is False


def test_context_var_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """명시적 set은 env보다 우선."""
    monkeypatch.setenv("DEMO_SAFE", "0")
    with safe_mode_scope(True):
        assert is_safe() is True
    assert is_safe() is False


def test_nested_scopes(monkeypatch: pytest.MonkeyPatch) -> None:
    """nested scope LIFO reset."""
    monkeypatch.delenv("DEMO_SAFE", raising=False)
    with safe_mode_scope(True):
        assert is_safe() is True
        with safe_mode_scope(False):
            assert is_safe() is False
        assert is_safe() is True
    assert is_safe() is False
