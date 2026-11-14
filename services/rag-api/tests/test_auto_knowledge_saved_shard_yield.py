"""Prove exact durable-boundary yield and same-operation, no-charge replay."""
import importlib.util
from pathlib import Path

from test_auto_knowledge_map import RecordingLearning, ready_document, service_at

from app.services.auto_knowledge_map import OrchestratorDraftGenerator


def test_saved_shard_yield_preserves_response_and_resumes_without_repeat(tmp_path: Path):
    source = Path(__file__).resolve().parents[3] / 'scripts/yield_auto_map_saved_shard.py'
    spec = importlib.util.spec_from_file_location('saved_shard_yield', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    database, service, _ = service_at(tmp_path)
    class CheckpointLearning(RecordingLearning):
        def generate(self, *args, **kwargs):
            output, run = super().generate(*args, **kwargs)
            sink = kwargs['transport_event_sink']
            sink({'phase': 'SEND_INTENT', 'input_hash': 'a' * 64})
            sink({'phase': 'RESPONSE_COMPLETE', 'provider_response_id': 'offline-test',
                  'output_text': output.model_dump_json()})
            sink({'phase': 'CONTRACT_VALID'})
            return output, run

    learning = CheckpointLearning()
    service.generator = OrchestratorDraftGenerator(database, learning)
    ready_document(database, document_id='large', chunk_id='large', content='x' * 13000)
    service.reconcile(force=True)
    with database.connect() as db:
        job_id = db.execute('select id from auto_knowledge_jobs').fetchone()[0]
        db.execute(module.boundary_sql(job_id))
        db.commit()
    yielded = service.run_once('first-worker')
    assert yielded == {'job_id': job_id, 'status': 'QUEUED', 'error': 'AUTO_LEASE_LOST'}
    assert len(learning.calls) == 1
    first_operation = learning.calls[0]['operation']
    with database.connect() as db:
        artifact_before = tuple(db.execute(
            'select model_operation_id,output_json,output_hash from auto_knowledge_job_artifacts'
        ).fetchone())
        assert artifact_before[0] == first_operation
        status = db.execute('select status from auto_knowledge_model_attempts').fetchone()[0]
        assert status == 'ACCEPTED'
        assert db.execute('select status from learning_operations where id=?',
                          (first_operation,)).fetchone()[0] == 'COMPLETED'
        db.execute(f'DROP TRIGGER {module.TRIGGER}')
        db.commit()
    resumed = service.run_once('second-worker')
    assert resumed['status'] == 'READY', resumed
    assert sum(call['operation'] == first_operation for call in learning.calls) == 1
    with database.connect() as db:
        artifact_after = tuple(db.execute(
            'select model_operation_id,output_json,output_hash from auto_knowledge_job_artifacts '
            'where model_operation_id=?', (first_operation,),
        ).fetchone())
    assert artifact_after == artifact_before
