# Critical Gaps — AX Showcase

미해결 이슈·결정 대기 사항. 해소 시 제거.

## Phase 2 진행 중 (2026-05-02 시점)

### 1. rhwp PoC 미수행 (Group G T16)
- design v2.1 §11: case06 진입 전 rhwp PoC 1일 의무
- plan v2 Deviation 2: PoC 실패 시 case06 fallback (Quick Look)
- **결정 필요**: PoC 옵션 A (HOP CLI subprocess) 1차 평가, 실패 시 옵션 B/C 또는 fallback
- 위험: PoC 실패 시 case06 시연 임팩트 하락
- `qlmanage -p file.hwpx`는 hwpx mime 미인식 가능 → hwpx → docx/pdf 임시 변환 경로 추가 필요

### 2. DoD §13 N6 — 실 영수증 10장 hold-out 검증 미수행 (T22)
- spec v2.1 변경점 21번: "OCR ≥90%는 잠정치, 실 영수증 10장 hold-out 교차 검증으로 보정"
- plan v2 Deviation 4: 데이터 확보 가능 시 수행, 불가 시 Phase 3 deferred
- **결정 시점**: Phase 2 Week 2 안 (T22 진입 시)
- 미수행 시 T25 (DoD integration) acceptance에 "DoD partially passed (N6 deferred)" 라벨링

### 3. case10 whisper deferral (Phase 3로 명시 deferred)
- plan v2 Deviation 3: 텍스트 입력만, 음성→텍스트는 Phase 3
- 결정 문서: `specs/case10-whisper-decision.md` (untracked)
- Phase 3 진입 시 옵션 A (openai-whisper) / B (OpenRouter audio API) / C (macOS 음성 인식) 평가

### 4. weasyprint 폴백 보류 (Phase 2 plan v2 Deviation 5)
- T0 진행 중 발견: system libs 의존성 OSError
- T5 결정: 폴백 없이 raise (시연 안정성 + 단순성 우선)
- **재검토 시점**: Phase 3 또는 다음 컨설팅 프로젝트에서 docgen 재사용 시
- 옵션: brew + weasyprint vs reportlab vs md-to-pdf only

### 5. safe_mode dummy 호환 architectural debt (Group H 또는 별도 chore)
- case03/04/05 모두 scenario에서 `{"_safe": True, ...}` dict 직접 감지 → SendResult/dict[Any] TypedDict 계약 bypass
- **해결안 후보**:
  - (a) `safe_mode.intercept` stub이 진입점별 contract 호환 dummy 반환하도록 통일
  - (b) send/build_quote 등 진입점에서 dummy 정규화 자체 처리
- 결정 시점: Group H 진입 시 또는 별도 chore commit

### 6. `core/excel/reader.py::read_excel(column_map=...)` 헬퍼 부재 (T2 deviation)
- case01/02/03/04/05/07 모두 `pd.read_excel` 직접 호출 + scenario 내부 column_map 적용
- **개선**: `core.excel.reader`에 `read_excel(path, *, column_map) -> pd.DataFrame` 헬퍼 추가하면 코드 중복 제거
- Group H refactor 후보 (모든 case scenario 영향 → 회귀 테스트 강화 필요)

## Phase 2 진입 전 환경 점검 (참고)

- `OPENROUTER_API_KEY` (실제 시연 시)
- `DISCORD_WEBHOOK_URL` (실제 시연 시)
- Ollama 데몬 + `gemma4:e2b`, `gemma4:e4b` 모델
- `npx` + md-to-pdf 스킬 (case05/06)
- Gmail OAuth 또는 SMTP credentials (case03)
- HWPX 정부지원사업 양식 라이선스 확인 (case06)
- `uv run python runner.py --check --strict` 통과 확인 (모든 의존성 사전 검증)

## case06 진입 전 의무 PoC

- **rhwp** (Rust+WASM, MIT) 미리보기 렌더링 검증 1일 (옵션 A 우선)
- 실패 시 fallback 변환 경로 (hwpx → docx/pdf 임시) 결정 필요
