import json
from datetime import datetime, timezone
from typing import Any

from app.conversation.openrouter import OpenRouterClient, OpenRouterError
from app.media.extraction import extract_text
from app.media.storage import delete_user_media, save_user_media
from database.connection import DatabaseConnection
from database.models.base import User
from database.operations.ai import AgentRepository, ModelRepository
from database.operations.content import MediaRepository


MAX_UPLOAD_SIZE = 70 * 1024 * 1024


async def process_media_upload(
    user: User,
    content: bytes,
    filename: str,
    content_type: str | None,
    name: str | None,
) -> dict[str, Any]:
    if len(content) > MAX_UPLOAD_SIZE:
        raise ValueError("File exceeds 70 MB limit.")

    display_name = (name or filename).strip() or "untitled"
    extension = _extension(filename)

    extracted_text = extract_text(content, filename)
    describer_input = _build_describer_input(
        filename=filename,
        content_type=content_type or "application/octet-stream",
        size=len(content),
        extracted_text=extracted_text,
    )

    description_data = await _describe(describer_input)
    written_description = description_data.get("written_description", "")
    embedding_description = description_data.get("embedding_description", "")

    embedding: list[float] | None = None
    if embedding_description:
        embedding = await _embed(embedding_description)

    bucket, subpath = await save_user_media(content, user.id, extension)

    description_json = json.dumps(
        {
            "written_description": written_description,
            "embedding_description": embedding_description,
            "content_type": description_data.get("content_type", ""),
            "language": description_data.get("language", ""),
            "key_topics": description_data.get("key_topics", []),
            "complexity": description_data.get("complexity", ""),
            "extracted_text": extracted_text[:2000],
        },
        ensure_ascii=False,
    )

    async with DatabaseConnection() as conn:
        media = await MediaRepository(conn).create_user_media(
            user_id=user.id,
            name=display_name[:100],
            bucket=bucket,
            subpath=subpath,
            media_format=extension or "bin",
            description=description_json,
            embedding=embedding,
        )

    return {
        "id": media.id,
        "public_id": str(media.public_id),
        "name": media.name,
        "bucket": media.bucket,
        "subpath": media.subpath,
        "format": media.format,
        "description": json.loads(media.description) if media.description else None,
        "inserted_at": media.inserted_at.isoformat() if media.inserted_at else None,
    }


async def delete_media(user: User, media_id: str) -> bool:
    async with DatabaseConnection() as conn:
        repository = MediaRepository(conn)
        media = await repository.find_by_identifier(media_id)

        if not media:
            return False

        if not user.is_admin and media.user_id != user.id:
            return False

        await delete_user_media(media.subpath)
        await repository.delete(media.id)

    return True


async def get_media(user: User, media_id: str) -> dict[str, Any] | None:
    async with DatabaseConnection() as conn:
        media = await MediaRepository(conn).find_by_identifier(media_id)

    if not media:
        return None

    if not user.is_admin and media.user_id != user.id:
        return None

    return _serialize(media)


async def list_user_media(user: User) -> list[dict[str, Any]]:
    async with DatabaseConnection() as conn:
        medias = await MediaRepository(conn).find_by_user(user.id)

    return [_serialize(m) for m in medias]


def _extension(filename: str) -> str:
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


def _build_describer_input(
    filename: str,
    content_type: str,
    size: int,
    extracted_text: str,
) -> str:
    lines = [
        f"Filename: {filename}",
        f"Content-Type: {content_type}",
        f"Size: {size} bytes",
    ]
    if extracted_text:
        lines.append("")
        lines.append("Extracted content:")
        lines.append(extracted_text[:8000])
    else:
        lines.append("")
        lines.append(
            "No text could be extracted from this file. "
            "Describe it based on the filename and content type."
        )
    return "\n".join(lines)


def _now_placeholder() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


async def _describe(input_text: str) -> dict[str, Any]:
    async with DatabaseConnection() as conn:
        agent = await AgentRepository(conn).find_by_name("describer")
        if not agent:
            raise RuntimeError("Describer agent not configured.")

        model = await ModelRepository(conn).find_by_id(agent.model_id)
        if not model:
            raise RuntimeError("Describer model not found.")

        prompt = agent.prompt.replace("{NOW}", _now_placeholder())
        json_schema = agent.structured_output or {}

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": input_text},
    ]

    try:
        client = OpenRouterClient()
        return await client.chat_structured(
            messages=messages,
            model=model.external_id,
            json_schema=json_schema,
            session_id=f"media-description-{datetime.now(timezone.utc).isoformat()}",
        )
    except OpenRouterError as exc:
        return {
            "written_description": f"OpenRouter description failed: {exc}",
            "embedding_description": "",
            "content_type": "unknown",
            "language": "",
            "key_topics": [],
            "complexity": "unknown",
        }


async def _embed(text: str) -> list[float]:
    async with DatabaseConnection() as conn:
        model = await ModelRepository(conn).find_first_embedding_model()
        if not model:
            raise RuntimeError("No embedding model configured.")

    client = OpenRouterClient()
    return await client.embed(text, model.external_id)


def _serialize(media) -> dict[str, Any]:
    return {
        "id": media.id,
        "public_id": str(media.public_id),
        "user_id": media.user_id,
        "name": media.name,
        "bucket": media.bucket,
        "subpath": media.subpath,
        "format": media.format,
        "description": json.loads(media.description) if media.description else None,
        "inserted_at": media.inserted_at.isoformat() if media.inserted_at else None,
    }
