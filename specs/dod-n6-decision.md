# DoD §13 N6 Hold-Out Decision (R2-M2)

- **Date**: 2026-05-02
- **Evaluator**: T22 (Phase 2 Group H DoD verification)
- **Status**: **partially passed**
- **Plan reference**: `specs/2026-05-01-phase2-plan.md` lines 1913-1924, 1988 (Deviation 4)

## Background

Plan v2 N6 hold-out 요구사항: 합성 영수증·세금계산서로 측정된 OCR 정확도 ≥90%
주장은 **잠정치**다. 실 영수증/세금계산서 10장 hold-out 교차 검증으로 보정해야
"DoD §13 N6 통과"로 라벨링 가능하다. 합성 데이터는 self-OCR 자기충족 위험
(생성 파이프라인이 만든 글꼴/노이즈/레이아웃을 같은 모델이 OCR하므로 실세계
캡처 대비 오차가 과소평가됨).

## Decision

이 세션에서 N6 hold-out을 **수행하지 않는다**. 대신 **partially passed**로
명시적으로 라벨링하고, Phase 3 진입 시 충족해야 할 조건을 잠근다.

### Reason

1. 레포에는 실 영수증/세금계산서가 존재하지 않는다. `personas/sample_data/`
   하위 자산은 모두 Pillow 합성 이미지 + ground truth JSON 쌍이며, 익명화
   정책상 실 고객 데이터를 레포에 포함하지 않는다 (`anonymization_policy.md`).
2. 실 데이터 확보는 별도 운영 절차가 필요하다 (콩코드/번영에프씨/온고롱 또는
   AX상사 페르소나의 가상 거래처에서 동의 기반 샘플 수집). 이는 컨설팅 실행
   단계 산출물이지 Phase 2 쇼케이스 셋업의 책임 범위가 아니다.
3. 합성 데이터 기준 ≥90% 통과는 별도 시험으로 검증한다
   (`test_case08_synthetic_accuracy_at_least_90_percent`). 이 시험은 ground
   truth 파일이 명시한 30장 중 corrupt 표시 (corrupt_supplier=True 또는
   corrupt_buyer=True) 2장을 제외한 28건이 검증을 통과해야 함을 강제한다 →
   28/30 = 93.3%.

## Phase 3 Entry Conditions (N6 final-pass 조건)

다음 모두 충족 시 N6를 "fully passed"로 승격하고 본 문서를 업데이트한다.

- [ ] 실 영수증 ≥ 10장 확보 (`personas/real_holdout/receipts/` 또는 외부 vault).
- [ ] 실 세금계산서 ≥ 10장 확보 (`personas/real_holdout/invoices/`).
- [ ] 각 hold-out 세트에 대해 case07/case08 시나리오를 **non-safe-mode** 로
      실행 (실제 Ollama Gemma 4 E2B/E4B 호출).
- [ ] 정확도 측정: 영수증은 (merchant, amount, date) 3-필드 정확 일치율 ≥90%,
      세금계산서는 (invoice_no, supplier_biznum, buyer_biznum, total_supply,
      total_vat) 5-필드 정확 일치율 ≥90%.
- [ ] hold-out 결과를 `specs/dod-n6-results.md` 로 기록하고 본 문서 status를
      "fully passed"로 갱신.

## Test Lock

`tests/test_phase2_dod_ocr.py::test_dod_n6_holdout_partially_passed_marker`
는 본 문서의 존재 + "partially passed" 라벨 + "Phase 3" 참조를 강제한다.
이는 partially-passed 상태가 **누락이 아닌 의도된 결정**임을 회귀 테스트로
잠그는 장치다 — 본 문서를 삭제하거나 라벨을 무단 상향하면 테스트가 실패한다.
