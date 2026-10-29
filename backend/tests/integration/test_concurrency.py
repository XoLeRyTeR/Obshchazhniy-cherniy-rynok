import asyncio
from uuid import uuid4

from sqlalchemy import func, select

from src.models import Chat, Dormitory, Message


async def test_concurrent_status_and_format(api):
    """Проверяет гонку бронирования и смены формата на услугу: проходит только одно совместимое изменение."""
    item = await api.listing()
    path = "/api/v1/listings/" + item["id"]
    replies = await asyncio.gather(
        api.client.patch(path + "/status", json={"expected_status": "active", "status": "reserved"}, headers=api.headers()),
        api.client.patch(path, json={"format": "service"}, headers=api.headers()),
    )
    assert sorted(r.status_code for r in replies) == [200, 409]
    final = (await api.client.get(path, headers=api.headers())).json()
    assert (final["format"], final["status"]) in {( "give", "reserved"), ("service", "active")}


async def test_concurrent_reserve_archive(api):
    """Проверяет, что одновременные бронь и архивирование дают один успех и один конфликт 409."""
    item = await api.listing()
    path = f"/api/v1/listings/{item['id']}/status"
    replies = await asyncio.gather(*[
        api.client.patch(path, json={"expected_status": "active", "status": value}, headers=api.headers())
        for value in ("reserved", "archived")
    ])
    assert sorted(r.status_code for r in replies) == [200, 409]


async def test_concurrent_chat_and_message_retries(api):
    """Проверяет, что параллельные повторы создания чата и отправки сообщения не создают дублей."""
    item = await api.listing()
    replies = await asyncio.gather(*[
        api.client.post("/api/v1/chats", json={"listing_id": item["id"]}, headers=api.headers(1)) for _ in range(2)
    ])
    assert sorted(r.status_code for r in replies) == [200, 201]
    assert replies[0].json()["id"] == replies[1].json()["id"]
    path = f"/api/v1/chats/{replies[0].json()['id']}/messages"
    key = str(uuid4())
    messages = await asyncio.gather(*[
        api.client.post(path, json={"text": "Один раз", "client_message_id": key}, headers=api.headers(1)) for _ in range(2)
    ])
    assert sorted(r.status_code for r in messages) == [200, 201]
    assert messages[0].json()["id"] == messages[1].json()["id"]
    async with api.db.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(Chat)) == 1
        assert await session.scalar(select(func.count()).select_from(Message)) == 1


async def test_concurrent_same_dormitory(api):
    """Проверяет, что два пользователя одновременно получают одно общежитие для одинакового имени в вузе."""
    replies = await asyncio.gather(*[
        api.client.patch("/api/v1/users/me", json={"university_id": api.university,
            "dormitory_name": " Северный  кампус "}, headers=api.headers(index)) for index in (0, 1)
    ])
    assert all(r.status_code == 200 for r in replies), [r.text for r in replies]
    assert replies[0].json()["dormitory"]["id"] == replies[1].json()["dormitory"]["id"]
    async with api.db.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(Dormitory)) == 2
