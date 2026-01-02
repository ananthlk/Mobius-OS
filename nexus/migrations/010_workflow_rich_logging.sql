-- Migration 010: Workflow Rich Logging
-- Purpose: Complete audit trail for the Shaping -> Planning -> Execution pipeline

-- 1. Enhanced Session Tracking
-- Replaces (or augments) the simple 'workflow_problem_identification' table
CREATE TABLE IF NOT EXISTS shaping_sessions (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    status TEXT NOT NULL, -- 'GATHERING', 'PLANNING', 'APPROVED', 'EXECUTING', 'COMPLETED'
    
    -- The State of the Consultant
    consultant_strategy TEXT, -- 'EVIDENCE_BASED', 'TABULA_RASA', 'CREATIVE'
    rag_citations JSONB DEFAULT '[]', -- References to manuals/history used
    
    -- The State of the Planner
    draft_plan JSONB DEFAULT '{}', -- The evolving plan shown on Left Rail
    final_recipe JSONB, -- The compiled AgentRecipe object
    
    transcript JSONB DEFAULT '[]', -- The chat history
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. LLM Trace Logs (The "Black Box" Recorder)
-- Captures the exact inputs and outputs of every LLM call for debugging and tuning
CREATE TABLE IF NOT EXISTS llm_trace_logs (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES shaping_sessions(id),
    
    -- Context
    module TEXT NOT NULL, -- 'Consultant', 'Planner', 'Auditor'
    operation TEXT NOT NULL, -- 'generate_strategy', 'update_draft', 'synthesize'
    
    -- The Payload
    model_config JSONB NOT NULL, -- { "model": "gemini-2.5-flash", "temp": 0.2 }
    system_prompt TEXT,
    user_prompt TEXT,
    
    -- The Result
    llm_response TEXT,
    token_usage JSONB, -- { "input": 100, "output": 50 }
    latency_ms INTEGER,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Execution Links
-- Links the execution of a recipe back to the session that created it
ALTER TABLE workflow_executions 
ADD COLUMN shaping_session_id INTEGER REFERENCES shaping_sessions(id);
