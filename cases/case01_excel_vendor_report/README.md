# Case 01 — 거래처별 월별 매출 보고서 자동 생성

## 시나리오
박과장이 매월 거래처 30곳 엑셀을 받아 합치고 피벗·차트로 보고서 만드는 일 — 평소 3시간.
이 케이스는 `personas/sample_data/vendors/`의 12개월 거래 데이터를 5초 안에 통합 보고서로.

## 실행
```bash
uv run python -m cases.case01_excel_vendor_report.scenario
```

## 시연 임팩트
- Before: 박과장 3시간 (180분)
- After: 5초
- 배수: ~2160배

## 1분 대본
`/Volumes/포터블/AX/showcase/docs/demo_scripts/case01.md` 참조.
