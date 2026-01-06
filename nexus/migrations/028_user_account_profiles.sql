-- Migration 028: User Account Profiles
-- Purpose: Store user preferences, settings, and metadata for user accounts
-- Note: This is separate from the user_profiles table which stores patient data

CREATE TABLE IF NOT EXISTS user_account_profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    preferences JSONB DEFAULT '{}', -- Flexible preferences storage
    settings JSONB DEFAULT '{}', -- User settings
    metadata JSONB DEFAULT '{}', -- Additional metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add comments for documentation
COMMENT ON TABLE user_account_profiles IS 'User account profiles for preferences and settings (separate from patient profiles)';
COMMENT ON COLUMN user_account_profiles.preferences IS 'User preferences (e.g., notification settings, UI preferences)';
COMMENT ON COLUMN user_account_profiles.settings IS 'User account settings';
COMMENT ON COLUMN user_account_profiles.metadata IS 'Additional user metadata';

-- Note: Communication preferences are already stored in user_communication_preferences table
-- This table extends that functionality with additional preferences and settings



