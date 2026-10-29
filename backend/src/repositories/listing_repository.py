from sqlalchemy import exists, or_, select
from sqlalchemy.orm import selectinload

from src.models import Chat, Dormitory, Listing


class ListingRepository:
    """Извлекает объявления со связями, применяет фильтры, сортировку и блокировки строк."""

    def __init__(self, session):
        self.session = session

    @staticmethod
    def query():
        """Строит базовый запрос с пакетной загрузкой автора, фото, общежития и вуза."""
        return select(Listing).options(
            selectinload(Listing.owner), selectinload(Listing.photos),
            selectinload(Listing.dormitory).selectinload(Dormitory.university),
        ).execution_options(populate_existing=True)

    async def get(self, listing_id, lock=False):
        query = self.query().where(Listing.id == listing_id)
        if lock:
            query = query.with_for_update(of=Listing)
        return await self.session.scalar(query)

    async def has_chat(self, listing_id, user_id):
        """Проверяет наличие чата покупателя по объявлению для проверки доступа к истории."""
        return await self.session.scalar(select(exists().where(
            Chat.listing_id == listing_id, Chat.buyer_id == user_id
        )))

    async def feed(self, params, offset, size):
        """Выбирает страницу активных/забронированных объявлений с фильтрами и поиском.

        Символы % и _ в поиске считаются обычными символами, а не шаблонами SQL LIKE.
        """
        query = self.query().join(Dormitory).where(Listing.status.in_(["active", "reserved"]))
        for field in ("category", "format", "dormitory_id"):
            value = getattr(params, field)
            if value is not None:
                query = query.where(getattr(Listing, field) == value)
        if params.university_id:
            query = query.where(Dormitory.university_id == params.university_id)
        if params.q:
            escaped = params.q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.where(or_(Listing.title.ilike(f"%{escaped}%", escape="\\"),
                                    Listing.description.ilike(f"%{escaped}%", escape="\\")))
        query = query.order_by(Listing.created_at.desc(), Listing.id.desc()).offset(offset).limit(size)
        return list((await self.session.scalars(query)).all())

    async def own(self, user_id, status, offset, size):
        """Выбирает страницу объявлений автора от новых к старым с необязательным статусом."""
        query = self.query().where(Listing.owner_id == user_id)
        if status:
            query = query.where(Listing.status == status)
        query = query.order_by(Listing.created_at.desc(), Listing.id.desc()).offset(offset).limit(size)
        return list((await self.session.scalars(query)).all())

