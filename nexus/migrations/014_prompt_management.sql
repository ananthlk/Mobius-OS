-- Migration 014: Prompt Management System
-- Purpose: Store prompt templates in PostgreSQL with versioning and history

-- 1. Prompt Templates (The Core Table)
CREATE TABLE IF NOT EXISTS prompt_templates (
    id SERIAL PRIMARY KEY,
    prompt_key VARCHAR(255) NOT NULL UNIQUE, -- 'workflow:TABULA_RASA:INITIAL_CLARIFICATION'
    module_name VARCHAR(50) NOT NULL,        -- 'workflow', 'chat', 'diary'
    strategy VARCHAR(50),                    -- 'TABULA_RASA', 'EVIDENCE_BASED', 'REPLICATION', NULL for default
    sub_level VARCHAR(50),                   -- 'INITIAL_CLARIFICATION', 'PLAN_DEVELOPMENT', etc., NULL for default
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    
    -- Prompt Structure (JSONB)
    prompt_config JSONB NOT NULL,            -- Full prompt structure including generation_config
    
    -- Metadata
    description TEXT,
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(100)
);

-- Indexes for fast lookup
CREATE INDEX IF NOT EXISTS idx_prompt_key ON prompt_templates(prompt_key);
CREATE INDEX IF NOT EXISTS idx_module_strategy ON prompt_templates(module_name, strategy, sub_level);
CREATE INDEX IF NOT EXISTS idx_active_prompts ON prompt_templates(module_name, strategy, sub_level) 
    WHERE is_active = true;

-- Unique constraint for active prompts (one active version per key)
CREATE UNIQUE INDEX IF NOT EXISTS unique_active_prompt 
    ON prompt_templates(module_name, strategy, sub_level) 
    WHERE is_active = true;

-- 2. Prompt Version History (Audit Trail)
CREATE TABLE IF NOT EXISTS prompt_history (
    id SERIAL PRIMARY KEY,
    prompt_template_id INT REFERENCES prompt_templates(id) ON DELETE CASCADE,
    prompt_key VARCHAR(255) NOT NULL,
    version INTEGER NOT NULL,
    prompt_config JSONB NOT NULL,
    changed_by VARCHAR(100),
    change_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(prompt_template_id, version)
);

CREATE INDEX IF NOT EXISTS idx_prompt_history_key ON prompt_history(prompt_key, version);

-- 3. Prompt Usage Analytics (Optional - for optimization)
CREATE TABLE IF NOT EXISTS prompt_usage (
    id SERIAL PRIMARY KEY,
    prompt_key VARCHAR(255) NOT NULL,
    session_id INT REFERENCES shaping_sessions(id) ON DELETE SET NULL,
    user_id VARCHAR(100),
    invoked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    response_quality_score NUMERIC(3,2), -- Optional: user feedback
    metadata JSONB -- Additional context
);

CREATE INDEX IF NOT EXISTS idx_prompt_usage_key ON prompt_usage(prompt_key, invoked_at);

-- 4. Add iteration tracking to shaping_sessions
ALTER TABLE shaping_sessions 
ADD COLUMN IF NOT EXISTS consultant_iteration_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS max_iterations INTEGER DEFAULT 15;



