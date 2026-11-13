from __future__ import annotations

import copy

import pytest

from app.lessons import load_lessons
from app.offline_export import build_learning_pack
from app.offline_pack import render, validate
from app.site import _render_visual


@pytest.fixture
def pack() -> dict:
    lesson = load_lessons()[0]
    return build_learning_pack(lesson, _render_visual(lesson))


def test_integrated_pack_is_valid(pack) -> None:
    validate(pack)
    assert pack["access"] == "synthetic"
    assert len(pack["sections"]) == 3
    assert len(pack["questions"]) == 3
    assert pack["visual"]["svg"].startswith("<svg")


def test_private_pack_is_refused(pack) -> None:
    changed = copy.deepcopy(pack)
    changed["access"] = "private-campus"
    with pytest.raises(ValueError, match="synthetic/public/permission-cleared"):
        validate(changed)


def test_missing_source_reference_is_refused(pack) -> None:
    changed = copy.deepcopy(pack)
    changed["questions"][0]["sourceIds"] = ["not-a-source"]
    with pytest.raises(ValueError, match="valid source references"):
        validate(changed)


def test_boolean_answer_index_is_refused(pack) -> None:
    changed = copy.deepcopy(pack)
    changed["questions"][0]["answer"] = True
    with pytest.raises(ValueError, match="Invalid answer index"):
        validate(changed)


def test_duplicate_question_id_is_refused(pack) -> None:
    changed = copy.deepcopy(pack)
    changed["questions"].append(copy.deepcopy(changed["questions"][0]))
    with pytest.raises(ValueError, match="unique"):
        validate(changed)


def test_script_payload_is_escaped(pack) -> None:
    changed = copy.deepcopy(pack)
    changed["sections"][0]["body"]["en"] = "</script><script>alert(1)</script>"
    output = render(changed)
    assert "</script><script>alert(1)</script>" not in output
    assert "&lt;/script&gt;&lt;script&gt;alert(1)&lt;/script&gt;" in output


def test_offline_pack_has_no_network_or_official_grade_claim(pack) -> None:
    output = render(pack)
    assert "connect-src 'none'" in output
    assert 'fetch(' not in output
    assert "https://" not in output
    assert "OFFLINE PRACTICE" in output
    assert "not an official grade" in output
    assert 'role="status"' in output
    assert 'aria-live="polite"' in output


def test_offline_visual_requires_safe_svg(pack) -> None:
    changed = copy.deepcopy(pack)
    changed["visual"]["svg"] = '<svg xmlns="http://www.w3.org/2000/svg"><script/></svg>'
    with pytest.raises(ValueError, match="safe allowlist"):
        validate(changed)
