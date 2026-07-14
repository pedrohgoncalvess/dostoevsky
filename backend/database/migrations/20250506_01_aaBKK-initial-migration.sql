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
    openrouter_id TEXT NOT NULL,
    for_embedding BOOLEAN NOT NULL,
    for_text BOOLEAN NOT NULL,
    for_tts BOOLEAN NOT NULL,
    for_stt BOOLEAN NOT NULL,
    for_planning BOOLEAN NOT NULL,
    voices TEXT[],
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

INSERT INTO "ai"."model" (name, openrouter_id, for_text, for_embedding, for_tts, for_planning, for_stt, voices) VALUES
('DeepSeek: DeepSeek V4 Pro', 'deepseek/deepseek-v4-pro', true, false, false, true, false, null),
('Qwen: Qwen3.5-Flash', 'qwen/qwen3.5-flash-02-23', true, false, false, false, false, null),
('OpenAI: gpt-oss-safeguard-20b', 'openai/gpt-oss-safeguard-20b', true, false, false, false, false, null),
('xAI: Grok Voice TTS 1.0', 'x-ai/grok-voice-tts-1.0', false, false, true, false, false, ARRAY['eve','ara','rex','sal', 'leo']),
('Canopy Labs: Orpheus 3B', 'canopylabs/orpheus-3b-0.1-ft', false, false, true, false, false, ARRAY['tara', 'leah', 'jess', 'leo', 'dan', 'mia', 'zac']),
('hexgrad: Kokoro 82M', 'hexgrad/kokoro-82m', false, false, true, false, false, ARRAY['af_alloy','af_aoede','af_bella','af_heart','af_jessica','af_kore','af_nicole','af_nova','af_river','af_sarah','af_sky','am_adam','am_echo','am_eric','am_fenrir','am_liam','am_michael','am_onyx','am_puck','am_santa','bf_alice','bf_emma','bf_isabella','bf_lily','bm_daniel','bm_fable','bm_george','bm_lewis','ef_dora','em_alex','em_santa','ff_siwis','hf_alpha','hf_beta','hm_omega','hm_psi','if_sara','im_nicola','jf_alpha','jf_gongitsune','jf_nezumi','jf_tebukuro','jm_kumo','pf_dora','pm_alex','pm_santa','zf_xiaobei','zf_xiaoni','zf_xiaoxiao','zf_xiaoyi','zm_yunjian','zm_yunxi','zm_yunxia','zm_yunyang']),
('Zyphra: Zonos v0.1 Transformer', 'zyphra/zonos-v0.1-transformer', false, false, true, false, false, ARRAY['american_female','american_male','british_female','british_male','random']),
('Microsoft: MAI-Voice-2', 'microsoft/mai-voice-2', false, false, true, false, false, ARRAY['en-US-Harper:MAI-Voice-2','es-MX-Valeria:MAI-Voice-2','fr-FR-Soleil:MAI-Voice-2','de-DE-Klaus:MAI-Voice-2']),
('Mistral: Voxtral Small 24B 2507', 'mistralai/voxtral-small-24b-2507', false, false, false, true, true, null),
('Google: Gemini 2.5 Flash', 'google/gemini-2.5-flash', true, false, false, true, true, null),
('Xiaomi: MiMo-V2.5', 'xiaomi/mimo-v2.5', true, false, false, true, true, null),
('OpenAI: Whisper', 'openai/whisper-1', false, false, false, false, true, null),
('BAAI: bge-m3', 'baai/bge-m3', false, true, false, false, false, null);
-- TODO: Move this models infos to .yaml config file and insert statements to a script

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

    inserted_at TIMESTAMP NOT NULL,

    CONSTRAINT message_pk PRIMARY KEY (id),
    CONSTRAINT message_interaction_fk FOREIGN KEY (interaction_id) REFERENCES "content"."interaction"(id),
    CONSTRAINT message_media_fk FOREIGN KEY (media_id) REFERENCES "content"."media"(id)
);
