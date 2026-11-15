"""Create a deterministic SHA-256 manifest for the competition delivery."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "evidence" / "HASH_MANIFEST.json"
EXCLUDED_NAMES = {OUTPUT.name}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tracked_files() -> list[Path]:
    raw = subprocess.check_output(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
    )
    return [
        ROOT / item.decode("utf-8")
        for item in raw.split(b"\0")
        if item and Path(item.decode("utf-8")).name not in EXCLUDED_NAMES
    ]


def generated_files(include_submission_artifacts: bool) -> list[Path]:
    paths: set[Path] = set()
    for pattern in (
        "apps/web/dist/**/*",
        "evidence/screenshots/**/*",
        "evidence/*.mp4",
        "evidence/*.webm",
        "evidence/*.srt",
    ):
        paths.update(path for path in ROOT.glob(pattern) if path.is_file())
    if include_submission_artifacts:
        paths.update(
            path
            for path in (ROOT / "submission").glob("*.zip")
            if path.is_file()
        )
    return sorted(paths)


def category_for(path: str) -> str:
    if path.startswith("apps/web/dist/"):
        return "generated_frontend"
    if path.startswith("evidence/screenshots/"):
        return "screenshot"
    if path.startswith("evidence/") and path.endswith((".mp4", ".webm", ".srt")):
        return "demo_media"
    if path.startswith("submission/") and path.endswith(".zip"):
        return "submission_artifact"
    if path.startswith("fixtures/"):
        return "fixture"
    if path.startswith("tests/"):
        return "test"
    if path.startswith("scripts/"):
        return "script"
    if path.startswith("evidence/"):
        return "evidence"
    if path.startswith("submission/"):
        return "submission_document"
    return "source_or_documentation"


def git_value(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--include-submission-artifacts",
        action="store_true",
        help="Include final source and demo ZIP hashes.",
    )
    args = parser.parse_args()

    files = sorted(set(tracked_files()) | set(generated_files(args.include_submission_artifacts)))
    entries = []
    for path in files:
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT).as_posix()
        entries.append(
            {
                "path": relative,
                "category": category_for(relative),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )

    manifest = {
        "schema": "coursejesus.accessed-hacks.hash-manifest.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository": "xiao18825501901-rgb/coursejesus-accessbridge",
        "branch": git_value("branch", "--show-current"),
        "source_commit_at_generation": git_value("rev-parse", "HEAD"),
        "file_count": len(entries),
        "total_bytes": sum(entry["bytes"] for entry in entries),
        "excluded": [
            ".git/",
            ".venv/",
            "node_modules/",
            "runtime/",
            "review-inputs/",
            "caches",
            "databases",
            "uploads",
            "secrets",
            "model weights",
            "private media",
        ],
        "files": entries,
    }
    OUTPUT.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(
        f"wrote {OUTPUT.relative_to(ROOT)}: "
        f"{len(entries)} files, {manifest['total_bytes']} bytes"
    )


if __name__ == "__main__":
    main()
