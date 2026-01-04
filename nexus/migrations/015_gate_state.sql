-- Migration 015: Gate State Storage
-- Purpose: Add gate_state JSONB column to shaping_sessions table for Gate Engine
-- This stores the canonical GateState (summary, gates, status) separately from transcript

-- Add gate_state column to shaping_sessions
ALTER TABLE shaping_sessions 
ADD COLUMN IF NOT EXISTS gate_state JSONB DEFAULT '{}'::jsonb;

-- Add index for querying gate states (optional, but useful for analytics)
CREATE INDEX IF NOT EXISTS idx_shaping_sessions_gate_state 
ON shaping_sessions USING GIN (gate_state);

-- Add comment for documentation
COMMENT ON COLUMN shaping_sessions.gate_state IS 
'Stores GateState JSON structure: {summary, gates: {gate_key: {raw, classified}}, status: {pass, next_gate, next_query}}';



