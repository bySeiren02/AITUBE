import numpy as np
import pytest
from bench_profile import generate_dummy_images, benchmark_adapter
from app.models.ai_adapter import MockAIModelAdapter


@pytest.fixture
def mock_adapter():
    return MockAIModelAdapter()


def test_benchmark_smoke(mock_adapter):
    """CI smoke test: benchmark runs without error for all image counts."""
    results = benchmark_adapter(mock_adapter, image_counts=(1, 2, 3, 4, 5), iterations=3)
    assert set(results.keys()) == {1, 2, 3, 4, 5}
    for n, stats in results.items():
        assert "avg" in stats
        assert "p95" in stats
        assert "max" in stats
        assert stats["avg"] >= 0
        assert stats["p95"] >= stats["avg"]
        assert stats["max"] >= stats["p95"]


def test_mock_adapter_speed(mock_adapter):
    """Mock adapter must complete all analyses in under 1 second per iteration."""
    results = benchmark_adapter(mock_adapter, image_counts=(3,), iterations=5)
    assert results[3]["avg"] < 1.0, f"avg latency too high: {results[3]['avg']:.3f}s"


def test_generate_dummy_images():
    imgs = generate_dummy_images(3)
    assert len(imgs) == 3
    for img in imgs:
        assert img.shape == (256, 256, 3)
        assert img.dtype == np.uint8
