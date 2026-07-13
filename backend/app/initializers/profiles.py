from pathlib import Path
from typing import Any

import yaml

from database.connection import DatabaseConnection
from database.models.content import Profile
from database.operations.content import ProfileRepository
from utils.path_config import project_root


PROFILES_CONFIG_PATH = Path(project_root) / "profiles" / "profiles.yaml"


def _load_yaml(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or []


def _resolve_path(relative_path: str) -> Path:
    return Path(project_root) / relative_path


def _read_file(path: Path) -> str:
    with path.open("r", encoding="utf-8") as file:
        return file.read()


async def initialize_profiles() -> None:
    if not PROFILES_CONFIG_PATH.exists():
        return

    config = _load_yaml(PROFILES_CONFIG_PATH)
    if not config:
        return

    async with DatabaseConnection() as conn:
        profile_repository = ProfileRepository(conn)

        for item in config:
            if not isinstance(item, dict):
                continue

            for name, metadata in item.items():
                if not isinstance(metadata, dict):
                    continue

                await _sync_profile(
                    conn,
                    profile_repository,
                    name,
                    metadata,
                )


async def _sync_profile(
    conn,
    profile_repository: ProfileRepository,
    name: str,
    metadata: dict[str, Any],
) -> None:
    prompt_relative_path = metadata.get("prompt")
    description = metadata.get("description") or ""
    tip = metadata.get("tip") or ""
    teacher_context = bool(metadata.get("teacher_context", True))

    prompt = ""
    if prompt_relative_path:
        prompt_path = _resolve_path(prompt_relative_path)
        if prompt_path.exists():
            prompt = _read_file(prompt_path)

    existing_profile = await profile_repository.find_by_name(name)

    if existing_profile:
        if _profile_is_up_to_date(
            existing_profile, description, tip, teacher_context, prompt
        ):
            return

        existing_profile.description = description
        existing_profile.tip = tip
        existing_profile.teacher_context = teacher_context
        existing_profile.prompt = prompt
        await conn.commit()
        return

    new_profile = Profile(
        name=name,
        description=description,
        tip=tip,
        teacher_context=teacher_context,
        prompt=prompt,
    )
    await profile_repository.insert(new_profile)


def _profile_is_up_to_date(
    profile: Profile,
    description: str,
    tip: str,
    teacher_context: bool,
    prompt: str,
) -> bool:
    return (
        (profile.description or "") == description
        and (profile.tip or "") == tip
        and profile.teacher_context == teacher_context
        and (profile.prompt or "") == prompt
    )
