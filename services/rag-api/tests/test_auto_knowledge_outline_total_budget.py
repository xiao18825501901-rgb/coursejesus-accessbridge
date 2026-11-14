"""The owner's final-tree limit is total nodes, not independent layout quotas."""

from pathlib import Path

import pytest
from test_auto_knowledge_map import (
    ManyConceptLearning,
    private_workspace,
    ready_document,
    settings_at,
)

from app.db import Database
from app.services.auto_knowledge_map import AutoKnowledgeMapService


class FinalShapeLearning(ManyConceptLearning):
    def __init__(self, modules: int, units: int) -> None:
        super().__init__()
        self.module_count = modules
        self.unit_count = units

    def generate(self, workspace_id, operation, schema, **kwargs):
        context = kwargs["context"]
        if schema.__name__ != "AutoKnowledgeCompactOutlineDraft":
            return super().generate(workspace_id, operation, schema, **kwargs)
        concepts = context["provisional_concepts"]
        assert len(concepts) == 52
        payload = {
            "title": "Grounded compact course",
            "modules": [
                {
                    "key": f"module-{i}",
                    "title": f"Chapter {i}",
                    "description": "Grounded grouping",
                    "major": "OTHER",
                }
                for i in range(self.module_count)
            ],
            "nodes": [
                {
                    "key": f"unit-{i}",
                    "parent_key": f"module-{i % self.module_count}",
                    "title": f"Learning unit {i}",
                    "description": "Source-supported learning unit",
                    "major": "OTHER",
                    "prerequisite_keys": [],
                    "evidence_ids": [c["key"] for c in concepts[i :: self.unit_count]],
                }
                for i in range(self.unit_count)
            ],
            "unmapped_evidence_ids": [],
        }
        return schema.model_validate(payload), {"status": "COMPLETED"}


@pytest.mark.parametrize("modules,units,eligible", [(8, 39, True), (9, 41, True), (8, 43, False)])
def test_final_outline_uses_total_fifty_node_budget(
    tmp_path: Path,
    modules: int,
    units: int,
    eligible: bool,
) -> None:
    settings = settings_at(tmp_path)
    database = Database(settings)
    database.initialize()
    private_workspace(database)
    for i in range(52):
        ready_document(
            database,
            document_id=f"budget-doc-{i}",
            chunk_id=f"budget-chunk-{i}",
            content=f"Independent source-supported concept {i} with explicit conditions.",
        )
    learning = FinalShapeLearning(modules, units)
    service = AutoKnowledgeMapService(database, settings, learning)  # type: ignore[arg-type]
    assert service.reconcile(force=True)["QUEUED"] == 1
    result = service.run_once("total-budget-test-worker")
    assert result is not None
    if eligible:
        assert result["status"] in {"READY", "READY_WITH_EXCEPTIONS"}
        with database.connect() as connection:
            job = connection.execute(
                "SELECT result_tree_version_id FROM auto_knowledge_jobs"
            ).fetchone()
            counts = connection.execute(
                "SELECT count(*),sum(teaching_spec_version IS NOT NULL) "
                "FROM knowledge_tree_memberships WHERE tree_version_id=?",
                (job["result_tree_version_id"],),
            ).fetchone()
        assert tuple(counts) == (modules + units, units)
    else:
        assert result["status"] not in {"READY", "READY_WITH_EXCEPTIONS"}
        with database.connect() as connection:
            assert (
                connection.execute("SELECT count(*) FROM knowledge_tree_memberships").fetchone()[0]
                == 0
            )
