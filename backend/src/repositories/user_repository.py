from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import Dormitory, User


class UserRepository:
    """Находит пользователей для авторизации и профиля, загружает общежитие и вуз."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: UUID, lock: bool = False) -> User | None:
        query = select(User).where(User.id == user_id).options(
            selectinload(User.dormitory).selectinload(Dormitory.university)
        ).execution_options(populate_existing=True)
        if lock:
            query = query.with_for_update()
        return await self.session.scalar(query)

    async def by_email(self, email: str) -> User | None:
        return await self.session.scalar(select(User).where(User.email == email))

