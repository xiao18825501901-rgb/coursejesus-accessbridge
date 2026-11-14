"""Known complete append-analysis recovery; never replay uncertain transport."""
import hashlib
import json
from pathlib import Path

import pytest
from test_auto_knowledge_map import RecordingLearning, ready_document, service_at

from app.errors import ApiError
from app.services.auto_knowledge_map import OrchestratorDraftGenerator, digest


class CheckpointLearning(RecordingLearning):
    def generate(self, *args, **kwargs):
        output, run = super().generate(*args, **kwargs)
        sink = kwargs['transport_event_sink']
        sink({'phase': 'SEND_INTENT', 'input_hash': 'a' * 64})
        sink({'phase': 'RESPONSE_COMPLETE', 'output_text': output.model_dump_json()})
        sink({'phase': 'CONTRACT_VALID'})
        return output, run


class SeedOldOutlineFailure(OrchestratorDraftGenerator):
    """Explicit old-failure fixture after native accepted analysis persistence."""

    def generate(self, **kwargs):
        self.job_id = kwargs['job_id']
        self.workspace = kwargs['workspace_id']
        return super().generate(**kwargs)

    def _legacy_reusable_spec(self, legacy_tree_id, node):
        operation = f'akm-{digest(self.job_id)[:16]}-o-00-00000'
        with self.database.connect() as db:
            db.execute(
                "INSERT INTO learning_operations(workspace_id,id,request_hash,kind,status) "
                "VALUES(?,?,?,'auto.knowledge.map','FAILED')",
                (self.workspace, operation, 'c' * 64),
            )
            db.execute(
                "INSERT INTO learning_model_call_reservations "
                "(id,workspace_id,operation_id,owner_user_id,course_id,role,"
                "reserved_output_tokens,status,input_tokens,output_tokens,finished_at) "
                "VALUES('old-outline-fee',?,?,'owner-a','private-course','teacher',"
                "4000,'FAILED',123,45,'2026-11-14T00:00:00Z')",
                (self.workspace, operation),
            )
            db.execute(
                "INSERT INTO auto_knowledge_model_attempts "
                "(operation_id,job_id,stage,shard_key,input_hash,status,output_text,output_hash) "
                "VALUES(?,?,'SECTION_MAP','outline-00-00000',?,'CONTRACT_REJECTED','{}',?)",
                (operation, self.job_id, 'c' * 64, hashlib.sha256(b'{}').hexdigest()),
            )
            db.execute('UPDATE auto_knowledge_jobs SET repair_calls_made=2 WHERE id=?',
                       (self.job_id,))
        raise ApiError(422, 'AUTO_REPAIR_LIMIT', 'Known complete old outline rejection')


@pytest.mark.parametrize('uncertain', [False, True])
def test_bounded_append_resume_keeps_failure_fees_and_original_analysis(tmp_path: Path, uncertain):
    database, service, _ = service_at(tmp_path)
    ready_document(database, document_id='old', chunk_id='old', content='Original topics')
    service.reconcile(force=True)
    service.run_once('base')
    learning = CheckpointLearning()
    service.generator = SeedOldOutlineFailure(database, learning)
    ready_document(database, document_id='append', chunk_id='append', content='New topics')
    service.reconcile(force=True)
    failed = service.run_once('old-version-fixture')
    assert failed['status'] == 'FAILED'
    first_operation = learning.calls[0]['operation']
    with database.connect() as db:
        fees_before = [tuple(r) for r in db.execute(
            'SELECT * FROM learning_model_call_reservations')]
        raw_before = [tuple(r) for r in db.execute(
            'SELECT operation_id,status,output_text,output_hash FROM auto_knowledge_model_attempts '
            'WHERE job_id=? ORDER BY operation_id', (failed['job_id'],),
        )]
        if uncertain:
            db.execute(
                "INSERT INTO auto_knowledge_model_attempts "
                "(operation_id,job_id,stage,shard_key,input_hash,status) "
                "VALUES('uncertain-send',?,'SECTION_MAP','map-unknown',?,'RESPONSE_UNKNOWN')",
                (failed['job_id'], 'd' * 64),
            )
        recovered = service._recover_safe_blocked_jobs(db, 'PRIVATE:workspace-a')
        db.commit()
    assert recovered == (0 if uncertain else 1)
    if uncertain:
        assert len(learning.calls) == 1
        return
    service.generator = OrchestratorDraftGenerator(database, learning)
    resumed = service.run_once('same-job-resume')
    assert resumed['job_id'] == failed['job_id']
    assert resumed['status'] == 'READY', resumed
    assert sum(c['operation'] == first_operation for c in learning.calls) == 1
    assert [c['schema'] for c in learning.calls] == [
        'AutoKnowledgeMapDraft', 'AutoKnowledgeSpecSetDraft',
    ]
    with database.connect() as db:
        assert fees_before == [tuple(r) for r in db.execute(
            'SELECT * FROM learning_model_call_reservations')]
        for previous in raw_before:
            current = db.execute(
                'SELECT operation_id,status,output_text,output_hash '
                'FROM auto_knowledge_model_attempts WHERE operation_id=?', (previous[0],),
            ).fetchone()
            assert tuple(current) == previous
        receipt = db.execute(
            'SELECT reason,prior_receipt_json FROM auto_knowledge_job_recovery_receipts '
            'WHERE job_id=?', (failed['job_id'],),
        ).fetchone()
        assert receipt['reason'] == 'BOUNDED_APPEND_LOCAL_RESUME_V1'
        assert json.loads(receipt['prior_receipt_json'])['status'] == 'FAILED'
