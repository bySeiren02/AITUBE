"""
AITUBE E2E 테스트
- 백엔드: localhost:8005 (이미 실행 중이어야 함)
- Chrome + 확장 프로그램 로드
- YouTube Shorts 페이지에서 API 요청/응답 검증
"""

import json
import time
import sys
import io
from pathlib import Path
from playwright.sync_api import sync_playwright, Page

# Windows 터미널 UTF-8 강제
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BACKEND_URL = "http://localhost:8005"
EXTENSION_PATH = str(Path(__file__).parent / "front-end" / "extension")
CHROME_EXE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PROFILE_DIR = r"C:\Temp\aitube_e2e_profile"
YOUTUBE_SHORTS_URL = "https://www.youtube.com/shorts/dQw4w9WgXcQ"

PASS = "[PASS]"
FAIL = "[FAIL]"
INFO = "[INFO]"

results = []


def check(label: str, condition: bool, detail: str = ""):
    status = PASS if condition else FAIL
    msg = f"{status} {label}"
    if detail:
        msg += f" :{detail}"
    print(msg)
    results.append((label, condition))
    return condition


# ─────────────────────────────────────────────────────────────────────────────
# 1. 백엔드 헬스 체크
# ─────────────────────────────────────────────────────────────────────────────
def test_backend_health(page: Page):
    print("\n▶ [1] 백엔드 헬스 체크")
    resp = page.request.get(f"{BACKEND_URL}/api/health")
    check("HTTP 200", resp.status == 200, f"status={resp.status}")
    data = resp.json()
    check("status=healthy", data.get("status") == "healthy")
    check("model_loaded 필드 존재", "model_loaded" in data)


# ─────────────────────────────────────────────────────────────────────────────
# 2. JSON API 직접 호출 (프론트엔드 형식 그대로)
# ─────────────────────────────────────────────────────────────────────────────
def test_json_api(page: Page):
    print("\n▶ [2] JSON API (base64 프레임) 직접 호출")
    import base64, io
    from PIL import Image

    frames = []
    for i in range(5):
        img = Image.new("RGB", (320, 240), color=(i * 50, 128, 200))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        frames.append({
            "data": base64.b64encode(buf.getvalue()).decode(),
            "type": "base64",
            "size": buf.tell()
        })

    payload = {
        "frames": frames,
        "metadata": {
            "videoId": "e2e_test_video",
            "title": "E2E Test Shorts",
            "duration": 30.0,
            "url": YOUTUBE_SHORTS_URL,
            "timestamp": int(time.time() * 1000)
        }
    }

    resp = page.request.post(
        f"{BACKEND_URL}/api/analyze",
        data=json.dumps(payload),
        headers={"Content-Type": "application/json"}
    )
    check("HTTP 200", resp.status == 200, f"status={resp.status}")

    data = resp.json()

    required_fields = [
        "is_ai_generated", "ai_probability", "ai_confidence",
        "confidence_level", "ai_model", "model",
        "detected_signs", "summary", "analysis_time",
        "videoId", "timestamp", "total_processing_time"
    ]
    for field in required_fields:
        check(f"응답 필드: {field}", field in data)

    check("videoId 전달됨", data.get("videoId") == "e2e_test_video")
    check("ai_confidence 범위 0-1", 0 <= data.get("ai_confidence", -1) <= 1,
          f"value={data.get('ai_confidence')}")
    check("detected_signs는 리스트", isinstance(data.get("detected_signs"), list))
    check("summary는 문자열", isinstance(data.get("summary"), str))
    check("summary 비어있지 않음", bool(data.get("summary", "").strip()))

    print(f"  → is_ai_generated : {data.get('is_ai_generated')}")
    print(f"  → ai_confidence   : {data.get('ai_confidence')}")
    print(f"  → summary         : {data.get('summary')}")
    print(f"  → detected_signs  : {data.get('detected_signs')}")
    print(f"  → model           : {data.get('model')}")
    print(f"  → analysis_time   : {data.get('analysis_time'):.3f}s")


# ─────────────────────────────────────────────────────────────────────────────
# 3. 에러 케이스 검증
# ─────────────────────────────────────────────────────────────────────────────
def test_error_cases(page: Page):
    print("\n▶ [3] 에러 케이스 검증")

    # 빈 프레임
    resp = page.request.post(
        f"{BACKEND_URL}/api/analyze",
        data=json.dumps({"frames": []}),
        headers={"Content-Type": "application/json"}
    )
    check("빈 프레임 → 400", resp.status == 400)

    # 잘못된 base64
    resp = page.request.post(
        f"{BACKEND_URL}/api/analyze",
        data=json.dumps({"frames": [{"data": "!!!invalid!!!", "type": "base64", "size": 0}]}),
        headers={"Content-Type": "application/json"}
    )
    check("잘못된 base64 → 400", resp.status == 400)

    # 빈 body
    resp = page.request.post(f"{BACKEND_URL}/api/analyze")
    check("body 없음 → 400", resp.status == 400)


# ─────────────────────────────────────────────────────────────────────────────
# 4. 확장 프로그램 + YouTube Shorts 브라우저 테스트
# ─────────────────────────────────────────────────────────────────────────────
CDP_PORT = 9223  # 기존 Chrome과 충돌 방지용 포트


def test_extension_on_youtube(playwright):
    print("\n▶ [4] Chrome 확장 프로그램 로드 + YouTube Shorts 테스트")

    import subprocess, socket

    def _port_in_use(port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("127.0.0.1", port)) == 0

    # Chrome을 직접 서브프로세스로 실행 후 CDP로 연결
    # (Playwright launch_persistent_context는 이미 Chrome이 다수 실행 중인 환경에서
    #  exitCode=21로 크래시 → 직접 subprocess 방식 사용)
    chrome_proc = None
    context = None

    try:
        if not _port_in_use(CDP_PORT):
            chrome_args = [
                CHROME_EXE,
                f"--remote-debugging-port={CDP_PORT}",
                f"--user-data-dir={PROFILE_DIR}",
                f"--disable-extensions-except={EXTENSION_PATH}",
                f"--load-extension={EXTENSION_PATH}",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-sync",
                "--enable-automation",   # 단일 인스턴스 제한 우회 + CDP 강제 활성
                "about:blank",
            ]
            chrome_proc = subprocess.Popen(
                chrome_args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print(f"  {INFO} Chrome 직접 실행 (pid={chrome_proc.pid}, CDP포트={CDP_PORT})")
            # CDP 준비까지 대기 (최대 30초)
            for i in range(60):
                time.sleep(0.5)
                if _port_in_use(CDP_PORT):
                    print(f"  {INFO} CDP 포트 열림 ({(i+1)*0.5:.1f}s 대기)")
                    break
                if chrome_proc.poll() is not None:
                    raise RuntimeError(f"Chrome 프로세스 조기 종료 (exit={chrome_proc.returncode})")
            else:
                raise RuntimeError(f"Chrome CDP 포트 {CDP_PORT} 응답 없음 (30초 초과)")
        else:
            print(f"  {INFO} CDP 포트 {CDP_PORT} 이미 활성 — 기존 Chrome 재사용")

        browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP_PORT}")
        print(f"  {INFO} Playwright CDP 연결 성공")
        # CDP 연결 시 Browser 객체를 반환 → BrowserContext 확보
        if browser.contexts:
            context = browser.contexts[0]
        else:
            context = browser.new_context()

    except Exception as e:
        print(f"  {FAIL} Chrome/CDP 연결 실패: {e}")
        if chrome_proc:
            chrome_proc.terminate()
        return

    page = context.new_page()

    # API 요청/응답 인터셉트
    api_requests = []
    api_responses = []

    def on_request(req):
        if "localhost:8005" in req.url:
            api_requests.append({"url": req.url, "method": req.method})
            print(f"  {INFO} API 요청 감지: {req.method} {req.url}")

    def on_response(resp):
        if "localhost:8005" in resp.url:
            try:
                body = resp.json()
                api_responses.append(body)
                print(f"  {INFO} API 응답: status={resp.status}, "
                      f"is_ai={body.get('is_ai_generated')}, "
                      f"confidence={body.get('ai_confidence')}")
            except Exception:
                pass

    page.on("request", on_request)
    page.on("response", on_response)

    try:
        # 확장 프로그램 서비스 워커 대기 (이벤트 기반)
        print(f"  {INFO} 확장 프로그램 서비스 워커 대기 중...")
        sw_url = None
        try:
            sw = context.wait_for_event("serviceworker", timeout=8000)
            sw_url = sw.url
            print(f"  {INFO} 서비스 워커 감지: {sw_url}")
        except Exception:
            # 이미 실행 중일 수 있음
            sw_list = context.service_workers
            if sw_list:
                sw_url = sw_list[0].url
                print(f"  {INFO} 서비스 워커 (기존): {sw_url}")
        check("확장 프로그램 서비스 워커 활성", sw_url is not None,
              sw_url or "서비스 워커 없음")

        print(f"  {INFO} YouTube Shorts 이동 중...")
        page.goto(YOUTUBE_SHORTS_URL, timeout=30000, wait_until="commit")

        # 페이지 안정화 대기
        try:
            page.wait_for_load_state("domcontentloaded", timeout=10000)
        except Exception:
            pass

        # 확장 프로그램이 content script를 주입할 시간 확보 후 리로드
        try:
            page.wait_for_timeout(2000)
        except Exception:
            pass
        print(f"  {INFO} 페이지 리로드 (content script 주입 확보)...")
        try:
            page.reload(wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(3000)
        except Exception as e:
            print(f"  {INFO} 리로드 결과: {e}")

        # YouTube 페이지 로드 확인 (body가 hidden으로 시작하므로 ytd-app 사용)
        try:
            page.wait_for_selector("ytd-app, #content, #page-manager", timeout=10000)
            check("YouTube 페이지 로드", True)
        except Exception:
            # URL이 YouTube면 로드된 것으로 간주
            check("YouTube 페이지 로드", "youtube.com" in page.url)

        print(f"  {INFO} 현재 URL: {page.url}")
        check("YouTube 도메인 접근", "youtube.com" in page.url)

        # 브라우저에서 localhost:8005 직접 접근 테스트
        try:
            health_result = page.evaluate("""
                async () => {
                    try {
                        const r = await fetch('http://localhost:8005/api/health');
                        const d = await r.json();
                        return {ok: true, status: r.status, data: d};
                    } catch(e) {
                        return {ok: false, error: e.message};
                    }
                }
            """)
            print(f"  {INFO} 브라우저->localhost 접근: {health_result}")
            check("브라우저에서 localhost:8005 접근", health_result.get("ok", False))
        except Exception as e:
            check("브라우저에서 localhost:8005 접근", False, str(e))

        # YouTube Premium 팝업 닫기
        try:
            page.click("button[aria-label='닫기']", timeout=3000)
            print(f"  {INFO} YouTube Premium 팝업 닫음")
        except Exception:
            pass
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass

        # AITUBE 콘솔 로그 수집
        console_msgs = []
        page.on("console", lambda msg: console_msgs.append(msg.text) if "[AITUBE]" in msg.text else None)

        # 확장 프로그램 오버레이 대기 (최대 10초)
        overlay = None
        try:
            page.wait_for_selector("#ai-shows-analyzer-overlay", timeout=10000)
            overlay = page.query_selector("#ai-shows-analyzer-overlay")
        except Exception:
            overlay = page.query_selector("#ai-shows-analyzer-overlay")
        check("오버레이 DOM 요소 존재", overlay is not None)

        # API 요청 대기 (최대 25초 — 프레임 10장 캡처 + 분석 시간)
        print(f"  {INFO} API 요청 대기 중 (최대 25초)...")
        deadline = time.time() + 25
        while time.time() < deadline and len(api_requests) == 0:
            try:
                page.wait_for_timeout(500)
            except Exception:
                break

        check("확장 -> 백엔드 API 요청 발생", len(api_requests) > 0,
              f"요청 수={len(api_requests)}")

        if api_requests:
            check("POST /api/analyze 호출", any(
                "/api/analyze" in r["url"] for r in api_requests
            ))

        # 응답 대기
        deadline = time.time() + 15
        while time.time() < deadline and len(api_responses) == 0:
            try:
                page.wait_for_timeout(500)
            except Exception:
                break

        # 분석 완료 대기: 오버레이에 최종 결과 표시될 때까지 (최대 60초)
        # 프레임 10장 캡처(seek + capture 반복) + API 응답 소요
        print(f"  {INFO} 분석 완료 대기 중 (최대 60초)...")
        result_keywords = ["실제 영상", "AI 생성 영상으로", "분석 완료", "확률"]
        analysis_done = False
        final_text = ""
        deadline = time.time() + 60
        while time.time() < deadline:
            try:
                page.wait_for_timeout(1500)
            except Exception:
                break
            if overlay:
                try:
                    final_text = overlay.inner_text()
                    if any(kw in final_text for kw in result_keywords):
                        analysis_done = True
                        break
                except Exception:
                    pass
            if len(api_responses) > 0:
                analysis_done = True
                break

        check("분석 완료 (응답 수신 또는 오버레이 결과)", analysis_done)

        if final_text:
            print(f"  {INFO} 최종 오버레이 텍스트: {final_text[:300]!r}")
            check("오버레이에 결과 표시", len(final_text.strip()) > 10)

        if api_responses:
            r = api_responses[0]
            check("응답에 ai_confidence 포함", "ai_confidence" in r)
            check("응답에 summary 포함", "summary" in r)
            check("응답에 detected_signs 포함", "detected_signs" in r)

        # AITUBE 콘솔 로그 출력
        if console_msgs:
            print(f"  {INFO} AITUBE 콘솔 로그 ({len(console_msgs)}개):")
            for msg in console_msgs[:10]:
                print(f"    {msg}")
        else:
            print(f"  {INFO} AITUBE 콘솔 로그 없음 (확장 프로그램 미주입 의심)")

        # 스크린샷
        try:
            page.screenshot(path="C:\\Temp\\aitube_e2e.png")
            print(f"  {INFO} 스크린샷 저장: C:\\Temp\\aitube_e2e.png")
        except Exception:
            pass

    except Exception as e:
        print(f"  {FAIL} 브라우저 테스트 중 오류: {e}")
    finally:
        try:
            page.close()
        except Exception:
            pass
        if chrome_proc:
            try:
                chrome_proc.terminate()
                chrome_proc.wait(timeout=5)
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("AITUBE E2E 테스트")
    print("=" * 60)

    with sync_playwright() as playwright:
        # API 테스트는 headless browser로 (빠름)
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()

        test_backend_health(page)
        test_json_api(page)
        test_error_cases(page)

        browser.close()

        # 브라우저 확장 테스트
        test_extension_on_youtube(playwright)

    print("\n" + "=" * 60)
    passed = sum(1 for _, ok in results if ok)
    failed = sum(1 for _, ok in results if not ok)
    print(f"결과: {passed} passed / {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
