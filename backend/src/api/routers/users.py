from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.api.dependencies.auth import current_user
from src.api.dependencies.services import service
from src.schemas.common import Page
from src.schemas.listings import ListingOut, OwnQuery
from src.schemas.users import ProfileOut, ProfilePatch
from src.services.listing_service import ListingService
from src.services.user_service import UserService
from src.services.views import profile

router = APIRouter(prefix="/users/me", tags=["Профиль"])
User = Annotated[object, Depends(current_user)]


@router.get("", response_model=ProfileOut)
async def me(user: User):
    """Возвращает профиль текущего пользователя с вузом и общежитием по Bearer-токену."""
    return profile(user)


@router.patch("", response_model=ProfileOut)
async def edit_profile(data: ProfilePatch, user: User,
                       users: Annotated[UserService, Depends(service(UserService))]):
    """Обновляет имя и/или общежитие текущего пользователя, возвращает сохранённый профиль."""
    return await users.update(user.id, data)


@router.get("/listings", response_model=Page[ListingOut])
async def own_listings(user: User, params: Annotated[OwnQuery, Query()],
                       listings: Annotated[ListingService, Depends(service(ListingService))]):
    """Возвращает страницу только своих объявлений, включая снятые и завершённые.

    Поддерживает фильтр статуса и offset/size; новые объявления идут первыми.
    """
    return await listings.own(user.id, params)

