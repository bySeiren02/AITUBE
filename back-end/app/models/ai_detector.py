import numpy as np
from typing import List, Dict, Any
import logging
import time

logger = logging.getLogger(__name__)

class AIModel:
    def __init__(self):
        import cv2 as _cv2
        self.cv2 = _cv2
        self.face_cascade = _cv2.CascadeClassifier(
            _cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

    def analyze_face_consistency(self, images: List[np.ndarray]) -> Dict[str, Any]:
        start_time = time.time()

        face_results = []
        for img in images:
            faces = self._detect_faces_fast(img)
            face_results.append(faces)

        consistency_score = self._calculate_face_consistency(face_results)

        analysis_time = time.time() - start_time
        return {
            "face_consistency": consistency_score,
            "face_count": [len(faces) for faces in face_results],
            "analysis_time": analysis_time
        }

    def analyze_frame_differences(self, images: List[np.ndarray]) -> Dict[str, Any]:
        if len(images) < 2:
            return {"frame_diff_score": 0.0, "temporal_consistency": 1.0}

        start_time = time.time()
        differences = []

        for i in range(len(images) - 1):
            diff = self._calculate_frame_difference(images[i], images[i + 1])
            differences.append(diff)

        avg_diff = np.mean(differences)
        consistency = 1.0 - min(avg_diff / 100.0, 1.0)

        analysis_time = time.time() - start_time
        return {
            "frame_diff_score": float(avg_diff),
            "temporal_consistency": float(consistency),
            "analysis_time": analysis_time
        }

    def detect_ai_artifacts(self, images: List[np.ndarray]) -> Dict[str, Any]:
        start_time = time.time()

        artifact_scores = []
        for img in images:
            score = self._analyze_single_image_artifacts(img)
            artifact_scores.append(score)

        avg_artifact_score = np.mean(artifact_scores)

        analysis_time = time.time() - start_time
        return {
            "ai_artifact_score": float(avg_artifact_score),
            "individual_scores": [float(s) for s in artifact_scores],
            "analysis_time": analysis_time
        }

    def _detect_faces_fast(self, image: np.ndarray) -> List:
        try:
            gray = self.cv2.cvtColor(image, self.cv2.COLOR_RGB2GRAY)
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.2,
                minNeighbors=3,
                minSize=(30, 30)
            )
            return faces.tolist()
        except Exception:
            return []

    def _calculate_face_consistency(self, face_results: List[List]) -> float:
        if not face_results or not any(face_results):
            return 0.5

        face_counts = [len(faces) for faces in face_results]
        if len(face_counts) <= 1:
            return 1.0

        std_count = np.std(face_counts)
        max_count = max(face_counts)

        if max_count == 0:
            return 1.0

        consistency = 1.0 - (std_count / max_count)
        return float(consistency)

    def _calculate_frame_difference(self, img1: np.ndarray, img2: np.ndarray) -> float:
        size = (256, 256)
        img1_resized = self.cv2.resize(img1, size)
        img2_resized = self.cv2.resize(img2, size)

        diff = self.cv2.absdiff(img1_resized, img2_resized)
        diff_score = np.mean(diff)

        return float(diff_score)

    def _analyze_single_image_artifacts(self, image: np.ndarray) -> float:
        gray = self.cv2.cvtColor(image, self.cv2.COLOR_RGB2GRAY)
        laplacian_var = self.cv2.Laplacian(gray, self.cv2.CV_64F).var()
        blur_score = min(laplacian_var / 500.0, 1.0)

        edges = self.cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (gray.shape[0] * gray.shape[1])
        edge_score = min(edge_density * 10, 1.0)

        texture_std = np.std(gray)
        texture_score = 1.0 - min(texture_std / 100.0, 1.0)

        artifact_score = (blur_score + edge_score + texture_score) / 3.0

        return artifact_score

    def is_animal_content(self, images: List[np.ndarray]) -> bool:
        try:
            for img in images:
                faces = self._detect_faces_fast(img)
                if len(faces) == 0:
                    gray = self.cv2.cvtColor(img, self.cv2.COLOR_RGB2GRAY)
                    edges = self.cv2.Canny(gray, 50, 150)
                    edge_density = np.sum(edges > 0) / (gray.shape[0] * gray.shape[1])

                    if 0.05 < edge_density < 0.2:
                        return True
        except Exception:
            return False

        return False

    def cleanup(self):
        pass
