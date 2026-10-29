from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from src.models import ChatRead
from src.repositories.db_repository import DbRepository
from tests.integration.test_api import png


@pytest.mark.parametrize("values", [
    {"price": -1}, {"price": 1}, {"format": "sell", "price": 0},
    {"format": "service", "status": "reserved"}, {"format": "service", "status": "completed"},
    {"category": "invalid"}, {"title": " "}, {"description": ""},
])
async def test_postgres_rejects_invalid_rows_without_api(api, values):
    """Проверяет прямой SQL-вставкой, что сама БД запрещает неверные цены, статусы, категории и пустой текст."""
    data = {"owner": UUID(api.users[0]["profile"]["id"]), "dorm": UUID(api.dorm),
            "title": "Стул", "description": "Рабочий", "category": "furniture",
            "format": "give", "price": 0, "status": "active", **values}
    async with api.db.sessions() as session:
        with pytest.raises(IntegrityError):
            await session.execute(text("""
                INSERT INTO listings(owner_id,dormitory_id,title,description,category,format,price,status)
                VALUES (:owner,:dorm,:title,:description,:category,:format,:price,:status)
            """), data)


async def test_postgres_rejects_cross_chat_read_marker(api):
    """Проверяет, что составной внешний ключ БД запрещает метку прочтения на сообщение другого чата."""
    listing = await api.listing()
    first, second = await api.chat(listing["id"]), await api.chat(listing["id"], buyer=2)
    message = await api.client.post(f"/api/v1/chats/{first['id']}/messages",
        json={"text": "Один", "client_message_id": str(uuid4())}, headers=api.headers(1))
    async with api.db.sessions() as session:
        session.add(ChatRead(chat_id=UUID(second["id"]), user_id=UUID(api.users[0]["profile"]["id"]),
                             last_read_message_id=UUID(message.json()["id"])))
        with pytest.raises(IntegrityError):
            await session.flush()


async def test_photo_survives_lost_commit_acknowledgment(api, monkeypatch):
    """Имитирует потерю ответа после успешного commit и проверяет сохранность записи фото и файла."""
    item = await api.listing()

    async def commit_then_fail(db):
        """Сохраняет изменения, затем имитирует разрыв соединения до подтверждения клиенту."""
        await db.session.commit()
        raise ConnectionError("commit-acknowledgment-lost")

    with monkeypatch.context() as patch:
        patch.setattr(DbRepository, "save", commit_then_fail)
        response = await api.client.post(f"/api/v1/listings/{item['id']}/photos",
            files={"file": ("image.png", png(), "image/png")}, headers=api.headers())
    assert response.status_code == 500
    detail = (await api.client.get(f"/api/v1/listings/{item['id']}", headers=api.headers())).json()
    assert len(detail["photos"]) == 1
    filename = detail["photos"][0]["url"].rsplit("/", 1)[1]
    assert (await api.client.get("/media/" + filename)).status_code == 200
