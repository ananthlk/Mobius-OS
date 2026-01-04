-- Migration 029: Add User ID to Missing Tables
-- Purpose: Enforce user_id across all database tables for personalization and access control

-- 1. Add user_id to llm_providers (migrate from created_by)
ALTER TABLE llm_providers 
ADD COLUMN IF NOT EXISTS user_id VARCHAR(255);

-- Migrate existing created_by values to user_id (if they exist and are valid user identifiers)
-- Note: This is a best-effort migration. Existing created_by values may not map to users table yet.

-- 2. Add user_id to llm_models (nullable, may reference provider's user_id)
ALTER TABLE llm_models 
ADD COLUMN IF NOT EXISTS user_id VARCHAR(255);

-- 3. Add user_id to agent_recipes (migrate from created_by)
ALTER TABLE agent_recipes 
ADD COLUMN IF NOT EXISTS user_id VARCHAR(255);

-- 4. Add user_id to problem_definitions
ALTER TABLE problem_definitions 
ADD COLUMN IF NOT EXISTS user_id VARCHAR(255);

-- 5. Add user_id to prompt_templates (migrate from created_by/updated_by)
ALTER TABLE prompt_templates 
ADD COLUMN IF NOT EXISTS user_id VARCHAR(255);

-- 6. Add user_id to prompt_history (migrate from changed_by)
ALTER TABLE prompt_history 
ADD COLUMN IF NOT EXISTS user_id VARCHAR(255);

-- 7. Add user_id to llm_trace_logs (derive from session_id → shaping_sessions.user_id)
ALTER TABLE llm_trace_logs 
ADD COLUMN IF NOT EXISTS user_id VARCHAR(255);

-- Update llm_trace_logs.user_id from shaping_sessions.user_id
UPDATE llm_trace_logs t
SET user_id = s.user_id
FROM shaping_sessions s
WHERE t.session_id = s.id AND t.user_id IS NULL;

-- Add indexes for user_id columns for performance
CREATE INDEX IF NOT EXISTS idx_llm_providers_user_id ON llm_providers(user_id);
CREATE INDEX IF NOT EXISTS idx_llm_models_user_id ON llm_models(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_recipes_user_id ON agent_recipes(user_id);
CREATE INDEX IF NOT EXISTS idx_problem_definitions_user_id ON problem_definitions(user_id);
CREATE INDEX IF NOT EXISTS idx_prompt_templates_user_id ON prompt_templates(user_id);
CREATE INDEX IF NOT EXISTS idx_prompt_history_user_id ON prompt_history(user_id);
CREATE INDEX IF NOT EXISTS idx_llm_trace_logs_user_id ON llm_trace_logs(user_id);

-- Add comments for documentation
COMMENT ON COLUMN llm_providers.user_id IS 'User who created/owns this provider';
COMMENT ON COLUMN llm_models.user_id IS 'User who created/owns this model';
COMMENT ON COLUMN agent_recipes.user_id IS 'User who created this recipe';
COMMENT ON COLUMN problem_definitions.user_id IS 'User who created this problem definition';
COMMENT ON COLUMN prompt_templates.user_id IS 'User who created this prompt template';
COMMENT ON COLUMN prompt_history.user_id IS 'User who made this change';
COMMENT ON COLUMN llm_trace_logs.user_id IS 'User who triggered this LLM call';

-- Note: user_id is VARCHAR(255) to match existing user_id format in other tables
-- This allows backward compatibility with existing user_id strings from Google Auth
-- Future migrations can normalize these to INTEGER foreign keys to users.id if desired

