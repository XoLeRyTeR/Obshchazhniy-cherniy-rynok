import importlib
import os
from dataclasses import dataclass
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text
from sqlalchemy.engine import make_url

from src.core.config import Settings
from src.db.database import Database
from src.main import create_app
from src.models import Dormitory, University


@dataclass
class Harness:
    """Хранит тестовый клиент, изолированную БД и трёх пользователей; помогает создавать данные через API."""

    client: httpx.AsyncClient
    db: Database
    app: object
    university: str
    dorm: str
    users: list

    def headers(self, index=0):
        """Возвращает Bearer-заголовок автора (0), покупателя (1) или постороннего (2)."""
        return {"Authorization": f"Bearer {self.users[index]['access_token']}"}

    async def listing(self, **values):
        """Публикует тестовое объявление выбранного автора и проверяет успешное создание."""
        owner = values.pop("owner", 0)
        payload = {"title": "Стул", "description": "Деревянный стул", "format": "give",
                   "category": "furniture", "price": 0, **values}
        response = await self.client.post("/api/v1/listings", json=payload, headers=self.headers(owner))
        assert response.status_code == 201, response.text
        return response.json()

    async def chat(self, listing_id, buyer=1):
        """Открывает чат выбранного покупателя по объявлению и проверяет успешный ответ."""
        response = await self.client.post("/api/v1/chats", json={"listing_id": listing_id},
                                           headers=self.headers(buyer))
        assert response.status_code in (200, 201), response.text
        return response.json()


@pytest_asyncio.fixture
async def api(tmp_path):
    """Готовит API с миграцией, справочниками и пользователями в отдельной временной схеме БД.

    Требует TEST_DATABASE_URL для базы с суффиксом _test; после теста удаляет только свою схему.
    """
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a disposable PostgreSQL database ending in _test")
    parsed = make_url(url)
    if parsed.drivername != "postgresql+asyncpg" or not parsed.database.endswith("_test"):
        raise RuntimeError("Integration tests require a separate PostgreSQL database ending in _test")
    if os.environ.get("DATABASE_URL") == url:
        raise RuntimeError("TEST_DATABASE_URL must not equal DATABASE_URL")
    schema = "test_" + uuid4().hex
    admin = Database(url)
    async with admin.engine.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    db = Database(url, schema=schema)
    try:
        migration = importlib.import_module("src.db.migrations.versions.0001_initial")

        def migrate(connection):
            """Применяет начальную миграцию в схеме текущего теста через синхронный адаптер Alembic."""
            with Operations.context(MigrationContext.configure(connection)):
                migration.upgrade()

        async with db.engine.begin() as connection:
            await connection.run_sync(migrate)
        settings = Settings(_env_file=None, database_url=url,
                            jwt_secret="test-key-with-at-least-32-characters-123",
                            media_dir=tmp_path / "media", media_base_url="https://test.example/media",
                            auth_rate_limit=1000)
        app = create_app(settings, database=db)
        async with db.sessions() as session:
            university = University(name="ИГЭУ")
            session.add(university)
            await session.flush()
            dorm = Dormitory(name="4", university_id=university.id)
            session.add(dorm)
            await session.commit()
            uni_id, dorm_id = str(university.id), str(dorm.id)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
                                     base_url="http://test") as client:
            harness = Harness(client, db, app, uni_id, dorm_id, [])
            for name in ("Автор", "Покупатель", "Посторонний"):
                response = await client.post("/api/v1/auth/register", json={
                    "name": name, "email": f"{uuid4().hex}@example.com", "password": "password123",
                    "dormitory_id": dorm_id,
                })
                assert response.status_code == 201, response.text
                harness.users.append(response.json())
            yield harness
    finally:
        await db.close()
        # Удаляем только уникальную схему этой фикстуры, никогда не всю базу данных.
        async with admin.engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin.close()

