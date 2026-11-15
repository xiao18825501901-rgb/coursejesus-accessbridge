"""Public visitor isolation for the integrated CourseJesus UI.

The guest session is deliberately narrower than ordinary authentication. It can
read public course material and write only to its own UI-extension namespace;
the host product APIs continue to accept Clerk/test identities only.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.ui_extension.guest import prune_expired_guest_data

UI = "/ui-extension/api/ui/v1"
SUBJECTS = {
    "Bearer token-a": "user-a",
    "Bearer admin-token": "user-admin",
}


class FakeAuthVerifier:
    def authenticate(self, request: Request) -> str | None:
        return SUBJECTS.get(request.headers.get("authorization", ""))


class FakeEmbeddingProvider:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0] for _ in texts]


def _authorization(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _seed_courses(client: TestClient) -> None:
    with client.app.state.database.connect() as connection:
        connection.execute(
            "INSERT INTO courses("
            "id,name,description,owner_user_id,course_type,visibility"
            ") VALUES(?,?,?,?,?,?)",
            (
                "public-guest-course",
                "Public guest course",
                "Synthetic public material",
                "user-a",
                "user",
                "public",
            ),
        )
        connection.execute(
            "INSERT INTO courses("
            "id,name,description,owner_user_id,course_type,visibility"
            ") VALUES(?,?,?,?,?,?)",
            (
                "private-owner-course",
                "Private owner course",
                "Synthetic private material",
                "user-a",
                "user",
                "private",
            ),
        )


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("CMUI_ALLOWED_ORIGINS", "https://coursejesus.com")
    settings = Settings(
        database_path=tmp_path / "rag.sqlite3",
        upload_dir=tmp_path / "uploads",
        admin_user_ids="user-admin",
        app_env="test",
        v3_enabled=True,
        ui_extension_enabled=True,
        rag_provider_mode="deterministic",
        ui_web_dir=tmp_path / "no-web-build",
        verification_secret="guest-contract-test-secret",
        guest_session_ttl_seconds=900,
    )
    application = create_app(
        settings=settings,
        embedding_provider=FakeEmbeddingProvider(),
        auth_verifier=FakeAuthVerifier(),
    )
    with TestClient(application) as test_client:
        _seed_courses(test_client)
        yield test_client


def _guest_token(client: TestClient) -> str:
    response = client.post(f"{UI}/guest-session")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["session_kind"] == "guest"
    assert body["expires_in_seconds"] == 900
    assert isinstance(body["expires_at"], int)
    assert isinstance(body["token"], str) and len(body["token"]) > 80
    return body["token"]


def test_guest_can_browse_only_public_courses_and_owner_ids_are_hidden(
    client: TestClient,
) -> None:
    token = _guest_token(client)

    listing = client.get(f"{UI}/courses", headers=_authorization(token))

    assert listing.status_code == 200, listing.text
    courses = listing.json()
    assert [course["id"] for course in courses] == ["public-guest-course"]
    assert "owner" not in courses[0]
    assert client.get(
        f"{UI}/courses/public-guest-course", headers=_authorization(token)
    ).status_code == 200
    private = client.get(
        f"{UI}/courses/private-owner-course", headers=_authorization(token)
    )
    assert private.status_code == 404
    verification = client.get(
        f"{UI}/me/verification", headers=_authorization(token)
    )
    assert verification.status_code == 200


def test_guest_sessions_are_isolated_from_each_other(client: TestClient) -> None:
    guest_a = _authorization(_guest_token(client))
    guest_b = _authorization(_guest_token(client))

    created = client.post(
        f"{UI}/pairs",
        headers=guest_a,
        json={"course": "public-guest-course"},
    )
    assert created.status_code == 201, created.text
    pair_id = created.json()["id"]

    own_pairs = client.get(
        f"{UI}/pairs?course_id=public-guest-course", headers=guest_a
    )
    other_pairs = client.get(
        f"{UI}/pairs?course_id=public-guest-course", headers=guest_b
    )
    assert [row["id"] for row in own_pairs.json()] == [pair_id]
    assert other_pairs.json() == []
    assert client.get(f"{UI}/pairs/{pair_id}", headers=guest_b).status_code == 404


def test_guest_cannot_use_management_or_ordinary_product_apis(
    client: TestClient,
) -> None:
    guest = _authorization(_guest_token(client))

    create_course = client.post(
        f"{UI}/courses",
        headers=guest,
        json={"name": "Guest must not create this"},
    )
    assert create_course.status_code == 403
    assert create_course.json()["detail"]["code"] == "GUEST_OPERATION_FORBIDDEN"

    admin = client.get(f"{UI}/admin/verification-codes", headers=guest)
    assert admin.status_code == 403
    assert admin.json()["detail"]["code"] == "GUEST_OPERATION_FORBIDDEN"

    host_api = client.get("/api/courses", headers=guest)
    assert host_api.status_code == 401


def test_tampered_or_ordinary_credentials_are_rejected(client: TestClient) -> None:
    token = _guest_token(client)
    replacement = "A" if token[-1] != "A" else "B"

    tampered = client.get(f"{UI}/me", headers=_authorization(token[:-1] + replacement))
    unauthenticated = client.get(f"{UI}/me")

    assert tampered.status_code == 401
    assert unauthenticated.status_code == 401


def test_expired_guest_workspaces_are_pruned(client: TestClient) -> None:
    token = _guest_token(client)
    authorization = _authorization(token)
    created = client.post(
        f"{UI}/pairs",
        headers=authorization,
        json={"course": "public-guest-course"},
    )
    assert created.status_code == 201, created.text
    pair_id = created.json()["id"]

    ui_database = client.app.state.ui_extension_app.state.db
    with ui_database.connect(write=True) as connection:
        connection.execute(
            "UPDATE cmui_users SET created_at='2000-01-01T00:00:00.000+00:00' "
            "WHERE id LIKE 'guest_%'"
        )
    deleted = prune_expired_guest_data(ui_database, 900)

    assert deleted == 1
    with ui_database.connect() as connection:
        assert connection.execute(
            "SELECT 1 FROM cmui_pairs WHERE id=?", (pair_id,)
        ).fetchone() is None
        assert connection.execute(
            "SELECT 1 FROM cmui_users WHERE id LIKE 'guest_%'"
        ).fetchone() is None
