-- Migration 033: Eligibility V2 Tables
-- Purpose: Create tables for Eligibility Agent V2 case management, scoring, and LLM call logging

-- 1. Eligibility Cases (The Core Table)
CREATE TABLE IF NOT EXISTS eligibility_cases (
    id SERIAL PRIMARY KEY,
    case_uuid TEXT NOT NULL,
    case_id TEXT NOT NULL,
    session_id INTEGER,
    status TEXT NOT NULL DEFAULT 'INIT',
    case_state JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for eligibility_cases
CREATE INDEX IF NOT EXISTS idx_eligibility_cases_case_id ON eligibility_cases(case_id);
CREATE INDEX IF NOT EXISTS idx_eligibility_cases_session_id ON eligibility_cases(session_id);
CREATE INDEX IF NOT EXISTS idx_eligibility_cases_status ON eligibility_cases(status);

-- 2. Eligibility Score Runs (Scoring History)
CREATE TABLE IF NOT EXISTS eligibility_score_runs (
    id SERIAL PRIMARY KEY,
    case_pk INTEGER NOT NULL REFERENCES eligibility_cases(id) ON DELETE CASCADE,
    turn_id INTEGER,
    scoring_version TEXT NOT NULL,
    score_state JSONB NOT NULL,
    inputs_used JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for eligibility_score_runs
CREATE INDEX IF NOT EXISTS idx_eligibility_score_runs_case_pk ON eligibility_score_runs(case_pk);
CREATE INDEX IF NOT EXISTS idx_eligibility_score_runs_turn_id ON eligibility_score_runs(turn_id);
CREATE INDEX IF NOT EXISTS idx_eligibility_score_runs_created_at ON eligibility_score_runs(created_at DESC);

-- 3. Eligibility LLM Calls (LLM Call Logging)
CREATE TABLE IF NOT EXISTS eligibility_llm_calls (
    id SERIAL PRIMARY KEY,
    case_pk INTEGER NOT NULL REFERENCES eligibility_cases(id) ON DELETE CASCADE,
    turn_id INTEGER,
    call_type TEXT NOT NULL,
    prompt_hash TEXT NOT NULL,
    response_json JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for eligibility_llm_calls
CREATE INDEX IF NOT EXISTS idx_eligibility_llm_calls_case_pk ON eligibility_llm_calls(case_pk);
CREATE INDEX IF NOT EXISTS idx_eligibility_llm_calls_turn_id ON eligibility_llm_calls(turn_id);
CREATE INDEX IF NOT EXISTS idx_eligibility_llm_calls_call_type ON eligibility_llm_calls(call_type);
CREATE INDEX IF NOT EXISTS idx_eligibility_llm_calls_prompt_hash ON eligibility_llm_calls(prompt_hash);

-- 4. Eligibility Case Turns (Turn History with Plans)
CREATE TABLE IF NOT EXISTS eligibility_case_turns (
    id SERIAL PRIMARY KEY,
    case_pk INTEGER NOT NULL REFERENCES eligibility_cases(id) ON DELETE CASCADE,
    plan_response JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for eligibility_case_turns
CREATE INDEX IF NOT EXISTS idx_eligibility_case_turns_case_pk ON eligibility_case_turns(case_pk);
CREATE INDEX IF NOT EXISTS idx_eligibility_case_turns_created_at ON eligibility_case_turns(created_at DESC);
