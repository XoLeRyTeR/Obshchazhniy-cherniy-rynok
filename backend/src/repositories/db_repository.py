from sqlalchemy.exc import IntegrityError

from src.core.errors import AppError
from src.repositories.catalog_repository import CatalogRepository
from src.repositories.chat_repository import ChatRepository
from src.repositories.listing_repository import ListingRepository
from src.repositories.photo_repository import PhotoRepository
from src.repositories.user_repository import UserRepository


class DbRepository:
    """Объединяет репозитории в одной сессии и управляет сохранением или откатом операции."""

    def __init__(self, session):
        self.session = session
        self.users = UserRepository(session)
        self.catalog = CatalogRepository(session)
        self.listings = ListingRepository(session)
        self.photos = PhotoRepository(session)
        self.chats = ChatRepository(session)

    def add(self, item):
        self.session.add(item)

    async def flush(self):
        await self.session.flush()

    async def save(self):
        """Фиксирует транзакцию; при нарушении ограничений откатывает её и выдаёт конфликт 409."""
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise AppError(409, "conflict", "Данные уже существуют или изменились") from None

    async def rollback(self):
        await self.session.rollback()

