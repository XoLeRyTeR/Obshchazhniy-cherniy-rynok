from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from src.models import Dormitory, University


class CatalogRepository:
    """Работает со справочниками вузов и общежитий, включая поиск или создание общежития."""

    def __init__(self, session):
        self.session = session

    async def get_dorm(self, dormitory_id):
        return await self.session.get(Dormitory, dormitory_id)

    async def get_university(self, university_id):
        return await self.session.get(University, university_id)

    async def resolve_dorm(self, university_id, name):
        """Возвращает ID существующего общежития либо атомарно создаёт новое.

        Уникальность нормализованного имени в пределах вуза защищает от параллельных дублей.
        """
        statement = insert(Dormitory).values(university_id=university_id, name=name)
        # При совпадении сохраняем написание имени; уникальный индекс согласует параллельные вставки.
        statement = statement.on_conflict_do_update(
            index_elements=[Dormitory.university_id, Dormitory.name_key],
            set_={"name": Dormitory.name},
        ).returning(Dormitory.id)
        return await self.session.scalar(statement)

    async def universities(self, offset, size):
        """Выбирает страницу вузов в порядке нормализованного имени, затем ID."""
        query = select(University).order_by(University.name_key, University.id).offset(offset).limit(size)
        return list((await self.session.scalars(query)).all())

    async def dormitories(self, university_id, offset, size):
        """Выбирает страницу общежитий одного вуза в алфавитном порядке."""
        query = (
            select(Dormitory)
            .where(Dormitory.university_id == university_id)
            .order_by(Dormitory.name_key, Dormitory.id)
            .offset(offset).limit(size)
        )
        return list((await self.session.scalars(query)).all())

