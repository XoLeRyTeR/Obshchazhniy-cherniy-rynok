from src.services.catalog_service import CatalogService
from src.services.views import profile


class UserService:
    """Обновляет имя и общежитие пользователя с проверкой справочников."""

    def __init__(self, db, settings):
        """Принимает репозитории и настройки приложения."""
        self.db, self.settings = db, settings

    async def update(self, user_id, data):
        """Меняет переданные поля профиля и возвращает его актуальное состояние.

        Пользователь и новое общежитие сохраняются в одной транзакции.
        """
        user = await self.db.users.get(user_id, lock=True)
        if "name" in data.model_fields_set:
            user.name = data.name
        if data.dormitory_id or data.university_id:
            user.dormitory_id = await CatalogService(self.db, self.settings).resolve(data)
        await self.db.save()
        return profile(await self.db.users.get(user_id))

