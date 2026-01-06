-- Migration: 020_planning_phase
-- Purpose: Add planning phase state columns to shaping_sessions table

-- Add planning phase decision column
ALTER TABLE shaping_sessions 
ADD COLUMN IF NOT EXISTS planning_phase_decision VARCHAR(20) DEFAULT NULL;

-- Add planning phase approval columns
ALTER TABLE shaping_sessions 
ADD COLUMN IF NOT EXISTS planning_phase_approved BOOLEAN DEFAULT FALSE;

ALTER TABLE shaping_sessions 
ADD COLUMN IF NOT EXISTS planning_phase_approved_at TIMESTAMP WITH TIME ZONE DEFAULT NULL;

-- Add index for faster queries
CREATE INDEX IF NOT EXISTS idx_shaping_sessions_planning_decision 
ON shaping_sessions(planning_phase_decision) 
WHERE planning_phase_decision IS NOT NULL;

-- Add comment for documentation
COMMENT ON COLUMN shaping_sessions.planning_phase_decision IS 'User decision: build_new or reuse';
COMMENT ON COLUMN shaping_sessions.planning_phase_approved IS 'Whether the workflow plan has been approved';
COMMENT ON COLUMN shaping_sessions.planning_phase_approved_at IS 'Timestamp when plan was approved';





