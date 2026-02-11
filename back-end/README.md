# AITUBE - AI 생성 영상 판별 백엔드 서비스

## 시스템 개요
AI로 생성된 영상을 빠르게(1-2초 내) 감지하는 FastAPI 기반 백엔드 서비스입니다.

## 주요 기능
- **1-5개** 이미지 프레임 입력 분석 (2-3개 권장)
- 얼굴 기반 AI 생성 감지
- 동물 영상 패턴 분석
- 프레임 간 변화 분석
- 1-2초 내 분석 완료

## 아키텍처

```
routes.py (API 진입점)
  └─ AIModelInterface (ai_adapter.py)
        ├─ MockAIModelAdapter  — 테스트·개발용
        └─ RealAIModelAdapter
              └─ AIModel (ai_detector.py)  — OpenCV 기반 실제 분석
```

- `create_ai_model(use_real=...)` 팩토리로 런타임에 어댑터 교체 가능
- `USE_REAL_AI_MODEL=False`(기본)이면 OpenCV가 로드되지 않음 (lazy import)

## 엔드포인트
| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/analyze` | 이미지 프레임 분석 및 AI 생성 가능성 반환 |
| GET | `/api/health` | 서버 상태 확인 |
| GET | `/api/` | API 정보 |

## 환경 변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `USE_REAL_AI_MODEL` | `False` | `True`이면 OpenCV 기반 실제 모델 사용 |
| `DEBUG` | `False` | 디버그 모드 (uvicorn reload 활성화) |
| `HOST` | `0.0.0.0` | 서버 바인딩 주소 |
| `PORT` | `8000` | 서버 포트 |
| `AI_DETECTION_THRESHOLD` | `0.6` (코드 내 상수) | AI 판정 임계값 |

## 설치 및 실행

### Windows
```bash
setup.bat
```

### Linux/Mac
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

서버가 http://localhost:8000 에서 실행됩니다.

## API 사용법

### 이미지 분석
```bash
curl -X POST "http://localhost:8000/api/analyze" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@image1.jpg" \
  -F "files=@image2.jpg"
```

허용 파일 형식: **JPEG, PNG, BMP** (최대 10MB/파일, 최대 5개)

### 응답 예시
```json
{
  "is_ai_generated": false,
  "ai_probability": 0.342,
  "confidence_level": "medium",
  "analysis_details": {
    "face_analysis": {"face_consistency": 0.8, "face_count": [1, 1], "analysis_time": 0.05},
    "frame_analysis": {"frame_diff_score": 12.3, "temporal_consistency": 0.88, "analysis_time": 0.02},
    "artifact_analysis": {"ai_artifact_score": 0.27, "individual_scores": [0.25, 0.29], "analysis_time": 0.03},
    "is_animal_content": false
  },
  "recommendations": ["Content appears to be authentic"],
  "limitations": ["Speed prioritized over accuracy for MVP", "..."],
  "total_processing_time": 0.12
}
```

## 테스트 실행

```bash
# 단위 + 통합 테스트 (mock 모드)
cd back-end
USE_REAL_AI_MODEL=False pytest tests/ -v

# 벤치마크
python bench_profile.py
```

## 프로젝트 구조
```
back-end/
├── app/
│   ├── config.py              # 설정 관리
│   ├── api/
│   │   └── routes.py          # API 라우트
│   ├── models/
│   │   ├── ai_adapter.py      # 인터페이스 + 어댑터
│   │   └── ai_detector.py     # OpenCV 기반 실제 감지기
│   └── utils/
│       └── image_processor.py # (미사용 — 향후 전처리 예정)
├── tests/
│   ├── test_api.py            # 기본 API + 유효성 검사 테스트
│   ├── test_api_additional.py # 이미지 수(1-5) 범위 테스트
│   ├── test_api_wrapper.py    # 어댑터 DI 테스트
│   ├── test_api_performance_extra.py  # 성능 테스트
│   └── test_benchmarks.py    # 벤치마크 CI smoke 테스트
├── conftest.py                # pytest sys.path 설정
├── main.py                    # FastAPI 앱 진입점
├── bench_profile.py           # 성능 프로파일링 도구
└── requirements.txt
```

## 알려진 제한 사항
- CORS `allow_origins=["*"]` — 프로덕션 배포 전 실제 오리진으로 변경 필요
- 분석 가중치(face 25%, temporal 30%, artifacts 35%, animal 10%) 하드코딩 — Config으로 이전 예정
- 동물 콘텐츠 감지는 에지 밀도 기반 휴리스틱
- 복잡한 딥페이크(스타일 전이 등)는 탐지하지 못할 수 있음
- `app/utils/image_processor.py`는 현재 사용되지 않음
