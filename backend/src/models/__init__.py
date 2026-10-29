"""Импорт всех сущностей регистрирует таблицы для Alembic и SQLAlchemy."""

from src.db.base import Base
from src.models.university import University
from src.models.dormitory import Dormitory
from src.models.user import User
from src.models.listing import Listing
from src.models.listing_photo import ListingPhoto
from src.models.chat import Chat
from src.models.message import Message
from src.models.chat_read import ChatRead
from src.models.enums import Category, ListingFormat, ListingStatus

__all__ = [
    "Base", "University", "Dormitory", "User", "Listing",
    "ListingPhoto", "Chat", "Message", "ChatRead", "Category", "ListingFormat", "ListingStatus",
]
