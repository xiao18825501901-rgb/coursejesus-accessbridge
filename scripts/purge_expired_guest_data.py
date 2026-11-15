"""Run the UI guest-retention cleanup explicitly.

This is intended for a platform scheduler. The application also performs the
same bounded cleanup whenever a guest session is issued.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "rag-api"))

from app.cm_update.db import Database  # noqa: E402
from app.ui_extension.guest import prune_expired_guest_data  # noqa: E402


def main() -> None:
    data_dir = Path(os.getenv("CMUI_DATA_DIR", ROOT / "runtime" / "ui-extension"))
    database_path = Path(os.getenv("CMUI_DATABASE_PATH", data_dir / "ui.sqlite3"))
    ttl_seconds = int(os.getenv("GUEST_SESSION_TTL_SECONDS", "86400"))
    deleted = prune_expired_guest_data(Database(database_path), ttl_seconds)
    print(f"purged_guest_workspaces={deleted}")


if __name__ == "__main__":
    main()
