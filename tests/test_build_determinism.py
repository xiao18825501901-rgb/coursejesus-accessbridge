from __future__ import annotations

import hashlib

from app.site import build_site


def _hashes(root):
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_two_clean_builds_are_byte_identical(tmp_path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    build_site(first)
    build_site(second)
    assert _hashes(first) == _hashes(second)
