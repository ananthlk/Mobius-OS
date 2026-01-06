-- Migration 023: Active Agent State Machine
-- Purpose: Simple state machine - only one agent active at a time
-- This simplifies routing logic in orchestrator

-- Add active_agent column to shaping_sessions
ALTER TABLE shaping_sessions 
ADD COLUMN IF NOT EXISTS active_agent TEXT; -- 'gate', 'planning', 'execution', or NULL

-- Index for fast lookup
CREATE INDEX IF NOT EXISTS idx_shaping_sessions_active_agent 
ON shaping_sessions(active_agent) 
WHERE active_agent IS NOT NULL;

-- Set default active_agent to 'gate' for existing sessions that are in GATHERING status
UPDATE shaping_sessions 
SET active_agent = 'gate' 
WHERE active_agent IS NULL AND status = 'GATHERING';

-- Set active_agent to 'planning' for existing sessions that are in PLANNING status
UPDATE shaping_sessions 
SET active_agent = 'planning' 
WHERE active_agent IS NULL AND status = 'PLANNING';

-- Set active_agent to 'execution' for existing sessions that are in EXECUTING status
UPDATE shaping_sessions 
SET active_agent = 'execution' 
WHERE active_agent IS NULL AND status = 'EXECUTING';




