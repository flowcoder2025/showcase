"""AX Showcase 시연 런처.

Usage:
    uv run python runner.py                  # 메뉴 모드
    uv run python runner.py case01           # 직접 실행
    uv run python runner.py --check          # 환경 점검
    uv run python runner.py --list           # 케이스 목록만
    DEMO_SAFE=1 uv run python runner.py case09  # 안전 모드
"""

import argparse
import importlib
import os
import platform
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.table import Table

from core.common import config, safe_mode
from core.common.demo_logger import demo_logger

console = Console()


def discover_cases() -> list[dict[str, Any]]:
    """cases/ 디렉토리 스캔 → meta.yaml 목록 반환.

    개별 meta.yaml 파싱 실패 시 warning + skip — 한 케이스의 손상이
    전체 런처를 막지 않도록 한다.
    """
    log = demo_logger("discover")
    cases_dir = Path("cases")
    out: list[dict[str, Any]] = []
    if not cases_dir.exists():
        return out
    for case_dir in sorted(cases_dir.iterdir()):
        meta_file = case_dir / "meta.yaml"
        if not meta_file.exists():
            continue
        try:
            meta = yaml.safe_load(meta_file.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            log.warning(f"skip case {case_dir.name}: invalid meta.yaml ({e})")
            continue
        if not isinstance(meta, dict):
            log.warning(f"skip case {case_dir.name}: meta.yaml is not a mapping")
            continue
        meta["_dir"] = case_dir
        out.append(meta)
    return out


def warm_up_gemma_async() -> None:
    """Ollama Gemma 4 더미 추론 1회로 콜드스타트 회피 (백그라운드)."""

    def _warm() -> None:
        try:
            import ollama

            for model in ("gemma4:e2b",):
                try:
                    ollama.generate(model=model, prompt="warm-up")
                except Exception:
                    pass
        except ImportError:
            pass

    t = threading.Thread(target=_warm, daemon=True)
    t.start()


def cmd_check(strict: bool = False) -> int:
    """환경 점검 — 의존성·키·webhook·Ollama.

    strict=False (기본): 의존성만 hard fail, 키·데이터 누락은 warning.
    strict=True (시연 직전): 키·데이터 누락도 hard fail.
    """
    log = demo_logger("check")
    ok = True

    # 의존성 (항상 hard fail)
    for mod in ("pandas", "openpyxl", "rich", "yaml", "openai", "discord_webhook"):
        try:
            importlib.import_module(mod)
        except ImportError as e:
            log.error(f"missing dep: {mod} ({e})")
            ok = False

    # API 키 (strict 모드에선 hard fail)
    def _check_required(name: str, value: str | None, strict_msg: str) -> None:
        nonlocal ok
        if not value:
            if strict:
                log.error(f"[STRICT] {name} missing — {strict_msg}")
                ok = False
            else:
                log.warning(f"{name} missing — {strict_msg}")

    _check_required(
        "OPENROUTER_API_KEY", os.getenv("OPENROUTER_API_KEY"), "AI 케이스는 --safe로만 실행 가능"
    )
    _check_required(
        "DISCORD_WEBHOOK_URL",
        os.getenv("DISCORD_WEBHOOK_URL"),
        "messaging 케이스는 --safe로만 실행 가능",
    )

    # 샘플 데이터
    if not Path("personas/sample_data/vendors.xlsx").exists():
        msg = "sample_data 미생성 — `uv run python personas/sample_data/generate.py`"
        if strict:
            log.error(f"[STRICT] {msg}")
            ok = False
        else:
            log.warning(msg)

    # Ollama Gemma 4 모델 존재 — strict 모드에서만 hard-fail (design §5)
    if strict:
        ok = _check_ollama_gemma(log) and ok
        ok = _check_discord_webhook(log) and ok
        ok = _check_email_transport(log) and ok
        ok = _check_md_to_pdf_skill(log) and ok

    log.success("--check 통과" if ok else "--check 실패")
    return 0 if ok else 1


def _check_md_to_pdf_skill(log: Any) -> bool:
    """strict 모드: md-to-pdf 스킬 디렉토리 존재 + npx 명령 PATH 검증.

    Phase 2 case05/T5에서 추가된 PDF 생성 의존성. AX_MD_TO_PDF_DIR로 override
    가능 (테스트·휴대용 환경). npx --version 호출이 5초 내에 응답해야 한다.
    """
    skill_dir_str = os.environ.get("AX_MD_TO_PDF_DIR", "/Users/jerome/.claude/skills/md-to-pdf")
    skill_dir = Path(skill_dir_str)
    if not skill_dir.exists():
        log.error(f"[STRICT] md-to-pdf skill dir not found: {skill_dir}")
        return False
    try:
        subprocess.run(
            ["npx", "--version"],
            check=True,
            capture_output=True,
            timeout=5,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        log.error(f"[STRICT] npx not available: {e}")
        return False
    return True


def _check_email_transport(log: Any) -> bool:
    """strict 모드: Gmail OAuth credential 또는 SMTP credential + ``GMAIL_SENDER``.

    Phase 2 case03용. 시연 시 둘 다 없으면 case03는 --safe로만 실행 가능.
    ``GMAIL_SENDER``는 ``email.build_message`` From 헤더로 사용되며 누락 시
    빌드 시점에 실패하므로 strict check에서 사전 차단한다 (T8.5).
    """
    gmail_creds = os.getenv("GMAIL_OAUTH_CREDENTIALS", "")
    has_gmail = bool(gmail_creds) and Path(gmail_creds).exists()
    has_smtp = bool(os.getenv("SMTP_HOST")) and bool(os.getenv("SMTP_USER"))
    if not (has_gmail or has_smtp):
        log.error(
            "[STRICT] no email transport configured — set GMAIL_OAUTH_CREDENTIALS "
            "(file must exist) or SMTP_HOST+SMTP_USER. case03 will only run in --safe mode."
        )
        return False
    if not os.getenv("GMAIL_SENDER"):
        log.error(
            "[STRICT] GMAIL_SENDER not set — case03 build_message will fail. "
            "Set GMAIL_SENDER='Display Name <user@example.com>'."
        )
        return False
    return True


def _check_ollama_gemma(log: Any) -> bool:
    """strict 모드: Ollama 데몬에 gemma4 모델이 설치돼있는지 검증."""
    try:
        import ollama
    except ImportError:
        log.error("[STRICT] ollama package not installed — `uv add ollama`")
        return False
    try:
        listing = ollama.list()
    except (ConnectionError, OSError) as e:
        log.error(f"[STRICT] ollama daemon unreachable: {e}")
        return False
    # Response shape: {"models": [{"model": "gemma4:e2b", ...}, ...]} or
    # an object with .models attribute (depends on ollama-python version).
    models_raw: Any = (
        listing.get("models", []) if isinstance(listing, dict) else getattr(listing, "models", [])
    )
    names: list[str] = []
    for m in models_raw:
        if isinstance(m, dict):
            n = m.get("model") or m.get("name") or ""
        else:
            n = getattr(m, "model", None) or getattr(m, "name", "") or ""
        if n:
            names.append(str(n))
    if not any(n.startswith("gemma4") for n in names):
        log.error(
            f"[STRICT] gemma4 model not found in ollama; installed={names!r} — "
            "`ollama pull gemma4:e2b`"
        )
        return False
    return True


def _check_discord_webhook(log: Any) -> bool:
    """strict 모드: Discord webhook URL 도달 가능 여부 (HEAD 200/204).

    Note: discord webhook도 GET을 받으면 200 + payload를 반환하지만, HEAD는
    Method Not Allowed(405)일 수 있다. 실제 운영 시연에선 webhook 호출이
    실패해도 case04 자체가 dry-run으로 동작하도록 설계돼 있으므로, 여기선
    "URL이 응답 자체는 한다"는 최소한의 reachability만 검증한다.
    """
    url = os.getenv("DISCORD_WEBHOOK_URL", "")
    if not url:
        # 위에서 _check_required가 이미 strict 시 ok=False 처리함
        return True
    # urllib.request의 보안 정책상 외부 fetch가 도구 권한 문제를 유발할 수 있어
    # Phase 2에서 정식 reachability 체크로 확장한다 (현재 기본 GET 응답으로 충분).
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            status = getattr(resp, "status", None) or resp.getcode()
        if status in {200, 204}:
            return True
        log.error(f"[STRICT] discord webhook returned status={status}")
        return False
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        log.error(f"[STRICT] discord webhook unreachable: {e}")
        return False


def cmd_list() -> int:
    cases = discover_cases()
    table = Table(title="AX 사무자동화 쇼케이스")
    table.add_column("ID", style="cyan")
    table.add_column("제목")
    table.add_column("카테고리", style="green")
    table.add_column("Before", style="dim")
    table.add_column("After", style="bold")
    for c in cases:
        table.add_row(
            c["id"],
            c["title"],
            c.get("category", ""),
            c.get("before", ""),
            c.get("after", ""),
        )
    console.print(table)
    return 0


def open_finder(path: Path) -> None:
    if platform.system() == "Darwin" and path.exists():
        try:
            subprocess.run(["open", str(path)], check=False)
        except Exception:
            pass


def run_case(case_id: str, safe: bool) -> int:
    cases = {c["id"]: c for c in discover_cases()}
    if case_id not in cases:
        console.print(f"[red]case not found: {case_id}[/red]")
        return 1
    if safe:
        os.environ["DEMO_SAFE"] = "1"

    meta = cases[case_id]
    apis = meta.get("external_apis", [])

    case_dir = meta["_dir"]
    module_name = f"cases.{case_dir.name}.scenario"
    mod = importlib.import_module(module_name)

    # 시나리오 시작 시점을 기록 — 자동 열기 시 "이번 실행"이 만든 파일만 대상
    start_mtime = time.time()
    with safe_mode.intercept(case_id, apis=apis):
        result = mod.run()

    # 결과 자동 열기 — 이번 실행 이후 생성/갱신된 비-언더스코어 파일만
    out_dir = case_dir / "output"
    if out_dir.exists():
        for f in sorted(out_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True):
            if f.is_file() and not f.name.startswith("_") and f.stat().st_mtime >= start_mtime:
                open_finder(f)
                break
    return 0 if result is None or result == 0 else 1


def cmd_menu() -> int:
    cmd_list()
    cases = discover_cases()
    while True:
        choice = console.input("\n선택 (id 또는 q): ").strip()
        if choice.lower() == "q":
            return 0
        if any(c["id"] == choice for c in cases):
            run_case(choice, safe=safe_mode.is_safe())
        else:
            console.print(f"[yellow]not found: {choice}[/yellow]")


def main() -> None:
    # config.load()가 내부적으로 .env를 os.environ에 주입한다 (dotenv 일원화).
    config.load()
    parser = argparse.ArgumentParser()
    parser.add_argument("case_id", nargs="?")
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--strict", action="store_true", help="--check와 함께 사용 — 키·데이터 누락도 fail"
    )
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--safe", action="store_true")
    args = parser.parse_args()

    warm_up_gemma_async()

    if args.check:
        sys.exit(cmd_check(strict=args.strict))
    if args.list:
        sys.exit(cmd_list())
    if args.case_id:
        sys.exit(run_case(args.case_id, safe=args.safe))
    sys.exit(cmd_menu())


if __name__ == "__main__":
    main()
