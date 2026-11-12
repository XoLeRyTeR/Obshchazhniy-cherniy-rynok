from collections.abc import AsyncIterator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.db_repository import DbRepository


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.database.sessions() as session:
        try:
            yield session
        finally:
            await session.rollback()


def get_db(session: AsyncSession = Depends(get_session)) -> DbRepository:
    return DbRepository(session)

