-- Add Recommendation Flag
ALTER TABLE llm_models 
ADD COLUMN IF NOT EXISTS is_recommended BOOLEAN DEFAULT FALSE;
