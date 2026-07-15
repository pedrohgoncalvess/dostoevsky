import asyncio
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation.providers import ensure_kokoro_model_files
from database.models.ai import Model, Voice
from database.operations.ai import ModelRepository, VoiceRepository
from database.operations.conf import UserPreferenceRepository

logger = logging.getLogger(__name__)

# Kokoro only supports a subset of the study-plan languages; fall back to English.
KOKORO_LANGUAGE_FALLBACK = "english"


async def _find_local_model(
    model_repo: ModelRepository, external_id: str
) -> Optional[Model]:
    model = await model_repo.find_by_external_id(external_id)
    if model:
        return model
    # If the local model entry is missing, pick the first matching capability.
    if "stt" in external_id:
        return await model_repo.find_first_stt_model()
    if "tts" in external_id:
        return await model_repo.find_first_tts_model()
    return None


async def _pick_default_voice(
    voice_repo: VoiceRepository,
    model_id: int,
    study_language: str,
) -> Optional[Voice]:
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
) -> Optional[str]:
    """
    Ensure the local audio assets for a study language are available.

    Downloads the Kokoro model/voices (shared across languages) on the first
    call and selects the default voice for the requested language. Other voices
    stay as selectable options without being marked as downloaded until the
    user explicitly picks one.

    Returns a short feedback message for the user when the voice had to be
    downloaded or when a fallback is used. Returns ``None`` when the voice was
    already available.
    """
    model_repo = ModelRepository(conn)
    voice_repo = VoiceRepository(conn)
    pref_repo = UserPreferenceRepository(conn)

    stt_model = await _find_local_model(model_repo, "local:faster-whisper")
    tts_model = await _find_local_model(model_repo, "local:kokoro")

    if not tts_model:
        return "Local voice model is not configured; voice chat will use cloud providers."

    default_voice = await _pick_default_voice(voice_repo, tts_model.id, study_language)
    if not default_voice:
        return f"No local voice found for {study_language}; voice chat will use cloud providers."

    voice_language = default_voice.language
    is_fallback = voice_language != study_language.lower()
    feedback: Optional[str] = None

    if not default_voice.downloaded and default_voice.download_status != "downloaded":
        if default_voice.download_status == "processing":
            logger.info("Voice %s is currently downloading by another task, waiting...", default_voice.voice_code)
            while default_voice.download_status == "processing":
                await asyncio.sleep(2)
                await conn.refresh(default_voice)
            if default_voice.download_status != "downloaded":
                return "Download failed in another task. Voice chat will use cloud providers."
        else:
            default_voice.download_status = "processing"
            await conn.commit()
            
            try:
                await asyncio.to_thread(ensure_kokoro_model_files)
            except Exception as exc:
                default_voice.download_status = "not_downloaded"
                await conn.commit()
                logger.exception("Failed to download Kokoro model files: %s", exc)
                if is_fallback:
                    return "Could not download the English fallback voice. Voice chat will use cloud providers."
                return f"Could not download the local voice for {study_language}. Voice chat will use cloud providers."

            default_voice.download_status = "downloaded"
            default_voice.downloaded = True
            await voice_repo.update(default_voice.id, {"downloaded": True, "download_status": "downloaded"})
            await conn.commit()

            if is_fallback:
                feedback = (
                    f"Downloaded the English voice as a fallback for {study_language}."
                )
            else:
                feedback = f"Downloaded the local voice for {study_language}."
    elif is_fallback:
        feedback = (
            f"{study_language.capitalize()} doesn't have a local voice yet; "
            f"using the {voice_language.capitalize()} voice as a fallback."
        )

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
    return feedback


async def ensure_local_models_for_study_plan(
    user_id: int,
    study_language: str,
) -> Optional[str]:
    """Entry point used by the study-plan creation endpoint."""
    from database.connection import DatabaseConnection

    async with DatabaseConnection() as conn:
        return await activate_language_for_user(conn, user_id, study_language)
