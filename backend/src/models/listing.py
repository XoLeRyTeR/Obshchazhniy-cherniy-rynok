from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, CreatedAtMixin, IdentityMixin
from src.models.enums import Category, ListingFormat, ListingStatus, enum_column


class Listing(IdentityMixin, CreatedAtMixin, Base):
    __tablename__ = "listings"
    __table_args__ = (
        CheckConstraint("title ~ '[^[:space:]]'", name="title_not_blank"),
        CheckConstraint("description ~ '[^[:space:]]'", name="description_not_blank"),
        CheckConstraint("price BETWEEN 0 AND 1000000000", name="price_range"),
        CheckConstraint("(format = 'sell' AND price > 0) OR (format IN ('give', 'exchange') AND price = 0) OR format = 'service'", name="price_matches_format"),
        CheckConstraint("format <> 'service' OR status IN ('active', 'archived')", name="service_status"),
        CheckConstraint("updated_at >= created_at", name="update_after_creation"),
        Index("ix_listings_dormitory_status_created_id", "dormitory_id", "status", "created_at", "id"),
        Index("ix_listings_owner_created_id", "owner_id", "created_at", "id"),
        Index("ix_listings_feed_created_id", "created_at", "id", postgresql_where=text("status IN ('active', 'reserved')")),
    )

    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    dormitory_id: Mapped[UUID] = mapped_column(ForeignKey("dormitories.id", ondelete="RESTRICT"))
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(5000))
    category: Mapped[Category] = mapped_column(enum_column(Category, "category"))
    format: Mapped[ListingFormat] = mapped_column(enum_column(ListingFormat, "format"))
    price: Mapped[int] = mapped_column(Integer)
    status: Mapped[ListingStatus] = mapped_column(enum_column(ListingStatus, "status"), server_default=text("'active'"))
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    owner: Mapped["User"] = relationship(back_populates="listings")
    dormitory: Mapped["Dormitory"] = relationship(back_populates="listings")
    photos: Mapped[list["ListingPhoto"]] = relationship(back_populates="listing", order_by="ListingPhoto.position", passive_deletes="all")
    chats: Mapped[list["Chat"]] = relationship(back_populates="listing", passive_deletes="all")
