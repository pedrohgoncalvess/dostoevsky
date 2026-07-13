import json
from pathlib import Path
from typing import Any

import yaml

from database.connection import DatabaseConnection
from database.models.ai import Agent
from database.operations.ai import AgentRepository, ModelRepository
from utils.path_config import project_root


AGENTS_CONFIG_PATH = Path(project_root) / "agents" / "agents.yaml"


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _read_file(path: Path) -> str:
    with path.open("r", encoding="utf-8") as file:
        return file.read()


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    content = _read_file(path)
    if not content.strip():
        return None
    return json.loads(content)


def _resolve_path(relative_path: str) -> Path:
    return Path(project_root) / relative_path


async def initialize_agents() -> None:
    if not AGENTS_CONFIG_PATH.exists():
        return

    config = _load_yaml(AGENTS_CONFIG_PATH)
    agents_config = config or []
    if not agents_config:
        return

    async with DatabaseConnection() as conn:
        agent_repository = AgentRepository(conn)
        model_repository = ModelRepository(conn)

        for item in agents_config:
            if not isinstance(item, dict):
                continue

            for name, metadata in item.items():
                if not isinstance(metadata, dict):
                    continue

                await _sync_agent(
                    conn,
                    agent_repository,
                    model_repository,
                    name,
                    metadata,
                )


async def _sync_agent(
    conn,
    agent_repository: AgentRepository,
    model_repository: ModelRepository,
    name: str,
    metadata: dict[str, Any],
) -> None:
    model_openrouter_id = metadata.get("model_id")
    prompt_relative_path = metadata.get("prompt_path")
    output_relative_path = metadata.get("output_path")
    description = metadata.get("description") or ""
    placeholders = metadata.get("placeholders") or []

    if not model_openrouter_id or not prompt_relative_path:
        return

    model = await model_repository.find_by_openrouter_id(model_openrouter_id)
    if not model:
        return

    prompt_path = _resolve_path(prompt_relative_path)
    output_path = _resolve_path(output_relative_path) if output_relative_path else None

    prompt = _read_file(prompt_path) if prompt_path.exists() else ""
    structured_output = _read_json(output_path) if output_path else None

    existing_agent = await agent_repository.find_by_name(name)

    if existing_agent:
        if _agent_is_up_to_date(
            existing_agent, model.id, description, prompt, structured_output, placeholders
        ):
            return

        existing_agent.model_id = model.id
        existing_agent.description = description
        existing_agent.prompt = prompt
        existing_agent.structured_output = structured_output
        existing_agent.placeholders = placeholders
        await conn.commit()
        return

    new_agent = Agent(
        model_id=model.id,
        name=name,
        description=description,
        prompt=prompt,
        structured_output=structured_output,
        placeholders=placeholders,
    )
    await agent_repository.insert(new_agent)


def _agent_is_up_to_date(
    agent: Agent,
    model_id: int,
    description: str,
    prompt: str,
    structured_output: dict[str, Any] | None,
    placeholders: list[str],
) -> bool:
    return (
        agent.model_id == model_id
        and (agent.description or "") == (description or "")
        and (agent.prompt or "") == prompt
        and agent.structured_output == structured_output
        and (agent.placeholders or []) == placeholders
    )
