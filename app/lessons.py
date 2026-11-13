from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.visual.spec import VisualSpec


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LocalizedText(StrictModel):
    en: str = Field(min_length=1)
    zh: str = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def require_both_locales(cls, data: object) -> object:
        if isinstance(data, dict):
            if not data.get("en") or not data.get("zh"):
                raise ValueError("both en and zh are required")
        return data


class SourceText(StrictModel):
    id: str = Field(min_length=1, max_length=80)
    title: LocalizedText
    rights: str = Field(min_length=1, max_length=500)
    text: LocalizedText


class LessonStep(StrictModel):
    id: str = Field(min_length=1, max_length=80)
    title: LocalizedText
    body: LocalizedText
    source_id: str = Field(min_length=1, max_length=80)


class QuizOption(StrictModel):
    en: str = Field(min_length=1, max_length=200)
    zh: str = Field(min_length=1, max_length=200)


class QuizQuestion(StrictModel):
    id: str = Field(min_length=1, max_length=80)
    prompt: LocalizedText
    options: list[QuizOption] = Field(min_length=2, max_length=6)
    answer: int = Field(ge=0)
    rationale: LocalizedText
    source_id: str = Field(min_length=1, max_length=80)

    @model_validator(mode="after")
    def validate_answer(self) -> "QuizQuestion":
        if self.answer >= len(self.options):
            raise ValueError("answer index is outside the option list")
        return self


class GlossaryEntry(StrictModel):
    term: LocalizedText
    definition: LocalizedText


class AccessLesson(StrictModel):
    lesson_id: Literal["stack-queue", "bfs-dfs", "matrix-transform"]
    title: LocalizedText
    concept: LocalizedText
    original_source_excerpt: LocalizedText
    sources: list[SourceText] = Field(min_length=1)
    steps: list[LessonStep] = Field(min_length=3, max_length=12)
    visual_spec: VisualSpec
    alt_text: LocalizedText
    long_description: LocalizedText
    glossary: list[GlossaryEntry] = Field(min_length=1)
    quiz: list[QuizQuestion] = Field(min_length=3, max_length=3)
    source_reference: str = Field(min_length=1, max_length=300)

    @model_validator(mode="after")
    def validate_references(self) -> "AccessLesson":
        source_ids = {source.id for source in self.sources}
        if not len(source_ids) == len(self.sources):
            raise ValueError("source ids must be unique")
        if any(step.source_id not in source_ids for step in self.steps):
            raise ValueError("step source_id must reference a lesson source")
        if any(question.source_id not in source_ids for question in self.quiz):
            raise ValueError("quiz source_id must reference a lesson source")
        return self


def load_lessons() -> list[AccessLesson]:
    root = Path(__file__).resolve().parents[1]
    fixtures = sorted(
        (root / "fixtures" / "lessons").glob("*.json"),
        key=lambda path: {"stack-queue": 0, "bfs-dfs": 1, "matrix-transform": 2}[path.stem],
    )
    if [path.stem for path in fixtures] != ["stack-queue", "bfs-dfs", "matrix-transform"]:
        raise ValueError("expected exactly the three original competition lessons")
    lessons = []
    for path in fixtures:
        data = json.loads(path.read_text(encoding="utf-8"))
        lessons.append(AccessLesson.model_validate(data))
    return lessons
