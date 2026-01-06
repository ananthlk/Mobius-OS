-- Migration 030: Gmail OAuth Tokens
-- Purpose: Store encrypted OAuth2 tokens for Gmail API access

CREATE TABLE IF NOT EXISTS gmail_oauth_tokens (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    email TEXT NOT NULL,
    encrypted_token TEXT,              -- Encrypted access token
    encrypted_refresh_token TEXT NOT NULL,  -- Encrypted refresh token (required for long-term access)
    token_uri TEXT DEFAULT 'https://oauth2.googleapis.com/token',
    client_id TEXT,
    client_secret TEXT,                -- Can be stored if needed (usually from env)
    scopes TEXT,                       -- JSON array of granted scopes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, email)
);

CREATE INDEX IF NOT EXISTS idx_gmail_oauth_user_id ON gmail_oauth_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_gmail_oauth_email ON gmail_oauth_tokens(email);



