# Anonymization Policy — AX Showcase

본 레포는 실고객 데이터를 직접 보관하지 않는다. 일부 케이스가 실고객 컨설팅에서 영감을 받았으나, 회사명·인물명·구체 수치는 모두 가공된 가상 데이터(AX상사 + Faker 시드)로 대체된다.

## 실고객 영감 케이스 (5건)

| 케이스 | 카테고리 | 영감 출처 (외부 보관) |
|--------|---------|--------------------|
| case02 | excel    | 1Password vault — `ax-showcase/inspirations` |
| case04 | messaging| 동상 |
| case06 | docgen   | 동상 (정부지원사업 양식은 공개 자료라 양식 자체는 사용 가능) |
| case08 | ocr      | 동상 |
| case10 | ai       | 동상 |

매핑 (어느 케이스가 어느 실고객에서 영감 받았는지) 자체는 **이 레포에 보관하지 않는다**. 대신:

1. **1Password vault**: `ax-showcase/inspirations` 항목 (사용자 GPG/SSH 키로 보호)
2. **age 암호화 옵션**: `age -e anonymization_map.md > anonymization_map.md.age` (1Password 미사용 시)
3. **레포 내 sentinel**: `.no_real_data` (이미 존재) — 실고객 데이터 미보관 표지

## 익명화 원칙

| 원칙 | 적용 |
|------|------|
| 회사명·인물명 직접 노출 금지 | 콩코드/노인철 → AX상사/김사장 |
| 실데이터 직접 사용 금지 | 거래처명·금액·날짜 모두 Faker로 생성 |
| 비즈니스 프로세스만 차용 | 패턴·구조만 재현, 구체 수치 노출 X |
| 공개 정보만 인용 가능 | 정부지원사업 양식 등 공공저작물 OK |
| 시연 시 표현 | "비슷한 제조업 패턴 일반화" — 실회사명 단정 X |
| NDA 영역 제외 | 도면, 거래조건, 단가표 등 미사용 |

## 시드 데이터 검증

- `personas/sample_data/` 하위 모든 데이터는 Faker 기반 합성 (deterministic seed 고정)
- 합성 시 `Faker(locale="ko_KR")` + 고정 seed → 동일 실행 시 동일 결과
- 영수증·세금계산서 이미지는 Pillow로 합성 (회전·노이즈·블러 추가 — self-OCR risk 회피)

## 데이터 누설 방지

- `.gitignore`에 `secrets/`, `.env`, `**/input/*_real.*` 등록
- `core/common/secrets_mask.py`로 webhook URL·OAuth 토큰 자동 마스킹
- 시연 전용 Discord 서버 별도 운영 (사내 NDA 채널과 분리)

## 위반 발견 시

실고객 데이터가 레포에 우발적으로 들어간 경우:
1. 즉시 해당 commit revert + force-push (사용자 명시 승인 후만)
2. webhook URL/API 키가 노출됐다면 즉시 폐기·재발급
3. lessons.md에 발견 패턴 기록

---
References:
- design v2.1 §8 (`/Volumes/포터블/AX/showcase/specs/2026-04-30-design.md`)
- Phase 2 plan T0 (`/Volumes/포터블/AX/showcase/specs/2026-05-01-phase2-plan.md`)
