from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.site import build_site


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the AccessBridge static learning app.")
    parser.add_argument("--output", type=Path, help="Output directory; defaults to app/dist.")
    args = parser.parse_args()
    files = build_site(args.output)
    print(
        json.dumps(
            {
                "status": "BUILT",
                "output": str((args.output or Path("app/dist")).resolve()),
                "files": len(files),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
