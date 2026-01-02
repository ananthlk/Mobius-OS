-- Migration: 013_session_state
-- Purpose: State management table for orchestrator session state
-- Used by BaseOrchestrator for caching and persistence

CREATE TABLE IF NOT EXISTS session_state (
    session_id INTEGER NOT NULL,
    state_key TEXT NOT NULL,
    state_data JSONB NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (session_id, state_key),
    FOREIGN KEY (session_id) REFERENCES shaping_sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_session_state_session_id ON session_state(session_id);
CREATE INDEX IF NOT EXISTS idx_session_state_key ON session_state(state_key);


