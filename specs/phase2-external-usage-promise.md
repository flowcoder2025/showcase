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

- **상태**: pending
- **마감**: Phase 2 종료 (T26 README finalize) + 1주
- **하드 마감일** (R3-L2): **2026-05-09** — 본 약속은 캘린더상 이 날짜까지
  미충족 시 "production-ready" 주장을 retract하고 Phase 3 게이트를 차단한다.
  (작성일 2026-05-02 기준 +7일.)
- **소유자**: 본인 (showcase 운영자)

## 관련 문서

- 3-reviewer audit R1-C2: `specs/2026-05-01-phase2-plan.md` (audit findings 섹션)
- Phase 2 plan: `specs/2026-05-01-phase2-plan.md`
- 시연 대본: `docs/demo_scripts/`
