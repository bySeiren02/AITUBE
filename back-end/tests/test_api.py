import pytest
import base64
import io
import time
import numpy as np
from PIL import Image
from fastapi.testclient import TestClient
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

client = TestClient(app)


def _make_jpeg_bytes(width=100, height=100, color=(100, 50, 150)) -> bytes:
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_jpeg_b64(width=100, height=100, color=(100, 50, 150)) -> str:
    return base64.b64encode(_make_jpeg_bytes(width, height, color)).decode()


class TestAPI:
    def test_root_endpoint(self):
        response = client.get("/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "endpoints" in data
        assert "version" in data

    def test_health_endpoint(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "model_loaded" in data

    def test_analyze_endpoint_no_files(self):
        response = client.post("/api/analyze")
        assert response.status_code == 400

    def test_analyze_endpoint_too_many_files(self):
        files = []
        for i in range(6):
            buf = io.BytesIO(_make_jpeg_bytes(color=(i * 40, 50, 150)))
            files.append(("files", (f"test_{i}.jpg", buf, "image/jpeg")))
        response = client.post("/api/analyze", files=files)
        assert response.status_code == 400
        assert "1-5 image files" in response.json()["error"]

    def test_analyze_endpoint_invalid_file_type(self):
        files = [("files", ("test.txt", io.BytesIO(b"not an image"), "text/plain"))]
        response = client.post("/api/analyze", files=files)
        assert response.status_code == 400
        assert "unsupported type" in response.json()["error"]

    def test_analyze_endpoint_valid_images(self):
        files = []
        for i in range(2):
            buf = io.BytesIO(_make_jpeg_bytes(width=200, height=200, color=(i * 100, 50, 150)))
            files.append(("files", (f"test_{i}.jpg", buf, "image/jpeg")))
        response = client.post("/api/analyze", files=files)
        assert response.status_code == 200

        data = response.json()
        assert "is_ai_generated" in data
        assert "ai_probability" in data
        assert "ai_confidence" in data
        assert "confidence_level" in data
        assert "analysis_details" in data
        assert "recommendations" in data
        assert "limitations" in data
        assert "total_processing_time" in data
        assert "detected_signs" in data
        assert "summary" in data
        assert "model" in data

        assert isinstance(data["is_ai_generated"], bool)
        assert isinstance(data["ai_probability"], (int, float))
        assert 0 <= data["ai_probability"] <= 1
        assert 0 <= data["ai_confidence"] <= 1
        assert data["confidence_level"] in ["low", "medium", "high"]
        assert isinstance(data["recommendations"], list)
        assert isinstance(data["limitations"], list)
        assert isinstance(data["detected_signs"], list)
        assert isinstance(data["summary"], str)


class TestValidation:
    def test_file_too_large(self):
        from app.config import Config
        oversized = io.BytesIO(b"\xff\xd8\xff" + b"\x00" * (Config.MAX_FILE_SIZE + 1))
        files = [("files", ("big.jpg", oversized, "image/jpeg"))]
        response = client.post("/api/analyze", files=files)
        assert response.status_code == 400
        assert "too large" in response.json()["error"]

    def test_six_files_rejected(self):
        files = []
        for i in range(6):
            buf = io.BytesIO(_make_jpeg_bytes(width=10, height=10, color=(0, 0, i * 40)))
            files.append(("files", (f"img_{i}.jpg", buf, "image/jpeg")))
        response = client.post("/api/analyze", files=files)
        assert response.status_code == 400
        assert "1-5 image files" in response.json()["error"]

    def test_video_content_type_rejected(self):
        files = [("files", ("clip.mp4", io.BytesIO(b"\x00" * 100), "video/mp4"))]
        response = client.post("/api/analyze", files=files)
        assert response.status_code == 400
        assert "unsupported type" in response.json()["error"]

    def test_gif_content_type_rejected(self):
        files = [("files", ("anim.gif", io.BytesIO(b"GIF89a" + b"\x00" * 50), "image/gif"))]
        response = client.post("/api/analyze", files=files)
        assert response.status_code == 400
        assert "unsupported type" in response.json()["error"]

    def test_corrupt_jpeg_bytes_rejected(self):
        files = [("files", ("corrupt.jpg", io.BytesIO(b"\xff\xd8\xff" + b"\xde\xad\xbe\xef" * 10), "image/jpeg"))]
        response = client.post("/api/analyze", files=files)
        assert response.status_code == 400
        assert "Invalid image file" in response.json()["error"]

    def test_png_format_accepted(self):
        img = Image.new("RGB", (50, 50), color=(0, 128, 255))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        files = [("files", ("test.png", buf, "image/png"))]
        response = client.post("/api/analyze", files=files)
        assert response.status_code == 200
        assert "ai_probability" in response.json()

    def test_mixed_valid_invalid_rejected(self):
        valid_buf = io.BytesIO(_make_jpeg_bytes(width=50, height=50, color=(0, 200, 0)))
        files = [
            ("files", ("ok.jpg", valid_buf, "image/jpeg")),
            ("files", ("bad.gif", io.BytesIO(b"GIF89a"), "image/gif")),
        ]
        response = client.post("/api/analyze", files=files)
        assert response.status_code == 400


class TestJSONEndpoint:
    """Chrome 확장 프로그램이 사용하는 JSON / base64 경로 테스트."""

    def test_json_single_frame(self):
        payload = {
            "frames": [{"data": _make_jpeg_b64(), "type": "base64", "size": 0}],
            "metadata": {"videoId": "test123", "duration": 15.0},
        }
        response = client.post(
            "/api/analyze",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "is_ai_generated" in data
        assert "ai_confidence" in data
        assert "detected_signs" in data
        assert "summary" in data
        assert data["videoId"] == "test123"
        assert "timestamp" in data

    def test_json_multiple_frames(self):
        frames = [
            {"data": _make_jpeg_b64(color=(i * 50, 100, 200)), "type": "base64", "size": 0}
            for i in range(3)
        ]
        payload = {"frames": frames}
        response = client.post(
            "/api/analyze",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["detected_signs"], list)
        assert isinstance(data["summary"], str)
        assert 0 <= data["ai_confidence"] <= 1

    def test_json_dataurl_frame(self):
        """data URL 형식(data:image/jpeg;base64,...)도 처리해야 한다."""
        raw_b64 = _make_jpeg_b64()
        data_url = f"data:image/jpeg;base64,{raw_b64}"
        payload = {"frames": [{"data": data_url, "type": "dataurl", "size": 0}]}
        response = client.post(
            "/api/analyze",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200

    def test_json_empty_frames_rejected(self):
        payload = {"frames": []}
        response = client.post(
            "/api/analyze",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400

    def test_json_invalid_base64_rejected(self):
        payload = {"frames": [{"data": "!!!not_valid_base64!!!", "type": "base64", "size": 0}]}
        response = client.post(
            "/api/analyze",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400

    def test_json_response_has_required_fields(self):
        payload = {
            "frames": [{"data": _make_jpeg_b64(), "type": "base64", "size": 0}],
            "metadata": {"videoId": "abc", "title": "테스트 영상", "duration": 30.0},
        }
        response = client.post(
            "/api/analyze",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        data = response.json()
        # 프론트엔드 parseAPIResponse에서 사용하는 모든 필드
        for field in ["is_ai_generated", "ai_confidence", "ai_model", "confidence",
                      "detected_signs", "summary", "analysis_time", "model",
                      "videoId", "timestamp"]:
            assert field in data, f"Missing field: {field}"


class TestPerformance:
    def test_analysis_speed(self):
        files = []
        for i in range(3):
            buf = io.BytesIO(_make_jpeg_bytes(width=300, height=300, color=(100, i * 50, 200)))
            files.append(("files", (f"test_{i}.jpg", buf, "image/jpeg")))

        start = time.time()
        response = client.post("/api/analyze", files=files)
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 5.0
        assert response.json().get("total_processing_time", 0) < 3.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
