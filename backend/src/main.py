import asyncio
import logging
from collections.abc import AsyncIterator
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
from src.repositories.db_repository import DbRepository
from src.services.seed_service import SeedService

logger = logging.getLogger(__name__)


async def request_rules(request: Request) -> None:
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


def create_app(settings: Settings | None = None, database: Database | None = None) -> FastAPI:
    settings = settings or Settings()
    settings.media_dir.mkdir(parents=True, exist_ok=True)
    database = database or Database(settings.database_url.get_secret_value())

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        """Добавляет разрешённые демо-данные перед приёмом запросов и освобождает соединения при остановке."""
        try:
            if settings.seed_demo_data:
                async with database.sessions() as session:
                    created = await SeedService(DbRepository(session)).populate()
                if created:
                    logger.info("Created %s demo listings", created)
            yield
        finally:
            await database.close()

    app = FastAPI(title="Общажный чёрный рынок", version="0.1.0", debug=False,
                  lifespan=lifespan, dependencies=[Depends(request_rules)])
    app.state.settings, app.state.database = settings, database
    app.state.auth_buckets = {}
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                       allow_methods=["GET", "POST", "PATCH", "DELETE"],
                       allow_headers=["Authorization", "Content-Type"])

    @app.exception_handler(AppError)
    async def app_error(_request: Request, error: AppError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if error.status == 401 else {}
        if error.status == 429:
            headers["Retry-After"] = str(settings.auth_rate_window)
        return JSONResponse(status_code=error.status,
                            content={"detail": {"code": error.code, "message": error.message}}, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request: Request, error: RequestValidationError) -> JSONResponse:
        # Pydantic input/ctx can contain a submitted password; never return them.
        return JSONResponse(status_code=422, content={"detail": [
            {"type": e["type"], "loc": list(e["loc"]), "msg": e["msg"]} for e in error.errors()
        ]})

    @app.exception_handler(Exception)
    async def unexpected(request: Request, error: Exception) -> JSONResponse:
        logger.error("Request failed: %s %s (%s)", request.method, request.url.path, type(error).__name__)
        return JSONResponse(status_code=500, content={"detail": {
            "code": "internal_error", "message": "Внутренняя ошибка сервера"}})

    @app.get("/health", tags=["Состояние"])
    async def health() -> dict[str, str]:
        """Проверяет работу процесса API без обращения к базе данных."""
        return {"status": "ok"}

    @app.get("/ready", tags=["Состояние"], response_model=None, responses={503: {"description": "БД недоступна"}})
    async def ready() -> dict[str, str] | JSONResponse:
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

