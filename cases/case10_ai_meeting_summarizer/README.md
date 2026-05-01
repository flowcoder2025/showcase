# Case 10 — 회의록 AI 요약 + 액션아이템 추출

## 시나리오

김사장이 매 회의 후 30분간 정리·할당·기한 메모를 손으로 정리한다.
이 케이스는 텍스트 회의록을 입력으로 받아 LLM이 자동으로

1. 핵심 요약
2. 액션 아이템 표 (담당자 / 할 일 / 기한)
3. 결정사항 리스트

를 markdown으로 출력한다.

**owner hallucinate 방지**: `_meeting_meta.json`에 회의별 attendees ground truth를
강제 — LLM이 명단 외 인물에게 액션을 배정하면 fail-loud (`core.ai.tasks.summarize_meeting`).

## 실행

```bash
# 라이브 (OpenRouter 호출)
uv run python -m cases.case10_ai_meeting_summarizer.scenario

# 안전 모드 (deterministic dummy)
DEMO_SAFE=1 uv run python -m cases.case10_ai_meeting_summarizer.scenario

# 런처 경유
uv run python runner.py case10_ai_meeting_summarizer --safe
```

기본 입력 디렉토리는 `input/`이며, 비어 있으면
`personas/sample_data/meeting_transcripts/`로 fallback한다 (시드 5건 포함).

## 한계 / Phase 3 연기 사항

- **음성 → 텍스트 (whisper)**: design v2.1 §7는 "음성 → 요약" 흐름을 명시하지만
  Phase 2에서는 텍스트 입력만 지원한다. 결정 근거는
  [`specs/case10-whisper-decision.md`](../../specs/case10-whisper-decision.md) 참조.
- **참석자 자동 분리**: 현재는 `_meeting_meta.json`에서 attendees를 받는다.
  발화자 자동 식별은 Phase 3 음성 입력 도입과 함께 검토.

## 구조

```
case10_ai_meeting_summarizer/
├── scenario.py          # thin wrapper (run())
├── meta.yaml            # runner 노출용
├── README.md            # 이 파일
├── input/               # 사용자 .txt 회의록 + _meeting_meta.json (없으면 fallback)
└── output/              # meeting_summary_{stem}.md (실행 결과)
```
