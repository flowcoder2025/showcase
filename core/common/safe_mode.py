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
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import Token
from pathlib import Path
from typing import Any
from unittest.mock import patch

from rich.console import Console

from core.common import safe_mode_v2

_console = Console()


def is_safe() -> bool:
    """T37 shim — :func:`core.common.safe_mode_v2.is_safe` 위임."""
    return safe_mode_v2.is_safe()


def force_safe(reason: str) -> Token[bool | None]:
    """런타임 자동 폴백 — OpenRouter 429/MLX timeout 등에서 호출.

    T37 변경:
        - ``os.environ["DEMO_SAFE"]`` 변경 0 (R1-H3) — ContextVar 기반.
        - Token 반환 (R2-M3) — 호출자가 caller-controlled scope에서 reset 가능.
        - 기존 호출자 (``core/ocr/gemma.py``, ``core/ai/client.py``,
          ``core/messaging/email.py``) 는 token을 discard — context 수명 동안
          override 유지. T38 에서 scenario 시그니처 변경 시 scope 정합화.
    """
    token = safe_mode_v2.force_safe()
    _console.print(f"[bold yellow][AUTO-SAFE] {reason}[/bold yellow]")
    return token


INTERCEPT_TARGETS: dict[str, tuple[str, str]] = {
    "openrouter": ("core.ai.client", "chat"),
    "ollama_gemma": ("core.ocr.gemma", "extract"),
    "discord_webhook": ("core.messaging.discord", "send"),
    "gmail": ("core.messaging.email", "send"),
}


def cache_path(case_id: str, key: str) -> Path:
    return Path("cases") / case_id / "output" / "_cached" / f"{key}.json"


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
    """
    if not is_safe():
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
