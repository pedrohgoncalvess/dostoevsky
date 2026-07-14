-- local audio models
-- depends: 20260712_01_vby31-profile-prompt

INSERT INTO "ai"."model" (name, openrouter_id, for_text, for_embedding, for_tts, for_stt, for_planning, voices) VALUES
('Local: Faster Whisper', 'local:faster-whisper', false, false, false, true, false, null),
('Local: Kokoro', 'local:kokoro', false, false, true, false, false, ARRAY['af_heart', 'af_bella', 'af_sky', 'am_adam']);
