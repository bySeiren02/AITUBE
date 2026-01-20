from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
import time
import logging
import numpy as np
# Lazy imports will be done inside functions to avoid heavy import at module load

from app.config import Config
from app.models.ai_adapter import create_ai_model

# Initialize logger
logger = logging.getLogger(__name__)

# Lazy-initialized AI model adapter (real or mock depending on config)
_ai_model = None

def get_ai_model():
    global _ai_model
    if _ai_model is None:
        _ai_model = create_ai_model(use_real=Config.USE_REAL_AI_MODEL)
    return _ai_model

router = APIRouter()


@router.post("/analyze")
async def analyze_images(files: List[UploadFile] = File(...)):
    """Analyze 2-3 image frames for AI-generated content detection."""
    start_time = time.time()
    
    try:
        # Lazy import heavy dependencies
        from PIL import Image  # type: ignore
        import io
        import numpy as np

        # Validate input
        if len(files) < 1 or len(files) > 5:
            raise HTTPException(
                status_code=400, 
                detail="Please provide 1-5 image files (2-3 recommended)"
            )
        
        # Process uploaded files
        images = []
        for file in files:
            if not file.content_type or not file.content_type.startswith('image/'):
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} is not an image"
                )
            
            contents = await file.read()
            # Enforce size limit
            if len(contents) > Config.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} is too large (max {Config.MAX_FILE_SIZE} bytes)"
                )
            try:
                pil_image = Image.open(io.BytesIO(contents))
                if pil_image.mode != 'RGB':
                    pil_image = pil_image.convert('RGB')
                image_array = np.array(pil_image)
                images.append(image_array)
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid image file {file.filename}: {str(e)}"
                )
        
        # Perform analysis
        result = await perform_analysis(images)
        total_time = time.time() - start_time
        result["total_processing_time"] = total_time
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in analysis: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def perform_analysis(images: List[np.ndarray]) -> Dict[str, Any]:
    """Perform comprehensive AI detection analysis"""
    # Lazy import of typing inside function for type hints compatibility
    from typing import Dict as _Dict
    result: _Dict[str, Any] = {
        "is_ai_generated": False,
        "ai_probability": 0.0,
        "confidence_level": "low",
        "analysis_details": {},
        "recommendations": [],
        "limitations": [
            "Speed prioritized over accuracy for MVP",
            "Limited AI model training data",
            "May miss sophisticated deepfakes",
            "Animal content detection is heuristic-based"
        ]
    }
    
    try:
        ai_model = get_ai_model()
        # 1. Face consistency analysis
        face_analysis = ai_model.analyze_face_consistency(images)
        result["analysis_details"]["face_analysis"] = face_analysis
        
        # 2. Frame difference analysis
        frame_analysis = ai_model.analyze_frame_differences(images)
        result["analysis_details"]["frame_analysis"] = frame_analysis
        
        # 3. AI artifact detection
        artifact_analysis = ai_model.detect_ai_artifacts(images)
        result["analysis_details"]["artifact_analysis"] = artifact_analysis
        
        # 4. Check for animal content
        is_animal = ai_model.is_animal_content(images)
        result["analysis_details"]["is_animal_content"] = is_animal
        
        # 5. Calculate overall AI probability
        ai_probability = calculate_ai_probability(
            face_analysis, frame_analysis, artifact_analysis, is_animal
        )
        
        result["ai_probability"] = round(ai_probability, 3)
        result["is_ai_generated"] = ai_probability > 0.6
        
        # 6. Set confidence level
        if ai_probability < 0.3:
            result["confidence_level"] = "low"
        elif ai_probability < 0.7:
            result["confidence_level"] = "medium"
        else:
            result["confidence_level"] = "high"
        
        # 7. Generate recommendations
        result["recommendations"] = generate_recommendations(result)
        
        return result
    except Exception as e:
        logger.error(f"Error during analysis: {e}")
        raise


def calculate_ai_probability(face_analysis, frame_analysis, artifact_analysis, is_animal):
    """Calculate overall AI generation probability"""
    weights = {
        "face_consistency": 0.25,
        "temporal_consistency": 0.30,
        "ai_artifacts": 0.35,
        "animal_penalty": 0.10
    }
    
    face_consistency_score = 1.0 - face_analysis.get("face_consistency", 0.5)
    temporal_consistency_score = frame_analysis.get("temporal_consistency", 0.5)
    artifact_score = artifact_analysis.get("ai_artifact_score", 0.0)
    animal_penalty = 0.0 if is_animal else 1.0
    
    ai_probability = (
        face_consistency_score * weights["face_consistency"] +
        temporal_consistency_score * weights["temporal_consistency"] +
        artifact_score * weights["ai_artifacts"] +
        animal_penalty * weights["animal_penalty"]
    )
    
    return min(max(ai_probability, 0.0), 1.0)


def generate_recommendations(result):
    """Generate recommendations based on analysis results"""
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
    """Health check endpoint"""
    try:
        model_loaded = get_ai_model() is not None
    except Exception as e:
        model_loaded = False
        logger.error(f"Health check error: {e}")
    return {"status": "healthy", "model_loaded": model_loaded}


@router.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "UltraWork AI Content Detection API",
        "version": "1.0.0",
        "endpoints": {
            "/analyze": "POST - Analyze images for AI-generated content",
            "/health": "GET - Health check"
        }
    }
