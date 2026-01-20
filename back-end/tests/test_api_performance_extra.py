import time
from fastapi.testclient import TestClient
from PIL import Image
import io
import sys

sys.path.append('C:\\c\\Users\\INFOTECH\\jjh\\realCheck')
from main import app

client = TestClient(app)


def _make_img_bytes(color=(0,0,0)):
    img = Image.new('RGB', (200, 200), color=color)
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    buf.seek(0)
    return buf


def test_analyze_endpoint_1x_performance():
    buf = _make_img_bytes((10,20,30))
    files = [('files', ('img0.jpg', buf, 'image/jpeg'))]
    start = time.time()
    resp = client.post("/api/analyze", files=files)
    end = time.time()
    assert resp.status_code == 200
    data = resp.json()
    assert "total_processing_time" in data
    wall = end - start
    assert wall < 6.0


def test_analyze_endpoint_3x_performance():
    imgs = [ _make_img_bytes((i*40, i*20, 100)) for i in range(3) ]
    files = [( 'files', ('img_%d.jpg' % i, imgs[i], 'image/jpeg') ) for i in range(3)]
    start = time.time()
    resp = client.post("/api/analyze", files=files)
    end = time.time()
    assert resp.status_code == 200
    data = resp.json()
    assert "total_processing_time" in data
    wall = end - start
    assert wall < 5.0


def test_analyze_endpoint_5x_performance():
    imgs = [ _make_img_bytes((i*20, i*40, 60)) for i in range(5) ]
    files = [( 'files', ('img_%d.jpg' % i, imgs[i], 'image/jpeg') ) for i in range(5)]
    start = time.time()
    resp = client.post("/api/analyze", files=files)
    end = time.time()
    assert resp.status_code == 200
    data = resp.json()
    assert "total_processing_time" in data
    wall = end - start
    assert wall < 6.0
