from datetime import datetime
from uuid import UUID

from pydantic import field_validator, model_validator

from src.schemas.common import Patch, Schema, clean_text

Name = clean_text(80)


class DormChoice(Schema):
    dormitory_id: UUID | None = None
    university_id: UUID | None = None
    dormitory_name: Name | None = None

    @field_validator("dormitory_name", mode="before")
    @classmethod
    def normalize_dorm(cls, value):
        return " ".join(value.split()) if isinstance(value, str) else value

    @model_validator(mode="after")
    def valid_choice(self):
        if any(getattr(self, k) is None for k in self.model_fields_set
               if k in {"dormitory_id", "university_id", "dormitory_name"}):
            raise ValueError("Общежитие не может быть null")
        if self.dormitory_id:
            if self.university_id or self.dormitory_name:
                raise ValueError("Выберите один способ указать общежитие")
        elif bool(self.university_id) != bool(self.dormitory_name):
            raise ValueError("Нужны вуз и название общежития")
        return self


class ProfilePatch(DormChoice, Patch):
    name: Name | None = None

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value):
        return " ".join(value.split()) if isinstance(value, str) else value


class UniversityOut(Schema):
    id: UUID
    name: str


class DormitoryOut(Schema):
    id: UUID
    university_id: UUID
    name: str


class ProfileOut(Schema):
    id: UUID
    name: str
    email: str
    created_at: datetime
    dormitory: DormitoryOut
    university: UniversityOut

