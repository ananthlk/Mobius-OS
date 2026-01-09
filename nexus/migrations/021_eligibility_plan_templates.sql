-- Migration 021: Eligibility Plan Templates
-- Purpose: Store deterministic plan templates for eligibility workflows
-- Follows module:domain:strategy:step pattern

CREATE TABLE IF NOT EXISTS eligibility_plan_templates (
    id SERIAL PRIMARY KEY,
    template_key VARCHAR(255) NOT NULL UNIQUE,
    module_name VARCHAR(50) NOT NULL DEFAULT 'workflow',
    domain VARCHAR(50) NOT NULL DEFAULT 'eligibility',
    strategy VARCHAR(50) NOT NULL DEFAULT 'TABULA_RASA',
    step VARCHAR(50) DEFAULT 'template',
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Template Structure (JSONB)
    template_config JSONB NOT NULL,
    
    -- Metadata
    match_pattern JSONB,
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_template_key ON eligibility_plan_templates(template_key);
CREATE INDEX IF NOT EXISTS idx_active_templates ON eligibility_plan_templates(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_template_path ON eligibility_plan_templates(module_name, domain, strategy, step);

COMMENT ON TABLE eligibility_plan_templates IS 'Stores deterministic plan templates for eligibility workflows following module:domain:strategy:step pattern';
COMMENT ON COLUMN eligibility_plan_templates.template_config IS 'Contains phases, steps, tool mappings';
COMMENT ON COLUMN eligibility_plan_templates.match_pattern IS 'Pattern to match gate states or context for this template';







