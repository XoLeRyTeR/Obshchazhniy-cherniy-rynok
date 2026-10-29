from starlette.concurrency import run_in_threadpool

from src.core.errors import AppError, unauthorized
from src.core.security import dummy_hash, hasher, issue_token, verify_password
from src.models import User
from src.schemas.auth import AuthOut
from src.services.catalog_service import CatalogService
from src.services.views import profile


class AuthService:
    """Регистрирует пользователей и проверяет учётные данные для выдачи JWT."""

    def __init__(self, db, settings):
        """Принимает репозитории и настройки авторизации."""
        self.db, self.settings = db, settings

    async def register(self, data):
        """Создаёт пользователя с хешем пароля и общежитием, возвращает токен и профиль.

        Занятая почта отклоняется с 409; новое общежитие сохраняется вместе с пользователем.
        """
        if await self.db.users.by_email(str(data.email)):
            raise AppError(409, "email_exists", "Почта уже зарегистрирована")
        dorm_id = await CatalogService(self.db, self.settings).resolve(data)
        user = User(email=str(data.email), name=data.name, dormitory_id=dorm_id,
                    password_hash=await run_in_threadpool(hasher.hash, data.password))
        self.db.add(user)
        await self.db.save()
        user = await self.db.users.get(user.id)
        return AuthOut(access_token=issue_token(user.id, self.settings), profile=profile(user))

    async def login(self, data):
        """Проверяет пароль и возвращает новый JWT и профиль без раскрытия наличия почты."""
        user = await self.db.users.by_email(str(data.email))
        valid = await run_in_threadpool(verify_password, data.password,
                                        user.password_hash if user else dummy_hash)
        if not valid or user is None:
            raise unauthorized()
        user = await self.db.users.get(user.id)
        return AuthOut(access_token=issue_token(user.id, self.settings), profile=profile(user))

