-- initial migration
-- depends: 

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE SCHEMA IF NOT EXISTS "base";
CREATE SCHEMA IF NOT EXISTS "content";
CREATE SCHEMA IF NOT EXISTS "ai";
CREATE SCHEMA IF NOT EXISTS "conf";

CREATE TABLE "ai"."model" (
    id SERIAL,
    public_id UUID NOT NULL UNIQUE DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    evaluation TEXT,
    type VARCHAR(50) NOT NULL DEFAULT 'openrouter',
    external_id TEXT NOT NULL,
    for_embedding BOOLEAN NOT NULL,
    for_text BOOLEAN NOT NULL,
    for_tts BOOLEAN NOT NULL,
    for_stt BOOLEAN NOT NULL,
    for_planning BOOLEAN NOT NULL,
    download_status VARCHAR(20) NOT NULL DEFAULT 'completed',
    inserted_at TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    deleted_at TIMESTAMP,

    CONSTRAINT model_pk PRIMARY KEY (id)
);

CREATE TABLE "ai"."model_price" (
    valid_from TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    model_id INTEGER NOT NULL,
    input_price NUMERIC(10, 3),
    output_price NUMERIC(10, 3),

    CONSTRAINT price_pk PRIMARY KEY (valid_from, model_id),
    CONSTRAINT price_model_fk FOREIGN KEY (model_id) REFERENCES "ai"."model"(id)
);

SELECT create_hypertable('ai.model_price', 'valid_from');

INSERT INTO "ai"."model" (name, type, external_id, for_text, for_embedding, for_tts, for_planning, for_stt) VALUES
('DeepSeek: DeepSeek V4 Pro', 'openrouter', 'deepseek/deepseek-v4-pro', true, false, false, true, false),
('Qwen: Qwen3.5-Flash', 'openrouter', 'qwen/qwen3.5-flash-02-23', true, false, false, false, false),
('OpenAI: gpt-oss-safeguard-20b', 'openrouter', 'openai/gpt-oss-safeguard-20b', true, false, false, false, false),
('xAI: Grok Voice TTS 1.0', 'openrouter', 'x-ai/grok-voice-tts-1.0', false, false, true, false, false),
('Canopy Labs: Orpheus 3B', 'openrouter', 'canopylabs/orpheus-3b-0.1-ft', false, false, true, false, false),
('hexgrad: Kokoro 82M', 'openrouter', 'hexgrad/kokoro-82m', false, false, true, false, false),
('Zyphra: Zonos v0.1 Transformer', 'openrouter', 'zyphra/zonos-v0.1-transformer', false, false, true, false, false),
('Microsoft: MAI-Voice-2', 'openrouter', 'microsoft/mai-voice-2', false, false, true, false, false),
('Mistral: Voxtral Small 24B 2507', 'openrouter', 'mistralai/voxtral-small-24b-2507', false, false, false, true, true),
('Google: Gemini 2.5 Flash', 'openrouter', 'google/gemini-2.5-flash', true, false, false, true, true),
('Xiaomi: MiMo-V2.5', 'openrouter', 'xiaomi/mimo-v2.5', true, false, false, true, true),
('OpenAI: Whisper', 'openrouter', 'openai/whisper-1', false, false, false, false, true),
('BAAI: bge-m3', 'openrouter', 'baai/bge-m3', false, true, false, false, false),
('Local: Faster Whisper', 'local', 'local:faster-whisper', false, false, false, false, true),
('Local: Kokoro', 'local', 'local:kokoro', false, false, true, false, false);
-- TODO: Move this models infos to .yaml config file and insert statements to a script

CREATE TABLE "ai"."voice"(
    id SERIAL,
    public_id UUID NOT NULL DEFAULT uuid_generate_v4() UNIQUE,
    model_id INTEGER NOT NULL,
    language VARCHAR(30) NOT NULL,
    voice_code VARCHAR(50) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    downloaded BOOLEAN NOT NULL DEFAULT FALSE,
    download_status VARCHAR(20) NOT NULL DEFAULT 'not_downloaded',
    inserted_at TIMESTAMP NOT NULL DEFAULT now(),

    CONSTRAINT voice_pk PRIMARY KEY (id),
    CONSTRAINT voice_model_fk FOREIGN KEY (model_id) REFERENCES "ai"."model"(id),
    CONSTRAINT voice_unique_voice UNIQUE (model_id, language, voice_code)
);

INSERT INTO "ai"."voice" (model_id, language, voice_code, display_name, is_default, downloaded, download_status) VALUES
((SELECT id FROM "ai"."model" WHERE external_id = 'x-ai/grok-voice-tts-1.0'), 'english', 'eve', 'Eve', TRUE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'x-ai/grok-voice-tts-1.0'), 'english', 'ara', 'Ara', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'x-ai/grok-voice-tts-1.0'), 'english', 'rex', 'Rex', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'x-ai/grok-voice-tts-1.0'), 'english', 'sal', 'Sal', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'x-ai/grok-voice-tts-1.0'), 'english', 'leo', 'Leo', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'canopylabs/orpheus-3b-0.1-ft'), 'english', 'tara', 'Tara', TRUE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'canopylabs/orpheus-3b-0.1-ft'), 'english', 'leah', 'Leah', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'canopylabs/orpheus-3b-0.1-ft'), 'english', 'jess', 'Jess', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'canopylabs/orpheus-3b-0.1-ft'), 'english', 'leo', 'Leo', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'canopylabs/orpheus-3b-0.1-ft'), 'english', 'dan', 'Dan', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'canopylabs/orpheus-3b-0.1-ft'), 'english', 'mia', 'Mia', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'canopylabs/orpheus-3b-0.1-ft'), 'english', 'zac', 'Zac', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'english', 'af_alloy', 'Af Alloy', TRUE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'english', 'af_aoede', 'Af Aoede', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'english', 'af_bella', 'Af Bella', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'english', 'af_heart', 'Af Heart', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'english', 'af_jessica', 'Af Jessica', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'english', 'af_kore', 'Af Kore', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'english', 'af_nicole', 'Af Nicole', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'english', 'af_nova', 'Af Nova', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'english', 'af_river', 'Af River', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'english', 'af_sarah', 'Af Sarah', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'english', 'af_sky', 'Af Sky', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'english', 'am_adam', 'Am Adam', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'english', 'am_echo', 'Am Echo', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'english', 'am_eric', 'Am Eric', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'english', 'am_fenrir', 'Am Fenrir', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'english', 'am_liam', 'Am Liam', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'english', 'am_michael', 'Am Michael', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'english', 'am_onyx', 'Am Onyx', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'english', 'am_puck', 'Am Puck', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'english', 'am_santa', 'Am Santa', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'english', 'bf_alice', 'Bf Alice', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'english', 'bf_emma', 'Bf Emma', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'english', 'bf_isabella', 'Bf Isabella', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'english', 'bf_lily', 'Bf Lily', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'english', 'bm_daniel', 'Bm Daniel', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'english', 'bm_fable', 'Bm Fable', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'english', 'bm_george', 'Bm George', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'english', 'bm_lewis', 'Bm Lewis', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'spanish', 'ef_dora', 'Ef Dora', TRUE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'spanish', 'em_alex', 'Em Alex', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'spanish', 'em_santa', 'Em Santa', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'french', 'ff_siwis', 'Ff Siwis', TRUE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'hindi', 'hf_alpha', 'Hf Alpha', TRUE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'hindi', 'hf_beta', 'Hf Beta', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'hindi', 'hm_omega', 'Hm Omega', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'hindi', 'hm_psi', 'Hm Psi', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'italian', 'if_sara', 'If Sara', TRUE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'italian', 'im_nicola', 'Im Nicola', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'japanese', 'jf_alpha', 'Jf Alpha', TRUE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'japanese', 'jf_gongitsune', 'Jf Gongitsune', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'japanese', 'jf_nezumi', 'Jf Nezumi', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'japanese', 'jf_tebukuro', 'Jf Tebukuro', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'japanese', 'jm_kumo', 'Jm Kumo', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'portuguese', 'pf_dora', 'Pf Dora', TRUE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'portuguese', 'pm_alex', 'Pm Alex', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'portuguese', 'pm_santa', 'Pm Santa', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'mandarim', 'zf_xiaobei', 'Zf Xiaobei', TRUE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'mandarim', 'zf_xiaoni', 'Zf Xiaoni', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'mandarim', 'zf_xiaoxiao', 'Zf Xiaoxiao', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'mandarim', 'zf_xiaoyi', 'Zf Xiaoyi', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'mandarim', 'zm_yunjian', 'Zm Yunjian', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'mandarim', 'zm_yunxi', 'Zm Yunxi', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'mandarim', 'zm_yunxia', 'Zm Yunxia', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'hexgrad/kokoro-82m'), 'mandarim', 'zm_yunyang', 'Zm Yunyang', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'zyphra/zonos-v0.1-transformer'), 'english', 'american_female', 'American Female', TRUE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'zyphra/zonos-v0.1-transformer'), 'english', 'american_male', 'American Male', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'zyphra/zonos-v0.1-transformer'), 'english', 'british_female', 'British Female', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'zyphra/zonos-v0.1-transformer'), 'english', 'british_male', 'British Male', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'zyphra/zonos-v0.1-transformer'), 'english', 'random', 'Random', FALSE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'microsoft/mai-voice-2'), 'english', 'en-US-Harper:MAI-Voice-2', 'En-Us-Harper:Mai-Voice-2', TRUE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'microsoft/mai-voice-2'), 'spanish', 'es-MX-Valeria:MAI-Voice-2', 'Es-Mx-Valeria:Mai-Voice-2', TRUE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'microsoft/mai-voice-2'), 'french', 'fr-FR-Soleil:MAI-Voice-2', 'Fr-Fr-Soleil:Mai-Voice-2', TRUE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'microsoft/mai-voice-2'), 'german', 'de-DE-Klaus:MAI-Voice-2', 'De-De-Klaus:Mai-Voice-2', TRUE, TRUE, 'downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'local:kokoro'), 'english', 'af_heart', 'Af Heart', TRUE, FALSE, 'not_downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'local:kokoro'), 'english', 'af_bella', 'Af Bella', FALSE, FALSE, 'not_downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'local:kokoro'), 'english', 'af_sky', 'Af Sky', FALSE, FALSE, 'not_downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'local:kokoro'), 'english', 'am_adam', 'Am Adam', FALSE, FALSE, 'not_downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'local:kokoro'), 'english', 'bf_alice', 'Bf Alice', FALSE, FALSE, 'not_downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'local:kokoro'), 'english', 'bf_emma', 'Bf Emma', FALSE, FALSE, 'not_downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'local:kokoro'), 'english', 'bm_daniel', 'Bm Daniel', FALSE, FALSE, 'not_downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'local:kokoro'), 'spanish', 'ef_dora', 'Ef Dora', TRUE, FALSE, 'not_downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'local:kokoro'), 'spanish', 'em_alex', 'Em Alex', FALSE, FALSE, 'not_downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'local:kokoro'), 'spanish', 'em_santa', 'Em Santa', FALSE, FALSE, 'not_downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'local:kokoro'), 'french', 'ff_siwis', 'Ff Siwis', TRUE, FALSE, 'not_downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'local:kokoro'), 'hindi', 'hf_alpha', 'Hf Alpha', FALSE, FALSE, 'not_downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'local:kokoro'), 'hindi', 'hm_omega', 'Hm Omega', FALSE, FALSE, 'not_downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'local:kokoro'), 'italian', 'if_sara', 'If Sara', FALSE, FALSE, 'not_downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'local:kokoro'), 'italian', 'im_nicola', 'Im Nicola', FALSE, FALSE, 'not_downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'local:kokoro'), 'japanese', 'jf_alpha', 'Jf Alpha', FALSE, FALSE, 'not_downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'local:kokoro'), 'japanese', 'jm_kumo', 'Jm Kumo', FALSE, FALSE, 'not_downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'local:kokoro'), 'portuguese', 'pf_dora', 'Pf Dora', TRUE, FALSE, 'not_downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'local:kokoro'), 'portuguese', 'pm_alex', 'Pm Alex', FALSE, FALSE, 'not_downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'local:kokoro'), 'portuguese', 'pm_santa', 'Pm Santa', FALSE, FALSE, 'not_downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'local:kokoro'), 'mandarim', 'zf_xiaobei', 'Zf Xiaobei', FALSE, FALSE, 'not_downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'local:kokoro'), 'mandarim', 'zf_xiaoni', 'Zf Xiaoni', FALSE, FALSE, 'not_downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'local:kokoro'), 'mandarim', 'zf_xiaoxiao', 'Zf Xiaoxiao', TRUE, FALSE, 'not_downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'local:kokoro'), 'mandarim', 'zf_xiaoyi', 'Zf Xiaoyi', FALSE, FALSE, 'not_downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'local:kokoro'), 'mandarim', 'zm_yunjian', 'Zm Yunjian', FALSE, FALSE, 'not_downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'local:kokoro'), 'mandarim', 'zm_yunxi', 'Zm Yunxi', FALSE, FALSE, 'not_downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'local:kokoro'), 'mandarim', 'zm_yunxia', 'Zm Yunxia', FALSE, FALSE, 'not_downloaded'),
((SELECT id FROM "ai"."model" WHERE external_id = 'local:kokoro'), 'mandarim', 'zm_yunyang', 'Zm Yunyang', FALSE, FALSE, 'not_downloaded');


CREATE TABLE "ai"."agent"(
    id SERIAL,
    public_id UUID NOT NULL UNIQUE DEFAULT uuid_generate_v4(),
    model_id INTEGER NOT NULL,
    name VARCHAR(50) NOT NULL UNIQUE,
    prompt TEXT NOT NULL,
    description TEXT,
    placeholders TEXT[],
    structured_output JSONB,

    inserted_at TIMESTAMP NOT NULL,

    CONSTRAINT agent_pk PRIMARY KEY (id),
    CONSTRAINT agent_model_fk FOREIGN KEY (model_id) REFERENCES "ai"."model"(id)
);

CREATE TYPE "conf"."language" AS ENUM ('portuguese', 'english', 'french', 'spanish', 'russian', 'mandarim');

CREATE TABLE "base"."user" (
    id SERIAL,
    public_id UUID NOT NULL DEFAULT uuid_generate_v4() UNIQUE,
    name VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password TEXT NOT NULL,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    native_language "conf"."language" NOT NULL DEFAULT 'portuguese',

    inserted_at TIMESTAMP NOT NULL DEFAULT now(),
    deleted_at TIMESTAMP,

    CONSTRAINT user_pk PRIMARY KEY (id)
);

CREATE TABLE "base"."refresh" (
    id SERIAL,
    public_id UUID NOT NULL DEFAULT uuid_generate_v4() UNIQUE,
    user_id INTEGER NOT NULL,
    token UUID NOT NULL UNIQUE,
    used BOOLEAN DEFAULT FALSE,

    inserted_at TIMESTAMP NOT NULL,

    CONSTRAINT refresh_pk PRIMARY KEY (id),
    CONSTRAINT refresh_user_fk FOREIGN KEY (user_id) REFERENCES "base"."user"(id)
);

CREATE TYPE "conf"."model_type" AS ENUM ('local', 'openrouter');

CREATE TABLE "conf"."user_preference"(
    id SERIAL,
    public_id UUID NOT NULL DEFAULT uuid_generate_v4() UNIQUE,
    user_id INTEGER NOT NULL,
    model_type "conf"."model_type" NOT NULL DEFAULT 'openrouter',
    tts_model_id INTEGER,
    stt_model_id INTEGER,
    planning_model_id INTEGER,
    voice VARCHAR(20),

    inserted_at TIMESTAMP NOT NULL,

    CONSTRAINT user_preference_pk PRIMARY KEY (id),
    CONSTRAINT user_preference_user_fk FOREIGN KEY (user_id) REFERENCES "base"."user"(id),
    CONSTRAINT user_preference_tts_model_id_fk FOREIGN KEY (tts_model_id) REFERENCES "ai"."model"(id),
    CONSTRAINT user_preference_stt_model_id_fk FOREIGN KEY (stt_model_id) REFERENCES "ai"."model"(id),
    CONSTRAINT user_preference_planning_model_id_fk FOREIGN KEY (planning_model_id) REFERENCES "ai"."model"(id)
);

CREATE TABLE "conf"."user_agent_preference"(
    id SERIAL,
    public_id UUID NOT NULL DEFAULT uuid_generate_v4() UNIQUE,
    agent_id INTEGER NOT NULL,
    model_id INTEGER NOT NULL,

    inserted_at TIMESTAMP NOT NULL,

    CONSTRAINT user_agent_preference_pk PRIMARY KEY (id),
    CONSTRAINT user_agent_preference_agent_fk FOREIGN KEY (agent_id) REFERENCES "ai"."agent"(id),
    CONSTRAINT user_agent_preference_model_fk FOREIGN KEY (model_id) REFERENCES "ai"."model"(id)
);

CREATE TYPE "conf"."knowledge_level" AS ENUM ('a2', 'a1', 'b2', 'b1', 'c2', 'c1');

CREATE TABLE "conf"."study_plan"(
    id SERIAL,
    public_id UUID NOT NULL DEFAULT uuid_generate_v4() UNIQUE,
    user_id INTEGER NOT NULL,
    study_language "conf"."language" NOT NULL,
    self_declared_level "conf"."knowledge_level" NOT NULL,
    goal TEXT,
    setup_completed BOOLEAN NOT NULL DEFAULT FALSE,

    inserted_at TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP,

    CONSTRAINT study_plan_pk PRIMARY KEY (id),
    CONSTRAINT study_plan_user_fk FOREIGN KEY (user_id) REFERENCES "base"."user"(id)
);

CREATE TABLE "base"."profile"(
    id SERIAL,
    public_id UUID NOT NULL DEFAULT uuid_generate_v4() UNIQUE,
    user_id INTEGER,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT NOT NULL UNIQUE,
    prompt TEXT,
    teacher_context BOOLEAN NOT NULL DEFAULT TRUE,
    tip TEXT,

    inserted_at TIMESTAMP NOT NULL,

    CONSTRAINT profile_pk PRIMARY KEY (id),
    CONSTRAINT profile_user_fk FOREIGN KEY (user_id) REFERENCES "base"."user"(id)
);

CREATE TABLE "content"."media"(
    id SERIAL,
    public_id UUID NOT NULL DEFAULT uuid_generate_v4() UNIQUE,
    user_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    bucket VARCHAR(50) NOT NULL,
    subpath VARCHAR(80) NOT NULL,
    format VARCHAR(10) NOT NULL,
    transcription TEXT,
    description TEXT,
    embedding VECTOR(1024),

    inserted_at TIMESTAMP NOT NULL,

    CONSTRAINT media_pk PRIMARY KEY (id),
    CONSTRAINT media_user_fk FOREIGN KEY (user_id) REFERENCES "base"."user"(id)
);

CREATE TABLE "content"."interaction"(
    id SERIAL,
    public_id UUID NOT NULL DEFAULT uuid_generate_v4() UNIQUE,
    profile_id INTEGER NOT NULL,
    study_plan_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    plan_id INTEGER,
    name VARCHAR(70),
    initial_context TEXT,
    need_tip BOOLEAN NOT NULL DEFAULT FALSE,

    inserted_at TIMESTAMP NOT NULL,

    CONSTRAINT interaction_pk PRIMARY KEY (id),
    CONSTRAINT interaction_profile_fk FOREIGN KEY (profile_id) REFERENCES "base"."profile"(id),
    CONSTRAINT interaction_user_fk FOREIGN KEY (user_id) REFERENCES "base"."user"(id),
    CONSTRAINT interaction_study_plan_fk FOREIGN KEY (study_plan_id) REFERENCES "conf"."study_plan"(id)
);

CREATE TABLE "content"."interaction_media"(
    id SERIAL,
    public_id UUID NOT NULL DEFAULT uuid_generate_v4() UNIQUE,
    interaction_id INTEGER NOT NULL,
    media_id INTEGER NOT NULL,
    instruction TEXT,

    inserted_at TIMESTAMP NOT NULL,

    CONSTRAINT interaction_media_pk PRIMARY KEY (id),
    CONSTRAINT interaction_media_media_fk FOREIGN KEY (media_id) REFERENCES "content"."media"(id),
    CONSTRAINT interaction_media_interaction_fk FOREIGN KEY (interaction_id) REFERENCES "content"."interaction"(id)
);

CREATE TABLE "content"."message"(
    id SERIAL,
    public_id UUID NOT NULL DEFAULT uuid_generate_v4() UNIQUE,
    interaction_id INTEGER NOT NULL,
    media_id INTEGER,
    sent_by VARCHAR(10) NOT NULL,
    content TEXT,
    tip TEXT,
    correction TEXT,

    inserted_at TIMESTAMP NOT NULL,

    CONSTRAINT message_pk PRIMARY KEY (id),
    CONSTRAINT message_interaction_fk FOREIGN KEY (interaction_id) REFERENCES "content"."interaction"(id),
    CONSTRAINT message_media_fk FOREIGN KEY (media_id) REFERENCES "content"."media"(id)
);
