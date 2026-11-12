from collections.abc import Callable
from typing import TypeVar

from fastapi import Depends, Request

from src.api.dependencies.db import get_db
from src.core.config import Settings
from src.repositories.db_repository import DbRepository

ServiceT = TypeVar("ServiceT")


def service(service_class: Callable[[DbRepository, Settings], ServiceT]) -> Callable[[Request, DbRepository], ServiceT]:
    """Создаёт зависимость сервиса, которому нужны репозитории и настройки приложения."""
    def build(request: Request, db: DbRepository = Depends(get_db)) -> ServiceT:
        """Передаёт сервису репозитории текущего запроса и настройки API."""
        return service_class(db, request.app.state.settings)
    return build


def db_service(service_class: Callable[[DbRepository], ServiceT]) -> Callable[[DbRepository], ServiceT]:
    """Создаёт зависимость сервиса, которому нужны только репозитории, без лишних настроек."""
    def build(db: DbRepository = Depends(get_db)) -> ServiceT:
        """Передаёт сервису репозитории текущего запроса."""
        return service_class(db)
    return build

