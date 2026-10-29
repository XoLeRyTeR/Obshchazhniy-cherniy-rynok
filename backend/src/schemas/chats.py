from datetime import datetime
from uuid import UUID

from src.models.enums import ListingStatus
from src.schemas.common import Schema, clean_text
from src.schemas.listings import AuthorOut


class ChatCreate(Schema):
    listing_id: UUID


class MessageCreate(Schema):
    text: clean_text(4000)
    client_message_id: UUID


class ReadChange(Schema):
    last_read_message_id: UUID


class MessageOut(Schema):
    id: UUID
    chat_id: UUID
    sender_id: UUID
    text: str
    client_message_id: UUID
    created_at: datetime


class ChatListing(Schema):
    id: UUID
    title: str
    status: ListingStatus


class ChatOut(Schema):
    id: UUID
    created_at: datetime
    last_activity_at: datetime
    listing: ChatListing
    counterpart: AuthorOut
    last_message: MessageOut | None
    unread: int


class ReadOut(Schema):
    chat_id: UUID
    user_id: UUID
    last_read_message_id: UUID

