-- Owner-approved append policy: <=50 NEW members, frozen base retained exactly.
-- Initial/manual trees retain the original50-member cap. No student rows are rewritten.
BEGIN IMMEDIATE;

CREATE VIEW auto_tree_append_bases AS
SELECT DISTINCT tree.id AS tree_version_id, base.id AS base_tree_version_id
FROM knowledge_tree_versions AS tree
JOIN knowledge_tree_versions AS base ON base.id=tree.base_tree_version_id
JOIN auto_knowledge_jobs AS job ON job.course_id=tree.course_id
 AND (job.workspace_id=tree.workspace_id OR
      (job.target_kind='AUTO_COURSE' AND tree.tree_kind='OFFICIAL'))
WHERE job.builder_version='AUTO_KNOWLEDGE_MAP_APPEND_50_V1'
 AND job.status IN ('RUNNING','READY','READY_WITH_EXCEPTIONS')
 AND job.corpus_fingerprint=tree.corpus_fingerprint
 AND base.course_id=tree.course_id
 AND json_extract(job.source_snapshot_json,'$.append_base_tree_version_id')=base.id
 AND json_extract(job.source_snapshot_json,'$.append_base_tree_hash')=base.content_hash;

CREATE VIEW auto_tree_budget_violations AS
SELECT tree.id AS tree_version_id FROM knowledge_tree_versions AS tree
WHERE (
 SELECT COUNT(*) FROM knowledge_tree_memberships AS member
 WHERE member.tree_version_id=tree.id AND NOT EXISTS (
  SELECT 1 FROM auto_tree_append_bases AS allowed
  JOIN knowledge_tree_memberships AS original
   ON original.tree_version_id=allowed.base_tree_version_id
  WHERE allowed.tree_version_id=tree.id AND original.node_id=member.node_id
 )
)>50 OR EXISTS (
 SELECT 1 FROM auto_tree_append_bases AS allowed
 JOIN knowledge_tree_memberships AS original
  ON original.tree_version_id=allowed.base_tree_version_id
 WHERE allowed.tree_version_id=tree.id AND NOT EXISTS (
  SELECT 1 FROM knowledge_tree_memberships AS retained
  WHERE retained.tree_version_id=tree.id AND retained.node_id=original.node_id
   AND retained.parent_node_id IS original.parent_node_id
   AND retained.ordinal=original.ordinal
   AND retained.teaching_spec_version IS original.teaching_spec_version
 )
);

DROP TRIGGER IF EXISTS limit_tree_membership_insert;
CREATE TRIGGER limit_tree_membership_insert BEFORE INSERT ON knowledge_tree_memberships
WHEN NOT EXISTS (
 SELECT 1 FROM auto_tree_append_bases AS allowed
 JOIN knowledge_tree_memberships AS original
  ON original.tree_version_id=allowed.base_tree_version_id
 WHERE allowed.tree_version_id=NEW.tree_version_id AND original.node_id=NEW.node_id
) AND (
 SELECT COUNT(*) FROM knowledge_tree_memberships AS member
 WHERE member.tree_version_id=NEW.tree_version_id AND NOT EXISTS (
  SELECT 1 FROM auto_tree_append_bases AS allowed
  JOIN knowledge_tree_memberships AS original
   ON original.tree_version_id=allowed.base_tree_version_id
  WHERE allowed.tree_version_id=NEW.tree_version_id AND original.node_id=member.node_id
 )
)>=50 BEGIN
 SELECT RAISE(ABORT,'A knowledge-tree batch may add at most50 members');
END;

DROP TRIGGER IF EXISTS limit_tree_membership_move;
CREATE TRIGGER limit_tree_membership_move BEFORE UPDATE OF tree_version_id
ON knowledge_tree_memberships
WHEN NEW.tree_version_id!=OLD.tree_version_id AND NOT EXISTS (
 SELECT 1 FROM auto_tree_append_bases AS allowed
 JOIN knowledge_tree_memberships AS original
  ON original.tree_version_id=allowed.base_tree_version_id
 WHERE allowed.tree_version_id=NEW.tree_version_id AND original.node_id=NEW.node_id
) AND (
 SELECT COUNT(*) FROM knowledge_tree_memberships AS member
 WHERE member.tree_version_id=NEW.tree_version_id AND NOT EXISTS (
  SELECT 1 FROM auto_tree_append_bases AS allowed
  JOIN knowledge_tree_memberships AS original
   ON original.tree_version_id=allowed.base_tree_version_id
  WHERE allowed.tree_version_id=NEW.tree_version_id AND original.node_id=member.node_id
 )
)>=50 BEGIN
 SELECT RAISE(ABORT,'A knowledge-tree batch may add at most50 members');
END;

DROP TRIGGER IF EXISTS limit_tree_status_activation;
CREATE TRIGGER limit_tree_status_activation BEFORE UPDATE OF status ON knowledge_tree_versions
WHEN NEW.status IN ('PUBLISHED','ACTIVE') AND EXISTS (
 SELECT 1 FROM auto_tree_budget_violations WHERE tree_version_id=NEW.id
) BEGIN
 SELECT RAISE(ABORT,'Knowledge-tree append exceeds50 new members or changes its frozen base');
END;

DROP TRIGGER IF EXISTS limit_auto_tree_activation_insert;
CREATE TRIGGER limit_auto_tree_activation_insert BEFORE INSERT ON auto_course_tree_activations
WHEN NEW.status='ACTIVE' AND EXISTS (
 SELECT 1 FROM auto_tree_budget_violations WHERE tree_version_id=NEW.tree_version_id
) BEGIN
 SELECT RAISE(ABORT,'Automatic tree append violates its member budget or frozen base');
END;

DROP TRIGGER IF EXISTS limit_auto_tree_activation_update;
CREATE TRIGGER limit_auto_tree_activation_update
BEFORE UPDATE OF tree_version_id,status ON auto_course_tree_activations
WHEN NEW.status='ACTIVE' AND EXISTS (
 SELECT 1 FROM auto_tree_budget_violations WHERE tree_version_id=NEW.tree_version_id
) BEGIN
 SELECT RAISE(ABORT,'Automatic tree append violates its member budget or frozen base');
END;

INSERT OR IGNORE INTO schema_migrations(version,name)
VALUES(88,'automatic tree append budget and immutable baseline');
COMMIT;
