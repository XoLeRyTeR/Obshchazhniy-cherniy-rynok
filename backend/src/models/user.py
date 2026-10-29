from __future__ import annotations

from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, CreatedAtMixin, IdentityMixin


class User(IdentityMixin, CreatedAtMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("email = lower(btrim(email)) AND char_length(email) > 0", name="email_normalized"),
        CheckConstraint("name ~ '[^[:space:]]'", name="name_not_blank"),
        CheckConstraint("char_length(password_hash) > 0", name="password_hash_not_empty"),
    )

    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(String(80))
    dormitory_id: Mapped[UUID] = mapped_column(ForeignKey("dormitories.id", ondelete="RESTRICT"), index=True)
    dormitory: Mapped["Dormitory"] = relationship(back_populates="users")
    listings: Mapped[list["Listing"]] = relationship(back_populates="owner", passive_deletes="all")
    buyer_chats: Mapped[list["Chat"]] = relationship(back_populates="buyer", passive_deletes="all")
    messages: Mapped[list["Message"]] = relationship(back_populates="sender", passive_deletes="all")
    chat_reads: Mapped[list["ChatRead"]] = relationship(back_populates="user", passive_deletes="all")
