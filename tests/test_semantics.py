from __future__ import annotations

import re
import html

from app.lessons import load_lessons
from app.site import _render_index, _render_visual


EXPECTED_ANSWER_TEXT = {
    "stack-queue": ["C", "A", "Last in, first out"],
    "bfs-dfs": ["B and C", "A, B, C, D, E", "A, B, D"],
    "matrix-transform": ["Scale", "Rotate", "(-2,4)"],
}


def test_quiz_answers_match_independent_fact_table() -> None:
    lessons = {lesson.lesson_id: lesson for lesson in load_lessons()}
    for lesson_id, expected in EXPECTED_ANSWER_TEXT.items():
        actual = [question.options[question.answer].en for question in lessons[lesson_id].quiz]
        assert actual == expected


def test_visual_text_matches_spec_and_semantics() -> None:
    for lesson in load_lessons():
        visual = _render_visual(lesson)
        for label in lesson.visual_spec.must_include:
            assert label in html.unescape(visual.svg)
        for node in lesson.visual_spec.diagram.nodes:
            assert node.label in html.unescape(visual.svg)
        assert lesson.alt_text.en in html.unescape(visual.svg)
        assert lesson.long_description.en in html.unescape(visual.svg)
        assert lesson.alt_text.zh in html.unescape(visual.svg)
        assert lesson.long_description.zh in html.unescape(visual.svg)


def test_bfs_layout_has_distinct_graph_layers() -> None:
    lesson = next(item for item in load_lessons() if item.lesson_id == "bfs-dfs")
    visual = _render_visual(lesson)
    positions = {
        match.group(3): (int(match.group(1)), int(match.group(2)))
        for match in re.finditer(
            r'<rect x="(\d+)" y="(\d+)"[^>]+id="ab-node-([^"]+)"',
            visual.svg,
        )
    }
    assert positions["a"][1] < positions["b"][1] < positions["d"][1]
    assert positions["b"][0] != positions["c"][0]


def test_index_links_only_the_three_original_lessons() -> None:
    lessons = load_lessons()
    visuals = {lesson.lesson_id: _render_visual(lesson) for lesson in lessons}
    index = _render_index(lessons, visuals)
    links = re.findall(r'href="lessons/([^"]+)\.html"', index)
    assert sorted(links) == sorted(EXPECTED_ANSWER_TEXT)
