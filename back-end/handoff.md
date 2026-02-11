# Handoff — AITUBE 백엔드

## 현재 상태
T1~T10 전체 구현 완료. 모든 버그 수정, 테스트 추가, CI 생성, 문서 업데이트 완료.

## 완료된 작업 (2026-02-11)

### Step 1 — T5: conftest.py + broken 테스트 수정
- `back-end/conftest.py` 신규 생성 — sys.path를 back-end 루트로 자동 설정
- `tests/test_api_wrapper.py:7` 하드코딩 sys.path 삭제
- `tests/test_api_performance_extra.py:7` 하드코딩 sys.path 삭제

### Step 2 — T1/T2: 핵심 버그 수정
- `ai_adapter.py:7` `except Exception` → `except ImportError`
- `routes.py:129` `ai_probability > 0.6` → `ai_probability > Config.AI_DETECTION_THRESHOLD`
- `main.py` 중복 ai_model 생성(라인 39,44) 제거
- `main.py:92` bare `except:` → `except Exception as e:` + `logger.warning()`
- `main.py` shutdown_event를 `routes.get_ai_model()` 참조로 변경

### Step 3 — T4: cv2 lazy loading + ThreadPoolExecutor 제거
- `ai_detector.py` 모듈 최상위 `import cv2`, `from concurrent.futures import ThreadPoolExecutor` 삭제
- `AIModel.__init__`에 `import cv2 as _cv2` + `self.cv2 = _cv2` 추가
- 모든 `cv2.` → `self.cv2.` 치환
- `is_animal_content`에 `try/except Exception` 추가
- `cleanup()`에서 executor.shutdown 제거 → `pass`

### Step 4 — T8: 유효성 검사 테스트 + MIME 강화
- `routes.py` ALLOWED_CONTENT_TYPES = {'image/jpeg', 'image/png', 'image/bmp'} 집합 검사로 변경
  - image/gif, image/webp 등 이전에 통과하던 타입 차단
- `tests/test_api.py` TestValidation 클래스 추가 (7개 테스트):
  - 파일 크기 초과, 6개 파일 거부, video/mp4 거부, image/gif 거부,
  - 손상된 JPEG 거부, PNG 정상 처리, 혼합 요청 거부

### Step 5 — T6: 입력 범위 테스트 완성
- `tests/test_api_additional.py` 5개 테스트 추가:
  - 4장 케이스, total_processing_time < Config.ANALYSIS_TIMEOUT 검증,
  - PNG 형식 정상 처리, BMP 형식 정상 처리

### Step 6 — T7: GitHub Actions CI
- `.github/workflows/ci.yml` 신규 생성
  - push/PR 경로 필터: back-end/**
  - matrix: Python 3.10, 3.11
  - pip cache, pytest, bench_profile.py 포함

### Step 8 — T10: 벤치마크 확장
- `bench_profile.py` 재작성: 1-5장 케이스별 avg/p95/max 출력 + cProfile 통합
- `tests/test_benchmarks.py` 신규 생성 (CI smoke 테스트 3개)

### Step 9 — T9: 문서 업데이트
- `README.md` 전면 개정:
  - "2-3개" → "1-5개(2-3개 권장)"
  - 아키텍처 다이어그램 추가
  - 환경 변수 표 추가
  - 테스트 실행 방법 추가
  - 알려진 제한 사항 추가

## 알려진 이슈
- `app/utils/image_processor.py` dead code 유지 (테스트가 참조 가능성)
- CORS `allow_origins=["*"]` — 프로덕션 전 수정 필요
- 분석 가중치(face/temporal/artifacts/animal) 하드코딩

## TODO
- 없음 (T1~T10 전체 완료)
- 프로덕션 배포 시: CORS 오리진 제한, 실제 AI 모델 가중치 Config화 검토
