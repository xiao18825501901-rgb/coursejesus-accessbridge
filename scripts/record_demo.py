from __future__ import annotations

import shutil
import os
import subprocess
import sys
import threading
import time
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.server import AccessBridgeHandler
from app.site import build_site


CHROME = Path(os.environ.get('CHROME_PATH', r"C:\Program Files\Google\Chrome\Application\chrome.exe"))
EVIDENCE = ROOT / "evidence"
RECORDING_DIR = EVIDENCE / "browser-record"


def _ensure_caption(page) -> None:
    page.evaluate(
        """() => {
          if (document.getElementById('demo-caption')) return;
          const style = document.createElement('style');
          style.textContent = `#demo-caption{position:fixed;left:0;right:0;bottom:0;
            z-index:99999;background:rgba(15,23,42,.96);color:#fff;padding:12px 24px;
            font:600 19px/1.35 system-ui,sans-serif;text-align:center;border-top:3px solid #8fb3ff}`;
          document.head.appendChild(style);
          const caption = document.createElement('div');
          caption.id = 'demo-caption';
          caption.setAttribute('role', 'status');
          caption.setAttribute('aria-live', 'polite');
          document.body.appendChild(caption);
        }"""
    )


def _srt_time(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def main() -> int:
    if not CHROME.exists():
        raise SystemExit(f"Chrome not found: {CHROME}")
    if RECORDING_DIR.exists():
        for path in RECORDING_DIR.iterdir():
            if path.is_file():
                path.unlink()
    RECORDING_DIR.mkdir(parents=True, exist_ok=True)
    build_site()

    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        partial(AccessBridgeHandler, directory=str(ROOT / "app" / "dist")),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    offline_path = ROOT / "app" / "dist" / "offline" / "stack-queue.html"
    captions: list[tuple[float, float, str]] = []
    started = time.monotonic()

    def show(page, text: str, seconds: float) -> None:
        _ensure_caption(page)
        page.evaluate(
            "(text) => { document.getElementById('demo-caption').textContent = text; }",
            text,
        )
        start = time.monotonic() - started
        page.wait_for_timeout(round(seconds * 1000))
        end = time.monotonic() - started
        captions.append((start, end, text))

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=str(CHROME),
                headless=True,
                args=["--allow-file-access-from-files"],
            )
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                record_video_dir=str(RECORDING_DIR),
                record_video_size={"width": 1280, "height": 720},
            )
            page = context.new_page()
            page.goto(f"{base_url}/index.html", wait_until="networkidle")
            show(page, "CourseJesus — AccessBridge · AccessED Hacks 2026", 5)
            show(
                page,
                "Three original lessons. No account, model, GPU, or network required.",
                6,
            )
            page.locator("#lessons").scroll_into_view_if_needed()
            show(page, "Choose a concept, then read one small step at a time.", 5)

            page.locator('a[href="lessons/stack-queue.html"]').first.click()
            page.wait_for_load_state("networkidle")
            show(page, "Every step is short, bilingual, and names its source.", 6)
            page.locator("figure").scroll_into_view_if_needed()
            show(
                page,
                "Validated VisualSpec 1.0 compiles locally to accessible SVG.",
                6,
            )
            page.locator("#toggle-language").click()
            show(
                page,
                "Chinese mode also updates the SVG title and long description.",
                6,
            )
            page.locator("#toggle-size").click()
            show(
                page,
                "Keyboard-accessible larger text and 200% reflow preserve reading order.",
                6,
            )
            page.locator("#toggle-size").click()
            page.locator("#toggle-language").click()

            page.locator("#quiz").scroll_into_view_if_needed()
            show(
                page,
                "Three short checks provide feedback and a traceable source.",
                5,
            )
            page.locator('input[name="stack-queue-q1"][value="0"]').check()
            page.locator('button[data-lesson="stack-queue"]').first.click()
            page.wait_for_timeout(2000)
            show(page, "A wrong choice gets a correction and a rationale.", 6)
            page.locator('input[name="stack-queue-q1"][value="2"]').check()
            page.locator('button[data-lesson="stack-queue"]').first.click()
            page.wait_for_timeout(2000)
            show(
                page,
                "Correct answers are practice evidence, not an official grade.",
                6,
            )

            page.locator('section[aria-labelledby="sources"]').scroll_into_view_if_needed()
            page.locator('section[aria-labelledby="sources"] summary').first.click()
            show(page, "Open each source to inspect its text and rights note.", 6)
            show(
                page,
                "The offline pack is generated from this same reviewed lesson.",
                5,
            )

            context.set_offline(True)
            page.goto(offline_path.as_uri(), wait_until="load")
            show(page, "With network disabled, the single HTML pack still opens.", 6)
            page.locator('input[name="q-Q1"][value="2"]').check()
            page.locator(".question button").first.click()
            page.locator("#language").click()
            show(
                page,
                "Steps, SVG, sources, and explanations remain available offline.",
                7,
            )

            context.set_offline(False)
            page.goto(f"{base_url}/lessons/bfs-dfs.html", wait_until="networkidle")
            page.locator('section[aria-labelledby="visual-section"]').scroll_into_view_if_needed()
            show(
                page,
                "The deterministic layout engine also handles branching graphs.",
                6,
            )
            page.goto(f"{base_url}/lessons/matrix-transform.html", wait_until="networkidle")
            page.locator('section[aria-labelledby="visual-section"]').scroll_into_view_if_needed()
            show(
                page,
                "No remote image, video, or GPU generation is part of the core demo.",
                6,
            )

            page.goto(f"{base_url}/index.html", wait_until="networkidle")
            page.locator('section[aria-labelledby="boundary-title"]').scroll_into_view_if_needed()
            show(
                page,
                "The boundary is explicit: practice is not certification and scores are untouched.",
                7,
            )
            show(
                page,
                "Everything runs from the isolated copy; tests, hashes, and manifests are included.",
                5,
            )
            video = page.video
            context.close()
            video_path = Path(video.path())
            browser.close()

        raw_target = EVIDENCE / "demo-raw.webm"
        shutil.copy2(video_path, raw_target)
        srt_lines = []
        for index, (start, end, text) in enumerate(captions, start=1):
            srt_lines.extend(
                [
                    str(index),
                    f"{_srt_time(start)} --> {_srt_time(end)}",
                    text,
                    "",
                ]
            )
        srt_path = EVIDENCE / "demo-captions.srt"
        srt_path.write_text("\n".join(srt_lines) + "\n", encoding="utf-8")

        ffmpeg = shutil.which("ffmpeg") or r"C:\Users\Hp\AppData\Local\Programs\ffmpeg\bin\ffmpeg.exe"
        mp4_path = EVIDENCE / "demo-captioned.mp4"
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(raw_target),
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "22",
                "-pix_fmt",
                "yuv420p",
                "-an",
                "-movflags",
                "+faststart",
                str(mp4_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"Video: {mp4_path}")
        print(f"Captions: {srt_path}")
        print(f"Duration: {captions[-1][1]:.1f}s")
        return 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
