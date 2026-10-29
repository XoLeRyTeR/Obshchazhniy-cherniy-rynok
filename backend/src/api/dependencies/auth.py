from collections import deque
from time import monotonic

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.api.dependencies.db import get_db
from src.core.errors import AppError, unauthorized
from src.core.security import read_token

bearer = HTTPBearer(auto_error=False)


async def current_user(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
                       db=Depends(get_db)):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized()
    user_id = read_token(credentials.credentials, request.app.state.settings)
    user = await db.users.get(user_id)
    if user is None:
        raise unauthorized()
    return user


async def auth_rate(request: Request):
    settings = request.app.state.settings
    now = monotonic()
    buckets = request.app.state.auth_buckets
    key = (request.client.host if request.client else "unknown", request.url.path)
    # Ограничение памяти однопроцессного MVP; при нескольких workers — лимит на reverse proxy.
    if key not in buckets and len(buckets) >= 10000:
        expired = [k for k, values in buckets.items() if not values or values[-1] <= now - settings.auth_rate_window]
        for k in expired:
            buckets.pop(k, None)
        if len(buckets) >= 10000:
            raise AppError(429, "rate_limit", "Попробуйте позже")
    values = buckets.setdefault(key, deque())
    while values and values[0] <= now - settings.auth_rate_window:
        values.popleft()
    if len(values) >= settings.auth_rate_limit:
        raise AppError(429, "rate_limit", "Слишком много попыток, попробуйте позже")
    values.append(now)

