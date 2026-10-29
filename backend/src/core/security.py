from datetime import datetime, timezone
from uuid import UUID, uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from src.core.errors import unauthorized

hasher = PasswordHasher()
# Одинаковая работа проверки для неизвестной почты и неверного пароля.
dummy_hash = hasher.hash("not-an-actual-user-password")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def issue_token(user_id: UUID, settings) -> str:
    now = int(datetime.now(timezone.utc).timestamp())
    return jwt.encode(
        {"sub": str(user_id), "iat": now, "exp": now + settings.access_token_ttl,
         "jti": str(uuid4()), "kind": "access"},
        settings.jwt_secret.get_secret_value(), algorithm="HS256",
    )


def read_token(token: str, settings) -> UUID:
    try:
        data = jwt.decode(token, settings.jwt_secret.get_secret_value(), algorithms=["HS256"],
                          options={"require": ["sub", "iat", "exp", "jti"]})
        if data.get("kind") != "access" or any(type(data[k]) is not int for k in ("iat", "exp")):
            raise ValueError()
        UUID(data["jti"])
        return UUID(data["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError, AttributeError):
        raise unauthorized() from None

