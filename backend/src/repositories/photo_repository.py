from uuid import UUID

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import ListingPhoto

MEDIA_LOCK = 20261029


class PhotoRepository:
    """Работает с записями фотографий и блокировкой согласованного изменения файлов и БД."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def lock_media(self) -> None:
        """Блокирует операции с медиа до commit/rollback, чтобы очистка не удаляла новые файлы."""
        await self.session.execute(select(func.pg_advisory_xact_lock(MEDIA_LOCK)))

    async def get(self, listing_id: UUID, photo_id: UUID) -> ListingPhoto | None:
        """Находит фотографию только внутри указанного объявления."""
        query = select(ListingPhoto).where(
            ListingPhoto.id == photo_id, ListingPhoto.listing_id == listing_id,
        )
        return await self.session.scalar(query)

    async def is_referenced(self, storage_key: str) -> bool:
        """Проверяет связь файла с записью БД, в том числе после потери подтверждения commit."""
        query = select(exists().where(ListingPhoto.storage_key == storage_key))
        return await self.session.scalar(query)

    async def storage_keys(self) -> set[str]:
        """Возвращает имена всех файлов с записями в БД для безопасной очистки сирот."""
        keys = await self.session.scalars(select(ListingPhoto.storage_key))
        return set(keys.all())

    async def delete(self, record: ListingPhoto) -> None:
        """Помечает запись фотографии на удаление; транзакцию фиксирует вызывающая операция."""
        await self.session.delete(record)
