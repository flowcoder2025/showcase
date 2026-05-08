# Case 10 — Whisper deferral decision (Phase 2)

## Decision

음성 → 텍스트 변환(whisper)은 Phase 2에서 제외하고 Phase 3로 deferred. Phase 2 case10은
**텍스트 회의록 입력만** 받아 요약 + 액션아이템 + 담당자 추출까지 수행한다.

Plan v2 Deviation 3으로 disclosure됨 (`specs/2026-05-01-phase2-plan.md`).
Phase 2 close commit (T26) 시점까지의 deviation 5건 중 하나.

## 평가 옵션 (Phase 3 진입 시 재평가)

### Option A — `openai-whisper` (로컬)
- 장점: API 키 불필요, 오프라인 동작, 한국어 정확도 양호 (large-v3 기준).
- 단점: 모델 크기 (large 1.5GB), 첫 로딩 30~60s, M5 Pro에서 large는 ~10x realtime.
- 시연 적합도: 사전 변환은 OK, 라이브 변환은 콜드스타트가 시연 흐름을 깰 위험.

### Option B — OpenRouter audio API
- 장점: 콜드스타트 없음, 클라우드 처리.
- 단점: 추가 API 비용, 네트워크 의존, 레포의 OpenRouter 폴백 체인과 통합 필요.
- 시연 적합도: 라이브 시연에 적합.

### Option C — macOS 음성 인식 (SFSpeechRecognizer)
- 장점: 운영체제 내장, 무료, 한국어 지원.
- 단점: macOS 한정 (다른 컨설팅 환경 비호환), Python 바인딩 부재 (PyObjC 필요).
- 시연 적합도: 시연 머신 고정 시 OK — 재사용성 낮음.

## Phase 3 결정 기준

- 라이브 음성 시연 빈도가 높으면 → B (OpenRouter audio).
- 오프라인 데모 / 사내 NDA 환경이 다수면 → A (`openai-whisper`, 사전 warmup).
- 시연 머신이 고정이면 → C 검토 가능.

본 결정 문서는 deferral 사실의 disclosure + Phase 3 평가 매트릭스 기록 목적이다.
참조: `cases/case10_ai_meeting_summarizer/`, `docs/demo_scripts/case10.md`,
`tests/test_phase2_dod_ai.py::test_case10_whisper_deferral_marker`.
