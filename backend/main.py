import asyncio
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.conversation.router import router as conversation_router
from app.initializers import initialize_agents, initialize_profiles, initialize_super_admin
from app.media.router import router as media_router
from app.profiles.router import router as profiles_router
from app.preferences.router import router as preferences_router
from app.study_plans.router import router as study_plans_router
from app.users.router import router as users_router
from database.connection import close_db, init_db
from database.migrations.run import apply_migrations_async
from schedulers import start_model_price_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialise the connection pool before anything else touches the DB.
    init_db()

    await apply_migrations_async()
    await initialize_super_admin()
    await initialize_agents()
    await initialize_profiles()

    asyncio.create_task(start_model_price_scheduler())

    yield

    # Gracefully drain the connection pool on shutdown.
    await close_db()


app = FastAPI(lifespan=lifespan)

# ── CORS ─────────────────────────────────────────────────────────────────────
# In production set ALLOWED_ORIGINS to a comma-separated list of origins,
# e.g. "https://app.example.com,https://www.example.com".
# Leaving it unset keeps "*" for local development only.
_raw_origins = os.getenv("ALLOWED_ORIGINS", "")
_allowed_origins: list[str] = (
    [o.strip() for o in _raw_origins.split(",") if o.strip()]
    if _raw_origins
    else ["*"]
)
# "allow_credentials=True" with allow_origins=["*"] is rejected by browsers;
# only enable credentials when origins are explicitly restricted.
_allow_credentials = _allowed_origins != ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(conversation_router)
app.include_router(media_router)
app.include_router(profiles_router)
app.include_router(preferences_router)
app.include_router(study_plans_router)
app.include_router(users_router)
