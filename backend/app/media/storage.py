import uuid
from pathlib import Path

import aiofiles

from utils import get_env_var, project_root


MEDIA_BUCKET = "_s3"


def media_root() -> Path:
    configured = get_env_var("S3_MEDIA_ROOT")
    if configured:
        return Path(configured)
    fallback = get_env_var("LOCAL_MEDIA_ROOT")
    if fallback:
        return Path(fallback) / "_s3"
    return Path(project_root) / "_s3"


def file_destination(user_id: int, extension: str) -> tuple[str, str, Path]:
    file_uuid = uuid.uuid4()
    filename = f"{file_uuid}.{extension.lower().strip('.') or 'bin'}"
    subpath = f"{user_id}/{filename}"
    destination = media_root() / subpath
    return str(file_uuid), subpath, destination


async def save_user_media(data: bytes, user_id: int, extension: str) -> tuple[str, str]:
    _, subpath, destination = file_destination(user_id, extension)
    destination.parent.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(destination, "wb") as file:
        await file.write(data)

    return MEDIA_BUCKET, subpath


async def delete_user_media(subpath: str) -> bool:
    destination = media_root() / subpath
    if destination.exists():
        destination.unlink()
        return True
    return False
