# Case 06 — 시연 대본 (정부지원사업 신청서 HWPX 자동 작성)

김사장 페르소나. AX상사 김사장이 매년 정부지원사업 신청서를 직접 양식에 채우면서 30분씩 쓰는 흐름을 30초로 줄이는 시연.

## 0. 시연 환경 사전 점검 (시연 시작 전 운영자 단독)

> **양식 fixture는 stand-in입니다.** 실제 사업 양식이 아니라 MIT 라이선스 Skeleton.hwpx 파생 8행×2열 표입니다. 라이브 시연에서 "TIPA 양식"이라 부를 거면 시연 직전에 진짜 양식으로 교체하세요 — `personas/sample_data/forms/grant_application_template.hwpx`. 셀 위치가 다르면 `cases/case06_hwpx_govt_form_filler/scenario.py`의 `_GRANT_TABLE_ID`/`_FIELD_ORDER` 도 함께 조정.

> **자동 미리보기 없음** — T16 rhwp PoC 실패. 시연 마지막에 "한글에서 직접 열기" 단계가 들어갑니다.

## 1분 버전 (고객 미팅 도입부)

**[10초] 페인 제시**
> "AX상사 김사장님은 매년 정부지원사업 신청서 4~5건 양식을 직접 채웁니다. 한 건당 8~12 필드, 회사명·대표자·사업자번호·신청금액·매출액. 30분짜리 작업인데 진짜 짜증 나는 건 사업자번호 한 자리 오타가 제출 후에 발견된다는 거죠."

**[5초] 실행**
```bash
uv run python -m cases.case06_hwpx_govt_form_filler.scenario
```
→ 콘솔: `정부지원사업 신청서 HWPX 자동 채움 완료: before 30m → after 0.0s`

**[30초] 결과**
- 출력 파일 경로 콘솔에 표시 → 한글로 결과 .hwpx 열기
- 회사명/대표자명/사업자등록번호/사업분야/신청금액/매출액/직원수/신청일자 8필드가 양식 우측 칸에 그대로 들어가 있음

**[15초] 임팩트**
> "회사 데이터가 코드의 단일 source(grant_data.py)에 있어서 양식만 갈아끼우면 매년 다른 사업, 다른 양식에 같은 데이터가 그대로 흘러 들어갑니다. 사업자번호 오타가 발생할 수 없는 구조."

## 3분 버전 (메인 시연)
1분 버전 + 다음 추가:

**[+30초] 데이터 한 곳, 양식 여러 개 시연**
- `personas/sample_data/grant_data.py` 열고 `AX_TRADING_GRANT` 보여주기 — 이게 진짜 회사 신청 정보
- "이 한 dict가 진실의 출처. 양식 .hwpx만 사업별로 바꾸면 동일 데이터로 재사용."
- (선택) 양식 fixture를 다른 셀 구조로 교체해 같은 데이터로 한 번 더 채우기 — 같은 8개 값이 다른 양식에 들어가는 모습 시연

**[+30초] 검증 게이트 시연**
- scenario 반환값 확인: `verification_passed=True`, `missing_values=[]`
- "extract_text 로 결과 .hwpx 안에 8개 값이 다 들어갔는지 자동 검증. 양식이 셀 위치 잘못 잡거나 채우기 실패하면 missing_values에 안 들어간 값이 그대로 떨어집니다."

**[+30초] Q&A 핵심**
- "한글 없는 환경에서도 미리보기 가능?" → "현재는 No. T16에서 rhwp(Rust+WASM HWPX 렌더러) PoC 진행했는데 실패해 자동 미리보기는 보류 (specs/rhwp-poc-decision.md). 시연·검수 시점엔 한글 GUI 필요."
- "양식별 셀 좌표가 다른데?" → "`_GRANT_TABLE_ID`와 `_FIELD_ORDER`만 양식별로 한 번 잡으면 같은 데이터로 재사용. 사업별 5분 셋업."
- "사업자번호 검증?" → "case08과 동일 모듈러스 알고리즘 재사용 가능. 본 케이스는 채우기에 집중하지만 grant_data 입력단에 검증 추가는 한 줄."

## 5분 버전 (강의)
3분 버전 + 다음 추가:

**[+1분] 라이선스·정직성 명시**
> "지금 보여드린 양식은 실제 TIPA 양식이 아닙니다. MIT 라이선스 오픈소스 hwpxcore의 Skeleton.hwpx에 8행 표를 한 번 주입해 만든 stand-in이에요. 실 정부 양식은 재배포 라이선스가 불명확해서 레포에 안 넣었습니다. 도입하실 때는 사업별 양식을 그 자리에 바꿔서 쓰시면 됩니다 — 셀 좌표만 한 번 매핑."

**[+1분] hwpx-editor 스킬 활용 흐름**
- `core/docgen/hwpx.py`가 hwpx-editor 스킬(MIT 외부 패키지)을 감싸 fill_form / extract_text 두 함수만 노출
- 스킬 위치 환경변수 (`AX_HWPX_EDITOR_DIR`) override → CI / 타 사용자 환경 호환
- 결과 .hwpx의 표 id/구조가 살아있어 한글에서 추가 편집/서명 가능

**[+30초] 향후 개선 (rhwp PoC 후일담)**
> "rhwp(Rust+WASM)로 자동 미리보기 시도했는데 PoC 단계에서 텍스트 노드가 빠지는 이슈로 실패. Phase 3에서 양식별 docx/pdf 사후 변환 또는 한글 자체 CLI render 옵션 재검토 예정. 지금은 시연 마지막에 한글 GUI에서 한 번 열어 확인하는 흐름으로 갑니다."
