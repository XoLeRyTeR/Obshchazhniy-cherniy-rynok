from src.schemas.chats import ChatListing, ChatOut, MessageOut
from src.schemas.listings import AuthorOut, ListingOut, PhotoOut
from src.schemas.users import DormitoryOut, ProfileOut, UniversityOut


def profile(user):
    """Преобразует пользователя в профиль API без хеша пароля, с вузом и общежитием."""
    return ProfileOut(id=user.id, name=user.name, email=user.email, created_at=user.created_at,
                      dormitory=DormitoryOut.model_validate(user.dormitory),
                      university=UniversityOut.model_validate(user.dormitory.university))


def photo(item, settings):
    """Формирует описание фотографии с публичным URL вместо внутреннего имени файла."""
    return PhotoOut(id=item.id, position=item.position,
                    url=f"{settings.media_base_url.rstrip('/')}/{item.storage_key}")


def listing(item, settings):
    """Собирает ответ объявления с автором, местоположением и фотографиями."""
    return ListingOut(
        id=item.id, owner_id=item.owner_id, title=item.title, description=item.description,
        category=item.category, format=item.format, price=item.price, status=item.status,
        created_at=item.created_at, updated_at=item.updated_at,
        author=AuthorOut.model_validate(item.owner),
        dormitory=DormitoryOut.model_validate(item.dormitory),
        university=UniversityOut.model_validate(item.dormitory.university),
        photos=[photo(p, settings) for p in item.photos],
    )


def chat(row, user_id):
    """Собирает карточку чата и выбирает собеседника относительно текущего пользователя."""
    item, activity, last_message, unread = row
    counterpart = item.listing.owner if item.buyer_id == user_id else item.buyer
    return ChatOut(id=item.id, created_at=item.created_at, last_activity_at=activity,
                   listing=ChatListing.model_validate(item.listing),
                   counterpart=AuthorOut.model_validate(counterpart),
                   last_message=MessageOut.model_validate(last_message) if last_message else None,
                   unread=unread)

