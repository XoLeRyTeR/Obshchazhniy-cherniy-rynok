from enum import StrEnum

from sqlalchemy import Enum


class ListingFormat(StrEnum):
    SELL = "sell"
    GIVE = "give"
    EXCHANGE = "exchange"
    SERVICE = "service"


class ListingStatus(StrEnum):
    ACTIVE = "active"
    RESERVED = "reserved"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Category(StrEnum):
    BOOKS = "books"
    ELECTRONICS = "electronics"
    FURNITURE = "furniture"
    CLOTHES = "clothes"
    DISHES = "dishes"
    FOOD = "food"
    OTHER = "other"


def enum_column(enum_class: type[StrEnum], name: str) -> Enum:
    """Храним API-коды, а допустимые значения защищаем CHECK в БД."""
    return Enum(
        enum_class, name=name, native_enum=False, create_constraint=True,
        validate_strings=True, values_callable=lambda cls: [item.value for item in cls],
    )
