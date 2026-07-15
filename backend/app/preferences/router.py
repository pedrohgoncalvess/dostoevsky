from typing import Any

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy import update as sql_update

from app.auth.services import get_current_user
from database.connection import DatabaseConnection
from database.models.ai import Agent, Model, Voice
from database.models.base import User
from database.operations.ai import AgentRepository, ModelRepository, VoiceRepository
from database.operations.base.user import UserRepository
from database.operations.conf import UserPreferenceRepository

router = APIRouter(prefix="/preferences", tags=["preferences"])


# ── helpers ───────────────────────────────────────────────────────────────────


def _model_summary(model: Model) -> dict[str, Any]:
    return {
        "id": model.id,
        "public_id": str(model.public_id),
        "name": model.name,
        "external_id": model.external_id,
        "for_stt": model.for_stt,
        "for_tts": model.for_tts,
        "for_text": model.for_text,
    }


def _model_list_item(model: Model) -> dict[str, Any]:
    return {
        "id": model.id,
        "public_id": str(model.public_id),
        "name": model.name,
        "external_id": model.external_id,
        "download_status": model.download_status,
    }


def _voice_item(voice: Voice) -> dict[str, Any]:
    return {
        "id": voice.id,
        "public_id": str(voice.public_id),
        "model_id": voice.model_id,
        "language": voice.language,
        "voice_code": voice.voice_code,
        "display_name": voice.display_name,
        "is_default": voice.is_default,
        "downloaded": voice.downloaded,
        "download_status": voice.download_status,
    }


# ── GET /preferences ──────────────────────────────────────────────────────────


@router.get("")
async def get_preferences(
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    async with DatabaseConnection() as conn:
        pref_repo = UserPreferenceRepository(conn)
        model_repo = ModelRepository(conn)

        pref = await pref_repo.find_by_user_id(user.id)

        # resolve STT model
        stt_model: dict[str, Any] | None = None
        if pref and pref.stt_model_id:
            m = await model_repo.find_by_id(pref.stt_model_id)
            stt_model = _model_summary(m) if m else None
        if stt_model is None:
            m = await model_repo.find_first_stt_model()
            stt_model = _model_summary(m) if m else None

        # resolve TTS model
        tts_model: dict[str, Any] | None = None
        if pref and pref.tts_model_id:
            m = await model_repo.find_by_id(pref.tts_model_id)
            tts_model = _model_summary(m) if m else None
        if tts_model is None:
            m = await model_repo.find_first_tts_model()
            tts_model = _model_summary(m) if m else None

        voice = pref.voice if pref else None

        return {
            "native_language": user.native_language,
            "stt_model": stt_model,
            "tts_model": tts_model,
            "voice": voice,
        }


# ── PATCH /preferences ────────────────────────────────────────────────────────


@router.patch("")
async def update_preferences(
    body: dict[str, Any],
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    stt_model_id: int | None = body.get("stt_model_id")
    tts_model_id: int | None = body.get("tts_model_id")
    voice: str | None = body.get("voice")
    native_language: str | None = body.get("native_language")

    async with DatabaseConnection() as conn:
        user_repo = UserRepository(conn)
        pref_repo = UserPreferenceRepository(conn)
        model_repo = ModelRepository(conn)

        # Update native_language on User if provided
        if native_language is not None:
            await user_repo.update(user.id, {"native_language": native_language})

        # Build preference updates
        pref_updates: dict[str, Any] = {}
        if stt_model_id is not None:
            m = await model_repo.find_by_id(stt_model_id)
            if not m:
                raise HTTPException(status_code=404, detail="STT model not found")
            pref_updates["stt_model_id"] = stt_model_id
        if tts_model_id is not None:
            m = await model_repo.find_by_id(tts_model_id)
            if not m:
                raise HTTPException(status_code=404, detail="TTS model not found")
            pref_updates["tts_model_id"] = tts_model_id
        if voice is not None:
            pref_updates["voice"] = voice

        if pref_updates:
            pref = await pref_repo.find_by_user_id(user.id)
            if pref:
                await pref_repo.update(pref.id, pref_updates)
            else:
                from database.models.conf import UserPreference
                new_pref = UserPreference(user_id=user.id, **pref_updates)
                await pref_repo.insert(new_pref)

        # commit any outstanding changes (update() already commits internally,
        # but native_language update goes through UserRepository.update which
        # also commits, so this is a safe no-op in those cases)

    return {"ok": True}


# ── GET /preferences/models ───────────────────────────────────────────────────


@router.get("/models")
async def list_models(
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    async with DatabaseConnection() as conn:
        # Query each category separately using direct SQLAlchemy selects
        # so we can use .is_(None) for deleted_at filtering.
        stt_result = await conn.execute(
            select(Model).where(Model.deleted_at.is_(None)).where(Model.for_stt.is_(True))
        )
        stt_models = stt_result.scalars().all()

        tts_result = await conn.execute(
            select(Model).where(Model.deleted_at.is_(None)).where(Model.for_tts.is_(True))
        )
        tts_models = tts_result.scalars().all()

        text_result = await conn.execute(
            select(Model).where(Model.deleted_at.is_(None)).where(Model.for_text.is_(True))
        )
        text_models = text_result.scalars().all()

    return {
        "stt": [_model_list_item(m) for m in stt_models],
        "tts": [_model_list_item(m) for m in tts_models],
        "text": [_model_list_item(m) for m in text_models],
    }


# ── GET /preferences/voices ───────────────────────────────────────────────────


@router.get("/voices")
async def list_voices(
    model_id: int | None = None,
    user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    async with DatabaseConnection() as conn:
        stmt = select(Voice)
        if model_id is not None:
            stmt = stmt.where(Voice.model_id == model_id)

        result = await conn.execute(stmt)
        voices = result.scalars().all()

    return [_voice_item(v) for v in voices]


# ── GET /preferences/agents ───────────────────────────────────────────────────


@router.get("/agents")
async def list_agents(
    user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    async with DatabaseConnection() as conn:
        agent_repo = AgentRepository(conn)
        model_repo = ModelRepository(conn)

        agents = await agent_repo.find_all()

        result: list[dict[str, Any]] = []
        for agent in agents:
            model_info: dict[str, Any] | None = None
            if agent.model_id:
                m = await model_repo.find_by_id(agent.model_id)
                if m:
                    model_info = {
                        "id": m.id,
                        "name": m.name,
                        "external_id": m.external_id,
                    }
            result.append(
                {
                    "id": agent.id,
                    "name": agent.name,
                    "description": agent.description,
                    "model": model_info,
                }
            )

    return result


# ── PATCH /preferences/agents/{agent_name} ────────────────────────────────────


@router.patch("/agents/{agent_name}")
async def update_agent_model(
    agent_name: str,
    body: dict[str, Any],
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    new_model_id: int | None = body.get("model_id")
    if new_model_id is None:
        raise HTTPException(status_code=422, detail="model_id is required")

    async with DatabaseConnection() as conn:
        model_repo = ModelRepository(conn)

        # Verify the model exists
        model = await model_repo.find_by_id(new_model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")

        # Verify the agent exists
        result = await conn.execute(select(Agent).where(Agent.name == agent_name))
        agent = result.scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
        await conn.execute(
            sql_update(Agent).where(Agent.name == agent_name).values(model_id=new_model_id)
        )
        await conn.commit()
    return {"status": "ok"}


# ── POST /preferences/audio-models/download ───────────────────────────────────


@router.post("/audio-models/download")
async def download_audio_model(
    body: dict[str, Any],
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    from app.study_plans.router import background_download_models

    model_type = body.get("type")
    
    if model_type not in ("stt", "tts"):
        raise HTTPException(status_code=422, detail="type must be 'stt' or 'tts'")

    if model_type == "tts":
        voice_code = body.get("voice_code")
        if not voice_code:
            raise HTTPException(status_code=422, detail="voice_code is required for tts")
        
        async def _download_tts(user_id: int, code: str):
            from database.connection import DatabaseConnection
            from app.conversation.local_model_manager import activate_language_for_user
            from database.operations.ai import VoiceRepository
            
            async with DatabaseConnection() as conn:
                voice = await VoiceRepository(conn).find_by_voice_code(code)
                if not voice:
                    return
                # Use activate_language_for_user to leverage the same locking and fallback logic
                await activate_language_for_user(conn, user_id, voice.language)
                
        background_tasks.add_task(_download_tts, user.id, voice_code)
        
    elif model_type == "stt":
        # we can just use the background_download_models with a dummy language 
        # or call FasterWhisper directly, but FasterWhisper is part of the study plan flow.
        async def _download_stt():
            from database.connection import DatabaseConnection
            from database.operations.ai import ModelRepository
            from app.conversation.providers import FasterWhisperSTTProvider
            import asyncio
            
            async with DatabaseConnection() as conn:
                model_repo = ModelRepository(conn)
                whisper_model = await model_repo.find_first_stt_model()
                if whisper_model and whisper_model.download_status != "downloaded":
                    if whisper_model.download_status == "processing":
                        pass
                    else:
                        whisper_model.download_status = "processing"
                        await conn.commit()
                        try:
                            await FasterWhisperSTTProvider()._ensure_model()
                            whisper_model.download_status = "downloaded"
                            await conn.commit()
                        except Exception:
                            whisper_model.download_status = "not_downloaded"
                            await conn.commit()
                            raise
        background_tasks.add_task(_download_stt)

    return {"status": "ok", "feedback": "Download started in background."}
