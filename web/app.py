"""Phase 3-Web T47/T48 — Streamlit MVP entry point.

Local-only demo surface for the in-house consulting flow. Bound to 127.0.0.1
via ``.streamlit/config.toml`` + the assertion at module load — both layers
must succeed for external exposure to be possible.

T48 wires per-case input forms (``web/_inputs.py``) and the upload-isolated
execution flow (``web/_runs.py``). T49 will replace the post-run JSON dump
with the rich result-card UI and progress adapter.
"""

from __future__ import annotations

import sys
from pathlib import Path

# `streamlit run web/app.py` 실행 시 sys.path[0] = web/ 디렉토리만 들어가고
# repo root 는 누락된다. pytest 처럼 `from web.* import ...` 가 resolve 되도록
# repo root 를 sys.path 에 보강 (다른 모든 import 보다 먼저 — E402 noqa).
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import importlib  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
from collections.abc import Callable  # noqa: E402
from typing import Any, TypedDict, cast  # noqa: E402

import streamlit as st  # noqa: E402
from flowcoder_office_tools.backends.factory import (  # noqa: E402
    default_backends,
    safe_backends,
)
from flowcoder_office_tools.common.safe_mode_v2 import safe_mode_scope  # noqa: E402
from flowcoder_office_tools.ocr import _mlx_server  # noqa: E402
from flowcoder_office_tools.protocols import (  # noqa: E402
    ScenarioResult,
    serialize_result,
)

from web._inputs import render_input_form  # noqa: E402
from web._render import render_result  # noqa: E402
from web._runs import (  # noqa: E402
    cleanup_expired_runs,
    create_run_dir,
    mark_active,
    mark_done,
    stream_save,
    validate_upload_path,
)

_ADDR = os.environ.get("STREAMLIT_SERVER_ADDRESS", "127.0.0.1")
assert _ADDR in {"127.0.0.1", "localhost"}, f"외부 노출 금지: STREAMLIT_SERVER_ADDRESS={_ADDR!r}"


RUNS_ROOT = Path("runs")
_PER_FILE_MB = 50
_TOTAL_UPLOAD_CAP_BYTES = 200 * 1024 * 1024


CASES: list[tuple[str, str]] = [
    ("case01_excel_vendor_report", "거래처 월별 매출 보고서"),
    ("case02_excel_invoice_validation", "단가 검증 + Discord 이상치 알림"),
    ("case03_email_quote_dispatch", "견적 메일 일괄 발송"),
    ("case04_discord_overdue_alert", "미수금 단계별 Discord 알림"),
    ("case05_doc_quote_generator", "견적서/거래명세서 (Word + PDF)"),
    ("case06_hwpx_govt_form_filler", "정부지원사업 HWPX 양식"),
    ("case07_ocr_receipt_to_excel", "영수증 OCR → 경비 정리"),
    ("case08_ocr_invoice_to_csv", "세금계산서 OCR → 회계 CSV"),
    ("case09_ai_email_drafter", "AI 메일 초안 (3안)"),
    ("case10_ai_meeting_summarizer", "회의록 요약 + 액션아이템"),
]


class ExecuteResult(TypedDict):
    run_id: str
    result: ScenarioResult
    run_dir: Path


def execute_case(
    case_id: str,
    form_result: dict[str, Any],
    *,
    safe_mode: bool,
) -> ExecuteResult:
    """Persist uploads under a fresh run_dir and invoke the scenario.

    Streaming write enforces ``_PER_FILE_MB`` per upload (R1-H1/H2). Total
    upload size is capped at ``_TOTAL_UPLOAD_CAP_BYTES`` to bound disk usage
    across multi-file cases. ``mark_active`` / ``mark_done`` protect the run
    directory from TTL reclamation while the scenario is executing (R1-H4).
    The result is serialized through :func:`serialize_result` so ``run.json``
    cannot leak secrets even if the scenario forgets to mask them (R1-C1).
    """
    run_dir = create_run_dir(RUNS_ROOT)
    in_dir = run_dir / "input"
    out_dir = run_dir / "output"
    mark_active(run_dir)
    try:
        total_bytes = 0
        for uf in form_result.get("uploaded_files", []):
            target = in_dir / uf.name
            validate_upload_path(RUNS_ROOT, target)
            # R1-H2 fail-early: pass the remaining headroom so a single file
            # cannot blow through the total cap before we get a chance to look.
            remaining = _TOTAL_UPLOAD_CAP_BYTES - total_bytes
            written = stream_save(
                uf,
                target,
                per_file_mb=_PER_FILE_MB,
                remaining_total=remaining,
            )
            total_bytes += written

        scenario_mod = importlib.import_module(f"cases.{case_id}.scenario")
        run_fn = cast(Callable[..., ScenarioResult], scenario_mod.run)
        backs = safe_backends() if safe_mode else default_backends()
        config: dict[str, Any] = dict(form_result.get("config", {}))

        with safe_mode_scope(safe_mode):
            result = run_fn(
                input_dir=in_dir if any(in_dir.iterdir()) else None,
                output_dir=out_dir,
                backends=backs,
                config=config or None,
            )

        run_json = run_dir / "run.json"
        run_json.write_text(
            json.dumps(serialize_result(result), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return ExecuteResult(run_id=run_dir.name, result=result, run_dir=run_dir)
    finally:
        mark_done(run_dir)


def main() -> None:
    st.set_page_config(page_title="AX Showcase", layout="wide")
    st.title("AX Showcase — 사무자동화 시연")

    # TTL start hook (R1-H4): reclaim stale run dirs before serving the page.
    # Active runs and any holding a `.lock` file are skipped by cleanup_expired_runs.
    cleanup_expired_runs(RUNS_ROOT, ttl_hours=24)

    with st.sidebar:
        st.subheader("실행 모드")
        running = bool(st.session_state.get("running", False))
        safe_mode = st.toggle(
            "Safe mode (외부 호출 차단)",
            value=bool(st.session_state.get("safe_mode", False)),
            disabled=running,
            help="외부 API 호출 없이 캐시·더미 응답으로 실행. 실행 중에는 변경 불가.",
        )
        st.session_state["safe_mode"] = safe_mode

        with st.expander("MLX OCR 서버 (메모리 관리)", expanded=False):
            mlx_running = _mlx_server.list_running()
            if mlx_running:
                for alias, info in mlx_running.items():
                    st.text(f"{alias}: port={info['port']}, pid={info['pid']}")
                if st.button(
                    "MLX 서버 종료",
                    key="mlx_shutdown",
                    disabled=running,
                    help="case07/08 OCR 후 weight 가 GPU 에 상주합니다. 다음 OCR "
                    "이 없으면 종료해 메모리 회수 (다음 OCR 시 자동 재spawn).",
                ):
                    _mlx_server.shutdown_all()
                    st.success("MLX 서버 종료됨")
                    st.rerun()
            else:
                st.caption("실행 중인 MLX 서버 없음")

    st.subheader("케이스 선택")
    cols = st.columns(2)
    for idx, (case_id, title) in enumerate(CASES):
        col = cols[idx % 2]
        clicked = col.button(
            # Markdown hard line break (trailing 2-space + \n) — Streamlit
            # button label 의 multi-line wrap 이 viewport width 에 따라 갈리는
            # 불일치를 차단해 모든 카드가 "타이틀(상단) / case_id(하단)" 2줄로
            # 일관 표시.
            f"**{title}**  \n`{case_id}`",
            use_container_width=True,
            key=f"case_btn_{case_id}",
        )
        if clicked:
            st.session_state["selected_case"] = case_id

    selected = st.session_state.get("selected_case")
    if not selected:
        return

    st.divider()
    st.subheader(f"실행: {selected}")
    form_result = render_input_form(selected)

    run_clicked = st.button("실행", type="primary", key=f"run_{selected}")
    if not run_clicked:
        return

    st.session_state["running"] = True
    try:
        with st.spinner("실행 중..."):
            execute_result = execute_case(
                selected,
                form_result,
                safe_mode=bool(st.session_state.get("safe_mode", False)),
            )
    except Exception as exc:
        st.error(f"실행 실패: {exc}")
        return
    finally:
        st.session_state["running"] = False

    st.success(f"실행 완료 — run_id={execute_result['run_id']}")
    render_result(execute_result)


if __name__ == "__main__":
    main()
