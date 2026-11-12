from uuid import UUID

from sqlalchemy import exists, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Listing, University


class SeedRepository:
    """Проверяет необходимость начального наполнения и согласует его между процессами API."""

    def __init__(self, session: AsyncSession) -> None:
        """Использует общую транзакцию с остальными репозиториями."""
        self.session = session

    async def lock(self) -> None:
        """Не даёт нескольким workers одновременно наполнить пустую базу; действует до commit/rollback."""
        await self.session.execute(select(func.pg_advisory_xact_lock(20261104)))

    async def has_listings(self) -> bool:
        """Проверяет наличие любых объявлений, включая архивные и завершённые."""
        return await self.session.scalar(select(exists().select_from(Listing)))

    async def university_id(self) -> UUID:
        """Находит ИГЭУ или создаёт его, не изменяя существующее название."""
        statement = insert(University).values(name="ИГЭУ")
        statement = statement.on_conflict_do_update(
            index_elements=[University.name_key], set_={"name": University.name},
        ).returning(University.id)
        return await self.session.scalar(statement)
