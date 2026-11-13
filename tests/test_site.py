from __future__ import annotations

import json

from app.site import build_site


def test_site_builds_three_lessons_and_offline_exports(tmp_path) -> None:
    outputs = build_site(tmp_path)
    expected = {
        tmp_path / "index.html",
        tmp_path / "lessons" / "stack-queue.html",
        tmp_path / "lessons" / "bfs-dfs.html",
        tmp_path / "lessons" / "matrix-transform.html",
        tmp_path / "offline" / "stack-queue.html",
        tmp_path / "offline" / "bfs-dfs.html",
        tmp_path / "offline" / "matrix-transform.html",
        tmp_path / "manifest.json",
    }
    assert expected <= set(outputs)
    index = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert index.count('class="lesson-card"') == 3


def test_site_avoids_remote_or_secret_content(tmp_path) -> None:
    build_site(tmp_path)
    for path in tmp_path.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        assert text.count("http://www.w3.org/2000/svg") == text.count("http://")
        assert "https://" not in text
        assert "OPENAI_API_KEY" not in text
        assert "Clerk" not in text
        assert "EAS" not in text
        assert "Comfy" not in text
        assert "Qwen" not in text


def test_manifest_is_a_json_object_with_hashes(tmp_path) -> None:
    build_site(tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == 1
    assert manifest["lessons"] == ["stack-queue", "bfs-dfs", "matrix-transform"]
    assert manifest["files"]
    assert all("sha256" in entry for entry in manifest["files"])
