# Lessons Learned — AX Showcase

기획 워크스페이스의 `lessons.md`에서 ax-showcase 관련 항목만 분리. 신규 교훈은 여기에 누적.

## Phase 2 (2026-05-01 ~ 진행 중)

- [2026-05-01] **plan 작성 시 외부 의존성은 ls/grep으로 실재 검증 후 기술**. 추정·가정은 plan 보호 효과를 약화시킨다. v1 plan에서 md-to-pdf 경로 (`convert.js` 가짜), client.chat 시그니처 (str 반환인데 response.content 가정), hwpx-editor 호출 (subprocess 가정인데 Python `sys.path.insert + import` 패턴) 3건이 R3 audit에서 적발. v2에서 모두 정정. 같은 패턴: subagent dispatch prompt에서 정확한 사실 정보 제공 시에도 ls/grep으로 실재 확인 우선.
- [2026-05-01] **cumulative file count 측정 기준 명문화 필요**. T7b에서 personas/ 포함 여부에 따라 56 vs 58 차이 발생. T7b.5에서 측정 명령 (`mypy --strict core/ runner.py cases/ personas/sample_data/ <Phase1/2 strict-locked tests>`)을 plan 박스에 명문화. N.5 fixer가 commit body에 명령과 함께 결과 첨부 필수.
- [2026-05-01] **TDD가 ThreadPoolExecutor `__exit__` 차단 버그 잡음** (T9). `with concurrent.futures.ThreadPoolExecutor() as pool` 패턴은 `__exit__`에서 `shutdown(wait=True)`를 강제 → timeout 후에도 worker 완료까지 메인 흐름 차단. `try/finally + shutdown(wait=False)` 패턴으로 정정. 시간 측정 테스트 (15s timeout 설정인데 실제 17s 초과)가 RED 단계에서 catch — TDD 효과적 사례.
- [2026-05-01] **openpyxl 빈 문자열 readback → None 정규화** (T11.5). `cell.value = ""` 저장 후 read 시 `None` 반환. 테스트는 `value in (None, "")` 양쪽 허용으로 작성. CSV/Excel roundtrip 시 동일 현상 가능성.
- [2026-05-01] **rich.markup.escape는 ASCII only** (T6.5). Korean `[브래킷]`은 markup tag로 인식되지 않아 escape 대상 아님. lessons L10 "vendor명 escape" 가이드는 ASCII markup-like 패턴에만 의미 있음. 한국어 데이터에서는 자연 차단.
- [2026-05-01] **weasyprint system libs 의존성** (Pango/Cairo/HarfBuzz) — `import weasyprint`만으로 OSError 발생. macOS는 `brew install pango cairo` 필요. Phase 2 plan v2 Deviation 5로 disclose, T0에서 의존성 보류 + T5에서 폴백 없이 raise 결정.
- [2026-05-01] **ollama Python SDK는 RequestError + ResponseError 둘 다 잡아야 함** (R3-O2 / T9). 클라이언트 측 + 서버 응답 에러로 분리. `Options`는 generation params (temperature 등)이고 timeout은 받지 않음 → client-side `concurrent.futures.ThreadPoolExecutor.future.result(timeout=...)` 사용.
- [2026-05-01] **subagent prompt에 INTEGRITY REQUIREMENT 문구만으로는 부족** (R3-H4). N.5 reviewer가 commit body의 verification 출력 로그를 직접 확인하는 체크리스트로 정착. `ruff check / ruff format --check / mypy --strict / pytest -v` 4가지 명령의 실제 출력을 commit body에 첨부 필수. 빈 출력 / 누락은 "NOT RUN" 명시.
- [2026-05-01] **ruff format 별도 commit 정책 정착**. semantic 변경과 분리. 각 N.5에서 `ruff format --check` 통과 필수, format 누적 필요 시 별도 `WI-T{N}.5-style: ruff format` commit. Phase 1 T18에서 framing 거짓 ("ruff clean" 클레임이 format --check 누락) 적발 후 Phase 2 컨벤션화.
- [2026-05-01] **safe_mode dummy 호환 architectural debt** (case03/04/05 반복 감지). scenario에서 `{"_safe": True, ...}` dict를 직접 감지해 SendResult 호환 처리하는 패턴이 case별 반복. SendResult/dict[Any] TypedDict 계약 bypass. Group H 또는 별도 chore commit으로 통합 처리 권장 — `safe_mode.intercept` stub이 진입점별 contract 호환 dummy 반환하도록 통일, 또는 send/build_quote 등 진입점에서 dummy 정규화.
- [2026-05-01] **`pd.isna` 명시 검증** (T8.5). pandas Excel readback에서 빈 셀이 NaN으로 들어오면 `str(NaN).strip() == "nan"`으로 falsy 가드 우회. 직접 `pd.isna(amount_raw)` 검증 필수.
- [2026-05-01] **N.5 fixer skip 정직성** (T2.5/T6.5/T13.5 등). plan 명시 acceptance 항목이 main task에서 미리 처리된 경우 별도 fixer dispatch 의미 없음. "plan 명시 항목 모두 처리됨" 명시 보고 후 skip이 정직.
- [2026-05-02] **3-reviewer audit 패턴 Phase 2도 효과** — Phase 1 T18 (architecture/quality/integrity) 패턴을 plan 작성 후 적용. R3 (feasibility & honesty)가 외부 의존성 hallucination 3건 + framing 거짓 위험 1건 catch. 단일 reviewer는 framing 편향에 취약 — 3개 독립 시각 cross-check 필수.

## Phase 1 (2026-04-30 ~ 2026-05-01)

- [2026-05-01] `uv run <tool>`이 venv-local인지 반드시 확인. dev deps에 빠져 있으면 homebrew 글로벌이 fallback돼 "가짜 clean" 검증이 발생. `uv pip list | grep <tool>` + `uv run which <tool>`로 `.venv/bin/` 경로 확인 필수
- [2026-05-01] openpyxl-stubs는 `_WorksheetOrChartsheetLike` 다중상속 트릭(Chartsheet + _WorksheetLike) 사용 → `wb.active` 후 `isinstance(ws, Worksheet)` 단독으론 narrowing 불충분. `assert isinstance + cast(Worksheet, ...)` 조합 필요
- [2026-05-01] subagent에게 plan-verbatim 보고를 시키려면 prompt에 "INTEGRITY REQUIREMENT" 섹션 명시 + 모든 deviation을 commit body + report에 disclose 요구. T6 사건에서 implementer가 "verbatim"이라 보고했지만 실제로는 docstrings 누락 + semantic guard 누락 drift 있었음
- [2026-05-01] rich Console에서 `[case01]` 같은 bracketed text는 markup tag로 해석돼 사라짐 → `rich.markup.escape()` 사용 필수. 테스트가 substring만 체크하면 회귀 못 잡음
- [2026-05-01] `timer.measure` ratio = `(before_minutes * 60) / elapsed`. sub-second op (1ms)이면 100만배 표시됨 → 데모에서 신뢰 손상. `min(ratio, 10000)` 클램프 + `max(elapsed, 0.05)` 플로어로 방어
- [2026-05-01] `unittest.mock.patch` 기반 intercept 시 `p.start()` 실패 가능성: `patches.append(p)` 를 `p.start()` 후로 이동 + finally에서 `try/except RuntimeError` 로 stop() 감싸야 일부 patch만 시작된 상태에서도 cleanup 안전
- [2026-05-01] `timedelta(days=30 * offset)` 은 12개월 시드 데이터에 30-day drift 생성 → `relativedelta(months=offset)` 사용해야 정확한 월별 분포
- [2026-05-01] z-score outlier 검출은 group z-score 시 outlier 자체가 std를 inflate해 boundary miss. **leave-one-out z-score** 필수
- [2026-05-01] Discord webhook은 HEAD 요청에 405 반환 → ping 검증은 GET (status 200/204 기준 동일)
- [2026-05-01] **3-reviewer 병렬 audit** (architecture/quality/integrity)이 단일 reviewer의 framing 편향을 catch. T18에서 "ruff clean" 거짓을 integrity reviewer가 발견
- [2026-05-01] **cumulative project lock**: 각 task 신규 파일이 mypy --strict 통과해야 다음 진입. 이전 부채 0 유지하면 Phase 종료 audit에서 14개 이슈도 한 번에 정리 가능

## 외부에서 가져온 관련 교훈

- [2026-03-23] Google API 키 leaked 감지로 차단됨 → OpenRouter 키를 대체 사용. API 키 노출 주의 (.env가 git에 올라간 경우 즉시 재발급)
- [2026-03-23] docx 모듈은 글로벌 설치 아님 → mark-docx skill의 node_modules 경로 직접 참조: `/Users/jerome/.claude/skills/mark-docx/scripts/node_modules/docx`
