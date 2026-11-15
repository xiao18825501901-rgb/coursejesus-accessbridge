from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "prepare_competition_browser.py"


def load_prepare_module():
    spec = importlib.util.spec_from_file_location("prepare_competition_browser_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("Could not load prepare_competition_browser.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_prepare_accepts_empty_directory_tree(tmp_path, monkeypatch):
    module = load_prepare_module()
    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir()
    monkeypatch.setattr(module, "RUNTIME_ROOT", runtime_root.resolve())
    target = runtime_root / "competition-empty-tree" / "data"
    (target / "ui-extension").mkdir(parents=True)

    database_path, uploads = module.prepare(target)

    assert database_path.is_file()
    assert uploads.is_dir()


def test_prepare_refuses_a_populated_directory_tree(tmp_path, monkeypatch):
    module = load_prepare_module()
    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir()
    monkeypatch.setattr(module, "RUNTIME_ROOT", runtime_root.resolve())
    target = runtime_root / "competition-populated" / "data"
    target.mkdir(parents=True)
    (target / "unexpected.txt").write_text("must not be overwritten", encoding="utf-8")

    with pytest.raises(ValueError, match="empty directories"):
        module.prepare(target)
