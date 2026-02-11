from typing import List, Dict, Any
from abc import ABC, abstractmethod

# Real AIModel implementation (heavy dependencies) import path
try:
    from app.models.ai_detector import AIModel
except ImportError:
    AIModel = None  # Will be loaded lazily if real model is requested

# CLIP detector (optional heavy dependency)
try:
    from app.models.clip_detector import CLIPDetector
except ImportError:
    CLIPDetector = None


class AIModelInterface(ABC):
    @abstractmethod
    def analyze_face_consistency(self, images: List[Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def analyze_frame_differences(self, images: List[Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def detect_ai_artifacts(self, images: List[Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def is_animal_content(self, images: List[Any]) -> bool:
        pass

    def cleanup(self) -> None:
        pass


class MockAIModelAdapter(AIModelInterface):
    def analyze_face_consistency(self, images: List[Any]) -> Dict[str, Any]:
        return {"face_consistency": 0.8, "face_count": [1, 1], "analysis_time": 0.1}

    def analyze_frame_differences(self, images: List[Any]) -> Dict[str, Any]:
        return {"frame_diff_score": 15.0, "temporal_consistency": 0.85, "analysis_time": 0.1}

    def detect_ai_artifacts(self, images: List[Any]) -> Dict[str, Any]:
        return {"ai_artifact_score": 0.3, "individual_scores": [0.2, 0.4], "analysis_time": 0.1}

    def is_animal_content(self, images: List[Any]) -> bool:
        return False

    def cleanup(self) -> None:
        pass


class RealAIModelAdapter(AIModelInterface):
    def __init__(self):
        # Lazily instantiate real model if available
        if AIModel is None:
            raise RuntimeError("Real AIModel class is not available in this environment.")
        self.impl = AIModel()

    def analyze_face_consistency(self, images: List[Any]) -> Dict[str, Any]:
        return self.impl.analyze_face_consistency(images)

    def analyze_frame_differences(self, images: List[Any]) -> Dict[str, Any]:
        return self.impl.analyze_frame_differences(images)

    def detect_ai_artifacts(self, images: List[Any]) -> Dict[str, Any]:
        return self.impl.detect_ai_artifacts(images)

    def is_animal_content(self, images: List[Any]) -> bool:
        return self.impl.is_animal_content(images)

    def cleanup(self) -> None:
        try:
            self.impl.cleanup()
        except Exception:
            pass


class CLIPModelAdapter(AIModelInterface):
    def __init__(self, device: str = "cpu", model_name: str = "openai/clip-vit-base-patch32"):
        if CLIPDetector is None:
            raise RuntimeError(
                "CLIP dependencies not available. Install: pip install torch transformers scipy"
            )
        self.impl = CLIPDetector(device=device, model_name=model_name)

    def analyze_face_consistency(self, images: List[Any]) -> Dict[str, Any]:
        return self.impl.detect_faces_with_clip(images)

    def analyze_frame_differences(self, images: List[Any]) -> Dict[str, Any]:
        return self.impl.analyze_temporal_consistency_clip(images)

    def detect_ai_artifacts(self, images: List[Any]) -> Dict[str, Any]:
        import time
        t0 = time.time()
        clip_result = self.impl.compute_ai_probability_score(images)
        freq_result = self.impl.detect_frequency_artifacts(images)
        # CLIP score 70% + DCT frequency 30%
        combined_score = (
            clip_result["ai_probability"] * 0.7
            + freq_result["frequency_artifact_score"] * 0.3
        )
        elapsed = time.time() - t0
        return {
            "ai_artifact_score": combined_score,
            "individual_scores": clip_result["individual_scores"],
            "clip_score": clip_result["ai_probability"],
            "frequency_score": freq_result["frequency_artifact_score"],
            "analysis_time": elapsed,
        }

    def is_animal_content(self, images: List[Any]) -> bool:
        return self.impl.detect_animal_content(images)

    def cleanup(self) -> None:
        try:
            self.impl.cleanup()
        except Exception:
            pass


def create_ai_model(use_real: bool = False, model_type: str = None) -> AIModelInterface:
    # model_type 우선, 없으면 use_real 하위호환
    if model_type is None:
        model_type = "opencv" if use_real else "mock"

    if model_type == "clip":
        return CLIPModelAdapter()
    elif model_type == "opencv":
        return RealAIModelAdapter()
    else:
        return MockAIModelAdapter()
