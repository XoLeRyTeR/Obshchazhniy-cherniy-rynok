from uuid import UUID

from src.core.errors import missing
from src.models import Dormitory, University
from src.repositories.db_repository import DbRepository
from src.schemas.common import PageQuery
from src.schemas.users import DormChoice


class CatalogService:
    """Проверяет выбор вуза и общежития, выдаёт страницы справочников."""

    def __init__(self, db: DbRepository) -> None:
        """Принимает репозитории справочников; настройки приложению здесь не нужны."""
        self.db = db

    async def resolve(self, data: DormChoice) -> UUID:
        """Возвращает ID выбранного общежития либо создаёт его в указанном вузе.

        Несуществующий вуз или общежитие отклоняется с 404.
        """
        if data.dormitory_id:
            dorm = await self.db.catalog.get_dorm(data.dormitory_id)
            if dorm is None:
                raise missing()
            return dorm.id
        if await self.db.catalog.get_university(data.university_id) is None:
            raise missing()
        return await self.db.catalog.resolve_dorm(data.university_id, data.dormitory_name)

    async def universities(self, params: PageQuery) -> dict[str, list[University]]:
        """Возвращает страницу вузов по offset и size в алфавитном порядке."""
        items = await self.db.catalog.universities(params.offset, params.size)
        return {"items": items}

    async def dormitories(self, university_id: UUID, params: PageQuery) -> dict[str, list[Dormitory]]:
        """Проверяет существование вуза и возвращает страницу его общежитий."""
        if await self.db.catalog.get_university(university_id) is None:
            raise missing()
        items = await self.db.catalog.dormitories(university_id, params.offset, params.size)
        return {"items": items}

