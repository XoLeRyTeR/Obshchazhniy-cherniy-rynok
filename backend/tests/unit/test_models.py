"""Проверки ORM/DDL без БД; не заменяют интеграционные тесты PostgreSQL."""

import unittest
import warnings
from uuid import uuid4

from sqlalchemy import ForeignKeyConstraint, UniqueConstraint, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SAWarning
from sqlalchemy.orm import configure_mappers, joinedload
from sqlalchemy.schema import CreateIndex, CreateTable

from src.models import (
    Base, Category, Chat, ChatRead, Dormitory, Listing, ListingFormat,
    ListingStatus, Message, University, User,
)


class ModelTests(unittest.TestCase):
    """Проверяет структуру ORM и генерируемый PostgreSQL DDL без запуска базы данных."""

    @classmethod
    def setUpClass(cls):
        """Готовит диалект PostgreSQL и требует, чтобы связи ORM настраивались без предупреждений."""
        cls.dialect = postgresql.dialect()
        with warnings.catch_warnings():
            warnings.simplefilter("error", SAWarning)
            configure_mappers()

    def test_all_models_compile_for_postgresql(self):
        """Проверяет восемь таблиц и компиляцию CREATE TABLE/INDEX для каждой из них."""
        self.assertEqual(len(Base.metadata.tables), 8)
        for table in Base.metadata.sorted_tables:
            with self.subTest(table=table.name):
                ddl = str(CreateTable(table).compile(dialect=self.dialect))
                self.assertIn("CREATE TABLE", ddl)
                for index in table.indexes:
                    self.assertIn("CREATE INDEX", str(CreateIndex(index).compile(dialect=self.dialect)))

    def test_queries_join_relationships_without_ambiguous_foreign_keys(self):
        """Проверяет компиляцию JOIN по связям пользователя, объявления, чата и метки без неоднозначных FK."""
        queries = [
            select(User).options(joinedload(User.dormitory).joinedload(Dormitory.university)),
            select(Listing).options(joinedload(Listing.owner), joinedload(Listing.photos)),
            select(Chat).options(joinedload(Chat.listing), joinedload(Chat.buyer)),
            select(ChatRead).options(joinedload(ChatRead.chat), joinedload(ChatRead.last_read_message)),
        ]
        for query in queries:
            with self.subTest(query=str(query)):
                self.assertIn("JOIN", str(query.compile(dialect=self.dialect)))

    def test_relationships_build_a_connected_object_graph(self):
        """Проверяет, что назначение связей ORM заполняет обратные коллекции от вуза до сообщений."""
        university = University(name="ИГЭУ")
        dorm = Dormitory(name="17", university=university)
        owner = User(name="Андрей", email="a@example.com", password_hash="hash", dormitory=dorm)
        buyer = User(name="Борис", email="b@example.com", password_hash="hash", dormitory=dorm)
        listing = Listing(owner=owner, dormitory=dorm, title="Стул", description="Рабочий",
                          category=Category.FURNITURE, format=ListingFormat.GIVE, price=0)
        chat = Chat(listing=listing, buyer=buyer)
        message = Message(chat=chat, sender=buyer, text="Заберу", client_message_id=uuid4())
        self.assertIn(dorm, university.dormitories)
        self.assertIn(listing, owner.listings)
        self.assertIn(chat, listing.chats)
        self.assertIn(message, chat.messages)
        self.assertIn(message, buyer.messages)

    def test_read_marker_foreign_key_requires_message_from_same_chat(self):
        """Проверяет составной FK метки на пару message_id/chat_id и обязательность ссылки на сообщение."""
        foreign_key = next(
            constraint for constraint in ChatRead.__table__.constraints
            if isinstance(constraint, ForeignKeyConstraint) and len(constraint.columns) == 2
        )
        self.assertEqual(list(foreign_key.column_keys), ["last_read_message_id", "chat_id"])
        self.assertEqual([element.target_fullname for element in foreign_key.elements],
                         ["messages.id", "messages.chat_id"])
        self.assertFalse(ChatRead.__table__.c.last_read_message_id.nullable)

    def test_concurrency_keys_are_database_unique_constraints(self):
        """Проверяет уникальные ключи, защищающие почты, общежития, чаты, повторы сообщений и места фото."""
        keys = {
            "users": ("email",),
            "dormitories": ("university_id", "name_key"),
            "chats": ("listing_id", "buyer_id"),
            "messages": ("chat_id", "sender_id", "client_message_id"),
            "listing_photos": ("listing_id", "position"),
        }
        for table_name, columns in keys.items():
            with self.subTest(table=table_name):
                unique_keys = {
                    tuple(column.name for column in constraint.columns)
                    for constraint in Base.metadata.tables[table_name].constraints
                    if isinstance(constraint, UniqueConstraint)
                }
                self.assertIn(columns, unique_keys)

    def test_enum_binding_uses_api_codes_and_rejects_unknown_values(self):
        """Проверяет сохранение строковых кодов enum и отказ неизвестным категориям, форматам и статусам."""
        for column, value in ((Listing.format, ListingFormat.EXCHANGE),
                              (Listing.status, ListingStatus.RESERVED),
                              (Listing.category, Category.BOOKS)):
            with self.subTest(column=column.key):
                bind = column.type.bind_processor(self.dialect)
                self.assertEqual(bind(value), value.value)
                with self.assertRaises(LookupError):
                    bind("invalid-value")

    def test_timestamps_are_timezone_aware_and_catalog_keys_are_generated(self):
        """Проверяет timezone у полей времени и хранимые вычисляемые name_key у вузов и общежитий."""
        for table in Base.metadata.tables.values():
            for column in table.columns:
                if column.name.endswith("_at"):
                    with self.subTest(column=f"{table.name}.{column.name}"):
                        self.assertTrue(column.type.timezone)
        for model in (University, Dormitory):
            self.assertTrue(model.__table__.c.name_key.computed.persisted)
            self.assertIn("GENERATED ALWAYS AS", str(CreateTable(model.__table__).compile(dialect=self.dialect)))

    def test_database_guards_price_status_photo_limit_and_history(self):
        """Проверяет наличие CHECK для цен/услуг/позиций фото и RESTRICT для сохранения истории связей."""
        listing_sql = str(CreateTable(Listing.__table__).compile(dialect=self.dialect))
        self.assertIn("price BETWEEN 0 AND 1000000000", listing_sql)
        self.assertIn("format <> 'service' OR status IN ('active', 'archived')", listing_sql)
        photos = Base.metadata.tables["listing_photos"]
        self.assertIn("position BETWEEN 0 AND 4", str(CreateTable(photos).compile(dialect=self.dialect)))
        for column in (Listing.__table__.c.owner_id, Chat.__table__.c.listing_id,
                       Message.__table__.c.chat_id, Message.__table__.c.sender_id):
            self.assertEqual(next(iter(column.foreign_keys)).ondelete, "RESTRICT")


if __name__ == "__main__":
    unittest.main()
