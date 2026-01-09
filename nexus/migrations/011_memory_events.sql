-- Migration: 011_memory_events
-- Architecture: Live-Streaming Agent (Dual-Path)
-- Purpose: Canonical event log for all agent memory buckets.

CREATE TABLE IF NOT EXISTS memory_events (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES shaping_sessions(id) ON DELETE CASCADE,
    bucket_type VARCHAR(50) NOT NULL, -- 'THINKING', 'ARTIFACTS', 'PERSISTENCE', 'OUTPUT'
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Index for fast retrieval of session history
    CONSTRAINT fk_session_id FOREIGN KEY (session_id) REFERENCES shaping_sessions (id)
);

CREATE INDEX IF NOT EXISTS idx_memory_events_session_bucket ON memory_events(session_id, bucket_type);
