from uuid import UUID, uuid4

import pytest

from src.models import Dormitory, University


async def test_offset_pages_for_catalog_own_listings_and_messages(api):
    """Проверяет порядок и offset/size для вузов, общежитий, своих объявлений и сообщений.

    Сверяет страницу по умолчанию и пустой результат при смещении за концом списка.
    """
    async with api.db.sessions() as session:
        session.add(University(name="Ярославский университет"))
        session.add(Dormitory(name="Северный", university_id=UUID(api.university)))
        await session.commit()

    first_item = await api.listing(title="Первое")
    second_item = await api.listing(title="Второе")
    conversation = await api.chat(first_item["id"])
    message_path = f"/api/v1/chats/{conversation['id']}/messages"
    message_ids = []
    for text in ("Первое", "Второе"):
        response = await api.client.post(message_path, headers=api.headers(1), json={
            "text": text, "client_message_id": str(uuid4()),
        })
        assert response.status_code == 201, response.text
        message_ids.append(response.json()["id"])

    cases = [
        ("/api/v1/universities", {}, ["ИГЭУ", "Ярославский университет"], "name"),
        ("/api/v1/dormitories", {"university_id": api.university}, ["4", "Северный"], "name"),
        ("/api/v1/users/me/listings", {}, [second_item["id"], first_item["id"]], "id"),
        (message_path, {}, list(reversed(message_ids)), "id"),
    ]
    for path, filters, expected, field in cases:
        default = await api.client.get(path, params=filters, headers=api.headers())
        assert default.status_code == 200, default.text
        assert set(default.json()) == {"items"}
        assert [item[field] for item in default.json()["items"]] == expected
        for offset in (0, 1, 2, 100):
            response = await api.client.get(path, headers=api.headers(), params={
                **filters, "offset": offset, "size": 1,
            })
            assert response.status_code == 200, response.text
            assert [item[field] for item in response.json()["items"]] == expected[offset:offset + 1]


@pytest.mark.parametrize("params", [
    {"offset": -1}, {"offset": "1.5"}, {"offset": "abc"},
    {"offset": 9_223_372_036_854_775_808},
    {"size": 0}, {"size": -1}, {"size": 101}, {"size": "1.5"}, {"size": "abc"},
    {"cursor": "old"}, {"limit": 20},
])
async def test_all_lists_validate_offset_and_size(api, params):
    """Проверяет 422 во всех списках для неверных offset/size и устаревших cursor/limit."""
    listing = await api.listing()
    conversation = await api.chat(listing["id"])
    paths = [
        ("/api/v1/universities", {}),
        ("/api/v1/dormitories", {"university_id": api.university}),
        ("/api/v1/listings", {}), ("/api/v1/users/me/listings", {}), ("/api/v1/chats", {}),
        (f"/api/v1/chats/{conversation['id']}/messages", {}),
    ]
    for path, filters in paths:
        response = await api.client.get(path, params={**filters, **params}, headers=api.headers())
        assert response.status_code == 422, (path, params, response.text)
