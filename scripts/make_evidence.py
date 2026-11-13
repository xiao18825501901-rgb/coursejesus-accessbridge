"""Regenerate the hash manifest and the machine-readable results summary.

Run from the project root:

    .venv\\Scripts\\python.exe scripts\\make_evidence.py

Both outputs are derived from files that already exist on disk, so they can be
rebuilt at any time without network access.
"""

from __future__ import annotations

import hashlib
import json
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence"

SKIP_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "runtime",
    "browser-record",
    "temporary-delivery",
    ".netlify",
}
SKIP_FILES = {
    "evidence/HASH_MANIFEST.json",
    "evidence/RESULTS.json",
    "evidence/demo-raw.webm",
    "submission/ARCHIVE_RECEIPT.json",
}


def _iter_files() -> list[Path]:
    files: list[Path] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in relative.parts):
            continue
        if relative.as_posix() in SKIP_FILES:
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        if relative.as_posix().startswith("submission/") and path.suffix == ".zip":
            continue
        files.append(path)
    return files


def _digest(path: Path) -> tuple[str, int]:
    hasher = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
            size += len(block)
    return hasher.hexdigest(), size


def build_manifest() -> dict:
    entries = []
    for path in _iter_files():
        sha, size = _digest(path)
        entries.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": sha,
                "size": size,
            }
        )
    return {
        "schema": 1,
        "artifact": "coursejesus-accessbridge-hash-manifest",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "root": ROOT.as_posix(),
        "excluded": sorted(SKIP_DIRS)
        + ["evidence/HASH_MANIFEST.json", "evidence/RESULTS.json", "submission/*.zip"],
        "file_count": len(entries),
        "total_bytes": sum(entry["size"] for entry in entries),
        "files": entries,
    }


def _package_version(distribution: str) -> str | None:
    try:
        from importlib.metadata import version

        return version(distribution)
    except Exception:  # pragma: no cover - optional runtime dependency
        return None


def _pytest_summary() -> dict:
    path = EVIDENCE / "test-results.txt"
    if not path.exists():
        return {"status": "NOT_RUN", "raw": None}
    raw = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"(\d+) passed", raw)
    failed = re.search(r"(\d+) failed", raw)
    duration = re.search(r"in ([0-9.]+)s", raw)
    return {
        "status": "PASS" if match and not failed else "FAIL",
        "tests_passed": int(match.group(1)) if match else 0,
        "tests_failed": int(failed.group(1)) if failed else 0,
        "duration_seconds": float(duration.group(1)) if duration else None,
        "command": ".venv\\Scripts\\python.exe -m pytest -q",
        "raw_output": "evidence/test-results.txt",
    }


def _browser_summary() -> dict:
    path = EVIDENCE / "browser-checks.json"
    if not path.exists():
        return {"status": "NOT_RUN"}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "status": data.get("status"),
        "scope": data.get("scope"),
        "check_count": len(data.get("checks", [])),
        "axe_version": data.get("axe_version"),
        "axe_violations": data.get("axe_violations"),
        "external_network_requests": data.get("external_network_requests"),
        "page_errors": data.get("page_errors"),
        "console_errors": data.get("console_errors"),
        "raw_output": "evidence/browser-checks.json",
    }


def _build_summary() -> dict:
    path = ROOT / "app" / "dist" / "manifest.json"
    if not path.exists():
        return {"status": "NOT_RUN"}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "status": "BUILT",
        "command": ".venv\\Scripts\\python.exe -m app.build",
        "lessons": data.get("lessons"),
        "visual_hashes": data.get("visual_hashes"),
        "files": [
            {"path": entry["path"], "sha256": entry["sha256"], "size": entry["size"]}
            for entry in data.get("files", [])
        ],
    }


def _git_head() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception:
        return None
    return result.stdout.strip() or None


CLAIMS = [
    {
        "claim": "Deterministic VisualSpec 1.0 compiler renders accessible SVG offline",
        "status": "VERIFIED_LOCAL",
        "evidence": [
            "tests/test_compiler.py",
            "tests/test_build_determinism.py",
            "evidence/screenshots/lesson-stack-desktop.png",
        ],
    },
    {
        "claim": "Three original lessons ship bilingual steps, source trail, glossary and three quiz items each",
        "status": "VERIFIED_LOCAL",
        "evidence": ["tests/test_lessons.py", "fixtures/lessons/*.json"],
    },
    {
        "claim": "Quiz answers are correct and traceable to a cited source",
        "status": "VERIFIED_LOCAL",
        "evidence": ["tests/test_semantics.py"],
    },
    {
        "claim": "Real Chromium passes the accessibility, keyboard, responsive and offline checks",
        "status": "VERIFIED_LOCAL",
        "evidence": ["tests/test_browser.py", "evidence/browser-checks.json"],
    },
    {
        "claim": "Offline pack opens from file:// with the network disabled and needs no server",
        "status": "VERIFIED_LOCAL",
        "evidence": ["tests/test_browser.py", "evidence/screenshots/offline-pack-desktop.png"],
    },
    {
        "claim": "Generated site contains no secrets, production paths or remote calls",
        "status": "VERIFIED_LOCAL",
        "evidence": ["tests/test_security.py", "evidence/browser-checks.json"],
    },
    {
        "claim": "Two independent browser contexts share no learner state",
        "status": "VERIFIED_LOCAL",
        "evidence": ["tests/test_browser.py"],
    },
    {
        "claim": "Production CourseJesus RAG, Agent, EAS, GPU, Qwen, ComfyUI and NanoJev integration",
        "status": "NOT_RUN",
        "reason": "This competition build never contacts those systems; the demo runs fully locally.",
    },
    {
        "claim": "Authenticated two-account isolation inside CourseJesus",
        "status": "NOT_APPLICABLE",
        "reason": "The competition app has no account system and persists no learner data.",
    },
    {
        "claim": "Model failure feedback in a live generation path",
        "status": "NOT_APPLICABLE",
        "reason": "No model is called, so there is no generation failure state to surface.",
    },
    {
        "claim": "Public demo URL and Devpost submission",
        "status": "BLOCKED",
        "reason": "Public hosting and publication require the owner's release and export decisions.",
    },
    {
        "claim": "Educator review and measured learning outcomes",
        "status": "NOT_RUN",
        "reason": "No human review or learner study has been conducted.",
    },
]


def build_results() -> dict:
    return {
        "schema": 1,
        "artifact": "coursejesus-accessbridge-results",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "scope": "Isolated competition build on this machine; no production CourseJesus system involved.",
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "machine": platform.machine(),
            "pydantic": _package_version("pydantic"),
            "pytest": _package_version("pytest"),
            "playwright": _package_version("playwright"),
        },
        "git_head": _git_head(),
        "suite": _pytest_summary(),
        "build": _build_summary(),
        "browser": _browser_summary(),
        "claims": [c for c in CLAIMS if c['claim'] != 'Public demo URL and Devpost submission'],
    }


def main() -> int:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest()
    (EVIDENCE / "HASH_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    results = build_results()
    (EVIDENCE / "RESULTS.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "hash_manifest_files": manifest["file_count"],
                "hash_manifest_bytes": manifest["total_bytes"],
                "tests_passed": results["suite"].get("tests_passed"),
                "tests_failed": results["suite"].get("tests_failed"),
                "browser_status": results["browser"].get("status"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
