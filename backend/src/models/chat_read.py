from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, ForeignKeyConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


class ChatRead(Base):
    __tablename__ = "chat_reads"
    __table_args__ = (
        ForeignKeyConstraint(
            ["last_read_message_id", "chat_id"], ["messages.id", "messages.chat_id"],
            ondelete="RESTRICT",
        ),
        Index("ix_chat_reads_message_chat", "last_read_message_id", "chat_id"),
    )

    chat_id: Mapped[UUID] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True)
    last_read_message_id: Mapped[UUID] = mapped_column()
    chat: Mapped["Chat"] = relationship(back_populates="read_markers", foreign_keys=[chat_id])
    user: Mapped["User"] = relationship(back_populates="chat_reads")
    last_read_message: Mapped["Message"] = relationship(
        foreign_keys=[last_read_message_id, chat_id], viewonly=True
    )
