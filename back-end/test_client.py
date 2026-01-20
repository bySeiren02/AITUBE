import requests
import json
import time

def test_api_with_sample_images():
    """Test the API with sample images"""
    
    BASE_URL = "http://localhost:8005/api"
    
    print("Testing AITUBE AI Detection API...")
    
    # Test health endpoint
    print("\n1. Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("[OK] Health check passed")
            print(f"Response: {response.json()}")
        else:
            print(f"[FAIL] Health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("[FAIL] Cannot connect to server. Make sure the server is running on localhost:8000")
        return False
    
    # Test analyze endpoint with sample images
    print("\n2. Testing image analysis endpoint...")
    
    # For testing, you should provide actual image files
    # Example with creating test images using PIL
    try:
        from PIL import Image
        import io
        
        # Create test images
        files = []
        for i in range(2):
            img = Image.new('RGB', (200, 200), color=(i*100, 50, 150))
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG')
            img_bytes.seek(0)
            files.append(('files', (f'test_{i}.jpg', img_bytes, 'image/jpeg')))
        
        print("Sending images for analysis...")
        start_time = time.time()
        
        response = requests.post(f"{BASE_URL}/analyze", files=files)
        
        end_time = time.time()
        
        if response.status_code == 200:
            result = response.json()
            print("[OK] Analysis completed successfully")
            print(f"Processing time: {end_time - start_time:.2f}s")
            print(f"AI Probability: {result.get('ai_probability', 0):.3f}")
            print(f"Is AI Generated: {result.get('is_ai_generated', False)}")
            print(f"Confidence Level: {result.get('confidence_level', 'unknown')}")
            print(f"Recommendations: {', '.join(result.get('recommendations', []))}")
        else:
            print(f"[FAIL] Analysis failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"[FAIL] Error during analysis test: {e}")
        return False
    
    print("\n[OK] All tests completed successfully!")
    return True

if __name__ == "__main__":
    test_api_with_sample_images()