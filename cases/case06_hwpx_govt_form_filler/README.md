# Case 06 — 정부지원사업 신청서 HWPX 자동 작성

## 시나리오
김사장이 매년 정부지원사업(TIPA·SMTECH·K-Startup 등) 신청서를 직접 채울 때 양식 8~12 필드 채우기 + 회사명·대표자·사업자번호·신청금액 오타 검수에 약 30분이 든다. 양식별 칸 위치가 미묘하게 다르고, 한 자리 오타가 발견되는 시점은 이미 제출 후라 재제출이 자주 필요하다.

이 케이스는 AX상사 신청 데이터를 한 번에 HWPX 양식의 8개 필드(회사명·대표자명·사업자등록번호·사업분야·신청금액·매출액·직원수·신청일자)에 채워 30초 내 결과 .hwpx를 산출한다.

## 실행
```bash
# 본 케이스는 외부 API가 없습니다 (로컬 hwpx-editor 스킬만 호출).
DEMO_SAFE=1 uv run python runner.py case06_hwpx_govt_form_filler --safe
uv run python runner.py case06_hwpx_govt_form_filler

# 직접 모듈 실행 (runner.safe_mode 인터셉트 무관 — 동일 결과)
uv run python -m cases.case06_hwpx_govt_form_filler.scenario
```

### 입력 데이터
- 양식: `personas/sample_data/forms/grant_application_template.hwpx`
- 신청 데이터: `personas/sample_data/grant_data.AX_TRADING_GRANT` (TypedDict)

### 양식 fixture 한계 (live demo 시 교체 필수)
현 fixture는 실 정부지원사업 양식이 아니라, MIT-라이선스 Skeleton.hwpx 파생물에 8행×2열 표를 주입한 **stand-in**입니다. 실 TIPA/SMTECH 양식은 재배포 라이선스가 불명확해 레포 포함을 보류했습니다. **라이브 시연 직전 운영자가 실제 사업별 .hwpx를 같은 경로로 교체**해야 합니다 (셀 좌표가 동일하지 않으면 `cell_fills`도 함께 조정). 자세한 내용: `personas/sample_data/forms/LICENSE.md`.

## 결과
- `output/grant_application_filled.hwpx` — 채워진 신청서 (한글 GUI에서 열어 시각 확인)

`hwpx.extract_text` 로 8개 값이 모두 결과 파일에 포함됐는지 자동 검증되어 `verification_passed=True/False`로 반환됩니다.

## 시각 확인
**자동 미리보기 미지원** — T16 rhwp PoC가 실패해 (`specs/rhwp-poc-decision.md`) 자동 렌더링 경로가 없습니다. 시연 흐름:
1. scenario 실행 → 콘솔에 "📄 채워진 양식: ..." 출력
2. 출력 .hwpx를 한글(Hancom Office)에서 직접 열기
3. 라벨/값 8쌍 확인 (좌측 라벨, 우측 채워진 값)

`qlmanage` (macOS Quick Look)는 .hwpx mime 미인식으로 빈 미리보기만 표시합니다 — 시도하지 마세요.

## 시연 임팩트
- Before: 신청서 1건당 양식 직접 작성 + 오타 검수 약 30분
- After: 30초 이내, 같은 회사 데이터로 양식만 갈아끼우면 매년/매 사업별 재사용
- 오타 0: 사업자번호·신청금액이 코드의 단일 source(grant_data)에서 오므로 양식별 재입력 시 발생하는 한 자리 오타가 원천 차단

## 주의
- `output/grant_application_filled.hwpx` 에는 사업자번호·신청금액 등 민감 데이터가 들어가므로 시연 환경 외 공유 금지
- Live demo 직전 fixture를 실 사업 양식으로 교체 + `_GRANT_TABLE_ID` / `_FIELD_ORDER` 가 양식 셀 위치와 일치하는지 확인
- hwpx-editor 스킬 (`/Users/jerome/.claude/skills/hwpx-editor/`) 의존 — 환경 변수 `AX_HWPX_EDITOR_DIR` 로 위치 override 가능
