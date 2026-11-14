"""An unsent busy workspace must not monopolize the single map worker."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from test_auto_knowledge_map import ready_document, service_at

from app.services.auto_knowledge_map import stamp


@pytest.mark.parametrize(
    "other_course,age_seconds,targeted,expected_workspace",
    [
        (True, 0, False, "other-workspace"),
        (False, 0, False, None),
        (False, 45, False, "workspace-a"),
        (False, 0, True, "workspace-a"),
    ],
)
def test_busy_map_claim_yields_without_clearing_workspace_state(
    tmp_path: Path,
    other_course: bool,
    age_seconds: int,
    targeted: bool,
    expected_workspace: str | None,
) -> None:
    database, service, generator = service_at(tmp_path)
    ready_document(
        database, document_id="busy-doc", chunk_id="busy-chunk", content="Grounded source."
    )
    if other_course:
        with database.connect() as connection:
            for course_id in ["other-course", "other-corpus"]:
                connection.execute(
                    "INSERT INTO courses(id,name,owner_user_id,course_type,"
                    "visibility,publication_status) "
                    "VALUES(?,?,'owner-a','user','private','private')",
                    (course_id, course_id),
                )
            connection.execute(
                "INSERT INTO learning_workspaces(id,owner_user_id,course_id,private_course_id) "
                "VALUES('other-workspace','owner-a','other-course','other-corpus')"
            )
        ready_document(
            database,
            document_id="free-doc",
            chunk_id="free-chunk",
            content="Another independently available source.",
            course_id="other-corpus",
        )
    assert service.reconcile(force=True)["QUEUED"] == (2 if other_course else 1)
    with database.connect() as connection:
        busy = connection.execute(
            "SELECT * FROM auto_knowledge_jobs WHERE workspace_id='workspace-a'"
        ).fetchone()
        connection.execute(
            "UPDATE auto_knowledge_jobs SET error_code='WORKSPACE_BUSY',"
            "created_at='2000-01-01T00:00:00.000Z',updated_at=? WHERE id=?",
            (stamp(datetime.now(UTC) - timedelta(seconds=age_seconds)), busy["id"]),
        )
    result = service.claim("fairness-worker", busy["target_key"] if targeted else None)
    assert (None if result is None else result["workspace_id"]) == expected_workspace
    assert generator.calls == 0
    if expected_workspace != "workspace-a":
        with database.connect() as connection:
            preserved = connection.execute(
                "SELECT status,error_code,attempt_count,model_calls_made FROM auto_knowledge_jobs "
                "WHERE id=?",
                (busy["id"],),
            ).fetchone()
        assert tuple(preserved) == ("QUEUED", "WORKSPACE_BUSY", 0, 0)
