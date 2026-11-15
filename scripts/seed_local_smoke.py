"""Seed an isolated local database with clearly synthetic access-control fixtures."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path


def main() -> None:
    app_env = os.getenv("APP_ENV", "")
    database_value = os.getenv("RAG_DATABASE_PATH", "")
    if app_env not in {"development", "test"}:
        raise SystemExit("Local smoke seeding is allowed only with APP_ENV=development or test.")
    if not database_value:
        raise SystemExit("RAG_DATABASE_PATH is required.")

    database_path = Path(database_value).resolve()
    if not database_path.is_file():
        raise SystemExit(f"Database does not exist: {database_path}")

    fixtures = (
        (
            "accessed-public-smoke-course",
            "AccessED Public Smoke Course",
            "Synthetic public fixture for local guest-access verification.",
            "competition-local-owner",
            "user",
            "public",
        ),
        (
            "accessed-private-smoke-course",
            "AccessED Private Smoke Course",
            "Synthetic private fixture that guest sessions must never expose.",
            "competition-local-owner",
            "user",
            "private",
        ),
    )
    with sqlite3.connect(database_path) as connection:
        connection.executemany(
            "INSERT OR IGNORE INTO courses("
            "id,name,description,owner_user_id,course_type,visibility"
            ") VALUES(?,?,?,?,?,?)",
            fixtures,
        )
        connection.commit()
    print(f"Seeded {len(fixtures)} synthetic access-control fixtures in {database_path}.")


if __name__ == "__main__":
    main()
