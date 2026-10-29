from __future__ import annotations

from sqlalchemy import CheckConstraint, Computed, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, IdentityMixin

# PostgreSQL вычисляет ключ сам, включая вставки в обход Python.
NAME_KEY_SQL = "lower(btrim(regexp_replace(name, '[[:space:]]+', ' ', 'g')))"


class University(IdentityMixin, Base):
    __tablename__ = "universities"
    __table_args__ = (
        CheckConstraint("char_length(name_key) > 0", name="name_not_blank"),
        Index("ix_universities_name_key_id", "name_key", "id"),
    )

    name: Mapped[str] = mapped_column(String(200))
    name_key: Mapped[str] = mapped_column(
        Text, Computed(NAME_KEY_SQL, persisted=True), unique=True
    )
    dormitories: Mapped[list["Dormitory"]] = relationship(
        back_populates="university", passive_deletes="all"
    )
