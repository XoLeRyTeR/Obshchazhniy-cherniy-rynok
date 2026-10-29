from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


def clean_text(max_length: int):
    return Annotated[str, StringConstraints(strict=True, strip_whitespace=True,
                                            min_length=1, max_length=max_length)]


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class Patch(Schema):
    @model_validator(mode="after")
    def not_empty(self):
        if not self.model_fields_set or any(getattr(self, k) is None for k in self.model_fields_set):
            raise ValueError("Передайте хотя бы одно поле без null")
        return self


class PageQuery(Schema):
    offset: int = Field(default=0, ge=0, le=9_223_372_036_854_775_807)
    size: int = Field(default=20, ge=1, le=100)


T = TypeVar("T")


class Page(Schema, Generic[T]):
    items: list[T]

