import time
import numpy as np
from app.models.ai_adapter import create_ai_model, MockAIModelAdapter


def generate_dummy_images(n: int):
    imgs = []
    for _ in range(n):
        imgs.append((np.random.rand(256, 256, 3) * 255).astype(np.uint8))
    return imgs


def benchmark_mock_adapter(iterations: int = 5, images_per_iter: int = 3):
    adapter = MockAIModelAdapter()
    imgs = generate_dummy_images(images_per_iter)
    times = []
    for _ in range(iterations):
        t0 = time.time()
        _ = adapter.analyze_face_consistency(imgs)
        _ = adapter.analyze_frame_differences(imgs)
        _ = adapter.detect_ai_artifacts(imgs)
        _ = adapter.is_animal_content(imgs)
        t1 = time.time()
        times.append(t1 - t0)
    return times


def main():
    print("Benchmarking MockAIModelAdapter...")
    times = benchmark_mock_adapter(iterations=10, images_per_iter=3)
    print("Sample times (s):", times)
    print("Avg:", sum(times)/len(times) if times else 0)


if __name__ == "__main__":
    main()
