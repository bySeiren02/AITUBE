from typing import List, Dict, Any
from abc import ABC, abstractmethod

# Real AIModel implementation (heavy dependencies) import path
try:
    from app.models.ai_detector import AIModel
except Exception:
    AIModel = None  # Will be loaded lazily if real model is requested


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


def create_ai_model(use_real: bool = False) -> AIModelInterface:
    if use_real:
        return RealAIModelAdapter()
    else:
        return MockAIModelAdapter()
