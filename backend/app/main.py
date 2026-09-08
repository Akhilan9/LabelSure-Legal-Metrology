from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.rule_repository import router as repository_router
from app.api.analysis import router as analysis_router
from app.api.rules import router as rules_router
from app.api.review import router as review_router
from app.api.reports import router as reports_router
from app.api.context import router as context_router
from app.api.extraction import router as extraction_router
from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.dev_access import router as dev_router
from app.api.health import router
from app.api.inspections import router as inspections_router
from app.api.inspection_center import router as inspection_center_router
from app.core.config import Settings
from app.db.session import build_engine, build_session_factory


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.engine = build_engine(settings.database_url)
        app.state.session_factory = build_session_factory(app.state.engine)
        try:
            yield
        finally:
            app.state.engine.dispose()

    app = FastAPI(title="LabelSure API", version="0.3.0", lifespan=lifespan,
                  description="APEX · SIH26034 · Inspection Creation and Evidence Ingestion")
    app.state.settings = settings
    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Pydantic's default error inputs can echo a submitted password.
        return JSONResponse(status_code=422, content={"detail": [
            {"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]}
            for error in exc.errors()
        ]})

    @app.middleware("http")
    async def add_security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    if settings.environment in {"development", "test"}:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                           allow_credentials=False,
                           allow_methods=["GET", "POST", "PATCH", "DELETE"],
                           allow_headers=["Authorization", "Content-Type"])
    app.include_router(router, prefix="/api/v1", tags=["System"])
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(repository_router, prefix="/api/v1")
    app.include_router(analysis_router, prefix="/api/v1")
    app.include_router(extraction_router, prefix="/api/v1")
    app.include_router(context_router, prefix="/api/v1")
    app.include_router(rules_router, prefix="/api/v1")
    app.include_router(review_router, prefix="/api/v1")
    app.include_router(reports_router, prefix="/api/v1")
    app.include_router(inspections_router, prefix="/api/v1")
    app.include_router(inspection_center_router, prefix="/api/v1")
    app.include_router(dashboard_router, prefix="/api/v1")
    if settings.environment in {"development", "test"}:
        app.include_router(dev_router, prefix="/api/v1")
    return app


app = create_app()
