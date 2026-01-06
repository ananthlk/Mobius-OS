-- Tool Conditional Execution Schema
-- Migration: 019_tool_conditional_execution.sql

-- Add conditional execution support to tools table
ALTER TABLE tools ADD COLUMN IF NOT EXISTS supports_conditional_execution BOOLEAN DEFAULT FALSE;
ALTER TABLE tools ADD COLUMN IF NOT EXISTS default_condition_type VARCHAR(50);
ALTER TABLE tools ADD COLUMN IF NOT EXISTS conditional_execution_examples JSONB;

-- Conditional execution rules for tools
CREATE TABLE IF NOT EXISTS tool_execution_conditions (
    id SERIAL PRIMARY KEY,
    tool_id INTEGER REFERENCES tools(id) ON DELETE CASCADE,
    
    -- Condition type
    condition_type VARCHAR(50) NOT NULL, -- 'if', 'on_success', 'on_failure', 'on_error', 'when', 'unless', 'if_else'
    
    -- Condition expression (JSONB for flexibility)
    condition_expression JSONB NOT NULL, -- e.g., {"field": "eligibility_status", "operator": "equals", "value": "active"}
    
    -- Action when condition is met
    action_type VARCHAR(50) NOT NULL, -- 'execute', 'skip', 'retry', 'escalate', 'notify', 'branch'
    action_target_tool_id INTEGER REFERENCES tools(id) ON DELETE SET NULL, -- Next tool to execute if condition met
    action_target_tool_name VARCHAR(255), -- Name of target tool (for reference)
    
    -- Condition metadata
    condition_description TEXT, -- Human-readable description
    icon_name VARCHAR(50), -- Icon identifier for UI (e.g., 'if-check', 'on-success', 'on-error')
    icon_color VARCHAR(20), -- Color for icon (e.g., 'green', 'red', 'blue', 'amber', 'purple')
    
    -- Execution order
    execution_order INTEGER DEFAULT 0, -- Order of condition evaluation
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_condition_type CHECK (condition_type IN ('if', 'on_success', 'on_failure', 'on_error', 'when', 'unless', 'if_else')),
    CONSTRAINT valid_action_type CHECK (action_type IN ('execute', 'skip', 'retry', 'escalate', 'notify', 'branch'))
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_tool_conditions_tool_id ON tool_execution_conditions(tool_id);
CREATE INDEX IF NOT EXISTS idx_tool_conditions_type ON tool_execution_conditions(condition_type);
CREATE INDEX IF NOT EXISTS idx_tool_conditions_active ON tool_execution_conditions(is_active);

COMMENT ON TABLE tool_execution_conditions IS 'Stores conditional execution rules for tools (if/then, on_success, on_failure, etc.)';
COMMENT ON COLUMN tool_execution_conditions.condition_expression IS 'JSONB structure: {"field": "field_name", "operator": "equals|not_equals|contains|greater_than|less_than", "value": "expected_value"}';
COMMENT ON COLUMN tool_execution_conditions.icon_name IS 'Icon identifier for UI display (e.g., if-check, on-success, on-failure)';





