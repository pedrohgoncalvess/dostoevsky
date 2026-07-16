import asyncio
import base64
import binascii
import json
import logging
import time
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import jwt
from fastapi import APIRouter, Body, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.services import ALGORITHM, SECRET_KEY, get_current_user
from app.conversation.audio import analyze_noise
from app.conversation.openrouter import OpenRouterClient, OpenRouterError
from app.conversation.providers import AudioProviderFactory
from app.conversation.storage import LOCAL_MEDIA_BUCKET, save_interaction_media
from database.connection import DatabaseConnection
from database.models.ai import Model
from database.models.base import User
from database.models.content import Interaction, Media, Message
from database.operations.ai import AgentRepository, ModelRepository
from database.operations.base import UserRepository
from database.operations.conf import StudyPlanRepository, UserPreferenceRepository
from database.operations.content import (
    InteractionMediaRepository,
    InteractionRepository,
    MediaRepository,
    MessageRepository,
    ProfileRepository,
)
from log import logger as struct_logger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversation")


DEFAULT_CHAT_MODEL = "qwen/qwen3.5-flash-02-23"
DEFAULT_PLANNING_MODEL = "deepseek/deepseek-r1"
DEFAULT_STT_MODEL = "google/gemini-2.5-flash"
DEFAULT_TTS_MODEL = "canopylabs/orpheus-3b-0.1-ft"
DEFAULT_TTS_VOICE = "tara"
DEFAULT_TTS_FORMAT = "pcm"


# Maximum audio buffer size per WebSocket session (bytes). Clients that
# stream more than this before committing will have their buffer cleared.
MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB

# Seconds of inactivity after which an idle WebSocket is closed.
WS_IDLE_TIMEOUT = 120  # 2 minutes

audio_factory = AudioProviderFactory()

from dataclasses import dataclass

SYSTEM_PROMPT = (
    "You are a concise language-learning conversation partner. "
    "Keep replies natural, short, and useful for spoken practice."
)

@dataclass
class AudioTurnState:
    user_message_id: int | None = None


@router.websocket("/ws")
async def conversation_ws(websocket: WebSocket) -> None:
    token = _extract_token(websocket)
    user = await _authenticate_user(token)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    try:
        async with DatabaseConnection() as conn:
            interaction = await _resolve_interaction(conn, user, dict(websocket.query_params))
    except ValueError as exc:
        await websocket.send_json({"type": "error", "detail": str(exc)})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    audio_format = websocket.query_params.get("audio_format", "wav")
    language = websocket.query_params.get("language")
    paused = False
    audio_buffer = bytearray()
    
    processing_task: asyncio.Task | None = None
    processing_audio = bytearray()
    turn_state = AudioTurnState()

    await websocket.send_json(
        {
            "type": "ready",
            "interaction_id": interaction.id,
            "interaction_public_id": str(interaction.public_id),
            "audio_format": audio_format,
        }
    )

    try:
        while True:
            try:
                message = await asyncio.wait_for(
                    websocket.receive(), timeout=WS_IDLE_TIMEOUT
                )
            except asyncio.TimeoutError:
                await websocket.send_json(
                    {"type": "error", "detail": "Connection closed due to inactivity."}
                )
                await websocket.close()
                break

            if message["type"] == "websocket.disconnect":
                break

            if message.get("bytes") is not None:
                if not paused:
                    chunk: bytes = message["bytes"]
                    if processing_task and not processing_task.done():
                        processing_task.cancel()
                        audio_buffer = processing_audio + audio_buffer
                        processing_audio = bytearray()
                        await websocket.send_json({"type": "processing_cancelled"})

                    if len(audio_buffer) + len(chunk) > MAX_AUDIO_BYTES:
                        await websocket.send_json(
                            {"type": "error", "detail": "Audio buffer limit exceeded."}
                        )
                        audio_buffer.clear()
                    else:
                        audio_buffer.extend(chunk)
                continue

            if message.get("text") is None:
                continue

            payload = _loads_json(message["text"])
            event_type = payload.get("type")

            if event_type in {"audio", "audio_chunk"}:
                if not paused:
                    try:
                        chunk = _decode_audio_payload(payload)
                        if chunk:
                            if processing_task and not processing_task.done():
                                processing_task.cancel()
                                audio_buffer = processing_audio + audio_buffer
                                processing_audio = bytearray()
                                await websocket.send_json({"type": "processing_cancelled"})

                            if len(audio_buffer) + len(chunk) > MAX_AUDIO_BYTES:
                                await websocket.send_json(
                                    {"type": "error", "detail": "Audio buffer limit exceeded."}
                                )
                                audio_buffer.clear()
                            else:
                                audio_buffer.extend(chunk)
                    except ValueError as exc:
                        await websocket.send_json({"type": "error", "detail": str(exc)})
                continue

            if event_type == "pause":
                paused = True
                audio_buffer.clear()
                await websocket.send_json(
                    {
                        "type": "paused",
                        "interaction_id": interaction.id,
                        "interaction_public_id": str(interaction.public_id),
                    }
                )
                continue

            if event_type == "resume":
                async with DatabaseConnection() as conn:
                    interaction = await _resolve_interaction(conn, user, payload)
                paused = False
                await websocket.send_json(
                    {
                        "type": "resumed",
                        "interaction_id": interaction.id,
                        "interaction_public_id": str(interaction.public_id),
                    }
                )
                continue

            if event_type == "commit":
                if paused:
                    await websocket.send_json({"type": "error", "detail": "Conversation is paused."})
                    continue

                commit_format = payload.get("audio_format") or audio_format
                commit_language = payload.get("language") or language
                
                if processing_task and not processing_task.done():
                    processing_task.cancel()
                    
                processing_audio = bytearray(audio_buffer)
                audio_buffer.clear()

                processing_task = asyncio.create_task(
                    _process_audio_turn(
                        websocket=websocket,
                        user=user,
                        interaction_id=interaction.id,
                        interaction=interaction,
                        audio=bytes(processing_audio),
                        audio_format=commit_format,
                        language=commit_language,
                        state=turn_state,
                    )
                )
                continue

            if event_type == "close":
                await websocket.close()
                break

            await websocket.send_json({"type": "error", "detail": "Unsupported websocket event."})
    except WebSocketDisconnect:
        return


async def _resolve_audio_models(
    conn: AsyncSession, user_id: int
) -> tuple[Model, Model, str]:
    """Pick STT/TTS models and voice from user preference or local defaults."""
    pref = await UserPreferenceRepository(conn).find_by_user_id(user_id)
    model_repo = ModelRepository(conn)

    stt_model: Model | None = None
    if pref and pref.stt_model_id:
        stt_model = await model_repo.find_by_id(pref.stt_model_id)
    if not stt_model:
        stt_model = await model_repo.find_by_external_id("local:faster-whisper")
    if not stt_model:
        stt_model = await model_repo.find_first_stt_model()
    if not stt_model:
        stt_model = SimpleNamespace(external_id=DEFAULT_STT_MODEL)  # type: ignore[assignment]

    tts_model: Model | None = None
    if pref and pref.tts_model_id:
        tts_model = await model_repo.find_by_id(pref.tts_model_id)
    if not tts_model:
        tts_model = await model_repo.find_by_external_id("local:kokoro")
    if not tts_model:
        tts_model = await model_repo.find_first_tts_model()
    if not tts_model:
        tts_model = SimpleNamespace(external_id=DEFAULT_TTS_MODEL)  # type: ignore[assignment]

    tts_voice = (pref.voice if pref else None) or DEFAULT_TTS_VOICE
    return stt_model, tts_model, tts_voice  # type: ignore[return-value]


async def _process_audio_turn(
    websocket: WebSocket,
    user: User,
    interaction_id: int,
    interaction: Interaction,
    audio: bytes,
    audio_format: str,
    language: str | None,
    state: AudioTurnState,
) -> None:
    if not audio:
        await websocket.send_json({"type": "error", "detail": "No audio received before commit."})
        return

    turn_start_time = time.perf_counter()


    vad_start = time.perf_counter()
    noise = analyze_noise(audio, audio_format)
    vad_time = time.perf_counter() - vad_start

    if noise.get("is_noise"):
        await websocket.send_json({"type": "noise_detected", "noise": noise})
        # Save a lightweight record only for diagnostic purposes — no media file.
        async with DatabaseConnection() as conn:
            await _save_message(conn, interaction_id, "user", "", None, "noise_detected", "")
        return


    async with DatabaseConnection() as conn:
        media = await _save_media_record(
            conn,
            user_id=user.id,
            interaction_id=interaction_id,
            data=audio,
            media_format=audio_format,
            transcription=None,
            description=json.dumps({"source": "user", "noise": noise}),
        )
        await _link_media(conn, interaction_id, media.id, "user_audio")

    await websocket.send_json({"type": "user_audio_saved", "media_id": media.id, "noise": noise})


    tts_format = DEFAULT_TTS_FORMAT

    try:
        async with DatabaseConnection() as conn:
            stt_model, tts_model, tts_voice = await _resolve_audio_models(conn, user.id)

        stt_provider = audio_factory.stt_provider(stt_model)
        stt_start = time.perf_counter()
        transcription = await stt_provider.transcribe(audio, audio_format, language)
        stt_time = time.perf_counter() - stt_start
    except Exception as exc:
        logger.exception("STT failed for interaction %s", interaction_id)
        await websocket.send_json({"type": "error", "detail": f"STT failed: {exc}"})
        return

    async with DatabaseConnection() as conn:
        await _update_media_transcription(conn, media.id, transcription)
        
        if state.user_message_id:
            await MessageRepository(conn).update(
                state.user_message_id,
                {"content": transcription, "media_id": media.id}
            )
        else:
            msg = await _save_message(conn, interaction_id, "user", transcription, media.id, None, "")
            state.user_message_id = msg.id
            
        history, _interaction = await _build_teacher_history(conn, interaction_id)

    await websocket.send_json(
        {
            "type": "user_transcription",
            "media_id": media.id,
            "text": transcription,
        }
    )

    if not transcription.strip():
        await websocket.send_json({"type": "no_speech_detected", "media_id": media.id})
        return


    try:
        async with OpenRouterClient() as client:
            llm_start = time.perf_counter()
            assistant_text, tip, correction = await _call_teacher(client, history, interaction_id)
            llm_time = time.perf_counter() - llm_start
            
        if not assistant_text:
            await websocket.send_json({"type": "error", "detail": "Empty teacher response."})
            return

        tts_provider = audio_factory.tts_provider(tts_model, tts_voice)
        tts_start = time.perf_counter()
        assistant_audio = await tts_provider.speech(assistant_text, tts_voice, tts_format)
        tts_time = time.perf_counter() - tts_start
    except OpenRouterError as exc:
        logger.error("LLM/TTS OpenRouter error for interaction %s: %s", interaction_id, exc)
        await websocket.send_json({"type": "error", "detail": f"Teacher/TTS failed: {exc}"})
        return
    except Exception as exc:
        logger.exception("Unexpected LLM/TTS error for interaction %s", interaction_id)
        await websocket.send_json({"type": "error", "detail": f"Teacher/TTS failed: {exc}"})
        return

    async with DatabaseConnection() as conn:
        assistant_media = await _save_media_record(
            conn,
            user_id=user.id,
            interaction_id=interaction_id,
            data=assistant_audio,
            media_format=tts_format,
            transcription=assistant_text,
            description=json.dumps({"source": "assistant", "voice": tts_voice}),
        )
        await _link_media(conn, interaction_id, assistant_media.id, "assistant_audio")
        assistant_message = await _save_message(
            conn,
            interaction_id,
            "assistant",
            assistant_text,
            assistant_media.id,
            tip,
            correction,
        )

    total_time = time.perf_counter() - turn_start_time
    await struct_logger.info(
        module="conversation.router",
        info_type="ProcessingTimes",
        message=f"VAD={vad_time:.2f}s, STT={stt_time:.2f}s, LLM={llm_time:.2f}s, TTS={tts_time:.2f}s (Total = {total_time:.2f}s)"
    )

    out: dict[str, Any] = {
        "type": "assistant_message",
        "message_id": assistant_message.id,
        "media_id": assistant_media.id,
        "text": assistant_text,
        "audio": {
            "format": tts_format,
            "sample_rate": 24_000 if tts_format == "pcm" else None,
            "channels": 1 if tts_format == "pcm" else None,
        },
    }
    if interaction and interaction.need_tip:
        out["tip"] = tip
    if correction:
        out["correction"] = correction

    await websocket.send_json(out)
    await websocket.send_bytes(assistant_audio)
    await websocket.send_json({"type": "assistant_audio_end", "media_id": assistant_media.id})

    # Reset state for the next turn
    state.user_message_id = None


def _extract_token(websocket: WebSocket) -> str | None:
    query_token = websocket.query_params.get("token")
    if query_token:
        return query_token

    authorization = websocket.headers.get("authorization")
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:]
    return None


async def _authenticate_user(token: str | None) -> User | None:
    if not token:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
    except jwt.exceptions.PyJWTError:
        return None

    if not email:
        return None

    async with DatabaseConnection() as conn:
        user = await UserRepository(conn).find_by_email(email)
        if not user or user.deleted_at is not None:
            return None
        return user


async def _resolve_interaction(
    conn: AsyncSession,
    user: User,
    payload: dict[str, Any],
) -> Interaction:
    interaction_value = payload.get("interaction_id") or payload.get("interaction_public_id")
    interaction_repository = InteractionRepository(conn)
    if interaction_value:
        interaction = await interaction_repository.find_for_user_by_identifier(
            interaction_value,
            user.id,
        )
        if not interaction:
            raise ValueError("Interaction not found for this user.")
        return interaction

    profile_value = payload.get("profile_id") or payload.get("profile_public_id")
    if not profile_value:
        raise ValueError("profile_id is required to start a new interaction.")

    profile = await ProfileRepository(conn).find_by_identifier(profile_value)
    if not profile:
        raise ValueError("Profile not found.")

    study_plan = await _resolve_study_plan(conn, user.id, payload)

    return await interaction_repository.create_interaction(
        profile_id=profile.id,
        user_id=user.id,
        study_plan_id=study_plan.id,
        name=payload.get("name"),
        initial_context=payload.get("initial_context"),
    )


async def _resolve_study_plan(
    conn: AsyncSession, user_id: int, payload: dict[str, Any]
) -> Any:
    study_plan_value = payload.get("study_plan_id") or payload.get("study_plan_public_id")
    if study_plan_value:
        study_plan = await StudyPlanRepository(conn).find_by_identifier(study_plan_value)
        if not study_plan or study_plan.user_id != user_id:
            raise ValueError("Study plan not found for this user.")
        return study_plan

    study_plan = await StudyPlanRepository(conn).find_first_by_user(user_id)
    if not study_plan:
        raise ValueError("No study plan found for this user.")
    return study_plan


async def _save_media_record(
    conn: AsyncSession,
    user_id: int,
    interaction_id: int,
    data: bytes,
    media_format: str,
    transcription: str | None,
    description: str | None,
) -> Media:
    filename, subpath = await save_interaction_media(data, user_id, interaction_id, media_format)
    return await MediaRepository(conn).create_user_media(
        user_id=user_id,
        name=filename,
        bucket=LOCAL_MEDIA_BUCKET,
        subpath=subpath,
        media_format=media_format,
        transcription=transcription,
        description=description,
    )


async def _link_media(conn: AsyncSession, interaction_id: int, media_id: int, instruction: str) -> None:
    await InteractionMediaRepository(conn).create_link(interaction_id, media_id, instruction)


async def _update_media_transcription(conn: AsyncSession, media_id: int, transcription: str) -> None:
    await MediaRepository(conn).update_transcription(media_id, transcription)


async def _save_message(
    conn: AsyncSession,
    interaction_id: int,
    sent_by: str,
    content: str,
    media_id: int | None,
    tip: str | None,
    correction: str | None,
) -> Message:
    return await MessageRepository(conn).create_message(
        interaction_id=interaction_id,
        sent_by=sent_by,
        content=content,
        media_id=media_id,
        tip=tip,
        correction=correction,
    )


async def _build_teacher_history(
    conn: AsyncSession, interaction_id: int
) -> tuple[list[dict[str, str]], Interaction | None]:
    interaction_with_profile = await InteractionRepository(conn).find_with_profile(interaction_id)
    if not interaction_with_profile:
        return [{"role": "system", "content": SYSTEM_PROMPT}], None

    interaction, profile = interaction_with_profile

    # Resolve the study plan so we can inject the actual languages into the prompt.
    study_plan = None
    if interaction.study_plan_id:
        study_plan = await StudyPlanRepository(conn).find_by_id(interaction.study_plan_id)

    native_language: str | None = None
    study_language: str | None = None
    if study_plan:
        study_language = study_plan.study_language

    # Fetch the user's native language via an explicit query.
    # Accessing interaction.user would trigger a lazy load outside the async
    # greenlet context and raise sqlalchemy.exc.MissingGreenlet.
    if interaction.user_id:
        user = await UserRepository(conn).find_by_id(interaction.user_id)
        if user:
            native_language = user.native_language

    system_message = await _build_teacher_system_message(
        conn,
        profile.prompt,
        native_language=native_language,
        study_language=study_language,
    )

    history = [{"role": "system", "content": system_message}]
    history.extend(await MessageRepository(conn).build_chat_messages(interaction_id))
    return history, interaction


async def _build_teacher_system_message(
    conn: AsyncSession,
    profile_description: str,
    native_language: str | None = None,
    study_language: str | None = None,
) -> str:
    agent = await AgentRepository(conn).find_by_name("teacher")
    if not agent:
        return SYSTEM_PROMPT

    prompt = agent.prompt
    prompt = prompt.replace("{NOW}", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))
    prompt = prompt.replace("$PROFILE$", profile_description or "")
    prompt = prompt.replace("$FILES$", await _load_interaction_files(conn))
    prompt = prompt.replace(
        "$NATIVE_LANGUAGE$", native_language or "the user's native language"
    )
    prompt = prompt.replace("$STUDY_LANGUAGE$", study_language or "the target language")
    return prompt


async def _load_interaction_files(conn: AsyncSession) -> str:
    # Placeholder: when interaction-media links carry selected context files,
    # load their descriptions/transcriptions here and return a single context block.
    # Currently no file injection endpoint exists, so we return an empty block.
    return ""


async def _call_teacher(
    client: OpenRouterClient,
    history: list[dict[str, str]],
    interaction_id: int,
) -> tuple[str, str, str]:
    """Call the teacher LLM and return (response_text, tip, correction).

    DB errors and OpenRouter errors are kept separate so callers can
    distinguish between infrastructure failures and API failures.
    """
    async with DatabaseConnection() as conn:
        agent = await AgentRepository(conn).find_by_name("teacher")
        if not agent:
            text = await client.chat(history, DEFAULT_CHAT_MODEL, session_id=str(interaction_id))
            return text, "", ""

        model = await ModelRepository(conn).find_by_id(agent.model_id)
        if not model:
            text = await client.chat(history, DEFAULT_CHAT_MODEL, session_id=str(interaction_id))
            return text, "", ""

        json_schema = agent.structured_output or {}
        model_id = model.external_id

    # DB session is closed; now call the external API.
    try:
        result = await client.chat_structured(
            messages=history,
            model=model_id,
            json_schema=json_schema,
            session_id=str(interaction_id),
        )
    except OpenRouterError:
        # Structured output failed — fall back to plain chat.
        text = await client.chat(history, model_id, session_id=str(interaction_id))
        return text, "", ""

    return result.get("response", ""), result.get("tip", ""), result.get("correction", "")


def _loads_json(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _decode_audio_payload(payload: dict[str, Any]) -> bytes:
    data = payload.get("data")
    if not data:
        return b""
    if "," in data:
        data = data.split(",", 1)[1]
    try:
        return base64.b64decode(data)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Invalid base64 audio payload.") from exc




@router.post("/interactions")
async def create_interaction(
    payload: dict[str, Any],
    user: User = Depends(get_current_user),
):
    profile_public_id = payload.get("profile_public_id")
    name = payload.get("name")
    initial_context = payload.get("initial_context")
    need_tip = bool(payload.get("need_tip", False))

    async with DatabaseConnection() as conn:
        profile = await ProfileRepository(conn).find_by_identifier(profile_public_id)
        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")

        study_plan = await _resolve_study_plan(conn, user.id, payload)

        interaction = await InteractionRepository(conn).create_interaction(
            profile_id=profile.id,
            user_id=user.id,
            study_plan_id=study_plan.id,
            name=name,
            initial_context=initial_context,
            need_tip=need_tip,
        )

    return {
        "id": interaction.id,
        "public_id": str(interaction.public_id),
        "name": interaction.name.replace("_", " ").title(),
        "profile_id": interaction.profile_id,
        "profile_public_id": str(profile.public_id),
        "profile_name": profile.name.replace("_", " ").title(),
        "study_plan_id": interaction.study_plan_id,
        "study_plan_public_id": str(study_plan.public_id),
        "need_tip": interaction.need_tip,
        "inserted_at": interaction.inserted_at.isoformat() if interaction.inserted_at else None,
    }


@router.get("/interactions")
async def list_interactions(
    limit: int = 20,
    user: User = Depends(get_current_user),
):
    async with DatabaseConnection() as conn:
        interactions = await InteractionRepository(conn).find_recent_by_user(
            user_id=user.id, limit=limit
        )

        from sqlalchemy import select
        from database.models.content import InteractionMedia, Media

        # Fetch all media links for these interactions
        interaction_ids = [i.id for i in interactions]
        media_map: dict[int, list[str]] = {i.id: [] for i in interactions}
        
        if interaction_ids:
            result = await conn.execute(
                select(InteractionMedia.interaction_id, Media.public_id)
                .join(Media, Media.id == InteractionMedia.media_id)
                .where(InteractionMedia.interaction_id.in_(interaction_ids))
            )
            for row in result.all():
                media_map[row.interaction_id].append(str(row.public_id))

    return [
        {
            "id": i.id,
            "public_id": str(i.public_id),
            "name": i.name.replace("_", " ").title(),
            "profile_id": i.profile_id,
            "need_tip": i.need_tip,
            "media_ids": media_map[i.id],
            "inserted_at": i.inserted_at.isoformat() if i.inserted_at else None,
        }
        for i in interactions
    ]


@router.patch("/interactions/{interaction_id}")
async def update_interaction(
	interaction_id: str,
	payload: dict[str, Any] = Body(...),
	user: User = Depends(get_current_user),
):
	async with DatabaseConnection() as conn:
		interaction = await InteractionRepository(conn).find_for_user_by_identifier(interaction_id, user.id)
		if not interaction:
			raise HTTPException(status_code=404, detail="Interaction not found")

		update_data = {}
		if "name" in payload:
			update_data["name"] = payload["name"]
		if "need_tip" in payload:
			update_data["need_tip"] = payload["need_tip"]

		if update_data:
			await InteractionRepository(conn).update(interaction.id, update_data)

		if "media_ids" in payload:
			from sqlalchemy import delete
			from database.models.content import InteractionMedia
			
			# Remove old media links
			await conn.execute(delete(InteractionMedia).where(InteractionMedia.interaction_id == interaction.id))
			
			# Add new ones
			media_repo = InteractionMediaRepository(conn)
			for m_id in payload["media_ids"]:
				try:
					from database.operations.content.media import MediaRepository
					media_obj = await MediaRepository(conn).find_for_user_by_identifier(m_id, user.id)
					if media_obj:
						await media_repo.create_link(interaction.id, media_obj.id)
				except Exception:
					pass

		await conn.commit()

	return {"status": "ok"}


@router.delete("/interactions/{interaction_id}")
async def delete_interaction(
	interaction_id: str,
	user: User = Depends(get_current_user),
):
	async with DatabaseConnection() as conn:
		interaction = await InteractionRepository(conn).find_for_user_by_identifier(interaction_id, user.id)
		if not interaction:
			raise HTTPException(status_code=404, detail="Interaction not found")

		await InteractionRepository(conn).delete(interaction.id)
		await conn.commit()

	return {"status": "ok"}


@router.get("/interactions/{interaction_id}/messages")
async def list_messages(
    interaction_id: str,
    user: User = Depends(get_current_user),
):
    async with DatabaseConnection() as conn:
        interaction = await InteractionRepository(conn).find_for_user_by_identifier(
            interaction_id, user.id
        )
        if not interaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interaction not found.",
            )

        messages = await MessageRepository(conn).find_by_interaction_id(interaction.id)

    return [
        {
            "id": m.id,
            "public_id": str(m.public_id),
            "sent_by": m.sent_by,
            "content": m.content,
            "tip": m.tip,
            "correction": m.correction,
            "media_id": str(m.media.public_id) if m.media else None,
            "inserted_at": m.inserted_at.isoformat() if m.inserted_at else None,
        }
        for m in messages
    ]


@router.post("/interactions/{interaction_id}/messages")
async def create_text_message(
    interaction_id: str,
    payload: dict[str, Any],
    user: User = Depends(get_current_user),
):
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="text is required.",
        )

    async with DatabaseConnection() as conn:
        interaction = await InteractionRepository(conn).find_for_user_by_identifier(
            interaction_id, user.id
        )
        if not interaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interaction not found.",
            )

        await _save_message(conn, interaction.id, "user", text, None, None, "")
        history, _ = await _build_teacher_history(conn, interaction.id)
        send_tip = interaction.need_tip

    try:
        async with OpenRouterClient() as client:
            assistant_text, tip, correction = await _call_teacher(client, history, interaction.id)
    except OpenRouterError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    async with DatabaseConnection() as conn:
        assistant_message = await _save_message(
            conn,
            interaction.id,
            "assistant",
            assistant_text,
            None,
            tip,
            correction,
        )

    response: dict[str, Any] = {
        "id": assistant_message.id,
        "public_id": str(assistant_message.public_id),
        "sent_by": assistant_message.sent_by,
        "content": assistant_message.content,
        "tip": assistant_message.tip if send_tip else None,
        "inserted_at": assistant_message.inserted_at.isoformat()
        if assistant_message.inserted_at
        else None,
    }
    return response
