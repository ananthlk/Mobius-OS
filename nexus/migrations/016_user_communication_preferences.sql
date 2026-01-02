-- Migration 016: User Communication Preferences
-- Purpose: Store user preferences for conversational formatting (tone, style, engagement level)

CREATE TABLE IF NOT EXISTS user_communication_preferences (
    user_id VARCHAR(100) PRIMARY KEY,
    tone VARCHAR(50) DEFAULT 'professional', -- e.g., 'professional', 'casual', 'friendly'
    style VARCHAR(50) DEFAULT 'brief',       -- e.g., 'brief', 'detailed', 'balanced'
    engagement_level VARCHAR(50) DEFAULT 'engaging', -- e.g., 'engaging', 'formal', 'neutral'
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add index for lookups (though user_id is already primary key, this is for documentation)
CREATE INDEX IF NOT EXISTS idx_user_comm_prefs_user_id ON user_communication_preferences(user_id);

-- Add comments for documentation
COMMENT ON TABLE user_communication_preferences IS 'Stores user preferences for conversational response formatting';
COMMENT ON COLUMN user_communication_preferences.tone IS 'Preferred communication tone: professional, casual, or friendly';
COMMENT ON COLUMN user_communication_preferences.style IS 'Preferred communication style: brief, detailed, or balanced';
COMMENT ON COLUMN user_communication_preferences.engagement_level IS 'Preferred engagement level: engaging, formal, or neutral';


