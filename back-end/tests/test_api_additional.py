import pytest
from fastapi.testclient import TestClient
from PIL import Image
import io
import os
import sys

# Ensure the API app is importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import app

client = TestClient(app)

class TestAPIAdditional:
    def test_analyze_endpoint_one_image(self):
        files = []
        img = Image.new('RGB', (200, 200), color=(10, 20, 30))
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        buf.seek(0)
        files.append(('files', ('one.jpg', buf, 'image/jpeg')))

        response = client.post("/api/analyze", files=files)
        assert response.status_code == 200
        data = response.json()
        assert "is_ai_generated" in data
        assert "ai_probability" in data
        assert "analysis_details" in data
        assert "total_processing_time" in data
        assert isinstance(data["total_processing_time"], (int, float))

    def test_analyze_endpoint_three_images(self):
        files = []
        for i in range(3):
            img = Image.new('RGB', (200, 200), color=(i*40, i*20, 80))
            buf = io.BytesIO()
            img.save(buf, format='JPEG')
            buf.seek(0)
            files.append(('files', (f'test_{i}.jpg', buf, 'image/jpeg')))
        response = client.post("/api/analyze", files=files)
        assert response.status_code == 200
        data = response.json()
        assert "is_ai_generated" in data
        assert "ai_probability" in data
        assert isinstance(data["ai_probability"], (int, float))

    def test_analyze_endpoint_five_images(self):
        files = []
        for i in range(5):
            img = Image.new('RGB', (200, 200), color=(i*30, i*10, 100))
            buf = io.BytesIO()
            img.save(buf, format='JPEG')
            buf.seek(0)
            files.append(('files', (f'five_{i}.jpg', buf, 'image/jpeg')))
        response = client.post("/api/analyze", files=files)
        assert response.status_code == 200
        data = response.json()
        assert "analysis_details" in data
        assert "ai_probability" in data
        assert isinstance(data["ai_probability"], (int, float))
