"""App factory: lifespan, middleware, CORS, exception handlers, routers."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.endpoints import health
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import DomainError
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.db.base import Base
from app.db.session import SessionFactory, engine
from app.repositories import RefreshTokenRepository, UserRepository
from app.schemas.common import ErrorResponse
from app.services.auth_service import AuthService
import app.models  # noqa: F401  (registers tables on Base.metadata)

logger = logging.getLogger("app")


def error_response(status_code: int, code: str, message: str, details=None, headers=None) -> JSONResponse:
    body = {"error": {"code": code, "message": message, "details": details}}
    return JSONResponse(status_code=status_code, content=body, headers=headers)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Learning shortcut: create tables on startup. Real projects use Alembic migrations (see docs/DATABASE.md).
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    if settings.first_admin_email and settings.first_admin_password:
        async with SessionFactory() as session:
            await AuthService(session, UserRepository(session), RefreshTokenRepository(session)).ensure_admin(
                settings.first_admin_email, settings.first_admin_password)
            await session.commit()
    yield
    await engine.dispose()


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_handler(_: Request, exc: DomainError):
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return error_response(exc.status_code, exc.code, exc.message, exc.details, headers)

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(_: Request, exc: StarletteHTTPException):
        code = {404: "not_found", 405: "method_not_allowed", 401: "unauthorized", 403: "forbidden"}.get(
            exc.status_code, "http_error")
        return error_response(exc.status_code, code, str(exc.detail), headers=getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError):
        details = [{"field": ".".join(str(p) for p in e["loc"]), "message": e["msg"], "type": e["type"]}
                   for e in exc.errors()]
        return error_response(422, "validation_error", "Request validation failed", details)

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error rid=%s", getattr(request.state, "request_id", "-"))
        return error_response(500, "internal_error", "Internal server error")


def create_app() -> FastAPI:
    configure_logging(settings.debug)
    app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan, debug=settings.debug)
    app.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)
    app.include_router(
        api_router, prefix="/api/v1",
        responses={code: {"model": ErrorResponse} for code in (401, 403, 404, 409, 422)},
    )
    # Convenience root-level liveness/readiness for orchestrators (hidden from OpenAPI).
    app.include_router(health.router, include_in_schema=False)
    return app


app = create_app()

