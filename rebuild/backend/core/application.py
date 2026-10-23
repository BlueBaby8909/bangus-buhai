"""Application composition with lazy account resources and closed-by-default access."""
import hmac
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from backend.core.config import AuthSettings
from backend.core.security import csrf_token, valid_token
from backend.database.config import make_engine
from backend.features.accounts.errors import AuthError
from backend.features.accounts.provider import SupabaseProvider
from backend.features.accounts.router import router
from backend.features.accounts.service import AccountService
from backend.features.registry.errors import RegistryError
from backend.features.registry.router import router as registry_router, device_router
from backend.features.readings.errors import ReadingsError
from backend.features.readings.router import router as readings_router
from backend.features.readings.operations import router as reading_operations
from backend.features.commands.router import router as commands_router
from backend.features.live.router import router as live_router
from backend.features.live.service import Connections, StreamPolicy


class AccountRuntime:
    def __init__(self, settings, service=None):
        self.settings, self.service = settings, service
        self.owned = service is None
        self.lock = threading.Lock()

    def get(self):
        if self.settings is None:
            raise AuthError(503, "authentication_not_configured")
        with self.lock:
            if self.service is None:
                try:
                    engine = make_engine()
                except (RuntimeError, ValueError):
                    raise AuthError(503, "authentication_not_configured") from None
                self.service = AccountService(self.settings, engine, SupabaseProvider(self.settings))
        return self.service

    def close(self):
        if self.owned and self.service:
            self.service.provider.close()
            self.service.engine.dispose()


def failure(status, code, retry=None):
    headers = {"Cache-Control": "no-store"}
    if retry is not None:
        headers["Retry-After"] = str(retry)
    return JSONResponse({"error": {"code": code}}, status_code=status, headers=headers)


def create_app(*, settings=None, service=None, device_only=False, device_hosts=()):
    if service is not None:
        settings = service.settings
    elif settings is None:
        try:
            settings = AuthSettings.load()
        except (ValueError, OSError, UnicodeError):
            settings = None
    runtime = AccountRuntime(settings, service)

    @asynccontextmanager
    async def lifespan(app):
        yield
        runtime.close()

    app = FastAPI(title="Bangus Buhai Rebuild", lifespan=lifespan,
                  docs_url=None if device_only else "/docs",
                  redoc_url=None if device_only else "/redoc",
                  openapi_url=None if device_only else "/openapi.json")
    app.state.account_runtime = runtime
    app.state.live_policy = StreamPolicy()
    app.state.live_connections = Connections()
    if not device_only:
        app.include_router(router)
        app.include_router(registry_router)
    app.include_router(device_router)
    if not device_only:
        app.include_router(readings_router)
        app.include_router(reading_operations)
        app.include_router(commands_router)
        app.include_router(live_router)

    @app.exception_handler(AuthError)
    async def auth_error(request, error):
        return failure(error.status, error.code, error.retry_after)

    @app.exception_handler(RegistryError)
    async def registry_error(request, error):
        return failure(error.status, error.code, error.retry_after)

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request, error):
        code = "registry_unavailable" if request.url.path.startswith(("/api/device/v1/", "/api/v1/hatcheries/")) else "authentication_unavailable"
        if "/readings" in request.url.path or "/manual-readings" in request.url.path:
            code = "readings_unavailable"
        return failure(503, code)

    @app.exception_handler(ReadingsError)
    async def readings_error(request, error):
        return failure(error.status, error.code)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, error):
        # FastAPI's default details may echo the submitted password/body.
        return failure(422, "invalid_request")

    @app.middleware("http")
    async def account_boundary(request: Request, call_next):
        browser = request.url.path.startswith("/api/v1/")
        device = request.url.path.startswith("/api/device/v1/")
        if (browser or device) and request.method != "OPTIONS":
            if settings is None:
                return failure(503, "authentication_not_configured")
            if device_only and (request.url.scheme != "https" or request.url.hostname not in device_hosts):
                return failure(503, "https_required")
            if not device_only and settings.development and request.url.hostname not in ("127.0.0.1", "localhost", "::1"):
                return failure(503, "authentication_not_configured")
            if not settings.development and request.url.scheme != "https":
                return failure(503, "https_required")
            if browser and request.method not in ("GET", "HEAD"):
                if request.headers.get("Origin") not in settings.origins:
                    return failure(403, "origin_denied")
                if request.url.path != "/api/v1/auth/login":
                    token = request.cookies.get(settings.cookie_name)
                    if valid_token(token):
                        supplied = request.headers.get("X-CSRF-Token", "")
                        if not supplied.isascii() or not hmac.compare_digest(csrf_token(token), supplied):
                            return failure(403, "csrf_denied")
            if request.method not in ("GET", "HEAD"):
                login = request.url.path == "/api/v1/auth/login"
                content_type = request.headers.get("Content-Type", "").split(";", 1)[0]
                if (login or content_type) and content_type != "application/json":
                    return failure(415, "json_required")
                body = bytearray()
                async for chunk in request.stream():
                    body.extend(chunk)
                    if len(body) > (8192 if login else 16384):
                        return failure(413, "request_too_large")
                if body and content_type != "application/json":
                    return failure(415, "json_required")
                request._body = bytes(body)
        response = await call_next(request)
        if browser or device:
            response.headers["Cache-Control"] = "no-store"
        return response

    app.add_middleware(CORSMiddleware, allow_origins=list(settings.origins) if settings else [],
                       allow_credentials=True, allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
                       allow_headers=["Content-Type", "X-CSRF-Token", "Idempotency-Key", "X-BB-Passive"])
    return app
