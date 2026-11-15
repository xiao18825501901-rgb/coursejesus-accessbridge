"""Prepare an empty, synthetic database for the public-guest browser acceptance.

The script deliberately refuses to run outside the competition ``runtime``
directory and never reads the production database. It creates only the two
clearly synthetic access-control fixtures used by the browser check.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = (ROOT / "runtime").resolve()
sys.path.insert(0, str(ROOT / "services" / "rag-api"))

from app.config import Settings  # noqa: E402
from app.db import Database  # noqa: E402


PUBLIC_COURSE = (
    "competition-public-course",
    "AccessED Public Learning Course",
    "Synthetic public course used only by the isolated browser acceptance.",
    "competition-browser-owner",
    "user",
    "public",
)
PRIVATE_COURSE = (
    "competition-private-course",
    "Private Control Course",
    "Synthetic private control that public guests must never see.",
    "competition-browser-owner",
    "user",
    "private",
)


def prepare(target: Path) -> tuple[Path, Path]:
    target = target.resolve()
    if not target.is_relative_to(RUNTIME_ROOT):
        raise ValueError("The browser fixture must stay under the competition runtime directory")
    if target.exists() and any(target.iterdir()):
        raise ValueError("The browser fixture directory must be absent or empty")

    uploads = target / "uploads"
    database_path = target / "rag.sqlite3"
    target.mkdir(parents=True, exist_ok=True)
    uploads.mkdir()
    database = Database(
        Settings(
            database_path=database_path,
            upload_dir=uploads,
            v3_enabled=True,
            ui_extension_enabled=True,
            app_env="test",
            rag_provider_mode="deterministic",
            visual_engine_enabled=True,
            visual_provider="mock",
        )
    )
    database.initialize()
    with sqlite3.connect(database_path) as connection:
        connection.executemany(
            "INSERT INTO courses("
            "id,name,description,owner_user_id,course_type,visibility"
            ") VALUES(?,?,?,?,?,?)",
            (PUBLIC_COURSE, PRIVATE_COURSE),
        )
        connection.commit()
    return database_path, uploads


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: prepare_competition_browser.py TARGET_DIRECTORY")
    prepared_database, prepared_uploads = prepare(Path(sys.argv[1]))
    print(f"database={prepared_database}")
    print(f"uploads={prepared_uploads}")
