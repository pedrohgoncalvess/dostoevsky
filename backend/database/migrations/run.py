import asyncio
from pathlib import Path

from yoyo import get_backend, read_migrations

from utils import get_env_var
from utils.path_config import project_root


MIGRATIONS_DIR = Path(project_root) / "database" / "migrations"


def _build_database_url() -> str:
    host = get_env_var("DB_HOST")
    port = get_env_var("DB_PORT")
    user = get_env_var("DB_USER")
    password = get_env_var("DB_PASSWORD")
    db_name = get_env_var("DB_NAME")

    missing = [name for name, value in {
        "DB_HOST": host,
        "DB_PORT": port,
        "DB_USER": user,
        "DB_PASSWORD": password,
        "DB_NAME": db_name,
    }.items() if not value]

    if missing:
        raise ValueError(f"Missing database environment variables: {', '.join(missing)}")

    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db_name}"


def apply_migrations() -> None:
    database_url = _build_database_url()
    backend = get_backend(database_url)
    migrations = read_migrations(str(MIGRATIONS_DIR))
    backend.apply_migrations(backend.to_apply(migrations))


async def apply_migrations_async() -> None:
    await asyncio.to_thread(apply_migrations)
