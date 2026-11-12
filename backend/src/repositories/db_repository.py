from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.errors import AppError
from src.db.base import Base
from src.repositories.catalog_repository import CatalogRepository
from src.repositories.chat_repository import ChatRepository
from src.repositories.listing_repository import ListingRepository
from src.repositories.photo_repository import PhotoRepository
from src.repositories.seed_repository import SeedRepository
from src.repositories.user_repository import UserRepository


class DbRepository:
    """Объединяет репозитории в одной сессии и управляет сохранением или откатом операции."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.catalog = CatalogRepository(session)
        self.listings = ListingRepository(session)
        self.photos = PhotoRepository(session)
        self.seed = SeedRepository(session)
        self.chats = ChatRepository(session)

    def add(self, item: Base) -> None:
        self.session.add(item)

    async def flush(self) -> None:
        await self.session.flush()

    async def save(self) -> None:
        """Фиксирует транзакцию; при нарушении ограничений откатывает её и выдаёт конфликт 409."""
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise AppError(409, "conflict", "Данные уже существуют или изменились") from None

    async def rollback(self) -> None:
        await self.session.rollback()

