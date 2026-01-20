import pytest
import asyncio
import numpy as np
from PIL import Image
import io
from fastapi.testclient import TestClient
import sys
import os

# Add the parent directory to the path to import the main app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

client = TestClient(app)

class TestAPI:
    def test_root_endpoint(self):
        response = client.get("/")
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
        assert response.status_code == 422  # Validation error
    
    def test_analyze_endpoint_too_many_files(self):
        # Create more than 5 test files
        files = []
        for i in range(6):
            img = Image.new('RGB', (100, 100), color='red')
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG')
            img_bytes.seek(0)
            files.append(('files', (f'test_{i}.jpg', img_bytes, 'image/jpeg')))
        
        response = client.post("/api/analyze", files=files)
        assert response.status_code == 400
        assert "Please provide 1-5 image files" in response.json()["detail"]
    
    def test_analyze_endpoint_invalid_file_type(self):
        # Create a text file instead of image
        files = [('files', ('test.txt', io.BytesIO(b'not an image'), 'text/plain'))]
        response = client.post("/api/analyze", files=files)
        assert response.status_code == 400
        assert "is not an image" in response.json()["detail"]
    
    def test_analyze_endpoint_valid_images(self):
        # Create valid test images
        files = []
        for i in range(2):
            img = Image.new('RGB', (200, 200), color=(i*100, 50, 150))
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG')
            img_bytes.seek(0)
            files.append(('files', (f'test_{i}.jpg', img_bytes, 'image/jpeg')))
        
        response = client.post("/api/analyze", files=files)
        assert response.status_code == 200
        
        data = response.json()
        assert "is_ai_generated" in data
        assert "ai_probability" in data
        assert "confidence_level" in data
        assert "analysis_details" in data
        assert "recommendations" in data
        assert "limitations" in data
        assert "total_processing_time" in data
        
        # Check data types
        assert isinstance(data["is_ai_generated"], bool)
        assert isinstance(data["ai_probability"], (int, float))
        assert 0 <= data["ai_probability"] <= 1
        assert data["confidence_level"] in ["low", "medium", "high"]
        assert isinstance(data["recommendations"], list)
        assert isinstance(data["limitations"], list)

class TestPerformance:
    def test_analysis_speed(self):
        """Test that analysis completes within the timeout"""
        import time
        
        # Create valid test images
        files = []
        for i in range(3):
            img = Image.new('RGB', (300, 300), color=(100, i*50, 200))
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG')
            img_bytes.seek(0)
            files.append(('files', (f'test_{i}.jpg', img_bytes, 'image/jpeg')))
        
        start_time = time.time()
        response = client.post("/api/analyze", files=files)
        end_time = time.time()
        
        assert response.status_code == 200
        
        processing_time = response.json().get("total_processing_time", 0)
        actual_time = end_time - start_time
        
        # Should complete within reasonable time (allow some margin)
        assert actual_time < 5.0  # 5 seconds max for test
        assert processing_time < 3.0  # 3 seconds max for API processing

if __name__ == "__main__":
    pytest.main([__file__, "-v"])