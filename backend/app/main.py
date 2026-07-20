"""FastAPI application factory for source development and packaged localhost use."""

from __future__ import annotations

import os
from pathlib import Path

# Pin native thread libraries before importing numpy/sklearn/xgboost modules.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

from app.runtime import (  # noqa: E402
    frontend_dist_path,
    is_frozen,
    lifespan_model_path,
    load_runtime_environment,
    public_runtime_config,
    verify_file_manifest,
)

# Auth and model modules read part of their configuration at import time.
load_runtime_environment()

from contextlib import asynccontextmanager  # noqa: E402
import threading  # noqa: E402

from fastapi import Depends, FastAPI, HTTPException, Request, status  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from app.auth import get_current_user  # noqa: E402
from app.db import database_healthcheck, init_db  # noqa: E402
from app.logging_config import get_logger  # noqa: E402
from app.model import model_load_status  # noqa: E402
from app.routers import classifier, carbon, generation, history, prognosis  # noqa: E402

logger = get_logger("ewaste.main")
_auth = [Depends(get_current_user)]


def _as_bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().casefold() in {"1", "true", "yes", "on"}


def _safe_frontend_file(frontend: Path, relative_path: str) -> Path | None:
    candidate = (frontend / relative_path).resolve()
    try:
        candidate.relative_to(frontend.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Backward-compatible default lifespan used by tests and diagnostics."""
    init_db()
    if os.getenv("EWASTE_SKIP_MODEL_PRELOAD") != "1":
        threading.Thread(
            target=classifier.warm_model,
            name="classifier-warmup",
            daemon=True,
        ).start()
    yield


def create_app(
    *,
    frontend_dir: Path | None = None,
    require_frontend: bool | None = None,
    enable_model_warmup: bool | None = None,
) -> FastAPI:
    """Create an app that can serve APIs alone or a same-origin React build."""
    frontend = Path(frontend_dir or frontend_dist_path()).resolve()
    index_file = frontend / "index.html"
    frontend_available = index_file.is_file()
    frontend_required = (
        require_frontend
        if require_frontend is not None
        else _as_bool_env("EWASTE_REQUIRE_FRONTEND", is_frozen())
    )
    warmup_enabled = (
        enable_model_warmup
        if enable_model_warmup is not None
        else os.getenv("EWASTE_SKIP_MODEL_PRELOAD") != "1"
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        init_db()

        if warmup_enabled:
            threading.Thread(
                target=classifier.warm_model,
                name="classifier-warmup",
                daemon=True,
            ).start()
        yield

    application = FastAPI(
        title="E-Waste Management Backend",
        description="Transparent e-waste decision-support and planning workflows.",
        version="3.0.0",
        lifespan=lifespan,
    )

    @application.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception(
            "Unhandled exception on %s %s: %s",
            request.method,
            request.url.path,
            type(exc).__name__,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )

    allowed_origins = [
        value.strip()
        for value in os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if value.strip()
    ]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Delete-Key"],
    )

    @application.middleware("http")
    async def response_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        if request.url.path.startswith("/assets/") and response.status_code == 200:
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif request.url.path in {"/", "/api/runtime-config"}:
            response.headers["Cache-Control"] = "no-store"
        return response

    application.include_router(prognosis.router, prefix="/api/v1", dependencies=_auth)
    application.include_router(generation.router, prefix="/api/v1", dependencies=_auth)
    application.include_router(carbon.router, prefix="/api/v1", dependencies=_auth)
    application.include_router(classifier.router, prefix="/api/v1", dependencies=_auth)
    application.include_router(history.router, prefix="/api/v1", dependencies=_auth)

    @application.get("/health/live", tags=["System"])
    async def health_live():
        return {
            "status": "online",
            "engine": "E-Waste Management v3",
            "version": "3.0.0",
        }

    @application.get("/api/runtime-config", include_in_schema=False)
    async def runtime_config():
        return JSONResponse(
            content=public_runtime_config(),
            headers={"Cache-Control": "no-store"},
        )

    @application.get("/health/ready", tags=["System"])
    async def health_ready():
        db_ready, db_error = database_healthcheck()
        auth_config = public_runtime_config()
        model_status = model_load_status()
        model_ready = (
            not warmup_enabled
            or model_status["state"] == "ready"
        )
        frontend_ready = frontend_available or not frontend_required
        lifespan_dir = lifespan_model_path()
        if os.getenv("EWASTE_SKIP_MODEL_PRELOAD") == "1":
            lifespan_ready, lifespan_errors = True, []
        else:
            lifespan_ready, lifespan_errors = verify_file_manifest(lifespan_dir)
        ready = all(
            (
                db_ready,
                auth_config["configured"],
                model_ready,
                frontend_ready,
                lifespan_ready,
            )
        )
        content = {
            "status": "ready" if ready else "not_ready",
            "components": {
                "database": {"ready": db_ready, "error": db_error},
                "authentication": {
                    "ready": auth_config["configured"],
                    "errors": auth_config["errors"],
                },
                "classifier": {
                    "ready": model_ready,
                    **model_status,
                },
                "lifespan_models": {
                    "ready": lifespan_ready,
                    "errors": lifespan_errors,
                },
                "frontend": {
                    "ready": frontend_ready,
                    "required": frontend_required,
                },
            },
        }
        return JSONResponse(
            status_code=200 if ready else 503,
            content=content,
            headers={"Cache-Control": "no-store"},
        )

    if frontend_available:
        assets = frontend / "assets"
        if assets.is_dir():
            application.mount("/assets", StaticFiles(directory=assets), name="assets")

        @application.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str):
            if full_path.startswith(("api/", "health/", "docs", "openapi.json", "redoc")):
                raise HTTPException(status_code=404, detail="Not found")

            if full_path:
                static_file = _safe_frontend_file(frontend, full_path)
                if static_file is not None:
                    return FileResponse(static_file)
                # Requests that look like missing assets should remain a 404;
                # extension-less paths are React Router deep links.
                if Path(full_path).suffix:
                    raise HTTPException(status_code=404, detail="Static file not found")
            return FileResponse(index_file, headers={"Cache-Control": "no-store"})
    else:
        @application.get("/", include_in_schema=False)
        async def root_without_frontend():
            return {
                "status": "online",
                "engine": "E-Waste Management v3",
                "version": "3.0.0",
                "frontend": "not built",
            }

    return application


app = create_app()
