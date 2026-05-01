"""md → PDF 변환 — md-to-pdf 스킬 (npx tsx) subprocess 호출.

Deviation 5 (2026-05-01 T0): weasyprint 폴백은 system libs 의존성 때문에 보류.
md-to-pdf 스킬 호출 실패 시 raise — 시연 안정성은 runner.py --check --strict로 사전 검증.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Literal

DEFAULT_MD_TO_PDF_DIR = "/Users/jerome/.claude/skills/md-to-pdf"
DEFAULT_MD_TO_PDF_SCRIPT = "scripts/md-to-pdf.ts"
DEFAULT_TIMEOUT = 60

StyleLiteral = Literal["document", "report", "minimal"]


class MdToPdfError(RuntimeError):
    """md-to-pdf 스킬 호출 실패."""


def md_to_pdf(
    md_path: Path | str,
    out_path: Path | str,
    *,
    style: StyleLiteral = "document",
    timeout: int | None = None,
) -> None:
    """Markdown 파일을 PDF로 변환.

    환경변수 override:
    - AX_MD_TO_PDF_DIR: 스킬 디렉토리 (기본: /Users/jerome/.claude/skills/md-to-pdf)
    - AX_MD_TO_PDF_SCRIPT: 상대 경로 (기본: scripts/md-to-pdf.ts)
    - AX_MD_TO_PDF_TIMEOUT: 타임아웃 초 (기본: 60)

    Raises:
        FileNotFoundError: md_path 미존재 또는 스킬 경로 미존재
        MdToPdfError: subprocess 실패, 타임아웃, npx 미존재, 또는 결과 파일 누락
    """
    md_abs = Path(md_path).resolve()
    out_abs = Path(out_path).resolve()
    if not md_abs.exists():
        raise FileNotFoundError(f"md input not found: {md_abs}")

    skill_dir = Path(os.environ.get("AX_MD_TO_PDF_DIR", DEFAULT_MD_TO_PDF_DIR))
    script = os.environ.get("AX_MD_TO_PDF_SCRIPT", DEFAULT_MD_TO_PDF_SCRIPT)
    if not skill_dir.exists():
        raise FileNotFoundError(f"md-to-pdf skill dir not found: {skill_dir}")

    eff_timeout = (
        timeout
        if timeout is not None
        else int(os.environ.get("AX_MD_TO_PDF_TIMEOUT", str(DEFAULT_TIMEOUT)))
    )

    out_abs.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            ["npx", "tsx", script, str(md_abs), str(out_abs), "--style", style],
            cwd=str(skill_dir),
            check=True,
            capture_output=True,
            timeout=eff_timeout,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        raise MdToPdfError(
            f"md-to-pdf failed (exit {e.returncode}): stdout={e.stdout!r} stderr={e.stderr!r}"
        ) from e
    except subprocess.TimeoutExpired as e:
        raise MdToPdfError(f"md-to-pdf timeout after {eff_timeout}s") from e
    except FileNotFoundError as e:
        raise MdToPdfError(f"npx/tsx not found in PATH: {e}") from e

    if not out_abs.exists():
        raise MdToPdfError(
            f"md-to-pdf returned 0 but output file missing: {out_abs}\n"
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
