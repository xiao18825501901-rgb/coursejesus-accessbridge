import hashlib
import json
from types import SimpleNamespace

import pytest
from test_auto_knowledge_map import ready_document, service_at


def test_all_normalizable_split_specs_reuse_saved_response_without_http(tmp_path):
    database, service, _ = service_at(tmp_path)
    ready_document(
        database,
        document_id="normalize-doc",
        chunk_id="normalize-chunk",
        content="Grounded concept.",
    )
    service.reconcile(force=True)
    job = service.claim("normalize-test")
    raw = json.dumps(
        {
            "specs": [
                {
                    "node_key": "concept",
                    "change_reason": "Source-bound",
                    "items": [
                        {
                            "item_id": "explain",
                            "requirement": "REQUIRED",
                            "objective": "Explain the concept",
                            "acceptance": "Explain accurately",
                            "evidence_ids": ["allowed", "foreign"],
                        }
                    ],
                }
            ]
        }
    )
    output_hash = hashlib.sha256(raw.encode()).hexdigest()
    with database.connect() as connection:
        connection.execute(
            "INSERT INTO auto_knowledge_model_attempts("
            "operation_id,job_id,stage,shard_key,input_hash,"
            "status,output_text,output_hash,rejection_code) "
            "VALUES(?,?,'TEACHING_SPEC','spec-00000',?,"
            "'BUSINESS_REJECTED',?,?,'AUTO_EVIDENCE_INVALID')",
            ("normalize-base-r2", job["id"], "a" * 64, raw, output_hash),
        )
    from app.services.auto_knowledge_map import OrchestratorDraftGenerator

    generator = OrchestratorDraftGenerator(database, None)
    result, calls = generator._recover_split_spec_batch(
        job_id=job["id"],
        shard_key="spec-00000",
        operation_base="normalize-base",
        workspace_id=job["workspace_id"],
        course_context={},
        nodes=[SimpleNamespace(key="concept", evidence_ids=["allowed"])],
        evidence_by_id={},
    )
    assert calls == 0
    assert result.specs[0].items[0].evidence_ids == ["allowed"]
    assert result.specs[0].items[0].objective == "Explain the concept"
    with database.connect() as connection:
        receipt = connection.execute(
            "SELECT * FROM auto_knowledge_spec_split_receipts WHERE job_id=?", (job["id"],)
        ).fetchone()
        assert receipt is None  # No split operation or fictitious split receipt.
        original = connection.execute(
            "SELECT output_text,output_hash FROM auto_knowledge_model_attempts WHERE job_id=?",
            (job["id"],),
        ).fetchone()
        assert original["output_text"] == raw
        assert original["output_hash"] == output_hash
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM auto_knowledge_model_attempts WHERE job_id=?", (job["id"],)
            ).fetchone()[0]
            == 1
        )


@pytest.mark.parametrize("uncertain", [False, True])
def test_legacy_normalizable_failure_resumes_same_job_only_without_unknown(tmp_path, uncertain):
    from app.services.auto_knowledge_map import digest

    database, service, _ = service_at(tmp_path)
    ready_document(
        database, document_id="legacy-doc", chunk_id="legacy-chunk", content="Grounded concept."
    )
    service.reconcile(force=True)
    job = service.claim("legacy-test")
    raw = json.dumps(
        {
            "specs": [
                {
                    "node_key": "concept",
                    "change_reason": "Grounded",
                    "items": [
                        {
                            "item_id": "explain",
                            "requirement": "REQUIRED",
                            "objective": "Explain",
                            "acceptance": "Accurately",
                            "evidence_ids": ["allowed", "foreign"],
                        }
                    ],
                }
            ]
        }
    )
    operation = f"akm-{digest(str(job['id']))[:16]}-s-00000-r2"
    with database.connect() as c:
        c.execute(
            "INSERT INTO auto_knowledge_model_attempts("
            "operation_id,job_id,stage,shard_key,input_hash,status,"
            "output_text,output_hash,rejection_code) "
            "VALUES(?,?,'TEACHING_SPEC','spec-00000',?,'BUSINESS_REJECTED',"
            "?,?,'AUTO_EVIDENCE_INVALID')",
            (operation, job["id"], "a" * 64, raw, hashlib.sha256(raw.encode()).hexdigest()),
        )
        if uncertain:
            c.execute(
                "INSERT INTO auto_knowledge_model_attempts("
                "operation_id,job_id,stage,shard_key,input_hash,status) "
                "VALUES(?,?,'TEACHING_SPEC','spec-00001',?,'RESPONSE_UNKNOWN')",
                (operation + "-unknown", job["id"], "b" * 64),
            )
        c.execute(
            "UPDATE auto_knowledge_jobs SET status='FAILED',"
            "error_code='AUTO_ARTIFACT_CONFLICT',"
            "error_message='The split Spec recovery found no irreducibly invalid node.' WHERE id=?",
            (job["id"],),
        )
        c.execute(
            "UPDATE auto_knowledge_targets SET status='FAILED' WHERE target_key=?",
            (job["target_key"],),
        )
        c.execute(
            "INSERT INTO auto_knowledge_job_receipts("
            "job_id,target_key,corpus_fingerprint,status,source_snapshot_hash,"
            "model_calls_made,detail_json) VALUES(?,?,?,'FAILED',?,1,'{}')",
            (
                job["id"],
                job["target_key"],
                job["corpus_fingerprint"],
                digest(json.loads(job["source_snapshot_json"])),
            ),
        )
    with database.connect() as c:
        recovered = service._recover_safe_blocked_jobs(c, job["target_key"])
    assert recovered == (0 if uncertain else 1)
    with database.connect() as c:
        jobs = c.execute("SELECT id,status FROM auto_knowledge_jobs").fetchall()
        assert len(jobs) == 1 and jobs[0]["id"] == job["id"]
        assert jobs[0]["status"] == ("FAILED" if uncertain else "QUEUED")
        assert (
            c.execute(
                "SELECT output_text FROM auto_knowledge_model_attempts WHERE operation_id=?",
                (operation,),
            ).fetchone()[0]
            == raw
        )
        if not uncertain:
            recovery = c.execute(
                "SELECT reason,prior_receipt_json FROM auto_knowledge_job_recovery_receipts "
                "WHERE job_id=?",
                (job["id"],),
            ).fetchone()
            assert recovery["reason"] == "SPEC_SPLIT_SOURCE_REPLAY_V1"
            assert json.loads(recovery["prior_receipt_json"])["status"] == "FAILED"
