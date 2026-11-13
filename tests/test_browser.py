from __future__ import annotations

import json
import os
import shutil
import threading
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import pytest

from app.server import AccessBridgeHandler
from app.site import build_site


ROOT = Path(__file__).resolve().parents[1]
CHROME = Path(os.environ.get('CHROME_PATH') or shutil.which('chromium') or shutil.which('google-chrome') or r"C:\Program Files\Google\Chrome\Application\chrome.exe")
AXE = ROOT / "tests" / "vendor" / "axe.min.js"


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    output = tmp_path_factory.mktemp("accessbridge-browser")
    build_site(output)
    handler = partial(AccessBridgeHandler, directory=str(output))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield output, f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _axe_violations(page):
    page.add_script_tag(path=str(AXE))
    return page.evaluate(
        """async () => {
          const result = await axe.run(document, {
            runOnly: {type: 'tag', values: [
              'wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'
            ]}
          });
          return result.violations;
        }"""
    )


def _clean_screenshot(page, path: Path) -> None:
    page.evaluate(
        """() => {
          if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
          document.documentElement.style.scrollBehavior = 'auto';
          window.scrollTo(0, 0);
        }"""
    )
    page.wait_for_timeout(100)
    page.screenshot(path=str(path), full_page=True)


def test_real_chromium_accessibility_and_offline_flow(site) -> None:
    from playwright.sync_api import sync_playwright

    output, base_url = site
    screenshots = ROOT / "evidence" / "screenshots"
    screenshots.mkdir(parents=True, exist_ok=True)
    checks: list[str] = []
    page_errors: list[str] = []
    console_errors: list[str] = []
    requests: list[str] = []
    axe_report: dict[str, list] = {}

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=str(CHROME) if CHROME.exists() else None,
            headless=True,
            args=["--allow-file-access-from-files"],
        )
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        page.set_default_navigation_timeout(90000)
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        page.on("request", lambda request: requests.append(request.url))

        page.goto(f"{base_url}/index.html", wait_until="networkidle")
        assert page.locator(".lesson-card").count() == 3
        assert page.locator('a[href^="lessons/"]').count() == 3
        assert page.evaluate("localStorage.length") == 0
        assert page.evaluate("document.cookie") == ""
        checks.append("index_three_lessons")
        checks.append("no_browser_persistent_learner_data")
        page.screenshot(path=str(screenshots / "index-desktop.png"), full_page=True)

        page.locator("#toggle-language").click()
        assert page.locator("html").get_attribute("lang") == "zh-CN"
        assert "一步一步无障碍" in page.locator("h1").inner_text()
        checks.append("index_chinese_toggle")
        page.locator("#toggle-language").click()

        page.locator("#toggle-size").focus()
        page.keyboard.press("Space")
        assert page.locator("#toggle-size").get_attribute("aria-pressed") == "true"
        assert page.evaluate("parseFloat(getComputedStyle(document.body).fontSize)") >= 22
        checks.append("keyboard_large_text")
        page.locator("#toggle-size").press("Space")

        for width in (1280, 768, 390, 360):
            page.set_viewport_size({"width": width, "height": 900})
            assert page.evaluate(
                "document.documentElement.scrollWidth <= window.innerWidth"
            ), f"horizontal overflow at {width}px"
        checks.append("responsive_no_horizontal_overflow_360_390_768_1280")
        page.set_viewport_size({"width": 390, "height": 844})
        page.screenshot(path=str(screenshots / "index-mobile-390.png"), full_page=True)

        page.set_viewport_size({"width": 1280, "height": 1000})
        axe_report["index"] = _axe_violations(page)
        checks.append("axe_index_wcag_scan")

        page.goto(f"{base_url}/lessons/stack-queue.html", wait_until="networkidle")
        assert page.locator(".step").count() == 3
        assert page.locator(".quiz-question").count() == 3
        assert page.locator("svg[role=img]").count() == 1
        assert page.locator("svg title").count() == 1
        assert page.locator("svg desc").count() == 1
        checks.append("lesson_three_steps_three_questions_accessible_svg")
        page.screenshot(path=str(screenshots / "lesson-stack-desktop.png"), full_page=True)

        page.reload(wait_until="networkidle")
        page.keyboard.press("Tab")
        assert page.evaluate(
            "document.activeElement && document.activeElement.classList.contains('skip-link')"
        )
        page.keyboard.press("Enter")
        assert page.url.endswith("#main")
        checks.append("keyboard_skip_link")

        page.locator("#toggle-language").focus()
        page.keyboard.press("Enter")
        assert page.locator("html").get_attribute("lang") == "zh-CN"
        assert "栈与队列" in page.locator("h1").inner_text()
        assert "对比栈与队列" in page.locator("#ab-visual-title").text_content()
        checks.append("keyboard_language_toggle_updates_svg_text")

        page.locator("#toggle-size").focus()
        page.keyboard.press("Space")
        assert page.locator("#toggle-size").get_attribute("aria-pressed") == "true"
        _clean_screenshot(page, screenshots / "lesson-stack-zh-large.png")
        page.locator("#toggle-size").press("Space")
        page.locator("#toggle-language").press("Enter")

        first_question = page.locator('input[name="stack-queue-q1"][value="0"]')
        first_question.focus()
        page.keyboard.press("Space")
        page.locator('button[data-lesson="stack-queue"]').first.focus()
        page.keyboard.press("Enter")
        feedback = page.locator(".quiz-feedback").first
        assert feedback.get_attribute("class") == "quiz-feedback incorrect"
        assert feedback.inner_text().startswith("Try again.")
        checks.append("keyboard_wrong_answer_feedback")

        page.locator('input[name="stack-queue-q1"][value="2"]').check()
        page.locator('button[data-lesson="stack-queue"]').first.click()
        assert feedback.get_attribute("class") == "quiz-feedback correct"
        assert feedback.inner_text().startswith("Correct.")
        assert "AB-S1" in feedback.inner_text()
        checks.append("quiz_correct_answer_and_source_feedback")

        source = page.locator('section[aria-labelledby="sources"] details').first
        assert source.count() == 1
        assert source.locator("summary").count() == 1
        source.locator("summary").click()
        assert source.get_attribute("open") is not None
        page.locator('section[aria-labelledby="sources"]').screenshot(
            path=str(screenshots / "source-expanded.png")
        )
        checks.append("source_expansion")

        page.set_viewport_size({"width": 640, "height": 900})
        assert page.evaluate(
            "document.documentElement.scrollWidth <= window.innerWidth"
        )
        _clean_screenshot(page, screenshots / "lesson-stack-zoom200-reflow.png")
        checks.append("zoom_200_percent_equivalent_reflow")

        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate(
            "document.documentElement.scrollWidth <= window.innerWidth"
        )
        _clean_screenshot(page, screenshots / "lesson-stack-mobile-390.png")
        checks.append("lesson_mobile_no_overflow")

        page.set_viewport_size({"width": 1280, "height": 1000})
        page.reload(wait_until="networkidle")
        axe_report["lesson"] = _axe_violations(page)
        checks.append("axe_lesson_wcag_scan")

        page.goto(f"{base_url}/lessons/bfs-dfs.html", wait_until="networkidle")
        assert page.locator("svg[role=img]").count() == 1
        page.locator('section[aria-labelledby="visual-section"]').screenshot(
            path=str(screenshots / "bfs-dag-visual.png")
        )
        assert page.locator("text").filter(has_text="A").count() >= 1
        checks.append("bfs_diagram_rendered")

        page.goto(f"{base_url}/lessons/matrix-transform.html", wait_until="networkidle")
        assert page.locator(".step").count() == 3
        page.locator('section[aria-labelledby="visual-section"]').screenshot(
            path=str(screenshots / "matrix-transform-visual.png")
        )
        checks.append("matrix_transform_lesson_opens")

        offline_path = output / "offline" / "stack-queue.html"
        context.set_offline(True)
        offline_page = context.new_page()
        offline_errors: list[str] = []
        offline_page.on("pageerror", lambda error: offline_errors.append(str(error)))
        offline_page.goto(offline_path.as_uri(), wait_until="load")
        assert offline_page.locator(".question").count() == 3
        assert offline_page.locator("svg[role=img]").count() == 1
        assert offline_page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        offline_page.locator('input[name="q-Q1"][value="2"]').check()
        offline_page.locator(".question button").first.click()
        assert offline_page.locator(".feedback").first.inner_text().startswith("Correct.")
        offline_page.locator("#language").click()
        assert offline_page.locator("html").get_attribute("lang") == "zh-CN"
        assert not offline_errors
        offline_page.locator(".question").first.locator(".check").click()
        assert offline_page.locator(".feedback").first.inner_text().startswith("正确。")
        offline_page.screenshot(
            path=str(screenshots / "offline-pack-desktop.png"),
            full_page=True,
        )
        checks.append("offline_file_opens_with_network_disabled")
        checks.append("offline_pack_quiz_and_language_toggle")

        second_context = browser.new_context()
        second_page = second_context.new_page()
        second_page.goto(f"{base_url}/index.html", wait_until="networkidle")
        assert second_page.evaluate("localStorage.length") == 0
        assert second_page.evaluate("document.cookie") == ""
        checks.append("second_browser_context_isolated_no_shared_state")

        external_requests = [
            url
            for url in requests
            if urlparse(url).scheme in {"http", "https"}
            and urlparse(url).hostname not in {"127.0.0.1", "localhost"}
        ]
        assert not external_requests
        checks.append("zero_external_network_requests")
        assert not page_errors
        assert not console_errors
        checks.append("zero_page_or_console_errors")
        browser.close()

    violations = {
        page_name: [
            {
                "id": item["id"],
                "impact": item["impact"],
                "description": item["description"],
                "targets": [node["target"] for node in item["nodes"]],
            }
            for item in items
        ]
        for page_name, items in axe_report.items()
    }
    result = {
        "status": "PASS" if not any(violations.values()) else "FAIL",
        "scope": "VERIFIED_LOCAL real Chrome against generated application",
        "checks": checks,
        "axe_version": "4.14.0",
        "axe_violations": violations,
        "network_requests": requests,
            "external_network_requests": external_requests,
        "page_errors": page_errors,
        "console_errors": console_errors,
        "notes": [
            "The accessibility scan is automated evidence, not WCAG certification.",
            "The 200% check uses a 640 CSS-pixel viewport as the equivalent reflow width for a 1280-pixel window.",
            "The offline page was opened through file:// while the browser context was offline.",
        ],
    }
    (ROOT / "evidence" / "browser-checks.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    assert not any(violations.values()), json.dumps(violations, indent=2)
