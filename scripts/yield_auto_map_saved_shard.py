"""One-shot operator recovery: yield one long map only AFTER a durable paid shard.

Uses existing QUEUED/lease and artifact replay semantics. No provider dispatch,
request cancellation, schema migration, alternate queue or operation identity.
Remove this exact temporary trigger before resuming the shared backlog.
"""

TRIGGER = 'cj_autotree_private_priority_yield_20261114'
JOB = 'akm-job-01dc8cc9e5fb6c3e045947080084daa3'


def boundary_sql(job_id: str) -> str:
    literal = "'" + job_id.replace("'", "''") + "'"
    return f"""CREATE TRIGGER {TRIGGER}
AFTER UPDATE OF status ON auto_knowledge_model_attempts
WHEN NEW.job_id={literal} AND NEW.stage='SECTION_MAP'
 AND NEW.status='ACCEPTED' AND OLD.status='CONTRACT_VALID'
 AND EXISTS (SELECT 1 FROM auto_knowledge_jobs WHERE id=NEW.job_id AND status='RUNNING')
 AND EXISTS (SELECT 1 FROM auto_knowledge_job_artifacts
             WHERE job_id=NEW.job_id AND model_operation_id=NEW.operation_id)
 AND EXISTS (SELECT 1 FROM learning_operations
             WHERE id=NEW.operation_id AND status='COMPLETED')
BEGIN
 UPDATE auto_knowledge_jobs SET status='QUEUED',lease_owner=NULL,lease_expires_at=NULL,
  updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=NEW.job_id AND status='RUNNING';
 UPDATE auto_knowledge_targets SET status='QUEUED',
  message='Saved shard checkpoint; new private uploads take priority',
  updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE active_job_id=NEW.job_id;
END"""


def main() -> None:
    import datetime
    import fcntl
    import json
    import os
    import sqlite3
    import subprocess
    from pathlib import Path

    root = Path('/srv/coursemate/data-volume/source-repair/private-first-window-20261114')
    database = '/srv/coursemate/data/releases/20260919T202006Z/rag.sqlite3'
    pid = subprocess.check_output(
        ['systemctl', 'show', 'coursemate-rag.service', '-p', 'MainPID', '--value'],
        text=True,
    ).strip()
    assert os.readlink('/proc/' + pid + '/cwd') == (
        '/srv/coursemate/releases/autotree-append-cbe4664/services/rag-api'
    )
    with open('/run/lock/coursejesus-production-publish.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        with sqlite3.connect(database, timeout=2) as db:
            db.row_factory = sqlite3.Row
            db.execute('BEGIN IMMEDIATE')
            assert db.execute('select max(version) from schema_migrations').fetchone()[0] == 88
            assert db.execute(
                "select 1 from sqlite_master where type='trigger' and name=?",
                ('cj_autotree_pause_legacy_20261114',),
            ).fetchone(), 'Future shared claims must remain paused during this exact yield'
            job = db.execute('select * from auto_knowledge_jobs where id=?', (JOB,)).fetchone()
            assert job is not None and job['target_kind'] == 'AUTO_COURSE'
            assert job['status'] == 'RUNNING', 'Already terminal/yielded: inspect, never repeat'
            assert not db.execute(
                "select 1 from sqlite_master where type='trigger' and name=?", (TRIGGER,),
            ).fetchone()
            with (root / 'saved-shard-yield-before.json').open('x') as out:
                json.dump({'captured_at': datetime.datetime.now(datetime.UTC).isoformat(),
                           'job': dict(job), 'sql': boundary_sql(JOB),
                           'remove_trigger': f'DROP TRIGGER {TRIGGER}',
                           'rollback_database': False}, out, indent=2)
            db.execute(boundary_sql(JOB))
        print(json.dumps({'status': 'YIELD_ARMED_AFTER_NEXT_DURABLE_SHARD', 'job': JOB,
                          'current_request_interrupted': False, 'provider_calls': 0,
                          'trigger': TRIGGER}), flush=True)


if __name__ == '__main__':
    main()
