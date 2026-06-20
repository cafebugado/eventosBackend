from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.limiter import limiter
from app.core.logging import setup_logging
from app.core.telemetry import setup_telemetry
from app.routers import audit, auth, communities, contributors, events, gallery, github, meta, tags, users

setup_logging()

app = FastAPI(
    title="Backend Eventos",
    description="API REST para agenda de eventos, integrando Supabase (DB, Auth e Storage)",
    version="0.1.0",
)

setup_telemetry(app)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(meta.router)
app.include_router(auth.router)
app.include_router(events.router)
app.include_router(tags.router)
app.include_router(users.router)
app.include_router(communities.router)
app.include_router(gallery.router)
app.include_router(contributors.router)
app.include_router(audit.router)
app.include_router(github.router)
