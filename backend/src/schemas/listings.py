from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from src.models.enums import Category, ListingFormat, ListingStatus
from src.schemas.common import PageQuery, Patch, Schema, clean_text
from src.schemas.users import DormitoryOut, UniversityOut

Title, Description = clean_text(120), clean_text(5000)


class ListingCreate(Schema):
    title: Title
    description: Description
    category: Category
    format: ListingFormat
    price: int = Field(strict=True, ge=0, le=1_000_000_000)
    dormitory_id: UUID | None = None

    @model_validator(mode="after")
    def valid_price(self):
        if ((self.format == ListingFormat.SELL and self.price == 0) or
                (self.format in (ListingFormat.GIVE, ListingFormat.EXCHANGE) and self.price != 0)):
            raise ValueError("Цена не соответствует формату")
        if "dormitory_id" in self.model_fields_set and self.dormitory_id is None:
            raise ValueError("Общежитие не может быть null")
        return self


class ListingPatch(Patch):
    title: Title | None = None
    description: Description | None = None
    category: Category | None = None
    format: ListingFormat | None = None
    price: int | None = Field(default=None, strict=True, ge=0, le=1_000_000_000)
    dormitory_id: UUID | None = None


class StatusChange(Schema):
    expected_status: ListingStatus
    status: ListingStatus


class ListingQuery(PageQuery):
    q: str | None = Field(default=None, max_length=200)
    category: Category | None = None
    format: ListingFormat | None = None
    university_id: UUID | None = None
    dormitory_id: UUID | None = None

    @field_validator("q", mode="before")
    @classmethod
    def trim_query(cls, value):
        return value.strip() or None if isinstance(value, str) else value


class OwnQuery(PageQuery):
    status: ListingStatus | None = None


class AuthorOut(Schema):
    id: UUID
    name: str


class PhotoOut(Schema):
    id: UUID
    position: int
    url: str


class ListingOut(Schema):
    id: UUID
    owner_id: UUID
    title: str
    description: str
    category: Category
    format: ListingFormat
    price: int
    status: ListingStatus
    created_at: datetime
    updated_at: datetime
    author: AuthorOut
    dormitory: DormitoryOut
    university: UniversityOut
    photos: list[PhotoOut]

