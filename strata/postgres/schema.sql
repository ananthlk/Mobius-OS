-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table: interactions
-- Stores the raw chat history between User and Nexus (Mobius).
CREATE TABLE IF NOT EXISTS interactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL, -- Google Auth Subject ID or Email
    role VARCHAR(50) NOT NULL,     -- 'user' | 'assistant' | 'system'
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',   -- For storing context, tokens, latency
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast retrieval by user
CREATE INDEX IF NOT EXISTS idx_interactions_user_id ON interactions(user_id);
