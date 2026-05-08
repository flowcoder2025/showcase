# MLX Gemma 4 servers — deploy options

`runner.py`는 시연 시작 시 자동으로 mlx_vlm.server 두 개(E2B 11437, E4B 11438)를 subprocess로 spawn하고, 종료(정상/SIGINT/SIGTERM/SIGHUP) 시 process group에 SIGTERM→SIGKILL을 보내 메모리를 회수합니다. 기본 시연 사용엔 추가 설정이 필요 없습니다.

이 디렉토리는 **장기 운영용 옵션** — 부팅 후 항상 떠 있는 LaunchAgent로 등록하고 싶을 때 참고합니다.

## subprocess 모드 (기본, 권장)

```bash
uv run python runner.py
# → 자동 spawn (포트 11437/11438), 메뉴/케이스 종료 시 자동 회수
```

좀비 방지: `start_new_session=True`로 새 process group 생성 → atexit + SIGINT/SIGTERM/SIGHUP에서 `os.killpg(pgid, SIGTERM)` → 5초 후 미응답 시 `SIGKILL`.

## plist 모드 (옵션)

영구 등록을 원할 때만 사용. `RunAtLoad=false`로 두었으니 `launchctl load`만 부팅 시 실행 안 되고, `launchctl kickstart`로 명시 시작.

```bash
# 1. 모델 경로/포트 환경에 맞게 수정 (필요 시)
# 2. ~/Library/LaunchAgents/로 복사
cp deploy/launchd/com.flowsystem.mlx-vlm-gemma4-e2b.plist ~/Library/LaunchAgents/
cp deploy/launchd/com.flowsystem.mlx-vlm-gemma4-e4b.plist ~/Library/LaunchAgents/

# 3. 로드
launchctl load ~/Library/LaunchAgents/com.flowsystem.mlx-vlm-gemma4-e2b.plist
launchctl load ~/Library/LaunchAgents/com.flowsystem.mlx-vlm-gemma4-e4b.plist

# 4. 시작
launchctl kickstart -k gui/$(id -u)/com.flowsystem.mlx-vlm-gemma4-e2b
launchctl kickstart -k gui/$(id -u)/com.flowsystem.mlx-vlm-gemma4-e4b

# 5. runner는 외부 서버를 사용하도록 환경변수로 알림 (subprocess spawn 스킵)
export AX_OCR_BASE_URL_E2B=http://127.0.0.1:11437/v1
export AX_OCR_BASE_URL_E4B=http://127.0.0.1:11438/v1
uv run python runner.py
```

## 종료/언로드

```bash
# subprocess 모드: runner 종료 시 자동
# plist 모드:
launchctl unload ~/Library/LaunchAgents/com.flowsystem.mlx-vlm-gemma4-e2b.plist
launchctl unload ~/Library/LaunchAgents/com.flowsystem.mlx-vlm-gemma4-e4b.plist
```

## 환경변수 override

| 변수 | 기본값 | 설명 |
|---|---|---|
| `AX_OCR_BASE_URL_E2B` | (unset → spawn) | 외부 E2B 서버. 설정 시 runner spawn 스킵. |
| `AX_OCR_BASE_URL_E4B` | (unset → spawn) | 외부 E4B 서버. 설정 시 runner spawn 스킵. |
| `AX_MLX_BIN` | `/Users/jerome/mlx-env/bin/mlx_vlm.server` | mlx_vlm.server 실행 파일. |
| `AX_GEMMA_E2B_MODEL_PATH` | `/Users/jerome/models/gemma-4-e2b-mlx` | E2B MLX 모델 경로. |
| `AX_GEMMA_E4B_MODEL_PATH` | `/Users/jerome/models/gemma-4-e4b-mlx` | E4B MLX 모델 경로. |
