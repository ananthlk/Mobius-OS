-- Add Latency Metrics to Models
ALTER TABLE llm_models 
ADD COLUMN IF NOT EXISTS last_latency_ms INTEGER,
ADD COLUMN IF NOT EXISTS last_verified_at TIMESTAMP;
