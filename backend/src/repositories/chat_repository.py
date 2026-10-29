from sqlalchemy import and_, func, or_, select, tuple_
from sqlalchemy.orm import aliased, selectinload

from src.models import Chat, ChatRead, Listing, Message


class ChatRepository:
    """Извлекает чаты, сообщения и метки прочтения, собирает превью и счётчики для списка чатов."""

    def __init__(self, session):
        self.session = session

    async def get(self, chat_id, lock=False):
        query = select(Chat).where(Chat.id == chat_id).options(
            selectinload(Chat.listing), selectinload(Chat.buyer)
        ).execution_options(populate_existing=True)
        if lock:
            query = query.with_for_update(of=Chat)
        return await self.session.scalar(query)

    async def by_listing(self, listing_id, buyer_id):
        return await self.session.scalar(select(Chat).where(
            Chat.listing_id == listing_id, Chat.buyer_id == buyer_id
        ))

    async def repeated_message(self, chat_id, sender_id, key):
        """Ищет ранее отправленное сообщение по ключу повтора внутри чата и отправителя."""
        return await self.session.scalar(select(Message).where(
            Message.chat_id == chat_id, Message.sender_id == sender_id,
            Message.client_message_id == key,
        ))

    async def message(self, chat_id, message_id):
        return await self.session.scalar(select(Message).where(
            Message.chat_id == chat_id, Message.id == message_id
        ))

    def _messages_query(self, chat_id):
        return select(Message).where(Message.chat_id == chat_id)

    async def messages(self, chat_id, offset, size):
        """Выбирает страницу истории от новых сообщений к старым; при равном времени сравнивает ID."""
        query = (
            self._messages_query(chat_id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .offset(offset).limit(size)
        )
        return list((await self.session.scalars(query)).all())

    async def latest(self, chat_id):
        return await self.session.scalar(self._messages_query(chat_id).order_by(
            Message.created_at.desc(), Message.id.desc()
        ).limit(1))

    async def read_marker(self, chat_id, user_id):
        return await self.session.get(ChatRead, (chat_id, user_id))

    async def summary(self, chat_id, user_id):
        """Извлекает одну строку превью доступного участнику чата для формирования ответа API."""
        query, _ = self._summaries_query(user_id)
        return (await self.session.execute(query.where(Chat.id == chat_id))).one()

    async def list(self, user_id, offset, size):
        """Выбирает страницу чатов участника по убыванию последней активности, затем ID."""
        query, activity = self._summaries_query(user_id)
        query = query.order_by(activity.desc(), Chat.id.desc()).offset(offset).limit(size)
        return list((await self.session.execute(query)).all())

    def _summaries_query(self, user_id):
        """Строит запрос чатов участника с последним сообщением и числом непрочитанных.

        Возвращает запрос и поле активности для сортировки; сам SQL здесь не выполняется.
        """
        ranked = self._ranked_messages()
        unread = self._unread_counts(user_id)
        # У пустого чата активность равна времени создания, у остальных — последнему сообщению.
        activity = func.coalesce(Message.created_at, Chat.created_at).label("activity")
        # LEFT JOIN сохраняет пустые чаты; position=1 оставляет только последнее сообщение.
        query = (
            select(Chat, activity, Message, func.coalesce(unread.c.unread_count, 0))
            .join(Listing)
            .outerjoin(ranked, and_(ranked.c.chat_id == Chat.id, ranked.c.position == 1))
            .outerjoin(Message, Message.id == ranked.c.id)
            .outerjoin(unread, unread.c.chat_id == Chat.id)
            .where(or_(Chat.buyer_id == user_id, Listing.owner_id == user_id))
            .options(selectinload(Chat.buyer), selectinload(Chat.listing).selectinload(Listing.owner))
        )
        return query, activity

    @staticmethod
    def _ranked_messages():
        """Строит подзапрос с нумерацией сообщений отдельно для каждого чата.

        Позиция 1 — самое новое; ID разрешает совпадения времени создания.
        """
        position = func.row_number().over(
            partition_by=Message.chat_id,
            order_by=[Message.created_at.desc(), Message.id.desc()],
        )
        return select(Message.id, Message.chat_id, position.label("position")).subquery()

    @staticmethod
    def _unread_counts(user_id):
        """Строит подзапрос количества чужих сообщений после метки прочтения в каждом чате.

        Без метки учитываются все чужие сообщения; свои сообщения не увеличивают счётчик.
        """
        # Это вторая ссылка на messages: она представляет сообщение из метки прочтения.
        read_message = aliased(Message)
        newer_than_read = tuple_(Message.created_at, Message.id) > tuple_(
            read_message.created_at, read_message.id
        )
        return (
            select(Message.chat_id, func.count().label("unread_count"))
            .outerjoin(
                ChatRead,
                and_(ChatRead.chat_id == Message.chat_id, ChatRead.user_id == user_id),
            )
            .outerjoin(read_message, read_message.id == ChatRead.last_read_message_id)
            .where(
                Message.sender_id != user_id,
                or_(ChatRead.last_read_message_id.is_(None), newer_than_read),
            )
            .group_by(Message.chat_id)
            .subquery()
        )
