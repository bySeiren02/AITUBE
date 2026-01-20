import io
import sys
from PIL import Image
from fastapi.testclient import TestClient

# Ensure main app imports
sys.path.append('C:\\c\\Users\\INFOTECH\\jjh\\realCheck')
from main import app

client = TestClient(app)

class DummyAdapter:
    def analyze_face_consistency(self, images):
        return {"face_consistency": 0.2, "face_count": [0, 0], "analysis_time": 0.01}
    def analyze_frame_differences(self, images):
        return {"frame_diff_score": 0.5, "temporal_consistency": 0.95, "analysis_time": 0.01}
    def detect_ai_artifacts(self, images):
        return {"ai_artifact_score": 0.1, "individual_scores": [0.1, 0.2], "analysis_time": 0.01}
    def is_animal_content(self, images):
        return False
    def cleanup(self):
        pass


def test_api_uses_ai_adapter_wrapper(monkeypatch):
    # Patch the factory in the API route to return DummyAdapter
    import app.api.routes as routes
    monkeypatch.setattr(routes, 'create_ai_model', lambda use_real=False: DummyAdapter())
    # Reset internal lazy model so wrapper is recreated
    if hasattr(routes, '_ai_model'):
        routes._ai_model = None

    # Create a tiny valid image and POST
    img = Image.new('RGB', (64, 64), color=(10, 20, 30))
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    buf.seek(0)

    files = [('files', ('test_wrapper.jpg', buf, 'image/jpeg'))]
    resp = client.post('/api/analyze', files=files)
    assert resp.status_code == 200
    data = resp.json()
    # Should include AI analysis fields populated by DummyAdapter
    assert 'ai_probability' in data
    assert 'analysis_details' in data
    assert data['analysis_details'].get('face_analysis') is not None
