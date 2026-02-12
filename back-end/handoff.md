# Handoff — AITUBE 백엔드

## 현재 상태
T1~T10 완료 + CLIP 통합 완료 + 프론트-백 연동 완료. 테스트 **28개** PASS (0 fail).
E2E 테스트 스크립트(`e2e_test.py`) 작성 완료 — API 테스트 24개 PASS 확인.

## 최근 작업

### 2026-02-12 — E2E 테스트 스크립트 + 브라우저 테스트 수정

#### `e2e_test.py` 신규 (프로젝트 루트)
- 4개 섹션: 헬스체크 / JSON API / 에러케이스 / 확장 프로그램+YouTube
- 섹션 1~3: **24 passed, 0 failed** (백엔드 localhost:8005 실행 중 조건)
- 섹션 4 (브라우저): Chrome 직접 subprocess 실행 + Playwright CDP 연결 방식
  - `playwright.chromium.launch_persistent_context` → exitCode=21 크래시 문제 해결
  - 원인: Chrome 다중 프로세스 환경에서 단일 인스턴스 제한 + `--enable-automation` 미포함
  - 해결: `subprocess.Popen(chrome_args)` + `connect_over_cdp(f"http://127.0.0.1:{CDP_PORT}")`
  - Chrome 실행 플래그: `--remote-debugging-port=9223 --enable-automation --disable-extensions-except=... --load-extension=...`
  - CDP 포트 대기 최대 30초 + 프로세스 조기 종료 감지

#### 브라우저 테스트 (섹션 4) 현재 상태
- Chrome 실행 및 CDP 연결은 `--enable-automation` 추가로 해결
- 서비스 워커 감지 / YouTube 이동 / API 요청 인터셉트 / 오버레이 확인 로직 구현

### 2026-02-12 — 프론트-백 API 연동 완성
- `app/api/routes.py` 수정:
  - `Content-Type: application/json` 요청 처리 추가 (Chrome 확장 프로그램용)
  - Pydantic 모델: `FrameData`, `AnalyzeMetadata`, `AnalyzeJSONRequest`
  - `_decode_frame()`: base64 / data URL 모두 numpy 배열로 변환
  - `_enrich_response()`: 프론트가 기대하는 필드 추가
    - `ai_confidence`, `confidence` (← ai_probability 매핑)
    - `detected_signs` (분석 결과 기반 자동 생성)
    - `summary` (한국어 요약 문장)
    - `model`, `ai_model`, `analysis_time`, `videoId`, `timestamp`
- `tests/test_api.py` 전면 개정:
  - 에러 응답 키: `["detail"]` → `["error"]`
  - `test_root_endpoint`: `GET /` → `GET /api/`
  - `test_analyze_endpoint_no_files`: 422 → 400
  - `TestJSONEndpoint` 클래스 신규: JSON/base64 경로 6개 테스트
  - **결과: 28 passed, 0 failed**

## 모델 선택 환경변수
| 환경변수 | 기본값 | 설명 |
|----------|--------|------|
| `AI_MODEL_TYPE` | `mock` | `mock` / `opencv` / `clip` |
| `CLIP_DEVICE` | `cpu` | `cpu` / `cuda` |
| `CLIP_MODEL_NAME` | `openai/clip-vit-base-patch32` | HuggingFace 모델명 |
| `USE_REAL_AI_MODEL` | `False` | 하위호환 (True → opencv) |

## 알려진 이슈
- `app/utils/image_processor.py` dead code 유지 중
- CORS `allow_origins=["*"]` — 프로덕션 전 수정 필요
- `on_event` DeprecationWarning — FastAPI lifespan 패턴 마이그레이션 권장
- E2E 섹션 4 전체 PASS 미확인 (CDP 연결 후 YouTube + 확장 프로그램 동작 검증 필요)

## TODO
- [ ] E2E 섹션 4 전체 통과 확인 (백엔드 실행 + YouTube Shorts + 오버레이 검증)
- [ ] 프로덕션 배포: CORS 오리진 제한, AI 모델 가중치 Config화
- [ ] `on_event` DeprecationWarning → FastAPI lifespan 패턴 마이그레이션
