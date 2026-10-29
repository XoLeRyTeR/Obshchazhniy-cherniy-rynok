from datetime import datetime, timedelta, timezone

from src.core.errors import AppError, missing
from src.models import Chat, ChatRead, Message
from src.schemas.chats import MessageOut, ReadOut
from src.services.listing_service import ListingService
from src.services.views import chat


class ChatService:
    """Управляет перепиской: проверяет участников, повторы отправки и прочтение."""

    def __init__(self, db, settings):
        """Принимает репозитории и настройки приложения."""
        self.db, self.settings = db, settings

    async def accessible(self, chat_id, user_id, lock=False):
        """Возвращает чат только покупателю или автору объявления, иначе выдаёт 404.

        При изменениях lock=True блокирует строку чата до завершения транзакции.
        """
        item = await self.db.chats.get(chat_id, lock=lock)
        if item is None or user_id not in (item.buyer_id, item.listing.owner_id):
            raise missing()
        return item

    async def summary(self, chat_id, user_id):
        """Формирует карточку одного чата с собеседником, превью и непрочитанными."""
        row = await self.db.chats.summary(chat_id, user_id)
        return chat(row, user_id)

    async def create(self, listing_id, user_id):
        """Создаёт чат по объявлению или возвращает существующий и признак создания.

        Запрещает чат с самим собой; новый чат разрешён для активной или забронированной вещи.
        """
        item = await ListingService(self.db, self.settings).accessible(listing_id, user_id, lock=True)
        if item.owner_id == user_id:
            raise AppError(409, "self_chat", "Нельзя написать самому себе")
        existing = await self.db.chats.by_listing(listing_id, user_id)
        if existing:
            return await self.summary(existing.id, user_id), False
        if item.status not in {"active", "reserved"}:
            raise missing()
        new_chat = Chat(listing_id=listing_id, buyer_id=user_id)
        self.db.add(new_chat)
        await self.db.save()
        return await self.summary(new_chat.id, user_id), True

    async def list(self, user_id, params):
        """Возвращает страницу чатов пользователя от наиболее активных к старым."""
        rows = await self.db.chats.list(user_id, params.offset, params.size)
        return {"items": [chat(row, user_id) for row in rows]}

    async def history(self, chat_id, user_id, params):
        """Проверяет участие в чате и возвращает страницу сообщений от новых к старым."""
        await self.accessible(chat_id, user_id)
        items = await self.db.chats.messages(chat_id, params.offset, params.size)
        return {"items": [MessageOut.model_validate(item) for item in items]}

    async def send(self, chat_id, user_id, data):
        """Сохраняет сообщение участника и возвращает его вместе с признаком создания.

        Повтор с тем же client_message_id и текстом не создаёт дубль; другой текст даёт 409.
        """
        await self.accessible(chat_id, user_id, lock=True)
        existing = await self.db.chats.repeated_message(chat_id, user_id, data.client_message_id)
        if existing:
            if existing.text != data.text:
                raise AppError(409, "message_key_conflict", "Этот ключ уже использован для другого сообщения")
            return MessageOut.model_validate(existing), False
        latest = await self.db.chats.latest(chat_id)
        now = datetime.now(timezone.utc)
        # Даже при совпадении времени новое сообщение должно следовать после предыдущего.
        if latest and now <= latest.created_at:
            now = latest.created_at + timedelta(microseconds=1)
        message = Message(chat_id=chat_id, sender_id=user_id, text=data.text,
                          client_message_id=data.client_message_id, created_at=now)
        self.db.add(message)
        await self.db.save()
        return MessageOut.model_validate(message), True

    async def read(self, chat_id, user_id, message_id):
        """Отмечает сообщения прочитанными до указанного сообщения этого же чата.

        Метка движется только вперёд: запоздавший запрос не возвращает непрочитанные.
        """
        await self.accessible(chat_id, user_id, lock=True)
        message = await self.db.chats.message(chat_id, message_id)
        if message is None:
            raise missing()
        marker = await self.db.chats.read_marker(chat_id, user_id)
        if marker is None:
            marker = ChatRead(chat_id=chat_id, user_id=user_id, last_read_message_id=message_id)
            self.db.add(marker)
        else:
            previous = await self.db.chats.message(chat_id, marker.last_read_message_id)
            if (message.created_at, message.id) > (previous.created_at, previous.id):
                marker.last_read_message_id = message_id
        await self.db.save()
        return ReadOut.model_validate(marker)

