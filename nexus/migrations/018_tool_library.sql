-- Tool Library Schema
-- Migration: 018_tool_library.sql

-- Main tools table
CREATE TABLE IF NOT EXISTS tools (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(100) NOT NULL,
    version VARCHAR(50) DEFAULT '1.0.0',
    
    -- Schema definition (JSONB for flexibility)
    schema_definition JSONB NOT NULL,
    
    -- Execution metadata
    requires_human_review BOOLEAN DEFAULT FALSE,
    is_batch_processable BOOLEAN DEFAULT FALSE,
    estimated_execution_time_ms INTEGER,
    timeout_ms INTEGER DEFAULT 30000,
    
    -- Tool behavior flags
    is_deterministic BOOLEAN DEFAULT TRUE,
    is_stateless BOOLEAN DEFAULT TRUE,
    supports_async BOOLEAN DEFAULT FALSE,
    
    -- Implementation details
    implementation_type VARCHAR(50) NOT NULL DEFAULT 'python_class',
    implementation_path VARCHAR(500),
    implementation_config JSONB,
    
    -- Metadata
    author VARCHAR(255),
    tags TEXT[],
    documentation_url TEXT,
    example_usage TEXT,
    
    -- Status and lifecycle
    status VARCHAR(50) DEFAULT 'active',
    is_public BOOLEAN DEFAULT TRUE,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deprecated_at TIMESTAMP,
    
    CONSTRAINT valid_status CHECK (status IN ('active', 'deprecated', 'archived', 'draft')),
    CONSTRAINT valid_implementation_type CHECK (implementation_type IN ('python_class', 'api_endpoint', 'webhook', 'script'))
);

-- Tool parameters schema (normalized for better querying)
CREATE TABLE IF NOT EXISTS tool_parameters (
    id SERIAL PRIMARY KEY,
    tool_id INTEGER REFERENCES tools(id) ON DELETE CASCADE,
    parameter_name VARCHAR(255) NOT NULL,
    parameter_type VARCHAR(100) NOT NULL,
    description TEXT,
    is_required BOOLEAN DEFAULT FALSE,
    default_value TEXT,
    validation_rules JSONB,
    order_index INTEGER DEFAULT 0,
    
    UNIQUE(tool_id, parameter_name)
);

-- Tool usage tracking
CREATE TABLE IF NOT EXISTS tool_usage_logs (
    id SERIAL PRIMARY KEY,
    tool_id INTEGER REFERENCES tools(id) ON DELETE SET NULL,
    session_id INTEGER REFERENCES shaping_sessions(id) ON DELETE SET NULL,
    workflow_execution_id INTEGER,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    execution_time_ms INTEGER,
    status VARCHAR(50),
    error_message TEXT,
    input_params JSONB,
    output_result JSONB,
    
    CONSTRAINT valid_status CHECK (status IN ('success', 'error', 'timeout', 'cancelled'))
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_tools_category ON tools(category);
CREATE INDEX IF NOT EXISTS idx_tools_status ON tools(status);
CREATE INDEX IF NOT EXISTS idx_tools_tags ON tools USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_tool_usage_tool_id ON tool_usage_logs(tool_id);
CREATE INDEX IF NOT EXISTS idx_tool_usage_session_id ON tool_usage_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_tool_parameters_tool_id ON tool_parameters(tool_id);

COMMENT ON TABLE tools IS 'Tool library for workflow builder - stores all available tools';
COMMENT ON TABLE tool_parameters IS 'Normalized tool parameters for better querying and validation';
COMMENT ON TABLE tool_usage_logs IS 'Tracks tool usage for analytics and debugging';



