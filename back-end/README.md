# AITUBE - AI 생성 영상 판별 백엔드 서비스

## 시스템 개요
AI로 생성된 영상을 빠르게(1-2초 내) 감지하는 FastAPI 기반 백엔드 서비스입니다.

## 주요 기능
- 2-3개 이미지 프레임 입력 분석
- 얼굴 기반 AI 생성 감지
- 동물 영상 패턴 분석
- 프레임 간 변화 분석
- 1-2초 내 분석 완료

## 엔드포인트
- `POST /api/analyze` - 이미지 프레임 분석 및 AI 생성 가능성 반환
- `GET /api/health` - 서버 상태 확인
- `GET /api/` - API 정보

## 설치 및 실행

### Windows
```bash
setup.bat
```

### Linux/Mac
```bash
# Python 3.8+ 필요
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### 서버 실행
```bash
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

### 응답 예시
```json
{
  "is_ai_generated": false,
  "ai_probability": 0.342,
  "confidence_level": "medium",
  "analysis_details": {
    "face_analysis": {...},
    "frame_analysis": {...},
    "artifact_analysis": {...},
    "is_animal_content": false
  },
  "recommendations": ["Content appears to be authentic"],
  "limitations": [...],
  "total_processing_time": 1.23
}
```

## 테스트
```bash
python test_client.py
```

## API 문서
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## MVP 한계점
- 정확도보다 속도 우선 설계
- 한정된 AI 모델 사용
- 실시간 학습 미지원
- 복잡한 딥페이크 감지 제한
- 동물 콘텐츠는 휴리스틱 기반 감지

## 프로젝트 구조
```
realCheck/
├── app/
│   ├── __init__.py
│   ├── config.py          # 설정 관리
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py     # API 라우트
│   ├── models/
│   │   └── __init__.py
│   │   └── ai_detector.py # AI 감지 모델
│   └── utils/
│       ├── __init__.py
│       └── image_processor.py # 이미지 처리
├── tests/
│   └── __init__.py
├── main.py               # 메인 서버 파일
├── requirements.txt      # 의존성
├── setup.bat            # Windows 설치 스크립트
├── test_client.py       # 테스트 클라이언트
└── README.md            # 프로젝트 문서
```