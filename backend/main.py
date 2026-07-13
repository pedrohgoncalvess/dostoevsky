import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.conversation.router import router as conversation_router
from app.initializers import initialize_agents, initialize_profiles, initialize_super_admin
from app.media.router import router as media_router
from app.profiles.router import router as profiles_router
from app.study_plans.router import router as study_plans_router
from app.users.router import router as users_router
from database.migrations.run import apply_migrations_async
from schedulers import start_model_price_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    await apply_migrations_async()
    await initialize_super_admin()
    await initialize_agents()
    await initialize_profiles()

    asyncio.create_task(start_model_price_scheduler())
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(conversation_router)
app.include_router(media_router)
app.include_router(profiles_router)
app.include_router(study_plans_router)
app.include_router(users_router)
