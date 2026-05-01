# Case 07 — 영수증 일괄 OCR → 경비 정리 엑셀

## 시나리오
박과장이 한 달 모은 영수증 100장 수기 입력하는 데 3시간. 이 케이스는 Ollama 로컬에서 Gemma 4 E2B로 가맹점·금액·일자를 자동 추출해 회계SW 임포트용 엑셀로 정리한다.

## 실행
```bash
# 사전 준비 (1회): Ollama 데몬 + 모델 풀
ollama pull gemma3:4b   # gemma4:e2b 별칭 — Phase 2 진입 전 환경 점검

# 시연
uv run python -m cases.case07_ocr_receipt_to_excel.scenario

# safe 모드 (Ollama 미설치 시)
DEMO_SAFE=1 uv run python runner.py case07_ocr_receipt_to_excel --safe
```

## 입력
- `cases/case07_ocr_receipt_to_excel/input/` 에 영수증 png/jpg를 넣으면 우선 사용.
- 비어 있으면 `personas/sample_data/receipts/` 의 합성 영수증 100장 fallback.

## 출력
- `cases/case07_ocr_receipt_to_excel/output/expense_report.xlsx`
- 컬럼: `거래일`, `가맹점`, `카테고리`, `결제수단`, `금액` (회계SW 임포트 호환).

## 시연 임팩트
- Before: 박과장 3시간 수기 입력 (180분)
- After: ~1분 (Ollama warm 후 영수증당 ~600ms)
- 정확도: 가맹점 90%+, 금액 95%+ (합성 영수증 hold-out 측정)

## Gemma 4 콜드스타트 안내
- 첫 영수증 처리 시 Gemma 4 E2B 모델 로딩에 5~10초.
- `runner.py`가 백그라운드 warmup을 트리거 (case07 진입 시 자동).
- 시연 직전 `uv run python runner.py --check --strict`로 Ollama 데몬 + 모델 ping 확인.

## 가상 데이터의 한계 (Risk Disclosure)
- `personas/sample_data/receipts/`의 영수증은 Pillow로 합성한 가상 데이터.
- 노이즈/회전/블러를 적용해 self-OCR 자기충족 위험을 줄였으나, 실 영수증과 조명·배경·폰트 차이로 정확도가 다를 수 있음.
- 시연 전 실 영수증 10장 hold-out 검증 필수 (DoD §13 N6).

## 1분 대본
`docs/demo_scripts/case07.md` 참조.
