-- Migration: 017_journey_state
-- Purpose: Dedicated table for journey state tracking (shared by frontend and backend)
-- This provides a clean, queryable structure for progress tracking

CREATE TABLE IF NOT EXISTS journey_state (
    session_id INTEGER NOT NULL PRIMARY KEY,
    
    -- Core journey fields (matching ProgressHeader interface)
    domain TEXT,
    strategy TEXT,
    current_step TEXT,
    percent_complete NUMERIC(5, 2) DEFAULT 0.0 CHECK (percent_complete >= 0 AND percent_complete <= 100),
    status TEXT DEFAULT 'GATHERING',
    
    -- Additional metadata
    step_details JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key
    FOREIGN KEY (session_id) REFERENCES shaping_sessions(id) ON DELETE CASCADE
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_journey_state_session_id ON journey_state(session_id);
CREATE INDEX IF NOT EXISTS idx_journey_state_status ON journey_state(status);
CREATE INDEX IF NOT EXISTS idx_journey_state_domain ON journey_state(domain);

-- Add comment for documentation
COMMENT ON TABLE journey_state IS 
'Stores current journey state for workflow sessions. Updated by orchestrators and consumed by frontend ProgressHeader component.';

COMMENT ON COLUMN journey_state.domain IS 'Current domain (e.g., "eligibility", "crm")';
COMMENT ON COLUMN journey_state.strategy IS 'Current strategy (e.g., "TABULA_RASA", "EVIDENCE_BASED")';
COMMENT ON COLUMN journey_state.current_step IS 'Current step identifier (e.g., "gate_1_data_availability", "planning")';
COMMENT ON COLUMN journey_state.percent_complete IS 'Progress percentage (0.0 to 100.0)';
COMMENT ON COLUMN journey_state.status IS 'Session status (e.g., "GATHERING", "PLANNING", "APPROVED")';
COMMENT ON COLUMN journey_state.step_details IS 'Additional step metadata (e.g., completed_gates, next_gate, next_question)';






