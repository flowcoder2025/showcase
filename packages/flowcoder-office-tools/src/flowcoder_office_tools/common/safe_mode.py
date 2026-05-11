"""DEMO_SAFE 모드 — 외부 호출 인터셉트 + 캐시 + 자동 폴백.

규칙:
- 외부 호출 함수는 모듈 참조로 호출해야 patch가 먹는다 (`from core.x import y; y.fn()` ✓)
- INTERCEPT_TARGETS에 (모듈경로, 함수명) 등록된 함수만 patch

T37 (Phase 3-A): ``is_safe()`` / ``force_safe()`` 모두 :mod:`core.common.safe_mode_v2`
(ContextVar 기반)에 위임. ``force_safe()`` 는 더 이상 ``os.environ`` 을 변경하지
않는다 (R1-H3). ``intercept()`` 는 T44 까지 동작 유지 — 새 코드는 Backends DI
패턴 (``core.backends.factory.safe_backends``) 사용을 권장.
"""

import hashlib
import importlib
import json
import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import Token
from pathlib import Path
from typing import Any
from unittest.mock import patch

from rich.console import Console

from flowcoder_office_tools.common import safe_mode_v2

_console = Console()

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def is_safe() -> bool:
    """T37 shim — :func:`core.common.safe_mode_v2.is_safe` 위임."""
    return safe_mode_v2.is_safe()


def force_safe(reason: str) -> Token[bool | None]:
    """런타임 자동 폴백 — OpenRouter 429/MLX timeout 등에서 호출.

    T37 변경:
        - ``os.environ["DEMO_SAFE"]`` 변경 0 (R1-H3) — ContextVar 기반.
        - Token 반환 (R2-M3) — 호출자가 caller-controlled scope에서 reset 가능.

    T41.5 정합:
        - 기존 호출자 (``core/ocr/gemma.py``, ``core/ai/client.py``,
          ``core/messaging/email.py``) 는 token을 discard 한다 — case 안에서
          force_safe 가 누적되어도 후속 백엔드 호출이 safe-mode 로 동작하도록
          (intentional sticky failover).
        - Cross-case leak 차단은 :func:`intercept` 가 entry-time 값을
          ``safe_mode_scope`` 로 lock 해서 처리. case 종료 시 자동 복원.
        - 따라서 호출자가 token 을 받아 직접 reset 할 필요 없음 (return Token 은
          contract 보존을 위해 유지 — 명시적 scope 가 필요한 caller 가 사용).
    """
    token = safe_mode_v2.force_safe()
    _console.print(f"[bold yellow][AUTO-SAFE] {reason}[/bold yellow]")
    return token


INTERCEPT_TARGETS: dict[str, tuple[str, str]] = {
    "openrouter": ("flowcoder_office_tools.ai.client", "chat"),
    "ollama_gemma": ("flowcoder_office_tools.ocr.gemma", "extract"),
    "discord_webhook": ("flowcoder_office_tools.messaging.discord", "send"),
    "gmail": ("flowcoder_office_tools.messaging.email", "send"),
}


def _cache_root() -> Path:
    """Cache 디렉터리 base — ``AX_CACHE_DIR`` env override → ``<repo>/cases`` default.

    T39 (G5): cwd-independence — 임의 cwd에서 호출돼도 캐시 위치가 흔들리지
    않도록 절대 경로 anchor. 테스트가 cwd-isolated 캐시를 원하면
    ``monkeypatch.setenv("AX_CACHE_DIR", str(tmp_path / "cases"))`` 사용.
    Resolution은 호출 시점이라 fixture/monkeypatch 호환.
    """
    override = os.environ.get("AX_CACHE_DIR")
    return Path(override) if override else _REPO_ROOT / "cases"


def cache_path(case_id: str, key: str) -> Path:
    return _cache_root() / case_id / "output" / "_cached" / f"{key}.json"


def _key(qualname: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    payload = json.dumps([qualname, list(args), sorted(kwargs.items())], default=str)
    return hashlib.sha1(payload.encode()).hexdigest()[:16]


def _make_stub(case_id: str, mod: str, fn: str) -> Callable[..., Any]:
    qualname = f"{mod}.{fn}"

    def stub(*args: Any, **kwargs: Any) -> Any:
        key = _key(qualname, args, kwargs)
        cpath = cache_path(case_id, key)
        if cpath.exists():
            data = json.loads(cpath.read_text(encoding="utf-8"))
            _console.print(f"[dim][SAFE] cache hit: {qualname}[/dim]")
            return data.get("result")
        _console.print(f"[yellow][SAFE] cache miss → dummy: {qualname}[/yellow]")
        return {"_safe": True, "qualname": qualname, "args_key": key}

    return stub


@contextmanager
def intercept(case_id: str, apis: list[str]) -> Iterator[None]:
    """meta.yaml의 external_apis 목록만 patch. 컨텍스트 종료 시 자동 복원.

    NOTE: INTERCEPT_TARGETS는 빌드되지 않은 모듈을 가리킬 수 있다 (Phase 진행 중).
    import 실패 시 명시적 warning을 출력하고 patch 없이 진행한다 — 그 경우
    실제 외부 호출이 발생할 수 있으므로 호출자(runner.py)는 missing 모듈을
    --check에서 사전 감지해야 한다.

    T41.5+: case 진입 시 ``safe_mode_v2`` 의 ContextVar 값을 lock 한다 — 시나리오
    안에서 :func:`force_safe` 가 호출돼도 컨텍스트 종료 시 entry-time 상태로
    복원된다. 이전 동작은 force_safe 가 다음 시나리오까지 leak 됐다 (caller-
    controlled scope 미적용 — critical-gaps §1). 이제 boundary = case 단위.
    """
    initial_safe = is_safe()
    with safe_mode_v2.safe_mode_scope(initial_safe):
        if not initial_safe:
            yield
            return

        patches = []
        skipped = []
        for api in apis:
            if api not in INTERCEPT_TARGETS:
                _console.print(f"[red][SAFE] unknown API: {api}[/red]")
                continue
            mod, fn = INTERCEPT_TARGETS[api]
            try:
                importlib.import_module(mod)
            except ImportError:
                skipped.append((api, mod))
                _console.print(
                    f"[bold yellow][SAFE] WARNING: cannot import {mod} for "
                    f"api={api} — patch SKIPPED, real call may proceed[/bold yellow]"
                )
                continue
            p = patch(f"{mod}.{fn}", _make_stub(case_id, mod, fn))
            try:
                p.start()
            except Exception as e:
                _console.print(f"[red][SAFE] failed to patch {api}: {e}[/red]")
                continue
            patches.append(p)

        if skipped and not patches:
            _console.print(
                "[bold red][SAFE] all targets skipped — intercept is no-op for this case[/bold red]"
            )

        try:
            yield
        finally:
            for p in patches:
                try:
                    p.stop()
                except RuntimeError:
                    # patcher wasn't started (or already stopped) — ignore so
                    # remaining patches still get cleaned up.
                    pass


def save_cache(
    case_id: str,
    qualname: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    result: Any,
) -> Path:
    """라이브 실행 결과를 캐시에 저장 (시연 캐시 사전 생성용)."""
    key = _key(qualname, args, kwargs)
    cpath = cache_path(case_id, key)
    cpath.parent.mkdir(parents=True, exist_ok=True)
    cpath.write_text(json.dumps({"result": result}, default=str), encoding="utf-8")
    return cpath
