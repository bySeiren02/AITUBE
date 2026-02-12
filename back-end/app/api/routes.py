import base64
import time
import logging
import io
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import numpy as np

from app.config import Config
from app.models.ai_adapter import create_ai_model

logger = logging.getLogger(__name__)

_ai_model = None


def get_ai_model():
    global _ai_model
    if _ai_model is None:
        model_type = Config.AI_MODEL_TYPE
        if model_type == "mock" and Config.USE_REAL_AI_MODEL:
            model_type = "opencv"
        _ai_model = create_ai_model(model_type=model_type)
    return _ai_model


router = APIRouter()

ALLOWED_CONTENT_TYPES = {'image/jpeg', 'image/png', 'image/bmp'}


# ── Pydantic models for JSON request (Chrome extension) ─────────────────────

class FrameData(BaseModel):
    data: str          # base64 string or data URL
    type: str = "base64"
    size: int = 0


class AnalyzeMetadata(BaseModel):
    duration: Optional[float] = None
    title: Optional[str] = None
    videoId: Optional[str] = None
    url: Optional[str] = None
    timestamp: Optional[int] = None


class AnalyzeJSONRequest(BaseModel):
    frames: List[FrameData]
    metadata: Optional[AnalyzeMetadata] = None


# ── Response helpers ─────────────────────────────────────────────────────────

def _generate_detected_signs(result: Dict[str, Any]) -> List[str]:
    signs = []
    details = result.get("analysis_details", {})

    artifact_score = details.get("artifact_analysis", {}).get("ai_artifact_score", 0)
    if artifact_score > 0.5:
        signs.append("AI 아티팩트 패턴 감지")

    face_consistency = details.get("face_analysis", {}).get("face_consistency", 1.0)
    if face_consistency < 0.5:
        signs.append("얼굴 비일관성 감지")

    temporal_consistency = details.get("frame_analysis", {}).get("temporal_consistency", 0)
    if temporal_consistency > 0.65:
        signs.append("비자연스러운 프레임 일관성")

    if details.get("is_animal_content", False):
        signs.append("동물 콘텐츠 감지 (정확도 낮음)")

    return signs


def _enrich_response(result: Dict[str, Any], video_id: str = "") -> Dict[str, Any]:
    """프론트엔드가 기대하는 필드를 추가한다."""
    ai_prob = result.get("ai_probability", 0.0)
    is_ai = result.get("is_ai_generated", False)
    confidence_pct = round(ai_prob * 100)

    if is_ai:
        summary = f"AI 생성 영상으로 판단됩니다. (AI 확률: {confidence_pct}%)"
    else:
        summary = f"실제 영상으로 판단됩니다. (AI 확률: {confidence_pct}%)"

    result["ai_confidence"] = ai_prob
    result["confidence"] = ai_prob
    result["ai_model"] = None  # 구체적 AI 모델명 탐지 미지원
    result["model"] = Config.AI_MODEL_TYPE
    result["detected_signs"] = _generate_detected_signs(result)
    result["summary"] = summary
    result["analysis_time"] = result.get("total_processing_time", 0.0)
    result["videoId"] = video_id
    result["timestamp"] = int(time.time() * 1000)
    return result


def _decode_frame(frame: FrameData) -> np.ndarray:
    """base64 / data URL 프레임을 numpy 배열로 변환한다."""
    from PIL import Image

    raw = frame.data
    if raw.startswith("data:"):
        # data URL: "data:image/jpeg;base64,<data>"
        raw = raw.split(",", 1)[1]
    image_bytes = base64.b64decode(raw)
    pil_image = Image.open(io.BytesIO(image_bytes))
    if pil_image.mode != "RGB":
        pil_image = pil_image.convert("RGB")
    return np.array(pil_image)


# ── Main endpoint ─────────────────────────────────────────────────────────────

@router.post("/analyze")
async def analyze_images(
    request: Request,
    files: Optional[List[UploadFile]] = File(None),
):
    """Accept either multipart/form-data (files) or application/json (base64 frames)."""
    start_time = time.time()
    content_type = request.headers.get("content-type", "")

    # ── JSON path (Chrome extension) ────────────────────────────────────────
    if "application/json" in content_type:
        try:
            from PIL import Image
            body = await request.json()
            req = AnalyzeJSONRequest(**body)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON body: {e}")

        if len(req.frames) < 1 or len(req.frames) > 10:
            raise HTTPException(
                status_code=400,
                detail="Please provide 1-10 frames"
            )

        images = []
        for i, frame in enumerate(req.frames):
            try:
                images.append(_decode_frame(frame))
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Frame {i + 1} decode error: {e}"
                )

        video_id = (req.metadata.videoId or "") if req.metadata else ""
        result = await perform_analysis(images)
        result["total_processing_time"] = time.time() - start_time
        result = _enrich_response(result, video_id=video_id)
        return JSONResponse(content=result)

    # ── Multipart path (tests / curl) ────────────────────────────────────────
    if not files:
        raise HTTPException(
            status_code=400,
            detail="No files or JSON body provided"
        )

    try:
        from PIL import Image

        if len(files) < 1 or len(files) > 5:
            raise HTTPException(
                status_code=400,
                detail="Please provide 1-5 image files (2-3 recommended)"
            )

        images = []
        for file in files:
            if not file.content_type or file.content_type not in ALLOWED_CONTENT_TYPES:
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} has unsupported type '{file.content_type}'. Allowed: jpeg, png, bmp"
                )

            contents = await file.read()
            if len(contents) > Config.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} is too large (max {Config.MAX_FILE_SIZE} bytes)"
                )
            try:
                pil_image = Image.open(io.BytesIO(contents))
                if pil_image.mode != "RGB":
                    pil_image = pil_image.convert("RGB")
                images.append(np.array(pil_image))
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid image file {file.filename}: {e}"
                )

        result = await perform_analysis(images)
        result["total_processing_time"] = time.time() - start_time
        result = _enrich_response(result, video_id="")
        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in analysis: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


def _get_limitations() -> list:
    model_type = Config.AI_MODEL_TYPE
    if model_type == "clip":
        return [
            "CLIP zero-shot classification (~85% accuracy)",
            "May miss sophisticated deepfakes not in training distribution",
            "DCT frequency analysis is supplementary",
            "Animal content detection is CLIP-based heuristic",
        ]
    return [
        "Speed prioritized over accuracy for MVP",
        "Limited AI model training data",
        "May miss sophisticated deepfakes",
        "Animal content detection is heuristic-based",
    ]


async def perform_analysis(images: List[np.ndarray]) -> Dict[str, Any]:
    """Perform comprehensive AI detection analysis."""
    result: Dict[str, Any] = {
        "is_ai_generated": False,
        "ai_probability": 0.0,
        "confidence_level": "low",
        "analysis_details": {},
        "recommendations": [],
        "limitations": _get_limitations(),
    }

    try:
        ai_model = get_ai_model()

        face_analysis = ai_model.analyze_face_consistency(images)
        result["analysis_details"]["face_analysis"] = face_analysis

        frame_analysis = ai_model.analyze_frame_differences(images)
        result["analysis_details"]["frame_analysis"] = frame_analysis

        artifact_analysis = ai_model.detect_ai_artifacts(images)
        result["analysis_details"]["artifact_analysis"] = artifact_analysis

        is_animal = ai_model.is_animal_content(images)
        result["analysis_details"]["is_animal_content"] = is_animal

        ai_probability = calculate_ai_probability(
            face_analysis, frame_analysis, artifact_analysis, is_animal
        )

        result["ai_probability"] = round(ai_probability, 3)
        result["is_ai_generated"] = ai_probability > Config.AI_DETECTION_THRESHOLD

        if ai_probability < 0.3:
            result["confidence_level"] = "low"
        elif ai_probability < 0.7:
            result["confidence_level"] = "medium"
        else:
            result["confidence_level"] = "high"

        result["recommendations"] = generate_recommendations(result)
        return result
    except Exception as e:
        logger.error(f"Error during analysis: {e}")
        raise


def calculate_ai_probability(face_analysis, frame_analysis, artifact_analysis, is_animal):
    weights = {
        "face_consistency": 0.25,
        "temporal_consistency": 0.30,
        "ai_artifacts": 0.35,
        "animal_penalty": 0.10,
    }

    face_consistency_score = 1.0 - face_analysis.get("face_consistency", 0.5)
    temporal_consistency_score = frame_analysis.get("temporal_consistency", 0.5)
    artifact_score = artifact_analysis.get("ai_artifact_score", 0.0)
    animal_penalty = 0.0 if is_animal else 1.0

    ai_probability = (
        face_consistency_score * weights["face_consistency"]
        + temporal_consistency_score * weights["temporal_consistency"]
        + artifact_score * weights["ai_artifacts"]
        + animal_penalty * weights["animal_penalty"]
    )

    return min(max(ai_probability, 0.0), 1.0)


def generate_recommendations(result):
    recommendations = []

    if result["is_ai_generated"]:
        recommendations.append("Content likely AI-generated - verify authenticity")
    else:
        recommendations.append("Content appears to be authentic")
        if result["ai_probability"] > 0.4:
            recommendations.append("Some AI-like characteristics detected - consider manual review")

    if result["analysis_details"].get("is_animal_content", False):
        recommendations.append("Animal content detected - AI detection less reliable")

    return recommendations


@router.get("/health")
async def health_check():
    try:
        model_loaded = get_ai_model() is not None
    except Exception as e:
        model_loaded = False
        logger.error(f"Health check error: {e}")
    return {"status": "healthy", "model_loaded": model_loaded}


@router.get("/")
async def root():
    return {
        "message": "UltraWork AI Content Detection API",
        "version": "1.0.0",
        "endpoints": {
            "/analyze": "POST - Analyze images for AI-generated content",
            "/health": "GET - Health check",
        },
    }
