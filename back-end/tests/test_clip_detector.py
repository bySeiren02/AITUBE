"""CLIP 탐지 모듈 테스트.

- CLIPDetector 각 메서드 반환 구조 검증
- CLIPModelAdapter 인터페이스 준수 검증
- factory "mock"/"opencv"/"clip" 모두 동작 확인
"""

import pytest
import numpy as np
import time

# CLIP 의존성 유무 확인
try:
    import torch
    from app.models.clip_detector import CLIPDetector
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False

from app.models.ai_adapter import (
    create_ai_model,
    MockAIModelAdapter,
    AIModelInterface,
)


def _make_dummy_images(n: int = 3, size: int = 224):
    """테스트용 더미 이미지(numpy) 생성."""
    return [np.random.randint(0, 255, (size, size, 3), dtype=np.uint8) for _ in range(n)]


# ──────────────────────────────────────────────
# Factory 테스트 (CLIP 의존성 불필요)
# ──────────────────────────────────────────────

def test_factory_mock():
    adapter = create_ai_model(model_type="mock")
    assert isinstance(adapter, MockAIModelAdapter)


def test_factory_use_real_backward_compat(monkeypatch):
    """use_real=True → model_type='opencv' 하위호환."""
    import app.models.ai_adapter as mod

    class DummyAIModel:
        def analyze_face_consistency(self, images): return {}
        def analyze_frame_differences(self, images): return {}
        def detect_ai_artifacts(self, images): return {}
        def is_animal_content(self, images): return False
        def cleanup(self): pass

    monkeypatch.setattr(mod, "AIModel", DummyAIModel)
    adapter = create_ai_model(use_real=True)
    assert isinstance(adapter, AIModelInterface)


def test_factory_clip_missing_dependency(monkeypatch):
    """CLIPDetector가 None이면 RuntimeError."""
    import app.models.ai_adapter as mod
    monkeypatch.setattr(mod, "CLIPDetector", None)
    with pytest.raises(RuntimeError, match="CLIP dependencies"):
        create_ai_model(model_type="clip")


# ──────────────────────────────────────────────
# CLIPDetector 직접 테스트 (CLIP 설치 시만)
# ──────────────────────────────────────────────

@pytest.mark.skipif(not CLIP_AVAILABLE, reason="CLIP dependencies not installed")
class TestCLIPDetector:

    @pytest.fixture(scope="class")
    def detector(self):
        """한 번만 모델 로드."""
        det = CLIPDetector(device="cpu")
        yield det
        det.cleanup()

    @pytest.fixture
    def images(self):
        return _make_dummy_images(3)

    def test_compute_ai_probability_score_structure(self, detector, images):
        result = detector.compute_ai_probability_score(images)
        assert "ai_probability" in result
        assert "individual_scores" in result
        assert isinstance(result["ai_probability"], float)
        assert 0.0 <= result["ai_probability"] <= 1.0
        assert len(result["individual_scores"]) == 3

    def test_detect_frequency_artifacts_structure(self, detector, images):
        result = detector.detect_frequency_artifacts(images)
        assert "frequency_artifact_score" in result
        assert "individual_scores" in result
        assert 0.0 <= result["frequency_artifact_score"] <= 1.0

    def test_temporal_consistency_structure(self, detector, images):
        result = detector.analyze_temporal_consistency_clip(images)
        assert "temporal_consistency" in result
        assert "frame_similarities" in result
        assert len(result["frame_similarities"]) == 2  # 3 images → 2 pairs

    def test_temporal_consistency_single_image(self, detector):
        result = detector.analyze_temporal_consistency_clip(_make_dummy_images(1))
        assert result["temporal_consistency"] == 0.5
        assert result["frame_similarities"] == []

    def test_detect_faces_structure(self, detector, images):
        result = detector.detect_faces_with_clip(images)
        assert "face_consistency" in result
        assert "face_count" in result
        assert len(result["face_count"]) == 3

    def test_detect_animal_content_returns_bool(self, detector, images):
        result = detector.detect_animal_content(images)
        assert isinstance(result, bool)

    def test_get_image_embeddings_shape(self, detector, images):
        embeds = detector.get_image_embeddings(images)
        assert embeds.shape[0] == 3
        assert embeds.shape[1] == 512  # CLIP ViT-B/32 dim


# ──────────────────────────────────────────────
# CLIPModelAdapter 인터페이스 테스트
# ──────────────────────────────────────────────

@pytest.mark.skipif(not CLIP_AVAILABLE, reason="CLIP dependencies not installed")
class TestCLIPModelAdapter:

    @pytest.fixture(scope="class")
    def adapter(self):
        adapter = create_ai_model(model_type="clip")
        yield adapter
        adapter.cleanup()

    @pytest.fixture
    def images(self):
        return _make_dummy_images(3)

    def test_implements_interface(self, adapter):
        assert isinstance(adapter, AIModelInterface)

    def test_analyze_face_consistency(self, adapter, images):
        result = adapter.analyze_face_consistency(images)
        assert "face_consistency" in result
        assert "face_count" in result

    def test_analyze_frame_differences(self, adapter, images):
        result = adapter.analyze_frame_differences(images)
        assert "temporal_consistency" in result

    def test_detect_ai_artifacts(self, adapter, images):
        result = adapter.detect_ai_artifacts(images)
        assert "ai_artifact_score" in result
        assert "clip_score" in result
        assert "frequency_score" in result

    def test_is_animal_content(self, adapter, images):
        result = adapter.is_animal_content(images)
        assert isinstance(result, bool)


# ──────────────────────────────────────────────
# 성능 테스트
# ──────────────────────────────────────────────

@pytest.mark.skipif(not CLIP_AVAILABLE, reason="CLIP dependencies not installed")
def test_clip_inference_performance():
    """CPU에서 3프레임 분석 < 5초 (모델 로드 제외)."""
    detector = CLIPDetector(device="cpu")
    images = _make_dummy_images(3)

    t0 = time.time()
    detector.compute_ai_probability_score(images)
    detector.detect_frequency_artifacts(images)
    detector.analyze_temporal_consistency_clip(images)
    detector.detect_faces_with_clip(images)
    detector.detect_animal_content(images)
    elapsed = time.time() - t0

    detector.cleanup()
    assert elapsed < 5.0, f"Inference took {elapsed:.2f}s, expected < 5s"
