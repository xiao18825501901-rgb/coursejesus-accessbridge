import json

import pytest
from test_auto_knowledge_map import _install_over_limit_private_tree, ready_document, service_at

from app.services.auto_knowledge_map import digest


def cancelled_scope_job(tmp_path, *, status="SUPERSEDED", sent=False):
    database, service, generator = service_at(tmp_path)
    service.settings.auto_knowledge_map_enabled = True
    service.settings.auto_knowledge_map_allow_billable = True
    ready_document(database, document_id="scope-doc", chunk_id="scope-chunk", content="Grounded")
    _install_over_limit_private_tree(database, tree_id="scope-legacy", evidence_id="scope-chunk")
    service.reconcile(force=True)
    with database.connect() as c:
        job = c.execute("SELECT * FROM auto_knowledge_jobs").fetchone()
        c.execute(
            "UPDATE auto_knowledge_jobs SET status=?,error_code='UNRELATED_EVENT_SCOPE_REPAIR' "
            "WHERE id=?",
            (status, job["id"]),
        )
        c.execute(
            "INSERT INTO auto_knowledge_job_receipts(job_id,target_key,corpus_fingerprint,"
            "status,source_snapshot_hash,model_calls_made,detail_json) VALUES(?,?,?,?,?,0,'{}')",
            (
                job["id"],
                job["target_key"],
                job["corpus_fingerprint"],
                status,
                digest(json.loads(job["source_snapshot_json"])),
            ),
        )
        if sent:
            c.execute(
                "INSERT INTO auto_knowledge_model_attempts(operation_id,job_id,stage,shard_key,"
                "input_hash,status) VALUES(?,?,'SECTION_MAP','map-00000',?,'SEND_INTENT')",
                (f"akm-{digest(job['id'])[:16]}-m-00000", job["id"], "a" * 64),
            )
    return database, service, generator, job


def test_authorized_full_sweep_creates_one_unsent_scope_successor(tmp_path):
    database, service, generator, original = cancelled_scope_job(tmp_path)
    service.reconcile(force=True, full=True)
    with database.connect() as c:
        target = c.execute("SELECT * FROM auto_knowledge_targets").fetchone()
        successor = c.execute(
            "SELECT * FROM auto_knowledge_jobs WHERE id=?", (target["active_job_id"],)
        ).fetchone()
        assert successor["id"] != original["id"]
        assert successor["status"] == "QUEUED"
        snapshot = json.loads(successor["source_snapshot_json"])
        assert snapshot["superseded_scope_job_id"] == original["id"]
        assert (
            c.execute(
                "SELECT status FROM auto_knowledge_jobs WHERE id=?", (original["id"],)
            ).fetchone()[0]
            == "SUPERSEDED"
        )
        assert (
            c.execute(
                "SELECT status FROM auto_knowledge_job_receipts WHERE job_id=?", (original["id"],)
            ).fetchone()[0]
            == "SUPERSEDED"
        )
        assert (
            c.execute(
                "SELECT status FROM knowledge_tree_versions WHERE id='scope-legacy'"
            ).fetchone()[0]
            == "ACTIVE"
        )
    service.reconcile(force=True, full=True)
    with database.connect() as c:
        assert (
            c.execute("SELECT active_job_id FROM auto_knowledge_targets").fetchone()[0]
            == successor["id"]
        )
        assert c.execute("SELECT COUNT(*) FROM auto_knowledge_jobs").fetchone()[0] == 2
        assert c.execute("SELECT COUNT(*) FROM auto_knowledge_model_attempts").fetchone()[0] == 0
    assert generator.calls == 0


@pytest.mark.parametrize("status,sent", [("SUPERSEDED", True), ("UNKNOWN", False)])
def test_scope_successor_refuses_sent_or_unknown_original(tmp_path, status, sent):
    database, service, _, original = cancelled_scope_job(tmp_path, status=status, sent=sent)
    service.reconcile(force=True, full=True)
    with database.connect() as c:
        assert c.execute("SELECT COUNT(*) FROM auto_knowledge_jobs").fetchone()[0] == 1
        target = c.execute("SELECT status FROM auto_knowledge_targets").fetchone()[0]
        assert target == ("UNKNOWN" if status == "UNKNOWN" else "BLOCKED")
        assert (
            c.execute(
                "SELECT status FROM auto_knowledge_jobs WHERE id=?", (original["id"],)
            ).fetchone()[0]
            == status
        )


def test_event_only_reconciliation_does_not_resume_cancelled_scope(tmp_path):
    database, service, _, _ = cancelled_scope_job(tmp_path)
    with database.connect() as c:
        c.execute(
            "UPDATE auto_knowledge_source_events SET status='PENDING',"
            "not_before='2000-01-01T00:00:00Z'"
        )
    service.reconcile(force=False, full=False)
    with database.connect() as c:
        assert c.execute("SELECT COUNT(*) FROM auto_knowledge_jobs").fetchone()[0] == 1
        assert c.execute("SELECT status FROM auto_knowledge_targets").fetchone()[0] == "BLOCKED"


@pytest.mark.parametrize("status", ["FAILED", "READY_WITH_EXCEPTIONS"])
def test_compaction_does_not_report_completed_or_failed_job_as_queued(tmp_path, status):
    database, service, _, original = cancelled_scope_job(tmp_path, status=status)
    service.reconcile(force=True, full=True)
    with database.connect() as c:
        assert c.execute("SELECT COUNT(*) FROM auto_knowledge_jobs").fetchone()[0] == 1
        assert c.execute("SELECT status FROM auto_knowledge_targets").fetchone()[0] == (
            "FAILED" if status == "FAILED" else "BLOCKED"
        )
        assert (
            c.execute(
                "SELECT status FROM auto_knowledge_jobs WHERE id=?", (original["id"],)
            ).fetchone()[0]
            == status
        )
