from __future__ import annotations

from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, CreatedAtMixin, IdentityMixin


class Message(IdentityMixin, CreatedAtMixin, Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("chat_id", "sender_id", "client_message_id"),
        UniqueConstraint("id", "chat_id"),  # Цель составного FK метки прочтения.
        CheckConstraint("text ~ '[^[:space:]]'", name="text_not_blank"),
        Index("ix_messages_chat_created_id", "chat_id", "created_at", "id"),
    )

    chat_id: Mapped[UUID] = mapped_column(ForeignKey("chats.id", ondelete="RESTRICT"))
    sender_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    text: Mapped[str] = mapped_column(String(4000))
    client_message_id: Mapped[UUID]
    chat: Mapped["Chat"] = relationship(back_populates="messages")
    sender: Mapped["User"] = relationship(back_populates="messages")
