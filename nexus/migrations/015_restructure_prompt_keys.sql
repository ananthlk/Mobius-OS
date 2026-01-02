-- Migration 015: Restructure Prompt Key System
-- Purpose: Change from MODULE:STRATEGY:SUB_LEVEL to MODULE:DOMAIN:MODE:STEP structure

-- 1. Add new columns
ALTER TABLE prompt_templates 
ADD COLUMN IF NOT EXISTS domain VARCHAR(50),
ADD COLUMN IF NOT EXISTS mode VARCHAR(50),
ADD COLUMN IF NOT EXISTS step VARCHAR(50);

-- 2. Rename existing columns (keep old ones temporarily for safety)
-- Note: We'll drop old columns after migration is complete
-- For now, we keep both old and new columns

-- 3. Update indexes to include domain
DROP INDEX IF EXISTS idx_module_strategy;
DROP INDEX IF EXISTS idx_active_prompts;
DROP INDEX IF EXISTS unique_active_prompt;

CREATE INDEX IF NOT EXISTS idx_module_domain_mode_step 
ON prompt_templates(module_name, domain, mode, step);

CREATE INDEX IF NOT EXISTS idx_active_prompts_new 
ON prompt_templates(module_name, domain, mode, step) 
WHERE is_active = true;

-- 4. New unique constraint for active prompts (one active version per key)
CREATE UNIQUE INDEX IF NOT EXISTS unique_active_prompt_new 
ON prompt_templates(module_name, domain, mode, step) 
WHERE is_active = true;

-- 5. Delete all existing prompts (fresh start per requirements)
-- NOTE: These DELETE statements were removed because this migration runs on every startup.
-- If you need to clear prompts, do it manually or create a separate one-time migration.
-- DELETE FROM prompt_history;
-- DELETE FROM prompt_templates;

-- 6. Update prompt_key column comment to reflect new structure
COMMENT ON COLUMN prompt_templates.prompt_key IS 'Format: MODULE:DOMAIN:MODE:STEP (e.g., workflow:eligibility:TABULA_RASA:gate)';
COMMENT ON COLUMN prompt_templates.domain IS 'Domain: eligibility, crm, etc.';
COMMENT ON COLUMN prompt_templates.mode IS 'Mode: TABULA_RASA, EVIDENCE_BASED, REPLICATION, etc.';
COMMENT ON COLUMN prompt_templates.step IS 'Step: gate, clarification, planning, etc.';

