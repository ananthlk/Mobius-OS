-- Migration 026: Bounded Plan State and User Profiles
-- Purpose: Add bounded plan state columns to shaping_sessions and create user_profiles table

-- 1. Add bounded plan state columns to shaping_sessions
ALTER TABLE shaping_sessions
ADD COLUMN IF NOT EXISTS bounded_plan_state JSONB DEFAULT NULL;

ALTER TABLE shaping_sessions
ADD COLUMN IF NOT EXISTS bound_plan_spec JSONB DEFAULT NULL;

-- Add comments
COMMENT ON COLUMN shaping_sessions.bounded_plan_state IS 'Session state for bounded plan generation (SessionState)';
COMMENT ON COLUMN shaping_sessions.bound_plan_spec IS 'Current BoundPlanSpec_v1 output from develop_bound_plan()';

-- 2. Create user_profiles table for synthetic patient data
CREATE TABLE IF NOT EXISTS user_profiles (
    patient_id VARCHAR(255) PRIMARY KEY,
    emr_data JSONB DEFAULT '{}',
    system_data JSONB DEFAULT '{}',
    health_plan_data JSONB DEFAULT '{}',
    availability_flags JSONB DEFAULT '{"emr": true, "system": true, "health_plan": true}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add indexes for search performance
CREATE INDEX IF NOT EXISTS idx_user_profiles_patient_id ON user_profiles(patient_id);

-- Index for name search (using GIN index for JSONB)
CREATE INDEX IF NOT EXISTS idx_user_profiles_name ON user_profiles USING GIN ((system_data->'demographics'->>'name'));

-- Index for DOB search
CREATE INDEX IF NOT EXISTS idx_user_profiles_dob ON user_profiles USING GIN ((system_data->'demographics'->>'dob'));

-- Add comments
COMMENT ON TABLE user_profiles IS 'Synthetic patient profiles with multiple views (EMR, system, health plan)';
COMMENT ON COLUMN user_profiles.emr_data IS 'Clinical data: diagnoses, medications, allergies, visits, labs, procedures';
COMMENT ON COLUMN user_profiles.system_data IS 'Demographics, preferences, local identifiers, registration info';
COMMENT ON COLUMN user_profiles.health_plan_data IS 'Insurance carrier, member ID, coverage, benefits, eligibility';
COMMENT ON COLUMN user_profiles.availability_flags IS 'Track which views are available/unavailable for testing scenarios';




