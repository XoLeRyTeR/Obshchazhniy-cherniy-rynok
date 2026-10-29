import io
from uuid import uuid4

from PIL import Image


async def test_two_user_exchange_flow(api):
    """FLOW-01/02: проверяет публикацию, чат, прочтение, бронь и завершение сделки двух пользователей.

    После передачи вещь скрыта из ленты, но доступна покупателю из переписки, не постороннему.
    """
    item = await api.listing()
    feed = await api.client.get("/api/v1/listings", headers=api.headers(1))
    assert feed.status_code == 200, feed.text
    assert feed.json()["items"][0]["id"] == item["id"]
    chat = await api.chat(item["id"])
    path = f"/api/v1/chats/{chat['id']}"
    message = await api.client.post(path + "/messages", json={"text": "Заберу", "client_message_id": str(uuid4())},
                                     headers=api.headers(1))
    assert message.status_code == 201, message.text
    chats = await api.client.get("/api/v1/chats", headers=api.headers())
    assert chats.status_code == 200, chats.text
    assert chats.json()["items"][0]["unread"] == 1
    read = await api.client.patch(path + "/read", json={"last_read_message_id": message.json()["id"]},
                                   headers=api.headers())
    assert read.status_code == 200, read.text
    assert (await api.client.get("/api/v1/chats", headers=api.headers())).json()["items"][0]["unread"] == 0
    for old, new in (("active", "reserved"), ("reserved", "completed")):
        response = await api.client.patch(f"/api/v1/listings/{item['id']}/status",
                                            json={"expected_status": old, "status": new}, headers=api.headers())
        assert response.status_code == 200, response.text
    assert not (await api.client.get("/api/v1/listings", headers=api.headers(1))).json()["items"]
    assert (await api.client.get(f"/api/v1/listings/{item['id']}", headers=api.headers(1))).status_code == 200
    assert (await api.client.get(f"/api/v1/listings/{item['id']}", headers=api.headers(2))).status_code == 404


async def test_photo_roundtrip(api):
    """Проверяет загрузку фото, безопасное имя, выдачу через /media и удаление файла с записью."""
    item = await api.listing()
    image = io.BytesIO()
    Image.new("RGB", (10, 10), "green").save(image, format="PNG")
    path = f"/api/v1/listings/{item['id']}/photos"
    response = await api.client.post(path, files={"file": ("../../test.png", image.getvalue(), "image/png")},
                                      headers=api.headers())
    assert response.status_code == 201, response.text
    photo = response.json()
    filename = photo["url"].rsplit("/", 1)[1]
    assert "/" not in filename and ".." not in filename
    assert (await api.client.get("/media/" + filename)).status_code == 200
    removed = await api.client.delete(path + "/" + photo["id"], headers=api.headers())
    assert removed.status_code == 204, removed.text
    assert (await api.client.get("/media/" + filename)).status_code == 404
