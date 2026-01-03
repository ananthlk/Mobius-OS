-- Migration 025: Task Catalog System
-- Purpose: Master reference system for tasks that must exist before being used in draft_plan
-- Tasks are reusable, versioned entities with rich metadata (automation, policy, dependencies, etc.)

-- 1. Main Task Catalog Table
CREATE TABLE IF NOT EXISTS task_catalog (
    id SERIAL PRIMARY KEY,
    task_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    task_key VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Classification (JSONB)
    classification JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Contract (JSONB)
    contract JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Automation (JSONB)
    automation JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Tool Binding (JSONB)
    tool_binding_defaults JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Information (JSONB)
    information JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Policy (JSONB)
    policy JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Temporal (JSONB)
    temporal JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Escalation (JSONB)
    escalation JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Dependencies (JSONB)
    dependencies JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Failure (JSONB)
    failure JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- UI (JSONB)
    ui JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Governance
    governance JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(50) DEFAULT 'draft', -- 'draft', 'active', 'deprecated'
    version INTEGER DEFAULT 1,
    schema_version VARCHAR(50) DEFAULT '1.0',
    
    -- Timestamps
    created_at_utc TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at_utc TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deprecated_at_utc TIMESTAMP WITH TIME ZONE,
    
    -- Actors
    created_by VARCHAR(255),
    updated_by VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_task_catalog_key ON task_catalog(task_key);
CREATE INDEX IF NOT EXISTS idx_task_catalog_status ON task_catalog(status);
CREATE INDEX IF NOT EXISTS idx_task_catalog_classification_domain ON task_catalog((classification->>'domain'));
CREATE INDEX IF NOT EXISTS idx_task_catalog_classification_category ON task_catalog((classification->>'category'));
CREATE INDEX IF NOT EXISTS idx_task_catalog_task_id ON task_catalog(task_id);

-- 2. Task Groups Table
CREATE TABLE IF NOT EXISTS task_groups (
    id SERIAL PRIMARY KEY,
    group_key VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    parent_group_key VARCHAR(255) REFERENCES task_groups(group_key) ON DELETE SET NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_task_groups_key ON task_groups(group_key);
CREATE INDEX IF NOT EXISTS idx_task_groups_parent ON task_groups(parent_group_key);

-- 3. Task Group Membership Table
CREATE TABLE IF NOT EXISTS task_group_memberships (
    id SERIAL PRIMARY KEY,
    task_key VARCHAR(255) NOT NULL REFERENCES task_catalog(task_key) ON DELETE CASCADE,
    group_key VARCHAR(255) NOT NULL REFERENCES task_groups(group_key) ON DELETE CASCADE,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(task_key, group_key)
);

CREATE INDEX IF NOT EXISTS idx_task_group_memberships_task ON task_group_memberships(task_key);
CREATE INDEX IF NOT EXISTS idx_task_group_memberships_group ON task_group_memberships(group_key);

-- 4. Task Version History Table
CREATE TABLE IF NOT EXISTS task_catalog_history (
    id SERIAL PRIMARY KEY,
    task_key VARCHAR(255) NOT NULL REFERENCES task_catalog(task_key) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    task_data JSONB NOT NULL,
    changed_by VARCHAR(255),
    change_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(task_key, version)
);

CREATE INDEX IF NOT EXISTS idx_task_catalog_history_key ON task_catalog_history(task_key);

COMMENT ON TABLE task_catalog IS 'Master reference catalog for all tasks. Tasks must exist here before being used in draft_plan.';
COMMENT ON TABLE task_groups IS 'Hierarchical grouping of tasks for organization';
COMMENT ON TABLE task_group_memberships IS 'Many-to-many relationship between tasks and groups';
COMMENT ON TABLE task_catalog_history IS 'Version history and audit trail for task changes';

