import cv2
import numpy as np
from PIL import Image
from typing import List, Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)

class ImageProcessor:
    @staticmethod
    def load_image(image_path: str) -> np.ndarray:
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not load image: {image_path}")
            return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        except Exception as e:
            logger.error(f"Error loading image {image_path}: {e}")
            raise
    
    @staticmethod
    def resize_image(image: np.ndarray, target_size: Tuple[int, int] = (512, 512)) -> np.ndarray:
        return cv2.resize(image, target_size)
    
    @staticmethod
    def detect_faces(image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            return faces.tolist()
        except Exception as e:
            logger.error(f"Face detection error: {e}")
            return []
    
    @staticmethod
    def analyze_image_quality(image: np.ndarray) -> Dict[str, float]:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        # Blur detection
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # Noise estimation
        noise_score = np.std(gray)
        
        # Contrast measurement
        contrast_score = np.std(gray) / np.mean(gray) if np.mean(gray) > 0 else 0
        
        return {
            "blur_score": float(blur_score),
            "noise_score": float(noise_score),
            "contrast_score": float(contrast_score)
        }
    
    @staticmethod
    def extract_texture_features(image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        # LBP (Local Binary Pattern) for texture analysis
        lbp = np.zeros_like(gray)
        for i in range(1, gray.shape[0]-1):
            for j in range(1, gray.shape[1]-1):
                center = gray[i, j]
                binary = 0
                for k in range(8):
                    x, y = i + [0, -1, -1, -1, 0, 1, 1, 1][k], j + [-1, -1, 0, 1, 1, 1, 0, -1][k]
                    if gray[x, y] >= center:
                        binary |= (1 << k)
                lbp[i, j] = binary
        
        return np.histogram(lbp, bins=256)[0]
    
    @staticmethod
    def detect_repetitive_patterns(image: np.ndarray) -> float:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        # FFT to detect periodic patterns
        fft = np.fft.fft2(gray)
        fft_shift = np.fft.fftshift(fft)
        magnitude = np.abs(fft_shift)
        
        # Peak detection in frequency domain
        threshold = np.percentile(magnitude, 95)
        peaks = np.sum(magnitude > threshold)
        
        return float(peaks / (gray.shape[0] * gray.shape[1]))