DELETE FROM "ai"."local_voice" WHERE model_id IN (SELECT id FROM "ai"."model" WHERE openrouter_id IN ('local:faster-whisper', 'local:kokoro'));
DROP TABLE IF EXISTS "ai"."local_voice";
DELETE FROM "ai"."model" WHERE openrouter_id IN ('local:faster-whisper', 'local:kokoro');
