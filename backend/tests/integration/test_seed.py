import asyncio
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import delete, func, select

from src.core.security import hasher, verify_password
from src.models import Dormitory, Listing, University, User
from src.repositories.db_repository import DbRepository
from src.services.seed_service import DEMO_PASSWORD, DEMO_USERS, SeedService


async def populate(db):
    """Запускает начальное наполнение в отдельной сессии изолированной тестовой схемы."""
    async with db.sessions() as session:
        return await SeedService(DbRepository(session)).populate()


async def test_seed_empty_feed_and_login(api):
    """Проверяет шесть объявлений, все форматы, переиспользование вуза и вход обоих демо-пользователей."""
    assert await populate(api.db) == 6
    async with api.db.sessions() as session:
        listings = list((await session.scalars(select(Listing))).all())
        assert len(listings) == 6
        assert {item.format for item in listings} == {"give", "sell", "exchange", "service"}
        assert {item.status for item in listings} == {"active"}
        assert await session.scalar(select(func.count()).select_from(University)) == 1
        assert await session.scalar(select(func.count()).select_from(Dormitory)) == 2
        assert await session.scalar(select(func.count()).select_from(User)) == 5
    for email, _, _ in DEMO_USERS:
        response = await api.client.post("/api/v1/auth/login", json={"email": email, "password": DEMO_PASSWORD})
        assert response.status_code == 200, response.text
        assert response.json()["access_token"]


async def test_seed_creates_missing_university(api):
    """Проверяет создание ИГЭУ, если существующий справочник содержит только другой вуз."""
    async with api.db.sessions() as session:
        university = await session.get(University, api.university)
        university.name = "Другой университет"
        await session.commit()
    assert await populate(api.db) == 6
    async with api.db.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(University)) == 2


async def test_seed_is_idempotent(api):
    """Проверяет, что повторный запуск не добавляет объявления и не заменяет их ID."""
    assert await populate(api.db) == 6
    async with api.db.sessions() as session:
        original = set((await session.scalars(select(Listing.id))).all())
    assert await populate(api.db) == 0
    async with api.db.sessions() as session:
        assert set((await session.scalars(select(Listing.id))).all()) == original
        assert await session.scalar(select(func.count()).select_from(User)) == 5


@pytest.mark.parametrize("status", ["active", "archived"])
async def test_seed_skips_existing_listings(api, status):
    """Проверяет отказ от наполнения, даже если единственное существующее объявление архивное."""
    listing = await api.listing()
    async with api.db.sessions() as session:
        item = await session.get(Listing, listing["id"])
        item.status = status
        await session.commit()
    assert await populate(api.db) == 0
    async with api.db.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(Listing)) == 1
        assert await session.scalar(select(func.count()).select_from(User)) == 3


async def test_seed_concurrent_startup(api):
    """Проверяет, что два одновременных запуска создают только один набор данных."""
    assert sorted(await asyncio.gather(populate(api.db), populate(api.db))) == [0, 6]
    async with api.db.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(Listing)) == 6
        assert await session.scalar(select(func.count()).select_from(User)) == 5


async def test_seed_does_not_use_someone_elses_email(api):
    """Проверяет, что занятая демо-почта не приводит к созданию объявлений от имени чужого пользователя."""
    async with api.db.sessions() as session:
        user = await session.scalar(select(User).limit(1))
        user.email = DEMO_USERS[0][0]
        await session.commit()
    assert await populate(api.db) == 0
    async with api.db.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(Listing)) == 0
        assert await session.scalar(select(func.count()).select_from(User)) == 3


async def test_seed_rolls_back_on_failure(api):
    """Проверяет откат пользователей, общежития и объявлений при ошибке перед commit."""
    async with api.db.sessions() as session:
        db = DbRepository(session)
        db.save = AsyncMock(side_effect=RuntimeError("seed failed"))
        with pytest.raises(RuntimeError, match="seed failed"):
            await SeedService(db).populate()
    async with api.db.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(Listing)) == 0
        assert await session.scalar(select(func.count()).select_from(User)) == 3
        assert await session.scalar(select(func.count()).select_from(Dormitory)) == 1


async def test_seed_preserves_edited_demo_profile(api):
    """Проверяет, что повторное наполнение пустой ленты не сбрасывает имя и изменённый пароль демо-аккаунта."""
    await populate(api.db)
    async with api.db.sessions() as session:
        user = await session.scalar(select(User).where(User.email == DEMO_USERS[0][0]))
        user.name = "Новое имя"
        user.password_hash = hasher.hash("changed-demo-password")
        await session.execute(delete(Listing))
        await session.commit()
    assert await populate(api.db) == 6
    async with api.db.sessions() as session:
        user = await session.scalar(select(User).where(User.email == DEMO_USERS[0][0]))
        assert user.name == "Новое имя"
        assert verify_password("changed-demo-password", user.password_hash)


async def test_seed_lifespan_and_disabled_setting(api):
    """Проверяет отключение через настройку и автоматическое наполнение при старте без дублей при рестарте."""
    api.app.state.settings.seed_demo_data = False
    async with api.app.router.lifespan_context(api.app):
        async with api.db.sessions() as session:
            assert await session.scalar(select(func.count()).select_from(Listing)) == 0
    api.app.state.settings.seed_demo_data = True
    for _ in range(2):
        async with api.app.router.lifespan_context(api.app):
            async with api.db.sessions() as session:
                assert await session.scalar(select(func.count()).select_from(Listing)) == 6
