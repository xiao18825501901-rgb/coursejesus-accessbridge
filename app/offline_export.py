from __future__ import annotations

from app.lessons import AccessLesson
from app.visual.compiler import CompiledVisual


def build_learning_pack(lesson: AccessLesson, visual: CompiledVisual) -> dict:
    """Map one reviewed AccessBridge lesson into the validated LearningPack schema."""

    return {
        "schema": 1,
        "packageId": f"cjab-{lesson.lesson_id}-v1",
        "sourceRevision": f"accessbridge-lessons-v1:{lesson.lesson_id}",
        "title": lesson.title.model_dump(),
        "access": "synthetic",
        "sources": [
            {
                "id": source.id,
                "title": source.title.model_dump(),
                "rights": source.rights,
                "text": source.text.model_dump(),
            }
            for source in lesson.sources
        ],
        "sections": [
            {
                "heading": step.title.model_dump(),
                "body": step.body.model_dump(),
                "sourceIds": [step.source_id],
            }
            for step in lesson.steps
        ],
        "visual": {
            "alt": lesson.alt_text.model_dump(),
            "longDescription": lesson.long_description.model_dump(),
            "svg": visual.svg,
        },
        "questions": [
            {
                "id": question.id,
                "prompt": question.prompt.model_dump(),
                "options": [option.model_dump() for option in question.options],
                "answer": question.answer,
                "explanation": question.rationale.model_dump(),
                "sourceIds": [question.source_id],
            }
            for question in lesson.quiz
        ],
    }
