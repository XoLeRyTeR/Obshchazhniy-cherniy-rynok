from typing import Annotated

from fastapi import APIRouter, Depends

from src.api.dependencies.auth import auth_rate
from src.api.dependencies.services import service
from src.schemas.auth import AuthOut, Login, Register
from src.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Авторизация"], dependencies=[Depends(auth_rate)])
Auth = Annotated[AuthService, Depends(service(AuthService))]


@router.post("/register", response_model=AuthOut, status_code=201)
async def register(data: Register, auth: Auth):
    """Регистрирует пользователя с выбранным общежитием и возвращает JWT и профиль.

    Почта должна быть свободна; общежитие можно выбрать по ID или указать названием внутри вуза.
    """
    return await auth.register(data)


@router.post("/login", response_model=AuthOut)
async def login(data: Login, auth: Auth):
    """Проверяет почту и пароль, возвращает JWT и профиль; неверные данные дают 401."""
    return await auth.login(data)

