from pydantic import EmailStr, Field, field_validator, model_validator

from src.schemas.common import Schema
from src.schemas.users import DormChoice, Name, ProfileOut


class Login(Schema):
    email: EmailStr = Field(max_length=254)
    password: str = Field(strict=True, min_length=8, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError("Пароль не может состоять из пробелов")
        return value


class Register(Login, DormChoice):
    name: Name

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value):
        return " ".join(value.split()) if isinstance(value, str) else value

    @model_validator(mode="after")
    def dorm_required(self):
        if not self.dormitory_id and not self.university_id:
            raise ValueError("Укажите общежитие")
        return self


class AuthOut(Schema):
    access_token: str
    token_type: str = "bearer"
    profile: ProfileOut

