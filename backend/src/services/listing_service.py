from pydantic import ValidationError

from src.core.errors import AppError, missing
from src.models import Listing, ListingFormat, ListingStatus
from src.schemas.listings import ListingCreate
from src.services.views import listing

TRANSITIONS = {"active": {"reserved", "archived"}, "reserved": {"active", "completed"},
               "completed": {"active"}, "archived": {"active"}}


class ListingService:
    """Применяет правила публикации объявлений, доступа, редактирования и смены статусов."""

    def __init__(self, db, settings):
        """Принимает репозитории и настройки для формирования ответов с фотографиями."""
        self.db, self.settings = db, settings

    async def accessible(self, listing_id, user_id, edit=False, lock=False):
        """Проверяет видимость объявления и, при edit=True, право автора на изменение.

        Снятые и завершённые объявления видны автору и покупателям с существующим чатом.
        lock=True блокирует строку для последующего изменения в транзакции.
        """
        item = await self.db.listings.get(listing_id, lock=lock)
        if item is None:
            raise missing()
        if item.status not in (ListingStatus.ACTIVE, ListingStatus.RESERVED) and item.owner_id != user_id:
            if not await self.db.listings.has_chat(item.id, user_id):
                raise missing()
        if edit and item.owner_id != user_id:
            raise AppError(403, "not_owner", "Изменять объявление может только автор")
        return item

    async def feed(self, user_id, params):
        """Проверяет совместимость фильтров вуза/общежития и возвращает страницу ленты."""
        if params.university_id and params.dormitory_id:
            dorm = await self.db.catalog.get_dorm(params.dormitory_id)
            if dorm and dorm.university_id != params.university_id:
                raise AppError(422, "inconsistent_filters", "Общежитие относится к другому вузу")
        items = await self.db.listings.feed(params, params.offset, params.size)
        return {"items": [listing(item, self.settings) for item in items]}

    async def own(self, user_id, params):
        """Возвращает страницу собственных объявлений, при необходимости по статусу."""
        items = await self.db.listings.own(user_id, params.status, params.offset, params.size)
        return {"items": [listing(item, self.settings) for item in items]}

    async def create(self, user, data):
        """Публикует объявление от имени пользователя с выбранным или его текущим общежитием."""
        values = data.model_dump(exclude_none=True)
        dorm_id = values.setdefault("dormitory_id", user.dormitory_id)
        if await self.db.catalog.get_dorm(dorm_id) is None:
            raise missing()
        item = Listing(owner_id=user.id, **values)
        self.db.add(item)
        await self.db.save()
        return listing(await self.db.listings.get(item.id), self.settings)

    async def detail(self, listing_id, user_id):
        """Возвращает подробности объявления после проверки его доступности пользователю."""
        return listing(await self.accessible(listing_id, user_id), self.settings)

    async def update(self, listing_id, user_id, data):
        """Изменяет поля объявления только автору, проверяя итоговое сочетание формата и цены.

        Переход к услуге запрещён, пока вещь забронирована или передана.
        """
        item = await self.accessible(listing_id, user_id, edit=True, lock=True)
        values = data.model_dump(exclude_unset=True)
        try:
            ListingCreate.model_validate({**{k: getattr(item, k) for k in ListingCreate.model_fields}, **values})
        except ValidationError:
            raise AppError(422, "invalid_listing", "Поля объявления не соответствуют формату") from None
        if (values.get("format") == ListingFormat.SERVICE and
                item.status in (ListingStatus.RESERVED, ListingStatus.COMPLETED)):
            raise AppError(409, "invalid_format_change", "Сначала верните объявление в активное состояние")
        if "dormitory_id" in values and await self.db.catalog.get_dorm(values["dormitory_id"]) is None:
            raise missing()
        for key, value in values.items():
            setattr(item, key, value)
        await self.db.save()
        return listing(await self.db.listings.get(item.id), self.settings)

    async def status(self, listing_id, user_id, data):
        """Меняет статус автору, если исходный статус совпадает и переход разрешён.

        Для услуги допустимы только active/archived; устаревший запрос отклоняется с 409.
        """
        item = await self.accessible(listing_id, user_id, edit=True, lock=True)
        if (item.status != data.expected_status or data.status not in TRANSITIONS[item.status] or
                (item.format == ListingFormat.SERVICE and data.status not in {"active", "archived"})):
            raise AppError(409, "status_conflict", "Статус уже изменён или переход запрещён")
        item.status = data.status
        await self.db.save()
        return listing(await self.db.listings.get(item.id), self.settings)

