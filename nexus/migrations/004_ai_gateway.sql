-- AI Gateway Schema

-- 1. Providers (The "Pipes")
CREATE TABLE IF NOT EXISTS llm_providers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE, -- 'google_vertex', 'openai', 'anthropic', 'ollama'
    provider_type VARCHAR(50) NOT NULL, -- 'vertex', 'openai_compatible'
    base_url VARCHAR(255),            -- Optional override (e.g. for Ollama)
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Encrypted Configuration (The "Vault")
CREATE TABLE IF NOT EXISTS llm_config (
    id SERIAL PRIMARY KEY,
    provider_id INT REFERENCES llm_providers(id) ON DELETE CASCADE,
    config_key VARCHAR(100) NOT NULL, -- 'project_id', 'location', 'api_key' (encrypted)
    encrypted_value TEXT NOT NULL,    -- AES-GCM Ciphertext
    is_secret BOOLEAN DEFAULT true,   -- If false, value is plain text (e.g. project_id)
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Models (The "Engines")
CREATE TABLE IF NOT EXISTS llm_models (
    id SERIAL PRIMARY KEY,
    provider_id INT REFERENCES llm_providers(id) ON DELETE CASCADE,
    model_id VARCHAR(100) NOT NULL,   -- 'gemini-pro', 'gpt-4'
    display_name VARCHAR(100),
    context_window INT,
    input_cost_per_1k NUMERIC(10, 6),
    output_cost_per_1k NUMERIC(10, 6),
    is_active BOOLEAN DEFAULT true
);

-- Seed Google Vertex AI Provider (since user requested it)
INSERT INTO llm_providers (name, provider_type, base_url) 
VALUES ('google_vertex', 'vertex', 'https://us-central1-aiplatform.googleapis.com')
ON CONFLICT (name) DO NOTHING;
