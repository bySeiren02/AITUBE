import pytest
import asyncio
import numpy as np
from PIL import Image
import io
import tempfile
import os

from app.models.ai_detector import AIModel
from app.utils.image_processor import ImageProcessor

class TestAIModel:
    def setup_method(self):
        self.ai_model = AIModel()
        
        # Create test images
        self.test_images = []
        for i in range(3):
            # Create a simple test image
            img_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
            self.test_images.append(img_array)
    
    def teardown_method(self):
        if hasattr(self, 'ai_model'):
            self.ai_model.cleanup()
    
    def test_analyze_face_consistency(self):
        result = self.ai_model.analyze_face_consistency(self.test_images)
        
        assert "face_consistency" in result
        assert "face_count" in result
        assert "analysis_time" in result
        assert isinstance(result["face_consistency"], float)
        assert isinstance(result["face_count"], list)
    
    def test_analyze_frame_differences(self):
        result = self.ai_model.analyze_frame_differences(self.test_images)
        
        assert "frame_diff_score" in result
        assert "temporal_consistency" in result
        assert "analysis_time" in result
        assert isinstance(result["frame_diff_score"], float)
        assert isinstance(result["temporal_consistency"], float)
    
    def test_detect_ai_artifacts(self):
        result = self.ai_model.detect_ai_artifacts(self.test_images)
        
        assert "ai_artifact_score" in result
        assert "individual_scores" in result
        assert "analysis_time" in result
        assert isinstance(result["ai_artifact_score"], float)
        assert isinstance(result["individual_scores"], list)
    
    def test_is_animal_content(self):
        result = self.ai_model.is_animal_content(self.test_images)
        assert isinstance(result, bool)

class TestImageProcessor:
    def test_analyze_image_quality(self):
        # Create test image
        img_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        
        result = ImageProcessor.analyze_image_quality(img_array)
        
        assert "blur_score" in result
        assert "noise_score" in result
        assert "contrast_score" in result
        assert all(isinstance(v, float) for v in result.values())
    
    def test_extract_texture_features(self):
        # Create test image
        img_array = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)
        
        features = ImageProcessor.extract_texture_features(img_array)
        
        assert isinstance(features, np.ndarray)
        assert len(features) == 256  # LBP histogram bins
    
    def test_detect_repetitive_patterns(self):
        # Create test image
        img_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        
        pattern_score = ImageProcessor.detect_repetitive_patterns(img_array)
        
        assert isinstance(pattern_score, float)
        assert 0 <= pattern_score <= 1

class TestIntegration:
    def test_full_analysis_pipeline(self):
        ai_model = AIModel()
        
        # Create test images
        test_images = []
        for i in range(3):
            img_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
            test_images.append(img_array)
        
        # Run all analysis methods
        face_result = ai_model.analyze_face_consistency(test_images)
        frame_result = ai_model.analyze_frame_differences(test_images)
        artifact_result = ai_model.detect_ai_artifacts(test_images)
        is_animal = ai_model.is_animal_content(test_images)
        
        # Verify all results have expected structure
        assert all("analysis_time" in result for result in [face_result, frame_result, artifact_result])
        assert isinstance(is_animal, bool)
        
        ai_model.cleanup()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])