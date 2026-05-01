# Case 08 — 세금계산서 OCR → 회계 CSV (Gemma 4 E4B)

## 시나리오
박과장이 거래처 세금계산서 30장을 회계SW에 수기 입력하면서 양측 사업자번호 오타까지 일일이 확인하는 데 4시간. 이 케이스는 Ollama 로컬에서 Gemma 4 E4B로 거래번호·공급자/공급받는자 사업자번호·공급가액·부가세를 자동 추출하고, 한국 사업자번호 모듈러스 체크섬으로 OCR 오인식을 즉시 가려낸 뒤 utf-8(BOM)·cp949 두 인코딩으로 CSV를 export한다.

## 실행
```bash
# 사전 준비 (1회): Ollama 데몬 + 모델 풀
ollama pull gemma3:8b   # gemma4:e4b 별칭 — Phase 2 case08용

# 시드 30장 생성 (idempotent)
uv run python personas/sample_data/generate_invoices.py

# 시연
uv run python -m cases.case08_ocr_invoice_to_csv.scenario

# safe 모드 (Ollama 미설치 시)
DEMO_SAFE=1 uv run python runner.py case08_ocr_invoice_to_csv --safe
```

## 입력
- `cases/case08_ocr_invoice_to_csv/input/` 에 세금계산서 png/jpg를 넣으면 우선 사용.
- 비어 있으면 `personas/sample_data/invoices_scanned/` 의 합성 세금계산서 30장 fallback.

## 출력
- `cases/case08_ocr_invoice_to_csv/output/invoices_utf8.csv` — UTF-8 BOM (Excel 호환).
- `cases/case08_ocr_invoice_to_csv/output/invoices_cp949.csv` — cp949 (레거시 회계SW 호환).
- `cases/case08_ocr_invoice_to_csv/output/validation_failures.json` — 체크섬·VAT 검증 실패 목록.
- 컬럼: `거래일`, `거래번호`, `공급자번호`, `공급자명`, `공급받는자번호`, `공급받는자명`, `공급가액`, `부가세`, `합계`.

## 시연 임팩트
- Before: 박과장 30장 4시간 수기 + 사업자번호 오타 검수 별도.
- After: ~4분 (Ollama warm 후 세금계산서당 ~6초, 30장 ~3분 + CSV 작성 ~수초).
- 회계SW가 cp949만 받는 레거시 환경에서도 즉시 import 가능.
- 사업자번호 체크섬 실패 항목은 별도 JSON으로 분리 — 사람이 직접 확인할 워크큐만 따로.

## Gemma 4 E4B 콜드스타트 안내
- 첫 세금계산서 처리 시 Gemma 4 E4B 모델 로딩에 10~20초 (E2B의 2배).
- E4B는 E2B 대비 정확도 우위, 세금계산서처럼 컬럼이 많은 표준 양식에서 의미가 큼.
- 시연 직전 `uv run python runner.py --check --strict`로 Ollama 데몬 + gemma4 모델 ping 확인.

## 가상 데이터의 한계 (Risk Disclosure)
- `personas/sample_data/invoices_scanned/`의 세금계산서는 Pillow로 합성한 가상 데이터.
- 사업자번호는 알고리즘으로 체크섬을 만족하는 임의값(공인 사업자번호 아님). 의도적으로 2장은 체크섬을 깨뜨려 검증 실패 케이스를 demo에서 노출.
- 노이즈/회전을 적용해 self-OCR 자기충족 위험을 줄였으나 실제 세금계산서와 폰트·여백·도장 흔적 차이가 있음.
- 시연 전 실 세금계산서 5장 hold-out 검증 권장.

## 1분 대본
`docs/demo_scripts/case08.md` 참조.
