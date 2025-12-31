-- Fix Legacy Vertex IDs to Stable Versions
UPDATE llm_models 
SET model_id = 'gemini-1.5-pro-001', 
    display_name = 'Gemini 1.5 Pro (001)',
    last_latency_ms = NULL -- Reset latency to force re-benchmark
WHERE model_id = 'gemini-1.5-pro';

UPDATE llm_models 
SET model_id = 'gemini-1.5-flash-001', 
    display_name = 'Gemini 1.5 Flash (001)',
    last_latency_ms = NULL
WHERE model_id = 'gemini-2.5-flash';

UPDATE llm_models 
SET model_id = 'gemini-1.5-flash-001', 
    display_name = 'Gemini 1.5 Flash (001)',
    last_latency_ms = NULL
WHERE model_id = 'gemini-1.5-flash';
