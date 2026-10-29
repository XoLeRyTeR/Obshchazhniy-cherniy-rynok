from __future__ import annotations

from uuid import UUID

from sqlalchemy import CheckConstraint, Computed, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, IdentityMixin
from src.models.university import NAME_KEY_SQL


class Dormitory(IdentityMixin, Base):
    __tablename__ = "dormitories"
    __table_args__ = (
        UniqueConstraint("university_id", "name_key"),
        CheckConstraint("char_length(name_key) > 0", name="name_not_blank"),
        Index("ix_dormitories_university_name_id", "university_id", "name_key", "id"),
    )

    university_id: Mapped[UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"))
    name: Mapped[str] = mapped_column(String(80))
    name_key: Mapped[str] = mapped_column(Text, Computed(NAME_KEY_SQL, persisted=True))
    university: Mapped["University"] = relationship(back_populates="dormitories")
    users: Mapped[list["User"]] = relationship(back_populates="dormitory", passive_deletes="all")
    listings: Mapped[list["Listing"]] = relationship(back_populates="dormitory", passive_deletes="all")
