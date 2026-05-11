# flowcoder-office-tools

사무자동화 재사용 라이브러리 (excel / messaging / docgen / ocr / ai).

## 상태

**0.1.0a1 (alpha)** — Phase 3-Pkg T42 scaffold 완료. T43 에서 `core/` 모듈
이주 진행 중. 외부 import 안정 contract 는 T46 (dogfood CI 통과) 시점에
선언된다.

## 출처

`/Users/jerome/AX/showcase` 모노레포의 `core/` 모듈을 추출한 재사용 패키지.
원본 케이스 (`cases/case01~10`) 와의 dogfood 검증을 통과한 모듈만 포함.

## 설치 (개발)

uv workspace 방식으로 부모 레포에 자동 link:

```bash
cd /path/to/showcase
uv sync
uv run python -c "import flowcoder_office_tools; print(flowcoder_office_tools.__version__)"
```

## Optional dependencies

- `ocr` — Pillow + jsonschema (OCR 결과 검증)
- `messaging` — google-auth* (Gmail OAuth)
- `docgen` — python-docx + Jinja2

## 라이선스

Proprietary. FlowCoder 내부 컨설팅 프로젝트 재사용 목적.
