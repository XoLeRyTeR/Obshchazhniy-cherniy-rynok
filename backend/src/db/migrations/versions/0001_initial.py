"""Initial schema: eight marketplace tables. Frozen independently of ORM models."""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def identity():
    return sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False)


def created():
    return sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False)


def upgrade():
    op.create_table("universities",
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("name_key", sa.Text(), sa.Computed("lower(btrim(regexp_replace(name, '[[:space:]]+', ' ', 'g')))", persisted=True), nullable=False),
        identity(),
        sa.CheckConstraint("char_length(name_key) > 0", name=op.f("ck_universities_name_not_blank")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_universities")),
        sa.UniqueConstraint("name_key", name=op.f("uq_universities_name_key")))
    op.create_index("ix_universities_name_key_id", "universities", ["name_key", "id"])
    op.create_table("dormitories",
        sa.Column("university_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("name_key", sa.Text(), sa.Computed("lower(btrim(regexp_replace(name, '[[:space:]]+', ' ', 'g')))", persisted=True), nullable=False),
        identity(),
        sa.CheckConstraint("char_length(name_key) > 0", name=op.f("ck_dormitories_name_not_blank")),
        sa.ForeignKeyConstraint(["university_id"], ["universities.id"], ondelete="RESTRICT", name=op.f("fk_dormitories_university_id_universities")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dormitories")),
        sa.UniqueConstraint("university_id", "name_key", name=op.f("uq_dormitories_university_id_name_key")))
    op.create_index("ix_dormitories_university_name_id", "dormitories", ["university_id", "name_key", "id"])
    op.create_table("users",
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("dormitory_id", sa.Uuid(), nullable=False), identity(), created(),
        sa.CheckConstraint("name ~ '[^[:space:]]'", name=op.f("ck_users_name_not_blank")),
        sa.CheckConstraint("char_length(password_hash) > 0", name=op.f("ck_users_password_hash_not_empty")),
        sa.CheckConstraint("email = lower(btrim(email)) AND char_length(email) > 0", name=op.f("ck_users_email_normalized")),
        sa.ForeignKeyConstraint(["dormitory_id"], ["dormitories.id"], ondelete="RESTRICT", name=op.f("fk_users_dormitory_id_dormitories")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")))
    op.create_index("ix_users_dormitory_id", "users", ["dormitory_id"])
    op.create_table("listings",
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("dormitory_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("description", sa.String(5000), nullable=False),
        sa.Column("category", sa.Enum("books", "electronics", "furniture", "clothes", "dishes", "food", "other", name="category", native_enum=False, create_constraint=True), nullable=False),
        sa.Column("format", sa.Enum("sell", "give", "exchange", "service", name="format", native_enum=False, create_constraint=True), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("active", "reserved", "completed", "archived", name="status", native_enum=False, create_constraint=True), server_default=sa.text("'active'"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), identity(), created(),
        sa.CheckConstraint("(format = 'sell' AND price > 0) OR (format IN ('give', 'exchange') AND price = 0) OR format = 'service'", name=op.f("ck_listings_price_matches_format")),
        sa.CheckConstraint("description ~ '[^[:space:]]'", name=op.f("ck_listings_description_not_blank")),
        sa.CheckConstraint("format <> 'service' OR status IN ('active', 'archived')", name=op.f("ck_listings_service_status")),
        sa.CheckConstraint("title ~ '[^[:space:]]'", name=op.f("ck_listings_title_not_blank")),
        sa.CheckConstraint("price BETWEEN 0 AND 1000000000", name=op.f("ck_listings_price_range")),
        sa.CheckConstraint("updated_at >= created_at", name=op.f("ck_listings_update_after_creation")),
        sa.ForeignKeyConstraint(["dormitory_id"], ["dormitories.id"], ondelete="RESTRICT", name=op.f("fk_listings_dormitory_id_dormitories")),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="RESTRICT", name=op.f("fk_listings_owner_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_listings")))
    op.create_index("ix_listings_dormitory_status_created_id", "listings", ["dormitory_id", "status", "created_at", "id"])
    op.create_index("ix_listings_feed_created_id", "listings", ["created_at", "id"], postgresql_where=sa.text("status IN ('active', 'reserved')"))
    op.create_index("ix_listings_owner_created_id", "listings", ["owner_id", "created_at", "id"])
    op.create_table("chats",
        sa.Column("listing_id", sa.Uuid(), nullable=False),
        sa.Column("buyer_id", sa.Uuid(), nullable=False), identity(), created(),
        sa.ForeignKeyConstraint(["buyer_id"], ["users.id"], ondelete="RESTRICT", name=op.f("fk_chats_buyer_id_users")),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="RESTRICT", name=op.f("fk_chats_listing_id_listings")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chats")),
        sa.UniqueConstraint("listing_id", "buyer_id", name=op.f("uq_chats_listing_id_buyer_id")))
    op.create_index("ix_chats_buyer_created_id", "chats", ["buyer_id", "created_at", "id"])
    op.create_table("listing_photos",
        sa.Column("listing_id", sa.Uuid(), nullable=False),
        sa.Column("storage_key", sa.String(100), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False), identity(),
        sa.CheckConstraint("storage_key ~ '^[a-zA-Z0-9_-]+[.](jpg|jpeg|png|webp)$'", name=op.f("ck_listing_photos_safe_storage_key")),
        sa.CheckConstraint("position BETWEEN 0 AND 4", name=op.f("ck_listing_photos_position_slot")),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE", name=op.f("fk_listing_photos_listing_id_listings")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_listing_photos")),
        sa.UniqueConstraint("listing_id", "position", name=op.f("uq_listing_photos_listing_id_position")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_listing_photos_storage_key")))
    op.create_table("messages",
        sa.Column("chat_id", sa.Uuid(), nullable=False),
        sa.Column("sender_id", sa.Uuid(), nullable=False),
        sa.Column("text", sa.String(4000), nullable=False),
        sa.Column("client_message_id", sa.Uuid(), nullable=False), identity(), created(),
        sa.CheckConstraint("text ~ '[^[:space:]]'", name=op.f("ck_messages_text_not_blank")),
        sa.ForeignKeyConstraint(["chat_id"], ["chats.id"], ondelete="RESTRICT", name=op.f("fk_messages_chat_id_chats")),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="RESTRICT", name=op.f("fk_messages_sender_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_messages")),
        sa.UniqueConstraint("chat_id", "sender_id", "client_message_id", name=op.f("uq_messages_chat_id_sender_id_client_message_id")),
        sa.UniqueConstraint("id", "chat_id", name=op.f("uq_messages_id_chat_id")))
    op.create_index("ix_messages_chat_created_id", "messages", ["chat_id", "created_at", "id"])
    op.create_index("ix_messages_sender_id", "messages", ["sender_id"])
    op.create_table("chat_reads",
        sa.Column("chat_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("last_read_message_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["chat_id"], ["chats.id"], ondelete="CASCADE", name=op.f("fk_chat_reads_chat_id_chats")),
        sa.ForeignKeyConstraint(["last_read_message_id", "chat_id"], ["messages.id", "messages.chat_id"], ondelete="RESTRICT", name=op.f("fk_chat_reads_last_read_message_id_chat_id_messages")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name=op.f("fk_chat_reads_user_id_users")),
        sa.PrimaryKeyConstraint("chat_id", "user_id", name=op.f("pk_chat_reads")))
    op.create_index("ix_chat_reads_message_chat", "chat_reads", ["last_read_message_id", "chat_id"])
    op.create_index("ix_chat_reads_user_id", "chat_reads", ["user_id"])


def downgrade():
    for table in ("chat_reads", "messages", "listing_photos", "chats", "listings", "users", "dormitories", "universities"):
        op.drop_table(table)
