import logging
from uuid import NAMESPACE_URL, uuid5

from starlette.concurrency import run_in_threadpool

from src.core.security import hasher
from src.models import Listing, User
from src.repositories.db_repository import DbRepository

logger = logging.getLogger(__name__)

DEMO_PASSWORD = "demo-pass-123"
DEMO_USERS = (
    ("andrey.demo@example.com", "Андрей · демо", "4"),
    ("maria.demo@example.com", "Мария · демо", "Студенческий кампус"),
)
# Цена хранится в копейках; последняя колонка — индекс автора в DEMO_USERS.
DEMO_LISTINGS = (
    ("Настольная лампа", "Работает, отдаю после переезда. Лампочка в комплекте.", "electronics", "give", 0, 0),
    ("Учебник по математике", "Продам учебник для первого курса, без пометок.", "books", "sell", 35000, 1),
    ("Обменяю худи", "Размер M. Обменяю на настольную игру или книгу.", "clothes", "exchange", 0, 0),
    ("Помощь с Python", "Помогу разобраться с основами Python и найти ошибки в коде. Цена за час.", "other", "service", 50000, 1),
    ("Офисный стул", "Удобный стул, регулировка высоты работает. Самовывоз из общежития.", "furniture", "sell", 120000, 0),
    ("Набор кружек", "Две чистые кружки без сколов. Забирайте бесплатно.", "dishes", "give", 0, 1),
)


class SeedService:
    """Наполняет пустую ленту демо-данными, не перезаписывая пользователей и объявления."""

    def __init__(self, db: DbRepository) -> None:
        """Принимает репозитории одной транзакции, не обращается к SQL напрямую."""
        self.db = db

    async def populate(self) -> int:
        """Атомарно добавляет два демо-аккаунта и шесть объявлений, если объявлений ещё нет.

        Стабильные ID отличают наши демо-аккаунты от пользователей, занявших такую же почту.
        Пароли и профиль уже существующих демо-аккаунтов не сбрасываются.
        """
        try:
            await self.db.seed.lock()
            if await self.db.seed.has_listings():
                await self.db.rollback()
                return 0

            users = []
            for email, _, _ in DEMO_USERS:
                user = await self.db.users.by_email(email)
                if user is not None and user.id != uuid5(NAMESPACE_URL, "mobilki:demo:" + email):
                    logger.warning("Demo seed skipped: a demo email is already in use")
                    await self.db.rollback()
                    return 0
                users.append(user)

            university_id = await self.db.seed.university_id()
            for index, (email, name, dorm) in enumerate(DEMO_USERS):
                if users[index] is None:
                    dorm_id = await self.db.catalog.resolve_dorm(university_id, dorm)
                    users[index] = User(
                        id=uuid5(NAMESPACE_URL, "mobilki:demo:" + email), email=email, name=name,
                        dormitory_id=dorm_id,
                        password_hash=await run_in_threadpool(hasher.hash, DEMO_PASSWORD),
                    )
                    self.db.add(users[index])
            await self.db.flush()

            for title, description, category, format_code, price, owner in DEMO_LISTINGS:
                user = users[owner]
                self.db.add(Listing(
                    owner_id=user.id, dormitory_id=user.dormitory_id, title=title,
                    description=description, category=category, format=format_code, price=price,
                ))
            await self.db.save()
            return len(DEMO_LISTINGS)
        except Exception:
            await self.db.rollback()
            raise
