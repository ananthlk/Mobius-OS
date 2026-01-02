-- Migration: 012_fix_trace_logs_fk
-- Purpose: Point llm_trace_logs.session_id to shaping_sessions instead of workflow_problem_identification

-- 1. Drop existing constraint (name might vary, so we drop by column or try standard names)
-- Postgres usually names it matching the table: llm_trace_logs_session_id_fkey
ALTER TABLE llm_trace_logs DROP CONSTRAINT IF EXISTS llm_trace_logs_session_id_fkey;

-- 2. Add correct constraint
-- We use ON DELETE CASCADE so if a session is deleted, traces are too (or SET NULL)
ALTER TABLE llm_trace_logs 
ADD CONSTRAINT llm_trace_logs_session_id_fkey 
FOREIGN KEY (session_id) 
REFERENCES shaping_sessions(id) 
ON DELETE CASCADE;
