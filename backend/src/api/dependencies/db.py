from fastapi import Depends, Request

from src.repositories.db_repository import DbRepository


async def get_session(request: Request):
    async with request.app.state.database.sessions() as session:
        try:
            yield session
        finally:
            await session.rollback()


def get_db(session=Depends(get_session)):
    return DbRepository(session)

