"""Owned private courses must stay deletable, and never half-deleted.

Two opposite risks are checked here. Entering a course's learning or files view
creates the caller's `learning_workspaces` row (and its private corpus course) by
design, and the existing V3 ingestion service refuses to delete a course while that
workspace exists. So the mounted shell must surface the refusal as an actionable
conflict and change nothing - not half-delete the course, the workspace or the
uploaded files.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

UI = "/ui-extension/api/ui/v1"
SUBJECTS = {
    "Bearer token-a": "user-a",
    "Bearer token-b": "user-b",
    "Bearer admin-token": "user-admin",
}


class FakeAuthVerifier:
    def authenticate(self, request: Request) -> str | None:
        return SUBJECTS.get(request.headers.get("authorization", ""))


class FakeEmbeddingProvider:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0] for _ in texts]


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(
        database_path=tmp_path / "rag.sqlite3",
        upload_dir=tmp_path / "uploads",
        admin_user_ids="user-admin",
        app_env="test",
        v3_enabled=True,
        ui_extension_enabled=True,
        rag_provider_mode="deterministic",
        ui_web_dir=tmp_path / "no-web-build",
    )
    application = create_app(
        settings=settings,
        embedding_provider=FakeEmbeddingProvider(),
        auth_verifier=FakeAuthVerifier(),
    )
    with TestClient(application) as test_client:
        yield test_client


def auth(token: str) -> dict[str, str]:
    return {"Authorization": token}


def create_private_course(client: TestClient, name: str = "My Stats Reading") -> dict:
    response = client.post(
        f"{UI}/courses", headers=auth("Bearer token-a"), json={"name": name, "code": "MINE"}
    )
    assert response.status_code == 201, response.text
    return response.json()


def delete(client: TestClient, course_id: str, confirm: str) -> object:
    return client.delete(
        f"{UI}/courses/{course_id}", headers=auth("Bearer token-a"), params={"confirm": confirm}
    )


def test_an_empty_course_with_its_new_owner_workspace_is_deleted(client: TestClient) -> None:
    course = create_private_course(client)
    response = delete(client, course["id"], course["name"])
    assert response.status_code == 200, response.text
    assert response.json()["deleted"] is True
    assert client.get(f"{UI}/courses/{course['id']}", headers=auth("Bearer token-a")).status_code == 404


def test_a_wrong_confirmation_name_is_rejected(client: TestClient) -> None:
    course = create_private_course(client)
    response = delete(client, course["id"], "not the name")
    assert response.status_code == 422
    # The course is untouched.
    assert client.get(f"{UI}/courses/{course['id']}", headers=auth("Bearer token-a")).status_code == 200


def test_creation_commits_owner_workspace_before_any_upload(client: TestClient) -> None:
    course = create_private_course(client)
    with client.app.state.database.connect() as db:
        row = db.execute(
            "select w.owner_user_id,c.owner_user_id as corpus_owner,c.visibility "
            "from learning_workspaces w join courses c on c.id=w.private_course_id "
            "where w.course_id=?", (course["id"],),
        ).fetchone()
    assert row is not None
    assert row["owner_user_id"] == row["corpus_owner"] == "user-a"
    assert row["visibility"] == "private"


def test_empty_course_with_map_audit_record_is_not_deleted(client: TestClient) -> None:
    course = create_private_course(client)
    with client.app.state.database.connect() as db:
        workspace = db.execute("select id from learning_workspaces where course_id=?",
                               (course["id"],)).fetchone()[0]
        db.execute(
            "insert into auto_knowledge_targets(target_key,course_id,workspace_id,"
            "owner_user_id,target_kind,status) values(?,?,?,'user-a','PRIVATE','WAITING_SOURCE')",
            (f"PRIVATE:{workspace}", course["id"], workspace),
        )
    assert delete(client, course["id"], course["name"]).status_code == 409
    with client.app.state.database.connect() as db:
        assert db.execute("select 1 from auto_knowledge_targets where workspace_id=?",
                          (workspace,)).fetchone() is not None


def test_enrollment_cap_does_not_block_owned_course_creation_and_upload(client: TestClient) -> None:
    from app.learning.workspaces import join_course

    database = client.app.state.database
    limit = client.app.state.settings.user_course_max_courses
    with database.connect() as db:
        for i in range(limit):
            db.execute(
                "insert into courses(id,name,owner_user_id,course_type,visibility,"
                "display_type,requires_student_verification,publication_status) "
                "values(?,?,NULL,'official','public','shared',0,'published')",
                (f"joined-{i}", f"Joined {i}"),
            )
    for i in range(limit):
        # These are ordinary workspaces, not private courses counted by the
        # separate course-creation quota.
        join_course(database, f"joined-{i}", "user-a", limit)
    response = client.post(f"{UI}/courses", headers=auth("Bearer token-a"),
                           json={"name": "My new course at enrollment cap"})
    assert response.status_code == 201, response.text
    course_id = response.json()["id"]
    opened = client.post(f"{UI}/courses/{course_id}/file-batches",
                         headers=auth("Bearer token-a"),
                         json={"batch_id": "owned-at-cap", "expected_items": 1})
    assert opened.status_code == 201, opened.text
    uploaded = client.post(f"{UI}/courses/{course_id}/files",
                           headers=auth("Bearer token-a"),
                           data={"batch_id": "owned-at-cap", "batch_item_id": "one"},
                           files={"file": (
                               "notes.md", b"# Sets\n\nA set contains distinct elements.",
                               "text/markdown")})
    assert uploaded.status_code == 201, uploaded.text
    assert client.get(f"{UI}/courses/{course_id}/files",
                      headers=auth("Bearer token-b")).status_code == 404
    assert client.app.state.auto_knowledge_map.reconcile(force=True)["QUEUED"] == 1
    with database.connect() as db:
        assert db.execute("select count(*) from learning_workspaces where course_id=?",
                          (course_id,)).fetchone()[0] == 1


def test_private_course_creation_and_upload_work_beyond_ten_courses(client: TestClient) -> None:
    limit = client.app.state.settings.user_course_max_courses
    with client.app.state.database.connect() as db:
        for i in range(limit + 1):
            db.execute(
                "insert into courses(id,name,owner_user_id,course_type,visibility) "
                "values(?,?,'user-a','user','private')", (f"owned-{i}", f"Owned {i}"),
            )
    response = client.post(f"{UI}/courses", headers=auth("Bearer token-a"),
                           json={"name": "Twelfth private course"})
    assert response.status_code == 201, response.text
    uploaded = client.post(
        f"{UI}/courses/{response.json()['id']}/files", headers=auth("Bearer token-a"),
        files={"file": ("sets.md", b"# Sets\n\nSets contain distinct objects.", "text/markdown")},
    )
    assert uploaded.status_code == 201, uploaded.text


def test_a_course_with_a_learning_workspace_reports_a_conflict(client: TestClient) -> None:
    """A course with uploaded material must not be half-deleted."""

    course = create_private_course(client)
    uploaded = client.post(
        f"{UI}/courses/{course['id']}/files", headers=auth("Bearer token-a"),
        files={"file": (
            "notes.md", b"# Sets\n\nA set is a collection of distinct objects.", "text/markdown"
        )},
    )
    assert uploaded.status_code == 201, uploaded.text
    with client.app.state.database.connect() as connection:
        workspace = connection.execute(
            "SELECT id, private_course_id FROM learning_workspaces WHERE course_id=? AND owner_user_id=?",
            (course["id"], "user-a"),
        ).fetchone()
    assert workspace is not None, "the adapter should have created a workspace for the caller"

    response = delete(client, course["id"], course["name"])
    assert response.status_code == 409, response.text
    detail = response.json()["detail"]
    assert "workspace" in str(detail).lower() or "归档" in str(detail)
    # Nothing was removed, and the private corpus is intact.
    assert client.get(f"{UI}/courses/{course['id']}", headers=auth("Bearer token-a")).status_code == 200
    with client.app.state.database.connect() as connection:
        still_there = connection.execute(
            "SELECT 1 FROM courses WHERE id=?", (workspace["private_course_id"],)
        ).fetchone()
    assert still_there is not None
