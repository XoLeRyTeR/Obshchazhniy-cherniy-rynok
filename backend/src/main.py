import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from starlette.staticfiles import StaticFiles

from src.api.routers import auth, catalog, chats, listings, users
from src.core.config import Settings
from src.core.errors import AppError
from src.db.database import Database

logger = logging.getLogger(__name__)


async def request_rules(request: Request):
    route = request.scope.get("route")
    if route is None or not hasattr(route, "dependant"):
        return
    allowed = set()
    for param in route.dependant.query_params:
        annotation = param.field_info.annotation
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            allowed.update(annotation.model_fields)
        else:
            allowed.add(param.alias)
    if set(request.query_params) - allowed:
        raise AppError(422, "unknown_query", "Неизвестный параметр запроса")
    if route.dependant.body_params:
        content_type = request.headers.get("content-type", "").split(";")[0].lower()
        expected = "multipart/form-data" if request.url.path.endswith("/photos") else "application/json"
        if content_type != expected:
            raise AppError(415, "content_type", "Неподдерживаемый Content-Type")


def create_app(settings: Settings | None = None, database: Database | None = None):
    settings = settings or Settings()
    settings.media_dir.mkdir(parents=True, exist_ok=True)
    database = database or Database(settings.database_url.get_secret_value())

    @asynccontextmanager
    async def lifespan(app):
        yield
        await database.close()

    app = FastAPI(title="Общажный чёрный рынок", version="0.1.0", debug=False,
                  lifespan=lifespan, dependencies=[Depends(request_rules)])
    app.state.settings, app.state.database = settings, database
    app.state.auth_buckets = {}
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                       allow_methods=["GET", "POST", "PATCH", "DELETE"],
                       allow_headers=["Authorization", "Content-Type"])

    @app.exception_handler(AppError)
    async def app_error(request, error):
        headers = {"WWW-Authenticate": "Bearer"} if error.status == 401 else {}
        if error.status == 429:
            headers["Retry-After"] = str(settings.auth_rate_window)
        return JSONResponse(status_code=error.status,
                            content={"detail": {"code": error.code, "message": error.message}}, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, error):
        # Pydantic input/ctx can contain a submitted password; never return them.
        return JSONResponse(status_code=422, content={"detail": [
            {"type": e["type"], "loc": list(e["loc"]), "msg": e["msg"]} for e in error.errors()
        ]})

    @app.exception_handler(Exception)
    async def unexpected(request, error):
        logger.error("Request failed: %s %s (%s)", request.method, request.url.path, type(error).__name__)
        return JSONResponse(status_code=500, content={"detail": {
            "code": "internal_error", "message": "Внутренняя ошибка сервера"}})

    @app.get("/health", tags=["Состояние"])
    async def health():
        """Проверяет работу процесса API без обращения к базе данных."""
        return {"status": "ok"}

    @app.get("/ready", tags=["Состояние"], responses={503: {"description": "БД недоступна"}})
    async def ready():
        """Проверяет соединение с БД через SELECT 1; при ошибке или таймауте возвращает 503."""
        try:
            async with asyncio.timeout(settings.readiness_timeout):
                async with database.engine.connect() as connection:
                    await connection.execute(text("SELECT 1"))
            return {"status": "ready"}
        except Exception:
            return JSONResponse(status_code=503, content={"detail": {
                "code": "not_ready", "message": "База данных недоступна"}})

    for router in (auth.router, users.router, catalog.router, listings.router, chats.router):
        app.include_router(router, prefix="/api/v1")
    app.mount("/media", StaticFiles(directory=settings.media_dir), name="media")
    return app

