from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from src.api.dependencies.services import db_service
from src.models import Dormitory, University
from src.schemas.common import Page, PageQuery
from src.schemas.users import DormitoryOut, UniversityOut
from src.services.catalog_service import CatalogService

router = APIRouter(tags=["Справочники"])
Catalog = Annotated[CatalogService, Depends(db_service(CatalogService))]


class DormQuery(PageQuery):
    """Параметры страницы общежитий с обязательным ID вуза."""

    university_id: UUID


@router.get("/universities", response_model=Page[UniversityOut])
async def universities(params: Annotated[PageQuery, Query()], catalog: Catalog) -> dict[str, list[University]]:
    """Возвращает страницу вузов по offset и size в алфавитном порядке, без авторизации."""
    return await catalog.universities(params)


@router.get("/dormitories", response_model=Page[DormitoryOut])
async def dormitories(params: Annotated[DormQuery, Query()], catalog: Catalog) -> dict[str, list[Dormitory]]:
    """Возвращает страницу общежитий указанного вуза, без авторизации; неизвестный вуз даёт 404."""
    return await catalog.dormitories(params.university_id, params)

