-- LLM Governance Schema

-- 1. Enhance llm_models with metadata
ALTER TABLE llm_models 
ADD COLUMN IF NOT EXISTS description TEXT,
ADD COLUMN IF NOT EXISTS latency_tier VARCHAR(50), -- 'fast', 'balanced', 'complex'
ADD COLUMN IF NOT EXISTS capabilities JSONB DEFAULT '[]'::JSONB; -- ['vision', 'code']

-- 2. System Rules (Global & Module Defaults)
-- Rules set by Admins to govern which models are used where.
CREATE TABLE IF NOT EXISTS llm_system_rules (
    id SERIAL PRIMARY KEY,
    rule_type VARCHAR(20) NOT NULL, -- 'GLOBAL', 'MODULE'
    module_id VARCHAR(50) NOT NULL, -- 'all' (for global), 'chat', 'workflow', etc.
    model_id INT REFERENCES llm_models(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_system_rule UNIQUE (rule_type, module_id)
);

-- 3. User Preferences (Overrides)
-- Rules set by Users to customize their experience.
CREATE TABLE IF NOT EXISTS user_llm_preferences (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    module_id VARCHAR(50) NOT NULL DEFAULT 'all', -- 'all' = global preference, or specific module
    model_id INT REFERENCES llm_models(id) ON DELETE CASCADE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_user_pref UNIQUE (user_id, module_id)
);

-- Seed Initial Global Default (if models exist)
-- We'll rely on the Python code to seed models first, but we can restart this table clean.
