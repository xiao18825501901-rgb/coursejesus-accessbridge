from __future__ import annotations

import pytest

from app.lessons import load_lessons


def test_exactly_three_original_lessons_load() -> None:
    lessons = load_lessons()

    assert [lesson.lesson_id for lesson in lessons] == ["stack-queue", "bfs-dfs", "matrix-transform"]
    assert all(len(lesson.steps) >= 3 for lesson in lessons)
    assert all(len(lesson.quiz) == 3 for lesson in lessons)
    assert all(lesson.alt_text.en and lesson.alt_text.zh for lesson in lessons)
    assert all(lesson.long_description.en and lesson.long_description.zh for lesson in lessons)
    assert all(lesson.original_source_excerpt.en and lesson.original_source_excerpt.zh for lesson in lessons)


def test_quiz_answers_have_rationales_and_sources() -> None:
    lessons = load_lessons()

    for lesson in lessons:
        for question in lesson.quiz:
            assert 0 <= question.answer < len(question.options)
            assert question.rationale.en and question.rationale.zh
            assert question.source_id


def test_lesson_visual_specs_are_safe_and_local() -> None:
    from app.visual.router import route_visual

    for lesson in load_lessons():
        assert route_visual(lesson.visual_spec)
        assert lesson.visual_spec.diagram is not None
        assert not lesson.visual_spec.reference_assets


def test_bilingual_field_rejects_missing_locale() -> None:
    from app.lessons import LocalizedText

    with pytest.raises(ValueError, match="both en and zh"):
        LocalizedText(en="Only English")
