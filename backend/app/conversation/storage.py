import uuid
from pathlib import Path

import aiofiles

from utils import get_env_var, project_root


LOCAL_MEDIA_BUCKET = "local"


def local_media_root() -> Path:
    configured = get_env_var("LOCAL_MEDIA_ROOT")
    if configured:
        return Path(configured)
    return Path(project_root) / "local_media"


async def save_interaction_media(
    data: bytes,
    user_id: int,
    interaction_id: int,
    media_format: str,
) -> tuple[str, str]:
    extension = media_format.lower().strip(".") or "bin"
    filename = f"{uuid.uuid4()}.{extension}"
    subpath = f"{user_id}/{interaction_id}/{filename}"
    destination = local_media_root() / subpath
    destination.parent.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(destination, "wb") as file:
        await file.write(data)

    return filename, subpath
