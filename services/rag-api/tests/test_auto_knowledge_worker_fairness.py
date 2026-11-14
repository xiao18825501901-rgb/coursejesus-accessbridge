import asyncio
from types import SimpleNamespace

import pytest
from test_auto_knowledge_map import ready_document, service_at, settings_at

from app.errors import ApiError


def test_worker_reconciles_new_uploads_between_backlog_jobs(tmp_path, monkeypatch):
    from app.main import create_app

    settings = settings_at(tmp_path).model_copy(
        update={
            "auto_knowledge_map_enabled": True,
            "auto_knowledge_map_allow_billable": True,
            "auto_knowledge_map_poll_seconds": 1.0,
        }
    )
    application = create_app(settings=settings)
    events = []

    def reconcile_background():
        events.append("reconcile")

    def reconcile(**kwargs):
        events.append("reconcile")

    def run_once(worker_id):
        events.append("job")
        return {"status": "READY"}  # A nonempty historical queue.

    application.state.auto_knowledge_map = SimpleNamespace(
        reconcile_background=reconcile_background, reconcile=reconcile, run_once=run_once
    )
    monkeypatch.setattr(
        application.state.learning, "run_configured_preparation_once", lambda worker_id: None
    )

    async def exercise():
        async with application.router.lifespan_context(application):

            async def observe():
                while events.count("reconcile") < 2:
                    await asyncio.sleep(0.01)

            await asyncio.wait_for(observe(), timeout=3)
            assert application.state.auto_knowledge_map.worker_running is True

    asyncio.run(exercise())
    assert application.state.auto_knowledge_map.worker_running is False
    assert events[:3] == ["reconcile", "job", "reconcile"]


def test_private_upload_claim_precedes_official_backfill_and_keeps_single_worker(tmp_path):
    database, service, _ = service_at(tmp_path)
    with database.connect() as connection:
        connection.execute(
            "INSERT INTO courses(id,name,course_type,visibility,publication_status) "
            "VALUES('official-old','Old official course','official','private','private')"
        )
    ready_document(database, document_id="private-doc", chunk_id="private-chunk", content="Private")
    ready_document(
        database,
        document_id="official-doc",
        chunk_id="official-chunk",
        content="Official",
        course_id="official-old",
    )
    with database.connect() as connection:
        connection.execute(
            "UPDATE courses SET visibility='public',publication_status='published' "
            "WHERE id='official-old'"
        )
    service.reconcile(force=True)
    with database.connect() as connection:
        connection.execute(
            "UPDATE auto_knowledge_jobs SET created_at='2000-01-01T00:00:00Z' "
            "WHERE target_kind='AUTO_COURSE'"
        )
    claimed = service.claim("student-upload")
    assert claimed["target_kind"] == "PRIVATE"
    assert service.claim("second-worker") is None


@pytest.mark.parametrize('open_batch', [False, True])
def test_shared_shard_heartbeat_yields_only_to_due_sealed_private_upload(tmp_path, open_batch):
    database, service, generator = service_at(tmp_path)
    with database.connect() as db:
        db.execute(
            "INSERT INTO courses(id,name,course_type,visibility,publication_status) "
            "VALUES('official-old','Old official','official','private','private')"
        )
    ready_document(database, document_id='old', chunk_id='old', content='Old source',
                   course_id='official-old')
    with database.connect() as db:
        db.execute("UPDATE courses SET visibility='public',publication_status='published' "
                   "WHERE id='official-old'")
    service.reconcile(force=True)
    job = service.claim('shared-worker', target_key='AUTO_COURSE:official-old')
    assert job is not None
    ready_document(database, document_id='new', chunk_id='new', content='Private upload')
    with database.connect() as db:
        db.execute("UPDATE auto_knowledge_source_events SET not_before='2000-01-01T00:00:00Z' "
                   "WHERE source_course_id='private-corpus'")
    if open_batch:
        service.begin_upload_batch(course_id='private-course', source_course_id='private-corpus',
                                   owner_user_id='owner-a', batch_id='still-open', expected_items=2)
        service._renew(job['id'], 'shared-worker')
        assert service.claim('second-worker') is None
    else:
        with pytest.raises(ApiError) as caught:
            service._renew(job['id'], 'shared-worker')
        assert caught.value.code == 'AUTO_LEASE_LOST'
        with database.connect() as db:
            assert db.execute('SELECT status FROM auto_knowledge_jobs WHERE id=?',
                              (job['id'],)).fetchone()[0] == 'QUEUED'
        service.reconcile(force=False, recover_safe_failures=False)
        assert service.claim('student-worker')['target_kind'] == 'PRIVATE'
    assert generator.calls == 0
