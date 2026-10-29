from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, CreatedAtMixin, IdentityMixin


class Chat(IdentityMixin, CreatedAtMixin, Base):
    __tablename__ = "chats"
    __table_args__ = (
        UniqueConstraint("listing_id", "buyer_id"),
        Index("ix_chats_buyer_created_id", "buyer_id", "created_at", "id"),
    )

    listing_id: Mapped[UUID] = mapped_column(ForeignKey("listings.id", ondelete="RESTRICT"))
    buyer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    listing: Mapped["Listing"] = relationship(back_populates="chats")
    buyer: Mapped["User"] = relationship(back_populates="buyer_chats")
    messages: Mapped[list["Message"]] = relationship(back_populates="chat", passive_deletes="all")
    read_markers: Mapped[list["ChatRead"]] = relationship(back_populates="chat", passive_deletes="all")
