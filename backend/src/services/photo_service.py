import asyncio
import io
import logging
import re
import warnings
from uuid import uuid4

from PIL import Image, UnidentifiedImageError

from src.core.errors import AppError, missing
from src.models import ListingPhoto
from src.services.listing_service import ListingService
from src.services.views import photo

MAX_BYTES = 5 * 1024 * 1024
KEY_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+\.(jpg|jpeg|png|webp)$")
logger = logging.getLogger(__name__)


def validate_image(data, content_type):
    """Проверяет содержимое, MIME, размеры и декодирование статичного изображения.

    Возвращает расширение JPEG/PNG/WebP; неверный формат даёт 415, повреждение или размеры — 422.
    """
    allowed = {"JPEG": ("image/jpeg", "jpg"), "PNG": ("image/png", "png"),
               "WEBP": ("image/webp", "webp")}
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in allowed or getattr(image, "is_animated", False):
                    raise AppError(415, "unsupported_image", "Нужен статический JPEG, PNG или WebP")
                mime, extension = allowed[image.format]
                if content_type != mime:
                    raise AppError(415, "image_type_mismatch", "Тип файла не соответствует содержимому")
                width, height = image.size
                if not (1 <= width <= 6000 and 1 <= height <= 6000 and width * height <= 20_000_000):
                    raise AppError(422, "image_dimensions", "Недопустимый размер изображения")
                image.verify()
            with Image.open(io.BytesIO(data)) as decoded:
                decoded.load()
            return extension
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError,
            Image.DecompressionBombWarning):
        raise AppError(422, "invalid_image", "Изображение повреждено или слишком велико") from None


class PhotoService:
    """Согласует файлы фотографий с записями БД, проверяет загрузки и удаляет сироты."""

    def __init__(self, db, settings):
        """Принимает репозитории и настройки каталога и публичных URL фотографий."""
        self.db, self.settings = db, settings

    async def add(self, listing_id, user_id, upload):
        """Добавляет автору фото до 5 МБ, проверяя изображение и лимит пяти фото.

        Сохраняет файл под случайным именем; при сбое удаляет его только после проверки БД.
        """
        # Один lock также используется очисткой файлов, чтобы не удалить незакоммиченный upload.
        await self.db.photos.lock_media()
        item = await ListingService(self.db, self.settings).accessible(listing_id, user_id, edit=True, lock=True)
        used = {p.position for p in item.photos}
        if len(used) >= 5:
            raise AppError(409, "photo_limit", "В объявлении уже пять фотографий")
        chunks, size = [], 0
        while chunk := await upload.read(65536):
            size += len(chunk)
            if size > MAX_BYTES:
                raise AppError(413, "photo_too_large", "Максимальный размер файла — 5 МБ")
            chunks.append(chunk)
        if not size:
            raise AppError(422, "empty_file", "Файл пуст")
        data = b"".join(chunks)
        extension = await asyncio.to_thread(validate_image, data, upload.content_type)
        key = f"{uuid4().hex}.{extension}"
        path = self.settings.media_dir / key
        record = ListingPhoto(listing_id=listing_id, storage_key=key,
                              position=next(p for p in range(5) if p not in used))
        try:
            await asyncio.to_thread(path.write_bytes, data)
            self.db.add(record)
            await self.db.save()
        except BaseException:
            await self.db.rollback()
            try:
                # Потеря ответа commit не означает откат: связанный с БД файл сохраняем.
                # Если БД недоступна, проверку оставляем последующей очистке сирот.
                if not await self.db.photos.is_referenced(key):
                    await asyncio.to_thread(path.unlink, missing_ok=True)
            except Exception:
                logger.warning("Image consistency check deferred to orphan cleanup")
            raise
        return photo(record, self.settings)

    async def delete(self, listing_id, photo_id, user_id):
        """Проверяет авторство, удаляет запись фото и затем файл после успешного commit.

        Если файл удалить не удалось, его уберёт последующая очистка сирот.
        """
        await self.db.photos.lock_media()
        await ListingService(self.db, self.settings).accessible(listing_id, user_id, edit=True, lock=True)
        record = await self.db.photos.get(listing_id, photo_id)
        if record is None:
            raise missing()
        path = self.settings.media_dir / record.storage_key
        await self.db.photos.delete(record)
        await self.db.save()
        try:
            await asyncio.to_thread(path.unlink, missing_ok=True)
        except OSError:
            logger.warning("Deleted image scheduled for orphan cleanup")

    async def cleanup(self):
        """Удаляет файлы допустимого имени без записи в БД и возвращает их количество.

        Общая блокировка с загрузкой не даёт удалить ещё не сохранённую фотографию.
        """
        await self.db.photos.lock_media()
        referenced = await self.db.photos.storage_keys()
        removed = 0
        for path in self.settings.media_dir.iterdir():
            if path.is_file() and KEY_PATTERN.fullmatch(path.name) and path.name not in referenced:
                await asyncio.to_thread(path.unlink, missing_ok=True)
                removed += 1
        await self.db.save()
        return removed

