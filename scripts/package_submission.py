"""Build the two submission archives.

    .venv\\Scripts\\python.exe scripts\\package_submission.py

Source archive: code, tests, fixtures, docs, evidence without the raw capture.
Demo archive: captioned video, captions, screenshots, browser checks, results.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUBMISSION = ROOT / "submission"

SOURCE_NAME = "CourseJesus_AccessBridge_Source_20261113_v2.zip"
DEMO_NAME = "CourseJesus_AccessBridge_Demo_20261113_v2.zip"

SOURCE_SKIP_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "runtime",
    "browser-record",
    "temporary-delivery",
    ".netlify",
}
SOURCE_SKIP_FILES = {"evidence/demo-raw.webm", "submission/ARCHIVE_RECEIPT.json"}

DEMO_PATHS = [
    "evidence/demo-captioned.mp4",
    "evidence/demo-captions.srt",
    "evidence/browser-checks.json",
    "evidence/RESULTS.json",
    "evidence/HASH_MANIFEST.json",
    "submission/SCREENSHOTS.md",
    "README.md",
]
DEMO_DIRS = ["evidence/screenshots"]


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def _source_files() -> list[Path]:
    files: list[Path] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if any(part in SOURCE_SKIP_DIRS for part in relative.parts):
            continue
        if relative.as_posix() in SOURCE_SKIP_FILES:
            continue
        if relative.as_posix().startswith("submission/") and path.suffix == ".zip":
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        files.append(path)
    return files


def _demo_files() -> list[Path]:
    files = [ROOT / name for name in DEMO_PATHS]
    for directory in DEMO_DIRS:
        files.extend(sorted((ROOT / directory).glob("*")))
    return [path for path in files if path.is_file()]


def _write_archive(target: Path, files: list[Path], extra: dict[str, str] | None = None) -> dict:
    SUBMISSION.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            archive.write(path, path.relative_to(ROOT).as_posix())
        if extra:
            for name, content in extra.items():
                archive.writestr(name, content)
    return {
        "path": target.relative_to(ROOT).as_posix(),
        "sha256": _sha256(target),
        "size": target.stat().st_size,
        "entries": len(files) + (len(extra) if extra else 0),
    }


def main() -> int:
    built = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "root": ROOT.as_posix(),
        "source_archive": None,
        "demo_archive": None,
    }
    source_files = _source_files()
    built["source_archive"] = _write_archive(
        SUBMISSION / SOURCE_NAME,
        source_files,
        extra={
            "PACKAGE_README.txt": (
                "CourseJesus - AccessBridge (AccessED Hacks 2026)\n"
                f"Packaged {built['generated_at']} from {ROOT.as_posix()}\n\n"
                "Start:   .\\scripts\\start.ps1   then http://127.0.0.1:15273/\n"
                "Stop:    .\\scripts\\stop.ps1\n"
                "Tests:   .venv\\Scripts\\python.exe -m pytest -q\n"
                "Read README.md, LICENSE_NOTES.md and submission/MANUAL_OWNER_ACTIONS.md first.\n"
            )
        },
    )
    built["demo_archive"] = _write_archive(SUBMISSION / DEMO_NAME, _demo_files())
    receipt = SUBMISSION / "ARCHIVE_RECEIPT.json"
    receipt.write_text(json.dumps(built, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(built, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
