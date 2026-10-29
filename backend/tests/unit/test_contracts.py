from datetime import datetime, timezone
from uuid import uuid4

import jwt
import pytest
from pydantic import ValidationError

from src.core.config import Settings
from src.core.errors import AppError
from src.core.security import issue_token, read_token
from src.schemas.auth import Register
from src.schemas.chats import MessageCreate
from src.schemas.listings import ListingCreate, ListingPatch
from src.schemas.users import ProfilePatch


def settings():
    """Создаёт изолированные настройки для проверки схем и JWT без подключения к БД."""
    return Settings(_env_file=None, database_url="postgresql+asyncpg://test@localhost/mobilki_test",
                    jwt_secret="unit-test-secret-with-more-than-32-characters")


@pytest.mark.parametrize("format,price,valid", [
    ("sell", 0, False), ("sell", 1, True), ("sell", 1_000_000_000, True),
    ("sell", 1_000_000_001, False), ("give", 0, True), ("give", 1, False),
    ("exchange", 0, True), ("exchange", 1, False), ("service", 0, True),
    ("service", 1, True), ("give", -1, False), ("sell", True, False),
    ("sell", "100", False), ("sell", 1.5, False), ("unknown", 0, False),
])
def test_listing_price_contract(format, price, valid):
    """Проверяет цену по формату: целые копейки в границах, положительная продажа, бесплатная отдача/обмен."""
    data = dict(title="Стул", description="Описание", category="furniture", format=format, price=price)
    if valid:
        assert ListingCreate.model_validate(data).price == price
    else:
        with pytest.raises(ValidationError):
            ListingCreate.model_validate(data)


@pytest.mark.parametrize("field,limit", [("title", 120), ("description", 5000)])
@pytest.mark.parametrize("boundary", [0, 1, -1])
def test_listing_text_boundaries(field, limit, boundary):
    """Проверяет длину заголовка/описания на максимуме, ниже и выше допустимой границы."""
    data = dict(title="Стул", description="Описание", category="furniture", format="give", price=0)
    data[field] = "x" * (limit + boundary)
    if boundary > 0:
        with pytest.raises(ValidationError):
            ListingCreate.model_validate(data)
    else:
        ListingCreate.model_validate(data)


@pytest.mark.parametrize("model,data", [
    (ListingPatch, {}), (ListingPatch, {"title": None}), (ListingPatch, {"exchange": "книга"}),
    (ListingPatch, {"place": "Холл"}), (ListingPatch, {"owner_id": str(uuid4())}),
    (ProfilePatch, {}), (ProfilePatch, {"name": "  "}), (ProfilePatch, {"email": "new@example.com"}),
    (ProfilePatch, {"university_id": str(uuid4())}),
    (ProfilePatch, {"dormitory_id": str(uuid4()), "dormitory_name": "4"}),
    (ProfilePatch, {"name": None}),
])
def test_invalid_partial_updates(model, data):
    """Проверяет отказ схем PATCH на пустые, null, лишние поля и несовместимый выбор общежития."""
    with pytest.raises(ValidationError):
        model.model_validate(data)


@pytest.mark.parametrize("length,valid", [(0, False), (1, True), (4000, True), (4001, False)])
def test_message_boundaries(length, valid):
    """Проверяет длину сообщения: от 1 до 4000 символов, с отказом для пустого и слишком длинного."""
    data = {"text": "x" * length, "client_message_id": str(uuid4())}
    if valid:
        MessageCreate.model_validate(data)
    else:
        with pytest.raises(ValidationError):
            MessageCreate.model_validate(data)


def test_registration_normalization():
    """Проверяет нормализацию почты, имени и общежития без изменения пробелов в самом пароле."""
    data = Register.model_validate(dict(email=" A@Example.com ", password=" password ",
                                          name="  Андрей   Куликов ", university_id=str(uuid4()),
                                          dormitory_name="  Северный   кампус "))
    assert str(data.email) == "a@example.com"
    assert data.name == "Андрей Куликов"
    assert data.dormitory_name == "Северный кампус"
    assert data.password == " password "


def test_jwt_is_stateless_unique_and_expired_tokens_rejected():
    """Проверяет разные JWT для одного пользователя, отсутствие sid и отказ просроченному токену."""
    config = settings()
    user_id = uuid4()
    first, second = issue_token(user_id, config), issue_token(user_id, config)
    assert first != second
    assert read_token(first, config) == user_id
    data = jwt.decode(first, config.jwt_secret.get_secret_value(), algorithms=["HS256"])
    assert "sid" not in data
    data["exp"] = int(datetime.now(timezone.utc).timestamp())
    expired = jwt.encode(data, config.jwt_secret.get_secret_value(), algorithm="HS256")
    with pytest.raises(AppError) as error:
        read_token(expired, config)
    assert error.value.status == 401


@pytest.mark.parametrize("claim,value", [("sub", "invalid"), ("jti", None), ("iat", True), ("exp", "123")])
def test_invalid_jwt_claims(claim, value):
    """Проверяет отказ JWT при неверных значении или типе обязательных sub/jti/iat/exp."""
    config = settings()
    token = issue_token(uuid4(), config)
    data = jwt.decode(token, config.jwt_secret.get_secret_value(), algorithms=["HS256"])
    data[claim] = value
    token = jwt.encode(data, config.jwt_secret.get_secret_value(), algorithm="HS256")
    with pytest.raises(AppError):
        read_token(token, config)

