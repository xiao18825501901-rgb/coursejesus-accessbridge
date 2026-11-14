"""A corpus sweep must not keep one writer transaction across all courses."""

import sqlite3
from pathlib import Path

from test_auto_knowledge_map import ready_document, service_at


def test_reconcile_releases_writer_between_independent_course_targets(tmp_path: Path) -> None:
    database, service, generator = service_at(tmp_path)
    ready_document(
        database, document_id="first-doc", chunk_id="first-chunk", content="First source."
    )
    with database.connect() as connection:
        for identifier in ["other-course", "other-corpus"]:
            connection.execute(
                "INSERT INTO courses(id,name,owner_user_id,course_type,visibility,"
                "publication_status) VALUES(?,?,'owner-a','user','private','private')",
                (identifier, identifier),
            )
        connection.execute(
            "INSERT INTO learning_workspaces(id,owner_user_id,course_id,private_course_id) "
            "VALUES('other-workspace','owner-a','other-course','other-corpus')"
        )
        connection.execute("CREATE TABLE test_writer_probe(value INTEGER)")
    ready_document(
        database,
        document_id="second-doc",
        chunk_id="second-chunk",
        content="Second source.",
        course_id="other-corpus",
    )
    ensure = service._ensure_target
    seen = 0
    writes = []
    failures = []

    def between_transactions(statement):
        if statement.strip().upper() == "BEGIN IMMEDIATE" and seen == 1:
            # Trace fires before the next transaction acquires its writer lock.
            try:
                with sqlite3.connect(database.path, timeout=0.05) as writer:
                    writer.execute("INSERT INTO test_writer_probe VALUES(1)")
                    writes.append(
                        writer.execute("SELECT count(*) FROM auto_knowledge_jobs").fetchone()[0]
                    )
            except sqlite3.Error as error:
                failures.append(str(error))

    def observe(connection, target, **kwargs):
        nonlocal seen
        if seen == 0:
            connection.set_trace_callback(between_transactions)
        seen += 1
        return ensure(connection, target, **kwargs)

    service._ensure_target = observe  # type: ignore[method-assign]
    assert service.reconcile(force=True)["QUEUED"] == 2
    assert seen == 2 and generator.calls == 0
    assert writes == [1] and failures == []
    service.reconcile(force=True)
    with database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM auto_knowledge_jobs").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM test_writer_probe").fetchone()[0] == 1
