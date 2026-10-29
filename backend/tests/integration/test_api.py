import asyncio
import io
from uuid import UUID, uuid4

import jwt
import pytest
from PIL import Image
from sqlalchemy import func, select

from src.models import Chat, Dormitory, Listing, Message, User
from src.repositories.db_repository import DbRepository


def png():
    """Создаёт небольшой валидный PNG в памяти для проверок загрузки фотографий."""
    data = io.BytesIO()
    Image.new("RGB", (10, 10)).save(data, format="PNG")
    return data.getvalue()


async def test_openapi_and_health(api):
    """Проверяет наличие 21 метода без refresh/logout и доступность публичных ручек и healthcheck."""
    paths = api.app.openapi()["paths"]
    assert sum(len(set(methods) & {"get", "post", "patch", "delete"}) for methods in paths.values()) == 21
    assert "/api/v1/auth/refresh" not in paths
    assert "/api/v1/auth/logout" not in paths
    for path in ("/health", "/ready", "/api/v1/universities", f"/api/v1/dormitories?university_id={api.university}"):
        response = await api.client.get(path)
        assert response.status_code == 200, response.text


@pytest.mark.parametrize("method,path,body", [
    ("GET", "/users/me", None), ("PATCH", "/users/me", {"name": "Новое"}),
    ("GET", "/listings", None), ("POST", "/listings", {}), ("GET", "/users/me/listings", None),
    ("GET", "/listings/{id}", None), ("PATCH", "/listings/{id}", {}),
    ("PATCH", "/listings/{id}/status", {}), ("POST", "/listings/{id}/photos", None),
    ("DELETE", "/listings/{id}/photos/{id}", None), ("GET", "/chats", None),
    ("POST", "/chats", {}), ("GET", "/chats/{id}/messages", None),
    ("POST", "/chats/{id}/messages", {}), ("PATCH", "/chats/{id}/read", {}),
])
async def test_all_protected_methods_require_authorization(api, method, path, body):
    """Проверяет ответ 401 без Bearer-токена для каждого защищённого метода, включая upload."""
    payload = {"files": {"file": ("test.png", png(), "image/png")}} if path.endswith("/photos") else {"json": body}
    response = await api.client.request(method, "/api/v1" + path.replace("{id}", str(uuid4())), **payload)
    assert response.status_code == 401, response.text


@pytest.mark.parametrize("field,value", [("sub", "invalid"), ("jti", None), ("kind", "other"), ("exp", 1)])
async def test_invalid_jwt(api, field, value):
    """Проверяет, что JWT с неверными sub/jti/kind или истёкшим сроком отклоняется с 401."""
    secret = api.app.state.settings.jwt_secret.get_secret_value()
    data = jwt.decode(api.users[0]["access_token"], secret, algorithms=["HS256"])
    data[field] = value
    token = jwt.encode(data, secret, algorithm="HS256")
    response = await api.client.get("/api/v1/users/me", headers={"Authorization": "Bearer " + token})
    assert response.status_code == 401


async def test_login_and_profile(api):
    """Проверяет вход, одинаковую ошибку неверного пароля/почты и нормализацию профиля и общежития."""
    email = api.users[0]["profile"]["email"]
    response = await api.client.post("/api/v1/auth/login", json={"email": email.upper(), "password": "password123"})
    assert response.status_code == 200, response.text
    assert response.json()["access_token"] != api.users[0]["access_token"]
    wrong = await api.client.post("/api/v1/auth/login", json={"email": email, "password": "wrongpassword"})
    unknown = await api.client.post("/api/v1/auth/login", json={"email": "unknown@example.com", "password": "wrongpassword"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    updated = await api.client.patch("/api/v1/users/me", json={"name": "  Андрей   Куликов ",
        "university_id": api.university, "dormitory_name": "  Северный   кампус "}, headers=api.headers())
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Андрей Куликов"
    assert updated.json()["dormitory"]["name"] == "Северный кампус"
    same = await api.client.patch("/api/v1/users/me", json={"university_id": api.university,
        "dormitory_name": "северный кампус"}, headers=api.headers(1))
    assert same.status_code == 200, same.text
    assert same.json()["dormitory"]["id"] == updated.json()["dormitory"]["id"]


async def test_profile_failed_update_rolls_back(api):
    """Проверяет, что неизвестное общежитие даёт 404 и не сохраняет одновременно переданное имя."""
    original = api.users[0]["profile"]["name"]
    response = await api.client.patch("/api/v1/users/me", json={"name": "Нельзя сохранить",
        "dormitory_id": str(uuid4())}, headers=api.headers())
    assert response.status_code == 404
    assert (await api.client.get("/api/v1/users/me", headers=api.headers())).json()["name"] == original


async def test_rate_limit(api):
    """Проверяет ответ 429 и Retry-After при превышении лимита попыток входа с одного IP."""
    api.app.state.settings.auth_rate_limit = 1
    api.app.state.auth_buckets.clear()
    data = {"email": "unknown@example.com", "password": "password123"}
    assert (await api.client.post("/api/v1/auth/login", json=data)).status_code == 401
    response = await api.client.post("/api/v1/auth/login", json=data)
    assert response.status_code == 429 and "Retry-After" in response.headers


async def test_feed_filters_pagination_and_privacy(api):
    """Проверяет страницы ленты, поиск с буквальным %, фильтры и отсутствие приватных полей автора.

    Дополнительно проверяет пустую страницу за концом и отказ от старых cursor/limit.
    """
    one = await api.listing(title="Алгоритмы 100%", description="Учебник", category="books", format="exchange")
    two = await api.listing(title="Лампа", category="electronics", format="sell", price=100)
    headers = api.headers(1)
    first = await api.client.get("/api/v1/listings?offset=0&size=1", headers=headers)
    assert first.status_code == 200, first.text
    second = await api.client.get("/api/v1/listings", params={"offset": 1, "size": 1}, headers=headers)
    assert second.status_code == 200, second.text
    assert {first.json()["items"][0]["id"], second.json()["items"][0]["id"]} == {one["id"], two["id"]}
    assert set(second.json()) == {"items"}
    end = await api.client.get("/api/v1/listings?offset=2&size=1", headers=headers)
    assert end.status_code == 200 and end.json() == {"items": []}
    for params in ({"q": "алгоритмы"}, {"q": "%"}, {"format": "exchange", "category": "books"}):
        response = await api.client.get("/api/v1/listings", params=params, headers=headers)
        assert response.status_code == 200, response.text
        assert [r["id"] for r in response.json()["items"]] == [one["id"]]
    card = first.json()["items"][0]
    assert "email" not in card["author"] and "password_hash" not in card["author"]
    assert "place" not in card and "exchange" not in card
    filtered = await api.client.get("/api/v1/listings?offset=1&size=1&format=exchange", headers=headers)
    assert filtered.status_code == 200 and filtered.json() == {"items": []}
    assert (await api.client.get("/api/v1/listings?cursor=broken", headers=headers)).status_code == 422
    assert (await api.client.get("/api/v1/listings?limit=1", headers=headers)).status_code == 422


@pytest.mark.parametrize("params", [{"size": 0}, {"size": 101}, {"category": "invalid"},
                                    {"owner_id": "other"}, {"q": "x" * 201}])
async def test_invalid_feed_query(api, params):
    """Проверяет ответ 422 для недопустимых размеров страницы, фильтров и лишних query-параметров."""
    assert (await api.client.get("/api/v1/listings", params=params, headers=api.headers())).status_code == 422


@pytest.mark.parametrize("field,value", [("price", True), ("price", -1), ("price", "100"),
    ("price", 0.5), ("format", "unknown"), ("title", "  "), ("description", "x" * 5001),
    ("owner_id", str(uuid4())), ("exchange", "На книгу"), ("place", "Холл")])
async def test_invalid_listing_body(api, field, value):
    """Проверяет отказ 422 при неверных цене, формате, тексте и запрещённых полях объявления."""
    data = dict(title="Стул", description="Описание", category="furniture", format="give", price=0)
    data[field] = value
    response = await api.client.post("/api/v1/listings", json=data, headers=api.headers())
    assert response.status_code == 422, response.text


async def test_listing_edit_permissions_and_format(api):
    """Проверяет запрет чужого редактирования, совместное изменение формата/цены и приватность своих вещей."""
    item = await api.listing()
    path = "/api/v1/listings/" + item["id"]
    assert (await api.client.patch(path, json={"title": "Чужое"}, headers=api.headers(1))).status_code == 403
    assert (await api.client.patch(path, json={"format": "sell"}, headers=api.headers())).status_code == 422
    changed = await api.client.patch(path, json={"format": "sell", "price": 500}, headers=api.headers())
    assert changed.status_code == 200, changed.text
    assert changed.json()["title"] == item["title"]
    own = await api.client.get("/api/v1/users/me/listings", headers=api.headers())
    assert own.status_code == 200 and len(own.json()["items"]) == 1
    assert not (await api.client.get("/api/v1/users/me/listings", headers=api.headers(1))).json()["items"]


@pytest.mark.parametrize("format", ["give", "sell", "exchange", "service"])
async def test_full_status_matrix(api, format):
    """Перебирает переходы статусов для каждого формата и сверяет разрешённые 200 и конфликты 409."""
    price = 100 if format == "sell" else 0
    item = await api.listing(format=format, price=price)
    path = f"/api/v1/listings/{item['id']}/status"
    allowed = {"active": {"reserved", "archived"}, "reserved": {"active", "completed"},
               "completed": {"active"}, "archived": {"active"}}
    states = ["active", "archived"] if format == "service" else list(allowed)
    for source in states:
        for target in allowed:
            async with api.db.sessions() as session:
                record = await session.get(Listing, UUID(item["id"]))
                record.status = source
                await session.commit()
            response = await api.client.patch(path, json={"expected_status": source, "status": target}, headers=api.headers())
            success = target in allowed[source] and (format != "service" or target in {"active", "archived"})
            assert response.status_code == (200 if success else 409), (source, target, response.text)


async def test_chat_privacy_idempotency_and_reading(api):
    """Проверяет доступ участников, запрет чата с собой, повторы сообщений и движение метки только вперёд."""
    item = await api.listing()
    chat = await api.chat(item["id"])
    repeated = await api.client.post("/api/v1/chats", json={"listing_id": item["id"]}, headers=api.headers(1))
    assert repeated.status_code == 200 and repeated.json()["id"] == chat["id"]
    base = f"/api/v1/chats/{chat['id']}"
    assert (await api.client.get(base + "/messages", headers=api.headers(2))).status_code == 404
    assert (await api.client.post("/api/v1/chats", json={"listing_id": item["id"]}, headers=api.headers())).status_code == 409
    data = {"text": "  Привет  ", "client_message_id": str(uuid4())}
    first = await api.client.post(base + "/messages", json=data, headers=api.headers(1))
    again = await api.client.post(base + "/messages", json=data, headers=api.headers(1))
    assert first.status_code == 201 and again.status_code == 200
    assert first.json() == again.json()
    data["text"] = "Другой текст"
    assert (await api.client.post(base + "/messages", json=data, headers=api.headers(1))).status_code == 409
    last = await api.client.post(base + "/messages", json={"text": "Второе", "client_message_id": str(uuid4())}, headers=api.headers(1))
    assert last.status_code == 201
    for message in (last, first):
        response = await api.client.patch(base + "/read", json={"last_read_message_id": message.json()["id"]}, headers=api.headers())
        assert response.status_code == 200
        assert response.json()["last_read_message_id"] == last.json()["id"]
    assert (await api.client.get("/api/v1/chats", headers=api.headers())).json()["items"][0]["unread"] == 0
    assert (await api.client.post(base + "/messages", json={"text": " ", "client_message_id": str(uuid4())}, headers=api.headers())).status_code == 422


async def test_cross_chat_read_is_rejected(api):
    """Проверяет, что сообщение другого чата нельзя использовать для прочтения: ответ 404."""
    item = await api.listing()
    first, second = await api.chat(item["id"]), await api.chat(item["id"], buyer=2)
    message = await api.client.post(f"/api/v1/chats/{first['id']}/messages",
        json={"text": "Привет", "client_message_id": str(uuid4())}, headers=api.headers(1))
    response = await api.client.patch(f"/api/v1/chats/{second['id']}/read",
        json={"last_read_message_id": message.json()["id"]}, headers=api.headers())
    assert response.status_code == 404


async def test_photo_validation_and_limit(api):
    """Проверяет пустой/повреждённый файл, неверный MIME, размер, авторство и лимит пяти фотографий."""
    item = await api.listing()
    path = f"/api/v1/listings/{item['id']}/photos"
    for data, mime, code in [(b"", "image/png", 422), (b"broken", "image/png", 422),
                              (png(), "image/jpeg", 415), (b"x" * (5 * 1024 * 1024 + 1), "image/png", 413)]:
        response = await api.client.post(path, files={"file": ("test.png", data, mime)}, headers=api.headers())
        assert response.status_code == code, response.text
    assert (await api.client.post(path, files={"file": ("t.png", png(), "image/png")}, headers=api.headers(1))).status_code == 403
    for _ in range(5):
        response = await api.client.post(path, files={"file": ("t.png", png(), "image/png")}, headers=api.headers())
        assert response.status_code == 201, response.text
    assert (await api.client.post(path, files={"file": ("t.png", png(), "image/png")}, headers=api.headers())).status_code == 409


async def test_commit_failure_rolls_back(api, monkeypatch):
    """Имитирует сбой после flush: API даёт 500, запись откатывается, следующий запрос работает."""
    async def fail(db):
        """Подменяет сохранение ошибкой после отправки изменений в БД, но до commit."""
        await db.session.flush()
        raise RuntimeError("simulated-write-failure")
    with monkeypatch.context() as patch:
        patch.setattr(DbRepository, "save", fail)
        response = await api.client.post("/api/v1/listings", json={"title": "Стул", "description": "Один",
            "category": "furniture", "format": "give", "price": 0}, headers=api.headers())
    assert response.status_code == 500
    async with api.db.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(Listing)) == 0
    await api.listing()


async def test_duplicate_registration_is_atomic(api):
    """Проверяет, что повтор почты с другим регистром даёт 409 без нового пользователя или общежития."""
    data = {"name": "Другой", "email": api.users[0]["profile"]["email"].upper(), "password": "password123",
            "university_id": api.university, "dormitory_name": "Не создавать"}
    response = await api.client.post("/api/v1/auth/register", json=data)
    assert response.status_code == 409
    async with api.db.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(Dormitory)) == 1
        assert await session.scalar(select(func.count()).select_from(User)) == 3


async def test_unknown_query_and_content_types(api):
    """Проверяет отказ 422 для лишнего query-параметра и 415 для JSON под видом text/plain."""
    assert (await api.client.get("/api/v1/users/me?unexpected=1", headers=api.headers())).status_code == 422
    response = await api.client.post("/api/v1/auth/login", content='{"email":"a@example.com","password":"password123"}',
        headers={"Content-Type": "text/plain"})
    assert response.status_code == 415
