"""Upload events and server receipts, without browser seal or provider HTTP."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from test_auto_knowledge_map import ready_document, service_at


@pytest.mark.parametrize("enabled,billable", [(False, True), (True, False), (True, True)])
def test_status_exposes_effective_worker_flags_without_enqueuing(tmp_path, enabled, billable):
    database, service, generator = service_at(tmp_path)
    service.settings = service.settings.model_copy(
        update={
            "auto_knowledge_map_enabled": enabled,
            "auto_knowledge_map_allow_billable": billable,
        }
    )
    status = service.status("private-course", "owner-a")
    assert status["worker_enabled"] is enabled
    assert status["billable_enabled"] is billable
    assert status["worker_running"] is False
    assert generator.calls == 0
    with database.connect() as db:
        assert db.execute("select count(*) from auto_knowledge_jobs").fetchone()[0] == 0


@pytest.mark.parametrize('terminal', ['FAILED', 'UNKNOWN'])
def test_failure_progress_retains_last_observed_outline_milestone(tmp_path, terminal):
    database, service, generator = service_at(tmp_path)
    ready_document(database, document_id='one', chunk_id='one', content='A source topic')
    service.reconcile(force=True)
    with database.connect() as db:
        job_id = db.execute('SELECT id FROM auto_knowledge_jobs').fetchone()[0]
        db.execute('UPDATE auto_knowledge_jobs SET status=?', (terminal,))
        db.execute('UPDATE auto_knowledge_targets SET status=?', (terminal,))
        db.execute(
            "INSERT INTO auto_knowledge_model_attempts "
            "(operation_id,job_id,stage,shard_key,input_hash,status) "
            "VALUES('outline-complete',?,'SECTION_MAP','outline-00-00000',?,'CONTRACT_REJECTED')",
            (job_id, 'a' * 64),
        )
        db.commit()
    result = service.status('private-course', 'owner-a')
    assert result['status'] == terminal
    assert result['progress']['phase'] == terminal
    assert result['progress']['last_observed_phase'] == 'OUTLINE'
    assert result['progress']['completed_stages'] == 2
    assert generator.calls == 0


def open_batch(service, count=3):
    service.begin_upload_batch(
        course_id="private-course",
        source_course_id="private-corpus",
        owner_user_id="owner-a",
        batch_id="three-files",
        expected_items=count,
    )


def record(service, key, status="INDEXED", document_id=None):
    service.record_upload_batch_item(
        batch_id="three-files",
        item_key=key,
        course_id="private-course",
        owner_user_id="owner-a",
        status=status,
        document_id=document_id,
    )


def test_server_terminal_receipts_seal_without_browser_and_build_once(tmp_path: Path):
    database, service, generator = service_at(tmp_path)
    open_batch(service)
    for i in range(3):
        ready_document(
            database, document_id=f"doc-{i}", chunk_id=f"chunk-{i}", content=f"Topic {i}"
        )
        record(service, f"item-{i}", document_id=f"doc-{i}")
    service.reconcile_background()
    with database.connect() as db:
        batch = db.execute("select * from auto_knowledge_upload_batches").fetchone()
        assert batch["status"] == "SEALED"
        assert batch["seal_hash"]
    result = service.run_once("upload-test")
    assert result is not None and result["status"] == "READY"
    service.reconcile_background()
    assert service.run_once("duplicate-test") is None
    assert generator.calls == 1
    with database.connect() as db:
        assert db.execute("select count(*) from auto_knowledge_jobs").fetchone()[0] == 1


def test_progress_reports_observed_file_and_job_milestones_without_dispatch(tmp_path: Path):
    database, service, generator = service_at(tmp_path)
    open_batch(service, count=2)
    ready_document(database, document_id="one", chunk_id="one", content="First topic")
    record(service, "one", document_id="one")
    record(service, "bad", status="FAILED")
    service.reconcile_background()
    progress = service.status("private-course", "owner-a")["progress"]
    assert progress["phase"] == "QUEUED"
    assert progress["files_completed"] == progress["files_total"] == 2
    assert progress["failed_files"] == 1
    assert progress["completed_stages"] < progress["total_stages"]
    assert generator.calls == 0
    service.run_once("progress")
    progress = service.status("private-course", "owner-a")["progress"]
    assert progress["phase"] == "READY_WITH_EXCEPTIONS"
    assert progress["completed_stages"] == progress["total_stages"] == 5
    before = generator.calls
    service.status("private-course", "owner-a")
    assert generator.calls == before


def test_open_batch_does_not_consume_its_only_due_source_event(tmp_path: Path):
    database, service, _ = service_at(tmp_path)
    open_batch(service)
    ready_document(database, document_id="first", chunk_id="first-chunk", content="First topic")
    record(service, "item-0", document_id="first")
    with database.connect() as db:
        db.execute("update auto_knowledge_source_events set not_before='2000-01-01T00:00:00Z'")
    assert service.reconcile_background().get("BATCH_OPEN") == 1
    with database.connect() as db:
        assert (
            db.execute(
                "select count(*) from auto_knowledge_source_events where status='PENDING'"
            ).fetchone()[0]
            > 0
        )
        assert db.execute("select count(*) from auto_knowledge_jobs").fetchone()[0] == 0


def test_server_document_status_recovers_accepted_receipt_and_isolates_bad_file(tmp_path: Path):
    database, service, generator = service_at(tmp_path)
    open_batch(service, count=2)
    ready_document(database, document_id="good", chunk_id="good-chunk", content="Good topic")
    record(service, "good-item", status="ACCEPTED", document_id="good")
    record(service, "bad-item", status="FAILED")
    service.reconcile_background()
    with database.connect() as db:
        assert (
            db.execute("select status from auto_knowledge_upload_batches").fetchone()[0] == "SEALED"
        )
        assert (
            db.execute(
                "select status from auto_knowledge_upload_batch_items where item_key='good-item'"
            ).fetchone()[0]
            == "INDEXED"
        )
    result = service.run_once("partial-upload")
    assert result is not None and result["status"] in {"READY", "READY_WITH_EXCEPTIONS"}
    assert generator.evidence_ids == ["good-chunk"]
    assert service.status("private-course", "owner-a")["upload_coverage"]["failed_items"] == 1


def test_recovered_document_does_not_keep_showing_missing_coverage(tmp_path: Path):
    database, service, generator = service_at(tmp_path)
    open_batch(service, count=1)
    ready_document(database, document_id="recovered", chunk_id="recovered-chunk",
                   content="Recovered topic")
    record(service, "item", status="FAILED", document_id="recovered")
    service.seal_upload_batch(
        course_id="private-course", owner_user_id="owner-a", batch_id="three-files",
        items=[{"item_key": "item", "status": "FAILED", "document_id": "recovered"}],
    )
    service.reconcile(force=True)
    assert service.run_once("recovered") is not None
    before_calls = generator.calls
    assert service.status("private-course", "owner-a")["upload_coverage"]["failed_items"] == 0
    assert generator.calls == before_calls
    with database.connect() as db:
        saved = db.execute("select status from auto_knowledge_upload_batch_items").fetchone()
        assert saved[0] == "FAILED"


def test_paused_backfill_never_claims_already_queued_official_jobs(tmp_path: Path):
    database, service, generator = service_at(tmp_path)
    with database.connect() as db:
        db.execute(
            "insert into courses(id,name,course_type,visibility,publication_status) "
            "values('old','Old','official','private','private')"
        )
    ready_document(
        database, document_id="old-doc", chunk_id="old-chunk", content="Old topic", course_id="old"
    )
    service.reconcile(force=True)
    service.settings = service.settings.model_copy(
        update={"auto_knowledge_map_legacy_backfill_enabled": False}
    )
    assert service.claim("fresh-only") is None
    assert generator.calls == 0
    with database.connect() as db:
        assert (
            db.execute(
                "select status from auto_knowledge_jobs where target_kind='AUTO_COURSE'"
            ).fetchone()[0]
            == "QUEUED"
        )


def test_shared_backfill_claim_does_not_bill_unpublished_official_courses(tmp_path: Path):
    database, service, _ = service_at(tmp_path)
    service.settings = service.settings.model_copy(
        update={"auto_knowledge_map_legacy_backfill_enabled": True}
    )
    with database.connect() as db:
        for cid in ("a-unpublished", "z-shared"):
            db.execute(
                "insert into courses(id,name,course_type,visibility,publication_status) "
                "values(?,?,'official','private','private')", (cid, cid),
            )
    for cid in ("a-unpublished", "z-shared"):
        ready_document(database, document_id=cid, chunk_id=cid, content="A teaching topic",
                       course_id=cid)
    with database.connect() as db:
        db.execute("update courses set visibility='public',publication_status='published' "
                   "where id='z-shared'")
    service.reconcile(force=True)
    job = service.claim("shared-only")
    assert job is not None and job["course_id"] == "z-shared"
    with database.connect() as db:
        assert db.execute(
            "select status from auto_knowledge_jobs where course_id='a-unpublished'"
        ).fetchone()[0] == "QUEUED"


def test_browser_seal_after_server_seal_preserves_host_failure_receipt(tmp_path: Path):
    database, service, _ = service_at(tmp_path)
    open_batch(service, count=2)
    ready_document(database, document_id="good", chunk_id="chunk", content="Good topic")
    record(service, "good", document_id="good")
    service.record_upload_batch_item(
        batch_id="three-files", item_key="bad", course_id="private-course",
        owner_user_id="owner-a", status="FAILED", error_code="UNSUPPORTED_FILE",
    )
    service.reconcile_background()
    result = service.seal_upload_batch(
        course_id="private-course", owner_user_id="owner-a", batch_id="three-files",
        items=[
            {"item_key": "good", "status": "INDEXED", "document_id": "good"},
            {"item_key": "bad", "status": "FAILED", "document_id": None,
             "error_code": "INGESTION_FAILED"},
        ],
    )
    assert result["status"] == "SEALED"
    with database.connect() as db:
        assert db.execute(
            "select error_code from auto_knowledge_upload_batch_items where item_key='bad'"
        ).fetchone()[0] == "UNSUPPORTED_FILE"


@pytest.mark.parametrize("changed", ["status", "document_id", "item_key"])
def test_browser_cannot_change_server_sealed_item_identity(tmp_path: Path, changed):
    from app.errors import ApiError

    database, service, _ = service_at(tmp_path)
    open_batch(service, count=1)
    ready_document(database, document_id="good", chunk_id="chunk", content="Good topic")
    record(service, "good", document_id="good")
    service.reconcile_background()
    item = {"item_key": "good", "status": "INDEXED", "document_id": "good"}
    item[changed] = "FAILED" if changed == "status" else "other"
    with pytest.raises(ApiError) as error:
        service.seal_upload_batch(
            course_id="private-course", owner_user_id="owner-a",
            batch_id="three-files", items=[item],
        )
    assert error.value.code == "AUTO_BATCH_CONFLICT"


def test_partial_upload_wait_has_short_configured_bound(tmp_path: Path):
    _, service, _ = service_at(tmp_path)
    batch = service.begin_upload_batch(
        course_id="private-course", source_course_id="private-corpus",
        owner_user_id="owner-a", batch_id="partial", expected_items=3,
    )
    expires = datetime.fromisoformat(batch["expires_at"].replace("Z", "+00:00"))
    remaining = expires - datetime.now(UTC)
    assert 0 < remaining.total_seconds() <= 95


def test_late_file_after_partial_snapshot_creates_new_tree_not_rewrite(tmp_path: Path):
    database, service, generator = service_at(tmp_path)
    open_batch(service, count=2)
    ready_document(database, document_id="first", chunk_id="first", content="First topic")
    record(service, "first", document_id="first")
    with database.connect() as db:
        db.execute("update auto_knowledge_upload_batches set expires_at='2000-01-01T00:00:00Z'")
    service.reconcile(force=True)
    first = service.run_once("partial")
    assert first["status"] in {"READY", "READY_WITH_EXCEPTIONS"}
    old_tree = service.status("private-course", "owner-a")["tree_version_id"]
    assert service.status("private-course", "owner-a")["upload_coverage"]["missing_items"] == 1
    ready_document(database, document_id="late", chunk_id="late", content="Late topic")
    record(service, "late", document_id="late")
    service.reconcile(force=True)
    second = service.run_once("late")
    assert second["status"] in {"READY", "READY_WITH_EXCEPTIONS"}
    assert service.status("private-course", "owner-a")["tree_version_id"] != old_tree
    assert set(generator.evidence_ids) == {"late"}
