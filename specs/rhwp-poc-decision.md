# rhwp PoC Decision — HWPX 미리보기 렌더 평가

**Date**: 2026-05-02
**Evaluator**: AX Showcase Phase 2 T16 작업자
**Project HEAD (pre-T16)**: `89b372f` (T15.5 — case08 validation threshold + column override)
**Plan reference**: `specs/2026-05-01-phase2-plan.md` Task 16 (lines 1654-1723)
**Plan v2 Deviation cross-ref**: Deviation 2 (rhwp PoC 실패 시 Quick Look fallback / Phase 3 deferred 명시 허용)

---

## 1. 평가 목표

case06 (정부지원사업 신청서 HWPX 자동 채우기) 시연 시 운영자가 결과물을
한글 GUI 없이 라이브로 미리보기할 수 있는 경로 확보.

**성공 정의**: 입력 HWPX → PNG 또는 PDF 출력 파일 (≥1KB) 30초 이내,
설치 시간 1시간 이내, 완전 오픈소스 라이선스(MIT/Apache).

---

## 2. 평가 옵션 매트릭스

| 옵션 | 시도 여부 | 설치 명령 시도 | 결과 | 소요 | Blocker |
|------|----------|---------------|------|------|---------|
| **A. HOP CLI** | 시도 | `which hop hop-cli` / `brew info hop` | brew cask로만 존재 (`HOP.app` GUI 앱), CLI 진입점 없음 | 5분 | CLI 인터페이스 부재 — README/저장소 어디에도 headless export 명령 미문서화 |
| **B. rhwp WASM + wasmtime-py** | 스킵 | `which wasmtime` | wasmtime 미설치 + WASM 모듈은 npm `@rhwp/core` (browser용), wasmtime-py 호스트 환경 검증 미수행 | 5분 | WASM 모듈이 브라우저 DOM/Canvas API 의존 가능성 — wasmtime headless 호환성 불확실, 1일 이상 PoC 필요 |
| **C. rhwp 로컬 HTTP 서버** | 스킵 | (해당 없음) | rhwp는 데모 사이트(edwardkim.github.io/rhwp)와 Chrome 확장만 제공 — 로컬 HTTP 서버 entry point 미문서화 | - | 자체 호스팅 워크플로우 부재 |
| **D. rhwp CLI (cargo from source)** | 부분 시도 | `cargo build --release` 미시도 | rhwp v0.7.9 CLI는 SVG export만 지원 (`rhwp export-svg`), PDF/PNG는 v2.0.0 로드맵 | 10분 (조사) | Rust 1.75+ 빌드 30~60분 + SVG→PDF 추가 변환 체인 필요 → 시간 초과 + scope creep |
| **E. LibreOffice headless** | 스킵 | `which soffice libreoffice` / `ls /Applications` | 미설치, brew cask 1GB+ 다운로드 + HWPX 호환성 실측 미보장 | 5분 | 설치 비용 + HWPX 변환 품질 검증에 별도 1일 필요 |
| **F. kordoc (npm)** | 부분 시도 | (조사만) | HWPX → Markdown만 지원 (PDF 직접 미지원). md → PDF 체인 가능하나 한글 양식 시각적 충실도 낮음 | 10분 (조사) | Markdown 중간 변환 시 표·체크박스·정부 양식 레이아웃 손실 — 미리보기 목적 부적합 |

---

## 3. 핵심 발견 (R3-H1 정직성)

### 3.1 rhwp CLI는 PDF/PNG를 지원하지 않는다 (v0.7.9 기준)

WebFetch `https://github.com/edwardkim/rhwp/blob/main/README_EN.md`:

> "CLI currently supports SVG export only. PDF and PNG exports are not mentioned as current capabilities."
> CLI commands: `export-svg`, `dump`, `dump-pages`, `info`
> Roadmap: "Additional output formats (PDF, DOCX, etc.)" → v2.0.0 (release date TBD)

`gh release view v0.7.9 -R edwardkim/rhwp` + `gh api repos/edwardkim/rhwp/releases/latest` 결과:
- `assets: []` — prebuilt binary 없음, 모든 설치는 source build
- 최신 릴리스 v0.7.9 (2026-04-30) 까지도 PDF export 미구현

### 3.2 HOP는 CLI가 없다

`brew info hop`:
```
==> hop (HOP): 0.1.9
View and edit HWP documents
==> Artifacts
  HOP.app (App)
```
GUI 앱(.app) 카스크 전용. README/저장소 검토 결과 `hop --export-pdf` 같은 진입점 미문서화.

### 3.3 wasmtime 호스트 + WASM 호환성 불확실

`which wasmtime` → not found. rhwp WASM 모듈(`@rhwp/core`)은 브라우저 환경 (Canvas/DOM) 가정 — wasmtime headless에서 동작하려면 별도 어댑터 작성 필요. 본 PoC 시간 budget(≤30분 조사 + ≤1시간 실행) 초과.

### 3.4 LibreOffice는 설치 자체가 부담

브랜드 정합성 검증 없이 1GB+ 카스크 설치는 시연 머신 부담. HWPX 변환 품질도 한글 폰트/표 레이아웃에서 손상 가능 (Hancom 측에서 별도 필터 제공하지 않음). Phase 3에서 별도 1일 PoC 필요.

---

## 4. 최종 결정

**PoC 실패 → Phase 3로 연기**.

Plan v2 Deviation 2가 명시적으로 허용하는 fallback 경로를 채택:

> "rhwp PoC fallback (실패 시 Quick Look)"

다만 macOS Quick Look(`qlmanage`)도 HWPX MIME을 인식하지 못할 수 있어, **case06 시연은 한글 GUI 수동 확인** 경로로 진행 (운영자가 출력된 .hwpx를 한글에서 열어 시각 검증).

### 4.1 인터페이스 결정

`core/docgen/hwp_preview.py::render_preview(hwpx_path, *, format="pdf") -> Path`:
- **항상 `NotImplementedError`** raise (format이 잘못된 경우만 ValueError가 먼저)
- 메시지에 (1) Phase 3 연기 사실, (2) hwpx-editor fallback 안내, (3) 결정 문서 위치 명시
- `format` 인자 검증은 유지 — 향후 Phase 3 구현 시 시그니처 안정성 확보

이 placeholder 함수가 raise하는 메시지는 **테스트가 검증** (`tests/test_docgen_hwp_preview.py::test_rhwp_unavailable_message_actionable`).

### 4.2 case06 (T18) 실행 전략

- **사용**: hwpx-editor `HwpxEditor` Python 클래스 (T17 wrapper) — `editor.set_cell` / `editor.replace_in_cell` / `editor.save`
- **미사용**: `hwp_preview.render_preview` (호출 시 즉시 NotImplementedError)
- **시연 흐름**:
  1. case06 시나리오가 입력 데이터 → 출력 .hwpx 생성
  2. 운영자가 `open output.hwpx` (macOS) 또는 한글에서 직접 open
  3. 시각 확인 후 시연 종료

라이브 미리보기가 빠지지만, 시연 대본(T20)에서 "한글에서 열어 확인" 단계를 1줄 추가하면 흐름이 깨지지 않음.

---

## 5. Phase 3 재진입 조건

다음 중 **하나라도** 충족되면 Phase 3에서 본 모듈을 실제 구현으로 교체한다:

1. **rhwp v2.0.0 (PDF 출력) prebuilt 배포** — npm `@rhwp/cli` 또는 cargo `rhwp` 패키지가 release assets로 macOS-arm64 binary를 제공
2. **HOP가 CLI subcommand 추가** — `hop --export-pdf input.hwpx output.pdf` 같은 headless 진입점이 README에 문서화
3. **LibreOffice 24+ HWPX 필터 검증 통과** — `soffice --headless --convert-to pdf input.hwpx`가 정부 양식 표/체크박스/한글 폰트를 손상 없이 변환함을 별도 1일 PoC로 실증
4. **kordoc + md-to-pdf 체인의 시각적 충실도가 정부 양식 시연에 충분함**을 별도 검증 (가능성 낮음 — 표/체크박스 손실 가설)

각 조건의 검증 task는 Phase 3 backlog에 다음 ID로 등록:
- `T-PHASE3-RHWP-1` rhwp v2 prebuilt 검증 (3시간)
- `T-PHASE3-RHWP-2` HOP CLI 추가 후 통합 (2시간)
- `T-PHASE3-RHWP-3` LibreOffice HWPX 필터 PoC (1일)

본 결정 문서는 Phase 3 진입 시 첫 번째 참조 자료로 사용한다.

---

## 6. T16 산출물 요약

| 항목 | 경로 | 비고 |
|------|------|------|
| 결정 문서 | `specs/rhwp-poc-decision.md` | 본 문서 |
| 인터페이스 모듈 | `core/docgen/hwp_preview.py` | `render_preview` placeholder (NotImplementedError) |
| smoke test | `tests/test_docgen_hwp_preview.py` | 5건: 4건 render_preview, 1건 hwpx-editor import smoke |

**검증**: `uv run pytest tests/test_docgen_hwp_preview.py -v` → 5 passed.

**hwpx-editor Python import 패턴 확인** (T17 사전 smoke):
```python
import sys
sys.path.insert(0, "/Users/jerome/.claude/skills/hwpx-editor/scripts")
from hwpx_utils import HwpxEditor  # type: ignore[import-untyped]

with HwpxEditor("template.hwpx") as editor:
    results = editor.analyze()  # list[dict] 반환
```

이 패턴이 정상 동작함을 `test_hwpx_editor_python_import_smoke`가 검증
(Skeleton.hwpx 샘플로 analyze 결과 list[dict] 구조 확인).

---

## 7. 아키텍처 부채 노트

- **Phase 3 진입 시 호환성 보존**: `render_preview` 시그니처 (`hwpx_path`, `format`, `-> Path`)는 향후 실제 구현이 채택해야 할 계약. Phase 3에서 본 시그니처를 유지하면 case06 호출부 변경 없이 NotImplementedError → 정상 Path 반환으로 swap 가능
- **시연 영향**: case06 라이브 미리보기 부재 → 시연 대본에서 "한글에서 열기" 1줄 추가 필요 (T20 demo script 작성 시 반영)
- **운영자 매뉴얼**: `output.hwpx`를 시연 노트북에 한글이 설치된 경우만 열 수 있음 — 한글 미설치 노트북에서는 case06 시연 불가 (시연 환경 전제조건 추가)
