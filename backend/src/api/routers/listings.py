from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile

from src.api.dependencies.auth import current_user
from src.api.dependencies.services import service
from src.core.errors import AppError
from src.schemas.common import Page
from src.schemas.listings import ListingCreate, ListingOut, ListingPatch, ListingQuery, PhotoOut, StatusChange
from src.services.listing_service import ListingService
from src.services.photo_service import PhotoService

router = APIRouter(prefix="/listings", tags=["Объявления"])
User = Annotated[object, Depends(current_user)]
Listings = Annotated[ListingService, Depends(service(ListingService))]
Photos = Annotated[PhotoService, Depends(service(PhotoService))]


@router.get("", response_model=Page[ListingOut])
async def feed(user: User, params: Annotated[ListingQuery, Query()], listings: Listings):
    """Возвращает авторизованному пользователю страницу активных и забронированных объявлений.

    Поддерживает поиск, фильтры категории/формата/вуза/общежития и offset/size; новые идут первыми.
    """
    return await listings.feed(user.id, params)


@router.post("", response_model=ListingOut, status_code=201)
async def create(data: ListingCreate, user: User, listings: Listings):
    """Публикует объявление от имени текущего пользователя и возвращает созданную запись с 201."""
    return await listings.create(user, data)


@router.get("/{listing_id}", response_model=ListingOut)
async def detail(listing_id: UUID, user: User, listings: Listings):
    """Возвращает подробности доступного объявления с автором и фото; недоступное даёт 404."""
    return await listings.detail(listing_id, user.id)


@router.patch("/{listing_id}", response_model=ListingOut)
async def edit(listing_id: UUID, data: ListingPatch, user: User, listings: Listings):
    """Частично обновляет объявление только его автору, проверяя формат, цену и общежитие."""
    return await listings.update(listing_id, user.id, data)


@router.patch("/{listing_id}/status", response_model=ListingOut)
async def status(listing_id: UUID, data: StatusChange, user: User, listings: Listings):
    """Меняет статус объявления только автору; неверный переход или expected_status даёт 409."""
    return await listings.status(listing_id, user.id, data)


@router.post("/{listing_id}/photos", response_model=PhotoOut, status_code=201)
async def upload_photo(listing_id: UUID, request: Request, user: User, photos: Photos,
                       file: Annotated[UploadFile, File()]):
    """Добавляет автору одну фотографию из multipart-поля file и возвращает её описание с 201.

    Допустимы статичные JPEG/PNG/WebP до 5 МБ, не более пяти фото на объявление.
    """
    form = await request.form()
    if set(form.keys()) != {"file"} or len(form.getlist("file")) != 1:
        raise AppError(422, "one_file_required", "Передайте один файл в поле file")
    try:
        return await photos.add(listing_id, user.id, file)
    finally:
        await file.close()


@router.delete("/{listing_id}/photos/{photo_id}", status_code=204)
async def delete_photo(listing_id: UUID, photo_id: UUID, user: User, photos: Photos):
    """Удаляет фотографию объявления только автору; успешный ответ — 204 без тела."""
    await photos.delete(listing_id, photo_id, user.id)
    return Response(status_code=204)

