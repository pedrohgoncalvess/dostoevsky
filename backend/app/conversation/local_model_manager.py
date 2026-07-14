import asyncio
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation.providers import ensure_kokoro_model_files
from database.models.ai import LocalVoice, Model
from database.operations.ai import LocalVoiceRepository, ModelRepository
from database.operations.conf import UserPreferenceRepository

logger = logging.getLogger(__name__)

# Kokoro only supports a subset of the study-plan languages; fall back to English.
KOKORO_LANGUAGE_FALLBACK = "english"


async def _find_local_model(
    model_repo: ModelRepository, openrouter_id: str
) -> Optional[Model]:
    model = await model_repo.find_by_openrouter_id(openrouter_id)
    if model:
        return model
    # If the local model entry is missing, pick the first matching capability.
    if "stt" in openrouter_id:
        return await model_repo.find_first_stt_model()
    if "tts" in openrouter_id:
        return await model_repo.find_first_tts_model()
    return None


async def _pick_default_voice(
    voice_repo: LocalVoiceRepository,
    model_id: int,
    study_language: str,
) -> Optional[LocalVoice]:
    language = study_language.lower()
    voice = await voice_repo.find_default_by_language(model_id, language)
    if voice:
        return voice

    # Fallback to English if the study language has no Kokoro voices.
    if language != KOKORO_LANGUAGE_FALLBACK:
        voice = await voice_repo.find_default_by_language(
            model_id, KOKORO_LANGUAGE_FALLBACK
        )
    return voice


async def activate_language_for_user(
    conn: AsyncSession,
    user_id: int,
    study_language: str,
) -> Optional[LocalVoice]:
    """
    Ensure the local audio assets for a study language are available.

    Downloads the Kokoro model/voices (shared across languages) on the first
    call and selects the default voice for the requested language. Other voices
    stay as selectable options without being marked as downloaded until the
    user explicitly picks one.
    """
    model_repo = ModelRepository(conn)
    voice_repo = LocalVoiceRepository(conn)
    pref_repo = UserPreferenceRepository(conn)

    stt_model = await _find_local_model(model_repo, "local:faster-whisper")
    tts_model = await _find_local_model(model_repo, "local:kokoro")

    if not tts_model:
        logger.warning("Local TTS model not found; skipping local model activation.")
        return None

    default_voice = await _pick_default_voice(voice_repo, tts_model.id, study_language)
    if not default_voice:
        logger.warning(
            "No default voice found for language %s; skipping local model activation.",
            study_language,
        )
        return None

    # Download the shared Kokoro model + voices bin. This only hits the network
    # the first time a study plan is created.
    try:
        await asyncio.to_thread(ensure_kokoro_model_files)
    except Exception as exc:
        logger.exception("Failed to download Kokoro model files: %s", exc)
        # Do not fail study-plan creation; the user can still switch to OpenRouter.
        return None

    # Mark the default voice as the one downloaded/selected for this language.
    if not default_voice.downloaded:
        await voice_repo.mark_downloaded(default_voice.id)

    # Point the user's preferences to the local models and default voice.
    preference = await pref_repo.find_by_user_id(user_id)
    if preference:
        preference.stt_model_id = stt_model.id if stt_model else preference.stt_model_id
        preference.tts_model_id = tts_model.id
        preference.voice = default_voice.voice_code
        await conn.commit()
    else:
        from database.models.conf import UserPreference

        preference = UserPreference(
            user_id=user_id,
            stt_model_id=stt_model.id if stt_model else None,
            tts_model_id=tts_model.id,
            voice=default_voice.voice_code,
        )
        await pref_repo.insert(preference)

    logger.info(
        "Activated local audio for user %s language %s with voice %s",
        user_id,
        study_language,
        default_voice.voice_code,
    )
    return default_voice


async def ensure_local_models_for_study_plan(
    user_id: int,
    study_language: str,
) -> None:
    """Entry point used by the study-plan creation endpoint."""
    from database.connection import DatabaseConnection

    async with DatabaseConnection() as conn:
        await activate_language_for_user(conn, user_id, study_language)
