from uuid import UUID

from src.repositories.db_repository import DbRepository
from src.schemas.users import ProfileOut, ProfilePatch
from src.services.catalog_service import CatalogService
from src.services.views import profile


class UserService:
    """Обновляет имя и общежитие пользователя с проверкой справочников."""

    def __init__(self, db: DbRepository) -> None:
        """Принимает репозитории для обновления профиля и выбора общежития."""
        self.db = db

    async def update(self, user_id: UUID, data: ProfilePatch) -> ProfileOut:
        """Меняет переданные поля профиля и возвращает его актуальное состояние.

        Пользователь и новое общежитие сохраняются в одной транзакции.
        """
        user = await self.db.users.get(user_id, lock=True)
        if "name" in data.model_fields_set:
            user.name = data.name
        if data.dormitory_id or data.university_id:
            user.dormitory_id = await CatalogService(self.db).resolve(data)
        await self.db.save()
        return profile(await self.db.users.get(user_id))
