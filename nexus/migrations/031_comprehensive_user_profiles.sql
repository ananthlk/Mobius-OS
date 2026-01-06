-- Migration 031: Comprehensive User Profile Schema
-- Purpose: Create detailed user profile tables with proper relationships

-- 1. Basic Profile - Personal information
CREATE TABLE IF NOT EXISTS user_basic_profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    preferred_name VARCHAR(255),
    phone VARCHAR(50),
    mobile VARCHAR(50),
    alternate_email VARCHAR(255),
    timezone VARCHAR(50) DEFAULT 'UTC',
    locale VARCHAR(10) DEFAULT 'en-US',
    avatar_url TEXT,
    bio TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE user_basic_profiles IS 'Basic personal information and contact details for users';

-- 2. Professional Profile - Work/organizational information
CREATE TABLE IF NOT EXISTS user_professional_profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    job_title VARCHAR(255),
    department VARCHAR(255),
    organization VARCHAR(255),
    manager_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    team_name VARCHAR(255),
    employee_id VARCHAR(100),
    office_location VARCHAR(255),
    start_date DATE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE user_professional_profiles IS 'Professional and organizational information for users';

-- 3. Communication Profile - Communication preferences
CREATE TABLE IF NOT EXISTS user_communication_profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    communication_style VARCHAR(50) DEFAULT 'professional',
    tone_preference VARCHAR(50) DEFAULT 'balanced',
    prompt_style_id INTEGER,
    preferred_language VARCHAR(10) DEFAULT 'en',
    response_format_preference VARCHAR(50) DEFAULT 'structured',
    notification_preferences JSONB DEFAULT '{}',
    engagement_level VARCHAR(50) DEFAULT 'engaging',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE user_communication_profiles IS 'Communication preferences and prompt style configurations';

-- 4. Use Case Profile - Workflow patterns
CREATE TABLE IF NOT EXISTS user_use_case_profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    primary_workflows JSONB DEFAULT '[]',
    workflow_frequency JSONB DEFAULT '{}',
    module_preferences JSONB DEFAULT '{}',
    task_patterns JSONB DEFAULT '[]',
    domain_expertise JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE user_use_case_profiles IS 'User workflow patterns, use cases, and module preferences';

-- 5. AI Preference Profile - AI interaction preferences with strategy links
CREATE TABLE IF NOT EXISTS user_ai_preference_profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    escalation_rules JSONB DEFAULT '{}',
    autonomy_level VARCHAR(50) DEFAULT 'balanced',
    confidence_threshold DECIMAL(3,2) DEFAULT 0.70,
    require_confirmation_for JSONB DEFAULT '[]',
    preferred_model_preferences JSONB DEFAULT '{}',
    feedback_preferences JSONB DEFAULT '{}',
    preferred_strategy VARCHAR(50),
    strategy_preferences JSONB DEFAULT '{}',
    task_category_preferences JSONB DEFAULT '{}',
    task_domain_preferences JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE user_ai_preference_profiles IS 'AI interaction preferences with links to task strategies';
COMMENT ON COLUMN user_ai_preference_profiles.preferred_strategy IS 'Preferred consultant strategy: TABULA_RASA, EVIDENCE_BASED, CREATIVE';
COMMENT ON COLUMN user_ai_preference_profiles.strategy_preferences IS 'JSONB map of preferences per strategy type';
COMMENT ON COLUMN user_ai_preference_profiles.task_category_preferences IS 'Preferences by task category (from task_catalog.classification)';
COMMENT ON COLUMN user_ai_preference_profiles.task_domain_preferences IS 'Preferences by task domain (from task_catalog.classification)';

-- 6. Query History Profile - Query patterns and statistics
CREATE TABLE IF NOT EXISTS user_query_history_profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    most_common_queries JSONB DEFAULT '[]',
    query_categories JSONB DEFAULT '{}',
    search_patterns JSONB DEFAULT '[]',
    question_templates JSONB DEFAULT '[]',
    interaction_stats JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE user_query_history_profiles IS 'Historical query patterns, most common questions, and interaction statistics';

-- 7. Query History Session Links - Junction table linking queries to sessions
CREATE TABLE IF NOT EXISTS user_query_session_links (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id INTEGER NOT NULL REFERENCES shaping_sessions(id) ON DELETE CASCADE,
    interaction_id UUID REFERENCES interactions(id) ON DELETE SET NULL,
    query_text TEXT,
    query_category VARCHAR(100),
    module VARCHAR(50),
    workflow_name VARCHAR(255),
    strategy VARCHAR(50),
    contributed_to_profile BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, session_id, interaction_id)
);

COMMENT ON TABLE user_query_session_links IS 'Junction table linking user query history to specific shaping_sessions and interactions';
COMMENT ON COLUMN user_query_session_links.strategy IS 'consultant_strategy from the session (TABULA_RASA, EVIDENCE_BASED, CREATIVE)';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_user_professional_manager ON user_professional_profiles(manager_id);
CREATE INDEX IF NOT EXISTS idx_user_professional_org ON user_professional_profiles(organization);
CREATE INDEX IF NOT EXISTS idx_user_communication_style ON user_communication_profiles(communication_style);
CREATE INDEX IF NOT EXISTS idx_user_ai_pref_strategy ON user_ai_preference_profiles(preferred_strategy);
CREATE INDEX IF NOT EXISTS idx_query_session_links_user ON user_query_session_links(user_id);
CREATE INDEX IF NOT EXISTS idx_query_session_links_session ON user_query_session_links(session_id);
CREATE INDEX IF NOT EXISTS idx_query_session_links_user_session ON user_query_session_links(user_id, session_id);
CREATE INDEX IF NOT EXISTS idx_query_session_links_strategy ON user_query_session_links(strategy);

-- Helper function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_user_profiles_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers to auto-update updated_at
CREATE TRIGGER update_user_basic_profiles_updated_at BEFORE UPDATE ON user_basic_profiles FOR EACH ROW EXECUTE FUNCTION update_user_profiles_updated_at();
CREATE TRIGGER update_user_professional_profiles_updated_at BEFORE UPDATE ON user_professional_profiles FOR EACH ROW EXECUTE FUNCTION update_user_profiles_updated_at();
CREATE TRIGGER update_user_communication_profiles_updated_at BEFORE UPDATE ON user_communication_profiles FOR EACH ROW EXECUTE FUNCTION update_user_profiles_updated_at();
CREATE TRIGGER update_user_use_case_profiles_updated_at BEFORE UPDATE ON user_use_case_profiles FOR EACH ROW EXECUTE FUNCTION update_user_profiles_updated_at();
CREATE TRIGGER update_user_ai_preference_profiles_updated_at BEFORE UPDATE ON user_ai_preference_profiles FOR EACH ROW EXECUTE FUNCTION update_user_profiles_updated_at();
CREATE TRIGGER update_user_query_history_profiles_updated_at BEFORE UPDATE ON user_query_history_profiles FOR EACH ROW EXECUTE FUNCTION update_user_profiles_updated_at();



