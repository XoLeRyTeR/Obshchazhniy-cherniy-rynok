from uuid import UUID, uuid4

from sqlalchemy import func, select

from src.repositories.db_repository import DbRepository
from src.repositories.photo_repository import MEDIA_LOCK, PhotoRepository
from src.services.photo_service import PhotoService
from tests.integration.test_api import png


async def test_photo_cleanup_keeps_referenced_files(api):
    """Проверяет очистку через репозиторий: связанное фото сохраняется, сирота удаляется, чужой файл не трогается."""
    listing = await api.listing()
    response = await api.client.post(
        f"/api/v1/listings/{listing['id']}/photos", headers=api.headers(),
        files={"file": ("image.png", png(), "image/png")},
    )
    assert response.status_code == 201, response.text
    image = response.json()
    key = image["url"].rsplit("/", 1)[1]
    settings = api.app.state.settings
    orphan = settings.media_dir / "orphan.png"
    unrelated = settings.media_dir / "notes.txt"
    orphan.write_bytes(b"orphan")
    unrelated.write_text("keep", encoding="utf-8")

    async with api.db.sessions() as session:
        db = DbRepository(session)
        record = await db.photos.get(UUID(listing["id"]), UUID(image["id"]))
        assert record is not None and record.storage_key == key
        assert await db.photos.get(uuid4(), UUID(image["id"])) is None
        assert await db.photos.is_referenced(key)
        assert not await db.photos.is_referenced(orphan.name)
        assert await db.photos.storage_keys() == {key}
        assert await PhotoService(db, settings).cleanup() == 1
        assert await PhotoService(db, settings).cleanup() == 0

    assert (settings.media_dir / key).exists()
    assert not orphan.exists()
    assert unrelated.exists()
    deleted = await api.client.delete(
        f"/api/v1/listings/{listing['id']}/photos/{image['id']}", headers=api.headers(),
    )
    assert deleted.status_code == 204, deleted.text
    async with api.db.sessions() as session:
        assert not await PhotoRepository(session).is_referenced(key)
    assert not (settings.media_dir / key).exists()


async def test_media_lock_lasts_until_transaction_ends(api):
    """Проверяет, что блокировка медиа мешает другой сессии до rollback и освобождается после него."""
    async with api.db.sessions() as first, api.db.sessions() as second:
        await PhotoRepository(first).lock_media()
        try_lock = select(func.pg_try_advisory_xact_lock(MEDIA_LOCK))
        assert not await second.scalar(try_lock)
        await first.rollback()
        assert await second.scalar(try_lock)
