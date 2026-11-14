"""Owner append contract: preserve frozen base; <=50 new display nodes per batch."""
import sqlite3
from pathlib import Path

import pytest
from test_auto_knowledge_map import FakeGenerator, RecordingLearning, ready_document, service_at

from app.db import LATEST_V3_SCHEMA_VERSION
from app.services.auto_knowledge_map import OrchestratorDraftGenerator


def test_runtime_requires_append_budget_schema():
    assert LATEST_V3_SCHEMA_VERSION >= 88


class SizedGenerator(FakeGenerator):
    def __init__(self):
        super().__init__()
        self.atomic_count = 49

    def generate(self, **kwargs):
        draft, specs, calls = super().generate(**kwargs)
        nodes = [draft.nodes[0].model_copy(update={
            "key": f"point-{i}", "title": f"Batch {self.calls} point {i}",
        }) for i in range(self.atomic_count)]
        node_specs = [specs.specs[0].model_copy(update={"node_key": n.key}) for n in nodes]
        return draft.model_copy(update={"nodes": nodes}), specs.model_copy(
            update={"specs": node_specs}), calls


def membership_rows(database, tree):
    with database.connect() as db:
        return [tuple(r) for r in db.execute(
            "select node_id,parent_node_id,ordinal,teaching_spec_version "
            "from knowledge_tree_memberships where tree_version_id=? order by node_id", (tree,),
        )]


def test_append_preserves_fifty_node_base_and_only_generates_delta(tmp_path: Path):
    database, service, _ = service_at(tmp_path)
    generator = SizedGenerator()
    service.generator = generator
    ready_document(database, document_id="first", chunk_id="first", content="Original topics")
    service.reconcile(force=True)
    assert service.run_once("first")["status"] == "READY"
    old_tree = service.status("private-course", "owner-a")["tree_version_id"]
    old = membership_rows(database, old_tree)
    assert len(old) == 50
    ready_document(database, document_id="append", chunk_id="append", content="New topics")
    service.reconcile(force=True)
    result = service.run_once("append")
    assert result["status"] == "READY", result
    new_tree = service.status("private-course", "owner-a")["tree_version_id"]
    new = membership_rows(database, new_tree)
    assert new_tree != old_tree
    assert len(new) == 100
    assert set(old) <= set(new)
    assert membership_rows(database, old_tree) == old
    assert generator.evidence_ids == ["append"]
    service.reconcile(force=True)
    assert service.run_once("no-repeat") is None
    assert generator.calls == 2
    ready_document(database, document_id="third", chunk_id="third", content="Third batch topics")
    service.reconcile(force=True)
    assert service.run_once("third")["status"] == "READY"
    third_tree = service.status("private-course", "owner-a")["tree_version_id"]
    third = membership_rows(database, third_tree)
    assert len(third) == 150
    assert set(new) <= set(third)
    assert generator.evidence_ids == ["third"]


def test_append_rejects_fifty_one_new_nodes_without_replacing_base(tmp_path: Path):
    database, service, _ = service_at(tmp_path)
    generator = SizedGenerator()
    service.generator = generator
    ready_document(database, document_id="first", chunk_id="first", content="Original topics")
    service.reconcile(force=True)
    service.run_once("first")
    old_tree = service.status("private-course", "owner-a")["tree_version_id"]
    generator.atomic_count = 50
    ready_document(database, document_id="append", chunk_id="append", content="New topics")
    service.reconcile(force=True)
    result = service.run_once("over-limit")
    assert result["status"] == "FAILED"
    assert result["error"] == "TREE_NODE_LIMIT_EXCEEDED"
    assert service.status("private-course", "owner-a")["tree_version_id"] == old_tree
    assert len(membership_rows(database, old_tree)) == 50


def test_append_preserves_legacy_tree_without_completed_job_lineage(tmp_path: Path):
    database, service, _ = service_at(tmp_path)
    generator = SizedGenerator()
    service.generator = generator
    ready_document(database, document_id="first", chunk_id="first", content="Original topics")
    service.reconcile(force=True)
    service.run_once("first")
    old_tree = service.status("private-course", "owner-a")["tree_version_id"]
    old = membership_rows(database, old_tree)
    with database.connect() as db:
        # Legacy/manual activation has no completed automatic-job link.
        db.execute("UPDATE auto_knowledge_jobs SET result_tree_version_id=NULL")
        db.commit()
    ready_document(database, document_id="append", chunk_id="append", content="New topics")
    service.reconcile(force=True)
    result = service.run_once("legacy-append")
    assert result["status"] == "READY", result
    tree = service.status("private-course", "owner-a")["tree_version_id"]
    assert set(old) <= set(membership_rows(database, tree))
    assert len(membership_rows(database, tree)) == 100
    assert generator.evidence_ids == ["append"]


def test_base_pointer_alone_cannot_bypass_initial_fifty_member_limit(tmp_path: Path):
    database, service, _ = service_at(tmp_path)
    service.generator = SizedGenerator()
    ready_document(database, document_id="first", chunk_id="first", content="Original topics")
    service.reconcile(force=True)
    service.run_once("first")
    tree = service.status("private-course", "owner-a")["tree_version_id"]
    with database.connect() as db:
        db.execute(
            "INSERT INTO knowledge_tree_versions "
            "(id,course_id,workspace_id,owner_user_id,tree_kind,version,status,title,"
            "change_reason,content_hash,base_tree_version_id) "
            "SELECT 'untrusted-append',course_id,workspace_id,owner_user_id,tree_kind,"
            "version+1,'DRAFT',title,change_reason,content_hash,id "
            "FROM knowledge_tree_versions WHERE id=?", (tree,),
        )
        db.execute(
            "INSERT INTO knowledge_tree_memberships "
            "SELECT 'untrusted-append',node_id,parent_node_id,ordinal,teaching_spec_version "
            "FROM knowledge_tree_memberships WHERE tree_version_id=? "
            "ORDER BY parent_node_id IS NOT NULL,ordinal", (tree,),
        )
        module = db.execute(
            "SELECT node_id FROM knowledge_tree_memberships WHERE tree_version_id=? "
            "AND parent_node_id IS NULL LIMIT 1", (tree,),
        ).fetchone()[0]
        with pytest.raises(sqlite3.IntegrityError, match="at most50"):
            db.execute(
                "INSERT INTO knowledge_tree_memberships VALUES ('untrusted-append',?,NULL,99,NULL)",
                (module + '-new',),
            )
        db.rollback()


def test_production_generator_receives_baseline_and_only_delta(tmp_path: Path):
    database, service, _ = service_at(tmp_path)
    ready_document(database, document_id="first", chunk_id="first", content="Original topics")
    service.reconcile(force=True)
    service.run_once("first")
    old_tree = service.status("private-course", "owner-a")["tree_version_id"]
    old = membership_rows(database, old_tree)

    class CaptureLearning(RecordingLearning):
        def generate(self, *args, **kwargs):
            context = kwargs["context"]
            assert context["policy"]["append_only"] is True
            assert context["existing_knowledge"]
            if "frozen_source_segments" in context:
                assert all(item["content"] == "New topics"
                           for item in context["frozen_source_segments"])
            return super().generate(*args, **kwargs)

    learning = CaptureLearning()
    service.generator = OrchestratorDraftGenerator(database, learning)
    ready_document(database, document_id="append", chunk_id="append", content="New topics")
    service.reconcile(force=True)
    result = service.run_once("real-generator-append")
    assert result["status"] == "READY", result
    tree = service.status("private-course", "owner-a")["tree_version_id"]
    assert set(old) <= set(membership_rows(database, tree))
    assert learning.calls
    assert [call['schema'] for call in learning.calls] == [
        'AutoKnowledgeMapDraft', 'AutoKnowledgeSpecSetDraft',
    ]


def test_redundant_append_preserves_base_without_inventing_nodes(tmp_path: Path):
    database, service, _ = service_at(tmp_path)
    ready_document(database, document_id="first", chunk_id="first", content="Original topics")
    service.reconcile(force=True)
    service.run_once("first")
    old_tree = service.status("private-course", "owner-a")["tree_version_id"]
    old = membership_rows(database, old_tree)

    class DuplicateLearning:
        calls = 0

        def generate(self, workspace_id, operation, schema, **kwargs):
            self.calls += 1
            assert schema.__name__ == "AutoKnowledgeMapDraft"
            return schema.model_validate({
                "title": "No new topics", "modules": [], "nodes": [],
                "dispositions": [{"evidence_id": item["id"], "status": "DUPLICATE",
                                  "reason": "Same learning objective as existing knowledge",
                                  "node_keys": []}
                                 for item in kwargs["context"]["frozen_source_segments"]],
            }), {"status": "COMPLETED"}

    learning = DuplicateLearning()
    service.generator = OrchestratorDraftGenerator(database, learning)
    ready_document(database, document_id="append", chunk_id="append",
                   content="Original topics restated")
    service.reconcile(force=True)
    result = service.run_once("duplicate-append")
    assert result["status"] == "READY", result
    tree = service.status("private-course", "owner-a")["tree_version_id"]
    assert membership_rows(database, tree) == old
    assert learning.calls == 1
