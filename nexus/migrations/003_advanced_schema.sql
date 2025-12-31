-- 1. Problem Definitions (The Root Cause)
CREATE TABLE IF NOT EXISTS problem_definitions (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    domain TEXT NOT NULL, -- 'Intake', 'Billing', etc.
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Workflow Problem Identification (The Shaping Session)
CREATE TABLE IF NOT EXISTS workflow_problem_identification (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    status TEXT NOT NULL, -- 'IDENTIFYING', 'PLAN_DRAFTED', 'CONVERTED'
    transcript JSONB, -- Full chat history
    draft_plan JSONB, -- Evolving plan
    mapped_problem_id INTEGER REFERENCES problem_definitions(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Update Agent Recipes (The Solution) - Add new columns if they don't exist
-- We use DO blocks for safe column additions in Postgres
-- 3. Update Agent Recipes (The Solution) - Add new columns if they don't exist
ALTER TABLE agent_recipes ADD COLUMN IF NOT EXISTS problem_id INTEGER REFERENCES problem_definitions(id);
ALTER TABLE agent_recipes ADD COLUMN IF NOT EXISTS channel TEXT DEFAULT 'API';
ALTER TABLE agent_recipes ADD COLUMN IF NOT EXISTS metadata JSONB;
ALTER TABLE agent_recipes ADD COLUMN IF NOT EXISTS created_by TEXT;
ALTER TABLE agent_recipes ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

-- 4. Workflow Executions (The History)
CREATE TABLE IF NOT EXISTS workflow_executions (
    id SERIAL PRIMARY KEY,
    recipe_id INTEGER REFERENCES agent_recipes(id), -- Uses the existing Serial ID from agent_recipes
    user_id TEXT NOT NULL,
    status TEXT NOT NULL, -- 'SUCCESS', 'FAILURE'
    duration_ms INTEGER,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP
);

-- 5. User Activity (Sidebar History)
CREATE TABLE IF NOT EXISTS user_activity (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    module TEXT NOT NULL, -- 'CHAT', 'WORKFLOW'
    resource_id TEXT NOT NULL, -- FK logic handled by app logic for now (could be string ID)
    resource_metadata JSONB, -- Cache title/icon
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. LLM Trace Logs (Observability)
CREATE TABLE IF NOT EXISTS llm_trace_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id INTEGER REFERENCES workflow_problem_identification(id),
    step_name TEXT, -- 'DIAGNOSIS', 'SHAPING_REPLY'
    prompt_snapshot TEXT, -- Full prompt context
    raw_completion JSONB, -- Raw LLM output
    model_metadata JSONB, -- { "model": "gpt-4", "tokens": 100 }
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
