from __future__ import annotations

from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, IdentityMixin


class ListingPhoto(IdentityMixin, Base):
    __tablename__ = "listing_photos"
    __table_args__ = (
        UniqueConstraint("listing_id", "position"),
        CheckConstraint("position BETWEEN 0 AND 4", name="position_slot"),
        CheckConstraint("storage_key ~ '^[a-zA-Z0-9_-]+[.](jpg|jpeg|png|webp)$'", name="safe_storage_key"),
    )

    listing_id: Mapped[UUID] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"))
    storage_key: Mapped[str] = mapped_column(String(100), unique=True)
    position: Mapped[int] = mapped_column(SmallInteger)
    listing: Mapped["Listing"] = relationship(back_populates="photos")
