-- local audio models and voices
-- depends: 20260712_01_vby31-profile-prompt

INSERT INTO "ai"."model" (name, openrouter_id, for_text, for_embedding, for_tts, for_stt, for_planning, voices) VALUES
('Local: Faster Whisper', 'local:faster-whisper', false, false, false, true, false, null),
('Local: Kokoro', 'local:kokoro', false, false, true, false, false, ARRAY['af_heart', 'af_bella', 'af_sky', 'am_adam', 'bf_alice', 'bf_emma', 'bm_daniel', 'ef_dora', 'em_alex', 'ff_siwis', 'hf_alpha', 'hm_omega', 'if_sara', 'im_nicola', 'jf_alpha', 'jm_kumo', 'pf_dora', 'pm_alex', 'zf_xiaoxiao', 'zm_yunxi']);

CREATE TABLE "ai"."local_voice"(
    id SERIAL,
    public_id UUID NOT NULL DEFAULT uuid_generate_v4() UNIQUE,
    model_id INTEGER NOT NULL,
    language "conf"."language" NOT NULL,
    voice_code VARCHAR(50) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    downloaded BOOLEAN NOT NULL DEFAULT FALSE,
    inserted_at TIMESTAMP NOT NULL DEFAULT now(),

    CONSTRAINT local_voice_pk PRIMARY KEY (id),
    CONSTRAINT local_voice_model_fk FOREIGN KEY (model_id) REFERENCES "ai"."model"(id),
    CONSTRAINT local_voice_unique_voice UNIQUE (model_id, language, voice_code)
);

WITH kokoro AS (
    SELECT id FROM "ai"."model" WHERE openrouter_id = 'local:kokoro'
)
INSERT INTO "ai"."local_voice" (model_id, language, voice_code, display_name, is_default) VALUES
((SELECT id FROM kokoro), 'english', 'af_heart', 'Heart (US)', true),
((SELECT id FROM kokoro), 'english', 'af_bella', 'Bella (US)', false),
((SELECT id FROM kokoro), 'english', 'af_sky', 'Sky (US)', false),
((SELECT id FROM kokoro), 'english', 'am_adam', 'Adam (US)', false),
((SELECT id FROM kokoro), 'portuguese', 'pf_dora', 'Dora (BR)', true),
((SELECT id FROM kokoro), 'portuguese', 'pm_alex', 'Alex (BR)', false),
((SELECT id FROM kokoro), 'portuguese', 'pm_santa', 'Santa (BR)', false),
((SELECT id FROM kokoro), 'french', 'ff_siwis', 'Siwis (FR)', true),
((SELECT id FROM kokoro), 'spanish', 'ef_dora', 'Dora (ES)', true),
((SELECT id FROM kokoro), 'spanish', 'em_alex', 'Alex (ES)', false),
((SELECT id FROM kokoro), 'spanish', 'em_santa', 'Santa (ES)', false),
((SELECT id FROM kokoro), 'mandarim', 'zf_xiaoxiao', 'Xiaoxiao (ZH)', true),
((SELECT id FROM kokoro), 'mandarim', 'zf_xiaoni', 'Xiaoni (ZH)', false),
((SELECT id FROM kokoro), 'mandarim', 'zm_yunxi', 'Yunxi (ZH)', false);
