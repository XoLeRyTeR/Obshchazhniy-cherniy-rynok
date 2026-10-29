from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from src.models import ChatRead, Message


async def test_chat_summaries_with_equal_timestamps_and_empty_chat(api):
    """Проверяет превью и непрочитанные при одинаковом времени сообщений, пустые чаты и страницы.

    ID разрешает совпадения времени; чужой чат не попадает в список, свои сообщения не считаются.
    """
    listing = await api.listing()
    conversation = await api.chat(listing["id"])
    empty = await api.chat(listing["id"], buyer=2)
    other_listing = await api.listing(owner=1)
    await api.chat(other_listing["id"], buyer=2)

    chat_id = UUID(conversation["id"])
    owner = UUID(api.users[0]["profile"]["id"])
    buyer = UUID(api.users[1]["profile"]["id"])
    # Одинаковое время проверяет выбор по ID и для последнего сообщения, и для непрочитанных.
    timestamp = datetime.now(timezone.utc) + timedelta(days=1)
    async with api.db.sessions() as session:
        for number, sender in ((1, buyer), (2, owner), (3, buyer)):
            session.add(Message(
                id=UUID(int=number), chat_id=chat_id, sender_id=sender,
                text=f"Сообщение {number}", client_message_id=uuid4(), created_at=timestamp,
            ))
        await session.flush()
        session.add(ChatRead(chat_id=chat_id, user_id=owner, last_read_message_id=UUID(int=1)))
        await session.commit()

    response = await api.client.get("/api/v1/chats", headers=api.headers())
    assert response.status_code == 200, response.text
    chats = response.json()["items"]
    assert [chat["id"] for chat in chats] == [conversation["id"], empty["id"]]
    assert chats[0]["last_message"]["id"] == str(UUID(int=3))
    assert chats[0]["unread"] == 1
    assert chats[1]["last_message"] is None
    assert chats[1]["unread"] == 0
    assert chats[1]["last_activity_at"] == chats[1]["created_at"]

    # У покупателя нет метки прочтения: непрочитанным считается только сообщение автора.
    response = await api.client.get("/api/v1/chats", headers=api.headers(1))
    assert response.status_code == 200, response.text
    buyer_chat = next(chat for chat in response.json()["items"] if chat["id"] == str(chat_id))
    assert buyer_chat["unread"] == 1

    first = await api.client.get("/api/v1/chats", params={"offset": 0, "size": 1}, headers=api.headers())
    assert first.status_code == 200, first.text
    assert first.json()["items"][0]["id"] == conversation["id"]
    second = await api.client.get("/api/v1/chats", headers=api.headers(), params={
        "offset": 1, "size": 1,
    })
    assert second.status_code == 200, second.text
    assert second.json()["items"][0]["id"] == empty["id"]
    end = await api.client.get("/api/v1/chats?offset=2&size=1", headers=api.headers())
    assert end.status_code == 200 and end.json() == {"items": []}
