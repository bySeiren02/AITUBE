import time
import cProfile
import pstats
import io
import numpy as np
from app.models.ai_adapter import create_ai_model, MockAIModelAdapter


def generate_dummy_images(n: int):
    imgs = []
    for _ in range(n):
        imgs.append((np.random.rand(256, 256, 3) * 255).astype(np.uint8))
    return imgs


def benchmark_adapter(adapter, image_counts=(1, 2, 3, 4, 5), iterations: int = 10):
    results = {}
    for n in image_counts:
        imgs = generate_dummy_images(n)
        times = []
        for _ in range(iterations):
            t0 = time.time()
            adapter.analyze_face_consistency(imgs)
            adapter.analyze_frame_differences(imgs)
            adapter.detect_ai_artifacts(imgs)
            adapter.is_animal_content(imgs)
            times.append(time.time() - t0)
        times_sorted = sorted(times)
        results[n] = {
            "avg": sum(times) / len(times),
            "p95": times_sorted[int(len(times) * 0.95)],
            "max": max(times),
        }
    return results


def print_results(label: str, results: dict):
    print(f"\n{label}")
    print(f"{'images':>8}  {'avg (ms)':>10}  {'p95 (ms)':>10}  {'max (ms)':>10}")
    print("-" * 45)
    for n, stats in sorted(results.items()):
        print(
            f"{n:>8}  {stats['avg']*1000:>10.2f}  {stats['p95']*1000:>10.2f}  {stats['max']*1000:>10.2f}"
        )


def profile_adapter(adapter, n_images: int = 3):
    imgs = generate_dummy_images(n_images)
    pr = cProfile.Profile()
    pr.enable()
    for _ in range(5):
        adapter.analyze_face_consistency(imgs)
        adapter.analyze_frame_differences(imgs)
        adapter.detect_ai_artifacts(imgs)
        adapter.is_animal_content(imgs)
    pr.disable()

    buf = io.StringIO()
    ps = pstats.Stats(pr, stream=buf).sort_stats("cumulative")
    ps.print_stats(10)
    print("\ncProfile top 10 (cumulative):")
    print(buf.getvalue())


def main():
    adapter = MockAIModelAdapter()

    results = benchmark_adapter(adapter, image_counts=(1, 2, 3, 4, 5), iterations=10)
    print_results("MockAIModelAdapter — 1-5 images benchmark", results)

    profile_adapter(adapter, n_images=3)


if __name__ == "__main__":
    main()
