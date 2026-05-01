# Case 10 시연 대본 — 회의록 AI 요약

페르소나: **김사장** — 매 회의 후 정리·할당·기한 메모를 손으로 30분간 정리.

## 1분 시연

**[Before]** "회의 끝나고 정리 30분이면 다음 미팅 들어가는데도 빠듯해요. 누가 뭐 하기로 했는지 또 까먹고."

```bash
uv run python -m cases.case10_ai_meeting_summarizer.scenario
```

**[After]** 화면에서 `meeting_summary_m001_monthly_sales.md` 열기 → 김사장 페르소나로:

> "회의 1건이 5초. 요약·액션·기한·결정사항이 표로 다 정리됐네요. 박과장은 5월 5일까지
> 미수금 회수, 이대리는 5월 12일까지 콩코드물산 견적. 메모 안 잃어버리고 바로 카톡으로
> 공유 가능합니다."

핵심 한 줄: **"30분 → 5초, 누가 뭐 할지 표 형태로 즉시 파악."**

## 3분 시연

1. **회의록 5건 일괄 처리** (1분)

   ```bash
   uv run python -m cases.case10_ai_meeting_summarizer.scenario
   ```

   `output/`에 5개 markdown 파일 생성됨. ⏱ 표시: "회의록 요약 (5건) 완료: before 30m → after Xs (~Y배)".

2. **담당자별 액션 아이템 정확도** (1분)

   `output/meeting_summary_m002_overdue_review.md`를 열고 액션 아이템 표를 보여준다.

   - 최주임: 4월 25일까지 상록기업 입금 일정 확정
   - 박과장: 4월 30일까지 새한물산 신용 재검토 통지

   강조: **회의록 본문에서 발화자 + 기한 + 할 일을 정확히 매칭한다.**

3. **owner hallucinate 방지** (1분)

   `_meeting_meta.json` 파일을 보여주며:

   > "AI가 명단 외 사람한테 일을 떠넘기는 hallucinate 문제, 우리는 attendees ground truth로
   > 강제했습니다. m002에는 김사장·박과장·최주임만 등록돼 있어서 LLM이 다른 이름 만들어내면
   > 바로 fail해요."

## 5분 시연

3분 시연 + 차별화 포인트 2가지

4. **ChatGPT 대비 차별화** (1분)

   - ChatGPT 웹UI: 매번 회의록 복붙·프롬프트 재작성·결과 재포맷 → 5건 처리에 15분
   - 이 시스템: 1번 실행 → 5건 일괄 → markdown 파일로 저장 → 사내 공유 즉시 가능
   - **owner ground truth 강제 + 캐시 deterministic** (caching → 라이브 시연 재현 가능)

5. **Phase 3 로드맵: 음성 입력** (1분)

   > "지금은 텍스트 회의록 입력입니다. 회의 자체는 녹음만 하고, 서기 노트 또는 자동 STT 결과를
   > 입력으로 넣는 구조에요. **음성 → 텍스트 STT는 Phase 3에서 추가합니다.**
   > whisper 로컬, OpenRouter audio API, macOS Speech 세 옵션 비교 후 결정 예정."

   결정 근거 문서: `specs/case10-whisper-decision.md`

핵심 한 줄: **"회의 정리 30분 → 5건 1분, 담당자 hallucinate 방지, 음성 입력은 Phase 3."**

## 안전 모드 (네트워크/시연 환경 불안정 시)

```bash
DEMO_SAFE=1 uv run python -m cases.case10_ai_meeting_summarizer.scenario
```

deterministic dummy 응답 → "[SAFE-FALLBACK 더미 요약 ...]" 표기. 시연 자체는 끊기지 않고
markdown 출력 형식·표 구조·파이프라인 흐름을 100% 시연 가능.
