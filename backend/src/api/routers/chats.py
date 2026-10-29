from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from src.api.dependencies.auth import current_user
from src.api.dependencies.services import service
from src.schemas.chats import ChatCreate, ChatOut, MessageCreate, MessageOut, ReadChange, ReadOut
from src.schemas.common import Page, PageQuery
from src.services.chat_service import ChatService

router = APIRouter(prefix="/chats", tags=["Чаты"])
User = Annotated[object, Depends(current_user)]
Chats = Annotated[ChatService, Depends(service(ChatService))]


@router.post("", response_model=ChatOut, status_code=201, responses={200: {"model": ChatOut}})
async def create(data: ChatCreate, response: Response, user: User, chats: Chats):
    """Открывает чат покупателя с автором объявления: 201 для нового, 200 для существующего.

    Нужна авторизация; написать самому себе нельзя, это конфликт 409.
    """
    item, created = await chats.create(data.listing_id, user.id)
    response.status_code = 201 if created else 200
    return item


@router.get("", response_model=Page[ChatOut])
async def list_chats(user: User, params: Annotated[PageQuery, Query()], chats: Chats):
    """Возвращает страницу чатов текущего пользователя с превью и счётчиком непрочитанного.

    Порядок — по убыванию последней активности; пагинация — offset и size.
    """
    return await chats.list(user.id, params)


@router.get("/{chat_id}/messages", response_model=Page[MessageOut])
async def history(chat_id: UUID, user: User, params: Annotated[PageQuery, Query()], chats: Chats):
    """Возвращает участнику страницу сообщений чата от новых к старым; чужой чат даёт 404."""
    return await chats.history(chat_id, user.id, params)


@router.post("/{chat_id}/messages", response_model=MessageOut, status_code=201,
             responses={200: {"model": MessageOut}})
async def send(chat_id: UUID, data: MessageCreate, response: Response, user: User, chats: Chats):
    """Отправляет сообщение от участника чата, возвращает 201 или 200 при повторе.

    Повторный client_message_id с тем же текстом не создаёт дубль; другой текст даёт 409.
    """
    item, created = await chats.send(chat_id, user.id, data)
    response.status_code = 201 if created else 200
    return item


@router.patch("/{chat_id}/read", response_model=ReadOut)
async def read(chat_id: UUID, data: ReadChange, user: User, chats: Chats):
    """Продвигает метку прочтения участника до сообщения этого чата, не перемещая её назад."""
    return await chats.read(chat_id, user.id, data.last_read_message_id)

