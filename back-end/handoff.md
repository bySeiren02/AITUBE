# Handoff — AITUBE 백엔드

## 현재 상태
T1~T10 전체 구현 완료. 테스트 39개 전부 PASS (0 fail).

## 최근 작업 (2026-02-11)

### 테스트 코드 버그 수정 — `tests/test_api.py`
- `test_root_endpoint`: `GET /` → `GET /api/` (라우터 prefix `/api`에 맞춤)
- 에러 응답 테스트 7개: `response.json()["detail"]` → `response.json()["error"]`
  - 원인: `main.py` 커스텀 exception handler가 `{"error": ...}` 형식으로 응답
  - 대상: too_many_files, invalid_file_type, file_too_large, six_files_rejected, video_rejected, gif_rejected, corrupt_jpeg_rejected
- `test_analyze_endpoint_invalid_file_type`: 메시지 검증도 `"is not an image"` → `"unsupported type"`으로 수정
- 결과: **39 passed, 0 failed** (0.95s)

## 알려진 이슈
- `app/utils/image_processor.py` dead code 유지 (테스트가 참조 가능성)
- CORS `allow_origins=["*"]` — 프로덕션 전 수정 필요
- 분석 가중치(face/temporal/artifacts/animal) 하드코딩
- `on_event` DeprecationWarning — FastAPI lifespan 패턴 마이그레이션 권장

## TODO
- 없음 (T1~T10 전체 완료, 테스트 전부 통과)
- 프로덕션 배포 시: CORS 오리진 제한, 실제 AI 모델 가중치 Config화 검토
