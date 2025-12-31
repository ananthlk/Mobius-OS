-- System-Wide Audit & Soft Delete

-- 1. Generic Audit Log
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,    -- Who did it
    session_id VARCHAR(100),          -- Traceability
    action VARCHAR(50) NOT NULL,      -- CREATE, UPDATE, DELETE, VIEW, LOGIN
    resource_type VARCHAR(50) NOT NULL, -- PROVIDER, WORKFLOW, PATIENT, USER
    resource_id VARCHAR(100),         -- The ID of the modified resource
    details JSONB DEFAULT '{}'::JSONB, -- Snapshot of changes or context
    ip_address VARCHAR(50),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for searching audit logs by user or resource
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_logs(resource_type, resource_id);

-- 2. Add Soft Delete to LLM Providers (and future tables)
ALTER TABLE llm_providers 
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS created_by VARCHAR(100),
ADD COLUMN IF NOT EXISTS updated_by VARCHAR(100);

-- Note: We retain the UNIQUE(name) constraint. 
-- If a provider is soft-deleted, we might want to allow creating a new one with the same name.
-- But standard soft-delete usually keeps the conflict to prevent ambiguity in history.
-- We will keep it simple: Name must be unique even if deleted (unless we rename on delete).
