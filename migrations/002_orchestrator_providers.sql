-- Migration 002: Replace IBM BOB orchestrator provider with Grok / Gemini / DeepSeek APIs
-- Idempotent: safe to run multiple times.

UPDATE providers SET is_enabled = 0 WHERE name = 'bob';

INSERT OR IGNORE INTO providers (
    name, display_name, provider_type, base_url, is_enabled,
    supports_streaming, supports_function_calling, max_tokens, default_model, config_schema
) VALUES
(
    'grok', 'Grok', 'llm', 'https://api.x.ai/v1', 1, 1, 1, 131072, 'grok-3',
    '{"role":"orchestrator","api_key":{"type":"string","required":true}}'
),
(
    'gemini-api', 'Gemini', 'llm', 'https://generativelanguage.googleapis.com/v1beta', 1, 1, 1, 1048576, 'gemini-2.5-pro',
    '{"role":"orchestrator","api_key":{"type":"string","required":true}}'
),
(
    'deepseek-api', 'DeepSeek', 'llm', 'https://api.deepseek.com/v1', 1, 1, 0, 65536, 'deepseek-chat',
    '{"role":"orchestrator","api_key":{"type":"string","required":true}}'
);
