import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .config import get_settings
from .db import SessionLocal
from .errors import install_handlers
from .routers import (audit_log, automation, auth, inquiries, notifications, projects, public, reports, services,
                      settings as settings_router, users)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_settings()  # fail fast on invalid configuration
    yield


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title="GST API", version="1.0.0", lifespan=lifespan,
                  description="Backend de Global Services Technologie (site public + administration).",
                  docs_url="/api/v1/docs", redoc_url=None, openapi_url="/api/v1/openapi.json")
    app.add_middleware(CORSMiddleware, allow_origins=s.cors_origin_list, allow_credentials=True,
                       allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
                       allow_headers=["Authorization", "Content-Type"], expose_headers=["Content-Disposition"])

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        resp = await call_next(request)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if not request.url.path.startswith("/api/v1/docs") and not request.url.path.startswith("/api/v1/openapi"):
            resp.headers.setdefault("Cache-Control", "no-store")
        if s.environment == "production":
            resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return resp

    install_handlers(app)
    api = APIRouter(prefix="/api/v1")
    for r in (auth.router, public.router, inquiries.router, projects.router, services.router, users.router,
              notifications.router, settings_router.router, reports.router, automation.router, audit_log.router):
        api.include_router(r)

    @api.get("/health", tags=["health"])
    def health():
        try:
            with SessionLocal() as db:
                db.execute(text("select 1"))
        except Exception:
            from fastapi.responses import JSONResponse
            return JSONResponse({"status": "degraded", "database": "down"}, status_code=503)
        return {"status": "ok", "database": "up"}

    app.include_router(api)
    return app


app = create_app()
