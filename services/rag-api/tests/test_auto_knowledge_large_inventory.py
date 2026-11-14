import pytest
from pydantic import ValidationError

from app.learning.models import AutoKnowledgeMapDraft
from app.services.auto_knowledge_map import OrchestratorDraftGenerator


def test_complete_large_inventory_reaches_compaction_without_dropping_sources():
    parts = []
    expected_sources = set()
    for start in range(0, 2001, 8):
        indices = range(start, min(start + 8, 2001))
        payload = {
            "title": "Bounded provider shard",
            "modules": [],
            "nodes": [
                {
                    "key": f"node-{index}",
                    "title": f"Distinct source concept {index}",
                    "description": "Grounded concept",
                    "evidence_ids": [f"segment-{index}"],
                }
                for index in indices
            ],
        }
        sources = {f"segment-{index}": f"source-{index}" for index in indices}
        expected_sources.update(sources.values())
        parts.append((AutoKnowledgeMapDraft.model_validate(payload), sources))

    inventory = OrchestratorDraftGenerator._merge_maps({"name": "Large course"}, parts)
    assert len(inventory.nodes) == 2001
    assert {e for node in inventory.nodes for e in node.evidence_ids} == expected_sources
    assert len(inventory.dispositions) == 2001
    assert len(OrchestratorDraftGenerator._outline_candidates(inventory)) == 2001

    # The model-facing contract remains bounded. Only the host's aggregate is larger.
    with pytest.raises(ValidationError, match="at most 2000"):
        AutoKnowledgeMapDraft.model_validate(inventory.model_dump())
    invalid = inventory.model_dump()
    invalid["nodes"][0]["parent_key"] = "missing-module"
    with pytest.raises(ValidationError, match="parent must be a module"):
        type(inventory).model_validate(invalid)
