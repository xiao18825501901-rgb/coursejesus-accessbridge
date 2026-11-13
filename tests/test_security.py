from __future__ import annotations

import json
import re
from pathlib import Path

from app.site import build_site


FORBIDDEN = (
    "OPENAI_API_KEY",
    "CLERK_SECRET_KEY",
    "CANVAS_TOKEN",
    "RAG_DATABASE_PATH",
    "BEGIN PRIVATE KEY",
    "AKIA",
    "sk-proj-",
    "serverless-prod",
    "comfyui-prod",
    "knowledge-map-ae8e786",
    "legacy-deb82cc518b2",
)


def test_generated_site_has_no_production_or_secret_references(tmp_path) -> None:
    build_site(tmp_path)
    for path in tmp_path.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for marker in FORBIDDEN:
            assert marker not in text, f"{marker} leaked into {path.name}"


def test_generated_site_has_no_remote_asset_or_api_url(tmp_path) -> None:
    build_site(tmp_path)
    for path in tmp_path.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        assert "https://" not in text
        assert text.count("http://") == text.count("http://www.w3.org/2000/svg")
        assert not re.search(r"(?:fetch|XMLHttpRequest|WebSocket)\s*\(", text)


def test_manifest_covers_every_generated_file(tmp_path) -> None:
    outputs = build_site(tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    listed = {entry["path"] for entry in manifest["files"]}
    actual = {
        path.relative_to(tmp_path).as_posix()
        for path in outputs
        if path.name != "manifest.json"
    }
    assert listed == actual


def test_public_runtime_has_no_source_archive_paths(tmp_path) -> None:
    build_site(tmp_path)
    for path in tmp_path.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        assert "D:\\CourseJesus" not in text
        assert "F:\\Hackathon" not in text
        assert "C:\\Users\\Hp" not in text
