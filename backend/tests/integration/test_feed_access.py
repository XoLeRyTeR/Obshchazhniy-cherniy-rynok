from tests.conftest import Harness


async def test_common_feed_is_authorized_but_not_personalized(api: Harness) -> None:
    """Проверяет одинаковую ленту у разных аккаунтов, сохранение фильтров и отказ без авторизации."""
    listing = await api.listing(title="Общий учебник", category="books")
    await api.listing(title="Лампа", category="electronics", owner=1)
    path = "/api/v1/listings?category=books&offset=0&size=1"
    anonymous = await api.client.get(path)
    assert anonymous.status_code == 401
    responses = [await api.client.get(path, headers=api.headers(index)) for index in range(3)]
    assert all(response.status_code == 200 for response in responses)
    assert all(response.json() == responses[0].json() for response in responses)
    assert [item["id"] for item in responses[0].json()["items"]] == [listing["id"]]
