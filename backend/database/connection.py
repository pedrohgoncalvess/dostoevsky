"""
Async PostgreSQL Database Connection Module with SQLAlchemy

Uses a module-level engine singleton with a proper asyncpg connection pool.
Call `init_db()` once at application startup (in the FastAPI lifespan), then
use `DatabaseConnection` as a context manager everywhere else.

Environment Variables:
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
    DB_POOL_SIZE        — number of persistent connections (default: 10)
    DB_MAX_OVERFLOW     — extra connections beyond pool_size (default: 20)
    DB_POOL_TIMEOUT     — seconds to wait for a connection (default: 30)
"""
import sys

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from utils import get_env_var

# ── Windows event-loop policy ────────────────────────────────────────────────
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# ── Module-level singletons (initialised once in lifespan) ───────────────────
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db() -> None:
    """Create the global engine + session factory. Call once at startup."""
    global _engine, _session_factory

    host = get_env_var("DB_HOST")
    port = get_env_var("DB_PORT")
    user = get_env_var("DB_USER")
    password = get_env_var("DB_PASSWORD")
    db_name = get_env_var("DB_NAME")

    missing = [
        name for name, value in {
            "DB_HOST": host,
            "DB_PORT": port,
            "DB_USER": user,
            "DB_PASSWORD": password,
            "DB_NAME": db_name,
        }.items()
        if not value
    ]
    if missing:
        raise ValueError(f"Missing database environment variables: {', '.join(missing)}")

    pool_size = int(get_env_var("DB_POOL_SIZE") or "10")
    max_overflow = int(get_env_var("DB_MAX_OVERFLOW") or "20")
    pool_timeout = float(get_env_var("DB_POOL_TIMEOUT") or "30")

    url = (
        f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db_name}"
    )

    _engine = create_async_engine(
        url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_pre_ping=True,   # detect stale connections
        echo=False,
        future=True,
    )

    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def close_db() -> None:
    """Dispose the engine and release all connections. Call once at shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None


class DatabaseConnection:
    """
    Async context manager that yields a SQLAlchemy AsyncSession from the
    shared connection pool.

    Usage::

        async with DatabaseConnection() as session:
            result = await SomeRepository(session).find_by_id(1)
    """

    async def __aenter__(self) -> AsyncSession:
        if _session_factory is None:
            raise RuntimeError(
                "Database not initialised. Call init_db() before using DatabaseConnection."
            )
        self._session: AsyncSession = _session_factory()
        return self._session

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            await self._session.rollback()
        await self._session.close()
