# Phase 2 외부 사용 약속 (R1-C2)

**작성일**: 2026-05-02 (Phase 2 T23)
**목적**: 3-reviewer audit R1-C2 — Phase 2 종료 후 1주 안에 실 미팅·강의에서 1회
이상 시연하지 않으면 "production-ready" 주장이 reviewer feedback 사용처
없이 self-validation으로 끝난다는 위험을 방지.

## 약속 (commitment)

> **Phase 2 종료 후 1주 안에 실제 고객 미팅 또는 강의에서 1회 이상 본 쇼케이스를
> 시연**한다.

- 시연 대상 케이스는 시점에 따라 자유롭게 선택 (case01/02/03/04/05/07/09/10 중).
- 시연 후 본 파일에 일자·청중·관찰 결과를 append한다.
- 시연 시 `runner.py --check --strict`이 통과하지 않으면 시연 자체를 보류한다.

## 약속 충족 추적 (Fulfillment Log)

| 일자 | 청중 | 시연 케이스 | 관찰 / 후속 액션 |
|------|------|-------------|------------------|
| _(미정)_ | _(미정)_ | _(미정)_ | _(미정)_ |

> 약속 충족 즉시 위 표에 row append + `## Status` 섹션을 `fulfilled`로 변경한다.

## Status

- **상태**: under-fulfilled (0/1 시연 — 약속 자체는 보존)
- **마감**: Phase 2 종료 (T26 README finalize) + 1주
- **하드 마감일** (R3-L2): **2026-05-09** — 본 약속은 캘린더상 이 날짜까지
  미충족 시 "production-ready" 주장을 retract하고 Phase 3 게이트를 차단한다.
  (작성일 2026-05-02 기준 +7일.)
- **소유자**: 본인 (showcase 운영자)

## Retraction (2026-05-08, T32 commit)

**"production-ready" 라벨 자체를 retract**한다. 약속(외부 시연 1회 이상)은 **보존**한다.

**Retract 사유**:
1. Phase 3 design v2.1 (HEAD `b5ffe0f`) 기준 Phase 3 의도가 **"재사용 라이브러리 추출 + 사내 단일 user 데모"**로 재정렬됨. SaaS production-ready 주장은 더 이상 의미 없음.
2. 외부 사용 시연 약속은 보존 — **0/1 미충족 사실을 마감 도래 전 정직 인정**.
3. 본래 우려 ("외부 reviewer feedback 부재 → self-validation 위험")는 다음으로 이중 처리:
   - (1) 외부 사용 약속 1회 이상 — **유지** (이 파일 추적표)
   - (2) dogfood fixture CI 통과 — **추가 검증** (재사용 가능성 코드로 증명, design v2.1 §5.1)

**라벨 변경**:
- 이전: "production-ready" 주장 (외부 시연 2회로 검증 예정)
- 이후: "사내 도구 + 재사용 라이브러리 추출" (외부 reviewer feedback 미수집 인정, dogfood로 import 가능성 증명)

**향후**:
- 외부 사용 (1) 충족 시 → 위 추적표에 row append + Status `partially-fulfilled` (1+/?)
- dogfood (2) 활성화 (T45) 시 → 영구 PR merge 차단 조건
- 둘 다 충족 시 → "검증된 재사용 라이브러리 + 외부 시연 검증" 라벨

## 관련 문서

- 3-reviewer audit R1-C2: `specs/2026-05-01-phase2-plan.md` (audit findings 섹션)
- Phase 2 plan: `specs/2026-05-01-phase2-plan.md`
- Phase 3 v2.1 design (게이트 정직 정정): `specs/2026-05-08-phase3-design-v2.md` (commit `b5ffe0f`)
- 시연 대본: `docs/demo_scripts/`
