-- Migration 022: Workflow Plan State Management
-- Purpose: Track plan lifecycle, phase/step status, and tool configurations
-- Follows module:domain:strategy:step pattern for plan tracking

CREATE TABLE IF NOT EXISTS workflow_plans (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES shaping_sessions(id) ON DELETE CASCADE,
    plan_name VARCHAR(255),
    problem_statement TEXT,
    goal TEXT,
    
    -- Plan structure (JSONB)
    plan_structure JSONB NOT NULL,
    
    -- Metadata (JSONB)
    metadata JSONB NOT NULL,
    
    -- Template reference (follows module:domain:strategy:step pattern)
    parent_template_key VARCHAR(255),
    
    -- Status tracking
    status VARCHAR(50) DEFAULT 'draft',
    version INTEGER DEFAULT 1,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP,
    execution_started_at TIMESTAMP,
    execution_completed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- User tracking
    created_by VARCHAR(100),
    approved_by VARCHAR(100),
    last_modified_by VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS workflow_plan_phases (
    id SERIAL PRIMARY KEY,
    plan_id INTEGER REFERENCES workflow_plans(id) ON DELETE CASCADE,
    phase_id VARCHAR(100) NOT NULL,
    phase_name VARCHAR(255),
    description TEXT,
    
    -- Phase structure (JSONB)
    phase_structure JSONB NOT NULL,
    
    -- Metadata (JSONB)
    metadata JSONB NOT NULL,
    
    -- Status
    status VARCHAR(50) DEFAULT 'planned',
    execution_order INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS workflow_plan_steps (
    id SERIAL PRIMARY KEY,
    plan_id INTEGER REFERENCES workflow_plans(id) ON DELETE CASCADE,
    phase_id INTEGER REFERENCES workflow_plan_phases(id) ON DELETE CASCADE,
    step_id VARCHAR(100) NOT NULL,
    description TEXT,
    
    -- Tool configuration (JSONB)
    tool_definition JSONB,
    
    -- Metadata (JSONB)
    metadata JSONB NOT NULL,
    
    -- Status
    status VARCHAR(50) DEFAULT 'planned',
    execution_order INTEGER DEFAULT 0,
    
    -- Dependencies
    depends_on_step_ids TEXT[],
    
    -- Execution results
    execution_result JSONB,
    execution_error TEXT,
    execution_duration_ms INTEGER,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    execution_started_at TIMESTAMP,
    execution_completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS workflow_plan_enhancements (
    id SERIAL PRIMARY KEY,
    plan_id INTEGER REFERENCES workflow_plans(id) ON DELETE CASCADE,
    step_id INTEGER REFERENCES workflow_plan_steps(id) ON DELETE CASCADE,
    
    -- Enhancement details
    enhancement_type VARCHAR(50),
    enhancement_data JSONB NOT NULL,
    
    -- Who/what enhanced
    enhanced_by VARCHAR(100),
    enhanced_by_type VARCHAR(50),
    enhancement_reason TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_plan_session ON workflow_plans(session_id);
CREATE INDEX IF NOT EXISTS idx_plan_status ON workflow_plans(status);
CREATE INDEX IF NOT EXISTS idx_plan_template ON workflow_plans(parent_template_key);
CREATE INDEX IF NOT EXISTS idx_phase_plan ON workflow_plan_phases(plan_id);
CREATE INDEX IF NOT EXISTS idx_step_phase ON workflow_plan_steps(phase_id);
CREATE INDEX IF NOT EXISTS idx_step_plan ON workflow_plan_steps(plan_id);
CREATE INDEX IF NOT EXISTS idx_enhancement_plan ON workflow_plan_enhancements(plan_id);
CREATE INDEX IF NOT EXISTS idx_enhancement_step ON workflow_plan_enhancements(step_id);

COMMENT ON TABLE workflow_plans IS 'Main workflow plans with lifecycle tracking following module:domain:strategy:step pattern';
COMMENT ON TABLE workflow_plan_phases IS 'Phases within a plan with status tracking';
COMMENT ON TABLE workflow_plan_steps IS 'Individual steps with tool configurations and agent enhancements';
COMMENT ON TABLE workflow_plan_enhancements IS 'Audit trail of agent/user enhancements to steps';





