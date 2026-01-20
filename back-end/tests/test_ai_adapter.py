import pytest

from app.models.ai_adapter import create_ai_model, MockAIModelAdapter, RealAIModelAdapter


def test_mock_adapter_basics():
    adapter = create_ai_model(use_real=False)
    assert isinstance(adapter, MockAIModelAdapter)
    res = adapter.analyze_face_consistency([])
    assert isinstance(res, dict)
    assert "face_consistency" in res


def test_real_adapter_with_dummy_dependency(monkeypatch):
    # Create a dummy AIModel to be used by RealAIModelAdapter
    class DummyAIModel:
        def analyze_face_consistency(self, images):
            return {"face_consistency": 0.5, "face_count": [0], "analysis_time": 0.01}
        def analyze_frame_differences(self, images):
            return {"frame_diff_score": 1.0, "temporal_consistency": 0.9, "analysis_time": 0.01}
        def detect_ai_artifacts(self, images):
            return {"ai_artifact_score": 0.1, "individual_scores": [0.1], "analysis_time": 0.01}
        def is_animal_content(self, images):
            return False
        def cleanup(self):
            self.cleaned = True

    import app.models.ai_adapter as adapter_mod
    monkeypatch.setattr(adapter_mod, "AIModel", DummyAIModel, raising=True)

    adapter = create_ai_model(use_real=True)
    assert isinstance(adapter, RealAIModelAdapter)

    # Ensure methods delegate to the DummyAIModel
    face = adapter.analyze_face_consistency([])
    assert isinstance(face, dict)
    assert face.get("face_consistency", None) == 0.5

    adapter.cleanup()


def test_real_adapter_missing_model_raises(monkeypatch):
    import app.models.ai_adapter as adapter_mod
    # Simulate missing AIModel implementation
    monkeypatch.setattr(adapter_mod, "AIModel", None, raising=False)
    with pytest.raises(RuntimeError):
        adapter_mod.RealAIModelAdapter()
