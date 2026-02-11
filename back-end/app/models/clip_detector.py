"""CLIP ViT-B/32 기반 AI 영상 탐지 모듈.

Zero-shot 분류를 통해 AI 생성 이미지 vs 실제 사진을 판별한다.
텍스트 임베딩은 init 시 1회 캐싱하여 추론 시 이미지 임베딩만 계산.
"""

import numpy as np
from typing import List, Dict, Any

import torch
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
from scipy.fft import dctn


def _to_tensor(output) -> torch.Tensor:
    """transformers v5+에서 BaseModelOutput → pooler_output 텐서 추출."""
    if isinstance(output, torch.Tensor):
        return output
    return output.pooler_output


class CLIPDetector:
    """CLIP ViT-B/32 zero-shot 분류 기반 AI 생성 이미지 탐지기."""

    REAL_PROMPTS = [
        "a real photograph taken by a camera",
        "an authentic unedited photo",
        "a natural photograph of a real scene",
        "a genuine photo captured in real life",
    ]
    AI_PROMPTS = [
        "an AI generated image",
        "a synthetic image created by artificial intelligence",
        "a deepfake or computer generated picture",
        "an image produced by a generative model",
    ]

    def __init__(self, device: str = "cpu", model_name: str = "openai/clip-vit-base-patch32"):
        self.device = torch.device(device)
        self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.model.eval()
        self._real_embeds, self._ai_embeds = self._cache_text_embeddings()

    def _cache_text_embeddings(self):
        """real / ai 프롬프트 텍스트 임베딩을 미리 계산하여 캐싱."""
        with torch.no_grad():
            real_inputs = self.processor(text=self.REAL_PROMPTS, return_tensors="pt", padding=True).to(self.device)
            real_embeds = _to_tensor(self.model.get_text_features(**real_inputs))
            real_embeds = real_embeds / real_embeds.norm(dim=-1, keepdim=True)

            ai_inputs = self.processor(text=self.AI_PROMPTS, return_tensors="pt", padding=True).to(self.device)
            ai_embeds = _to_tensor(self.model.get_text_features(**ai_inputs))
            ai_embeds = ai_embeds / ai_embeds.norm(dim=-1, keepdim=True)

        return real_embeds, ai_embeds

    def get_image_embeddings(self, images: List[np.ndarray]) -> torch.Tensor:
        """numpy 배열 리스트 → 정규화된 CLIP 이미지 임베딩 텐서."""
        pil_images = [Image.fromarray(img) if isinstance(img, np.ndarray) else img for img in images]
        inputs = self.processor(images=pil_images, return_tensors="pt").to(self.device)
        with torch.no_grad():
            embeds = _to_tensor(self.model.get_image_features(**inputs))
            embeds = embeds / embeds.norm(dim=-1, keepdim=True)
        return embeds

    def compute_ai_probability_score(self, images: List[np.ndarray]) -> Dict[str, Any]:
        """real vs ai 프롬프트 코사인 유사도 → AI 생성 확률.

        temperature scaling (x10) + softmax 로 확률 변환.
        """
        img_embeds = self.get_image_embeddings(images)  # (N, D)

        real_sim = (img_embeds @ self._real_embeds.T).mean(dim=-1)  # (N,)
        ai_sim = (img_embeds @ self._ai_embeds.T).mean(dim=-1)      # (N,)

        logits = torch.stack([real_sim, ai_sim], dim=-1) * 10.0  # (N, 2)
        probs = torch.softmax(logits, dim=-1)  # (N, 2)
        ai_probs = probs[:, 1].cpu().numpy()  # AI 확률

        return {
            "ai_probability": float(ai_probs.mean()),
            "individual_scores": ai_probs.tolist(),
            "real_similarity": real_sim.cpu().numpy().tolist(),
            "ai_similarity": ai_sim.cpu().numpy().tolist(),
        }

    def detect_frequency_artifacts(self, images: List[np.ndarray]) -> Dict[str, Any]:
        """DCT 주파수 분석으로 AI 특유의 고주파 패턴 부족을 감지."""
        scores = []
        for img in images:
            gray = np.mean(img, axis=2) if img.ndim == 3 else img.astype(np.float64)
            dct = dctn(gray, type=2, norm="ortho")
            h, w = dct.shape
            high_freq = dct[h // 2 :, w // 2 :]
            low_freq = dct[: h // 2, : w // 2]
            high_energy = np.mean(np.abs(high_freq))
            low_energy = np.mean(np.abs(low_freq)) + 1e-8
            ratio = high_energy / low_energy
            # AI 이미지는 고주파 에너지가 상대적으로 낮은 경향
            artifact_score = max(0.0, min(1.0, 1.0 - (ratio - 0.02) / 0.13))
            scores.append(artifact_score)

        return {
            "frequency_artifact_score": float(np.mean(scores)),
            "individual_scores": scores,
        }

    def analyze_temporal_consistency_clip(self, images: List[np.ndarray]) -> Dict[str, Any]:
        """프레임 간 CLIP 임베딩 코사인 유사도로 시간적 일관성 분석."""
        if len(images) < 2:
            return {"temporal_consistency": 0.5, "frame_similarities": [], "analysis_time": 0.0}

        import time
        t0 = time.time()
        embeds = self.get_image_embeddings(images)  # (N, D)
        similarities = []
        for i in range(len(embeds) - 1):
            sim = float((embeds[i] @ embeds[i + 1]).cpu())
            similarities.append(sim)

        mean_sim = float(np.mean(similarities))
        elapsed = time.time() - t0

        return {
            "temporal_consistency": mean_sim,
            "frame_similarities": similarities,
            "analysis_time": elapsed,
        }

    def detect_faces_with_clip(self, images: List[np.ndarray]) -> Dict[str, Any]:
        """얼굴 관련 프롬프트로 얼굴 존재/일관성 분석."""
        import time
        t0 = time.time()

        face_prompts = [
            "a photo of a human face",
            "a photo with no human face",
        ]
        with torch.no_grad():
            text_inputs = self.processor(text=face_prompts, return_tensors="pt", padding=True).to(self.device)
            text_embeds = _to_tensor(self.model.get_text_features(**text_inputs))
            text_embeds = text_embeds / text_embeds.norm(dim=-1, keepdim=True)

        img_embeds = self.get_image_embeddings(images)
        logits = (img_embeds @ text_embeds.T) * 10.0
        probs = torch.softmax(logits, dim=-1)
        face_probs = probs[:, 0].cpu().numpy()  # "face present" 확률

        face_count_approx = [1 if p > 0.5 else 0 for p in face_probs]
        consistency = 1.0 - float(np.std(face_probs)) if len(face_probs) > 1 else 0.8
        elapsed = time.time() - t0

        return {
            "face_consistency": max(0.0, min(1.0, consistency)),
            "face_count": face_count_approx,
            "face_probabilities": face_probs.tolist(),
            "analysis_time": elapsed,
        }

    def detect_animal_content(self, images: List[np.ndarray]) -> bool:
        """동물 vs 사람 프롬프트 zero-shot 분류."""
        animal_prompts = [
            "a photo of an animal",
            "a photo of a person or human",
        ]
        with torch.no_grad():
            text_inputs = self.processor(text=animal_prompts, return_tensors="pt", padding=True).to(self.device)
            text_embeds = _to_tensor(self.model.get_text_features(**text_inputs))
            text_embeds = text_embeds / text_embeds.norm(dim=-1, keepdim=True)

        img_embeds = self.get_image_embeddings(images)
        logits = (img_embeds @ text_embeds.T) * 10.0
        probs = torch.softmax(logits, dim=-1)
        animal_probs = probs[:, 0].cpu().numpy()

        return bool(float(np.mean(animal_probs)) > 0.5)

    def cleanup(self):
        """모델 자원 해제."""
        del self.model
        del self.processor
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
