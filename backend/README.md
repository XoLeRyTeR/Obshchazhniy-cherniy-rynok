# Бэкенд «Общажный чёрный рынок»

Python 3.12, FastAPI, SQLAlchemy 2.0, PostgreSQL, Alembic. Реализован 21 метод: регистрация/вход с одним JWT, профиль, справочники, объявления со статусами, фотографии, чаты и сообщения с отметками прочтения. Мобильный frontend подключён к API; настройка его адреса описана в [корневом README](../README.md).

## Запуск

Команды выполняются из `D:/Projects/Mobilki/backend`. Нужна доступная PostgreSQL с отдельной базой и пользователем приложения.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

В `.env` задать настоящий DATABASE_URL, случайный JWT_SECRET длиной от 32 символов, MEDIA_BASE_URL и CORS_ORIGINS. Секрет можно получить командой `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Файл `.env` не коммитится. ACCESS_TOKEN_TTL — секунды, пример 7 дней; после истечения нужен повторный вход.

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m src.manage seed-universities "ИГЭУ" "Другой вуз"
.\.venv\Scripts\python.exe -m uvicorn src.main:create_app --factory --reload --host 127.0.0.1 --port 8000
```

Swagger: http://127.0.0.1:8000/docs. В API доступен публичный список вузов, после чего можно зарегистрироваться с названием своего общежития. Для закрытых методов нажать Authorize и вставить access_token из ответа регистрации/входа. Таблицы и демо-аккаунты при старте API не создаются автоматически. `alembic check` проверяет соответствие моделей и миграций.

## Основные запросы

Регистрация: POST /api/v1/auth/register с email, password, name и либо dormitory_id, либо парой university_id/dormitory_name. Ответ: access_token, token_type, profile. Вход: POST /api/v1/auth/login с email/password. Запросы передают `Authorization: Bearer TOKEN`. Выход выполняется удалением токена на устройстве; таблицы токенов и методов refresh/logout нет.

Пример объявления:

```json
{
  "title": "Стул",
  "description": "Деревянный стул в хорошем состоянии",
  "category": "furniture",
  "format": "give",
  "price": 0
}
```

Общежитие по умолчанию берётся из профиля; price — копейки. Форматы sell/give/exchange/service; категории books/electronics/furniture/clothes/dishes/food/other. Отдельных exchange/place нет. Фото передаётся отдельным multipart-запросом в поле file; без фото публиковать можно.

Сообщение: text и новый UUID client_message_id. При повторе после сетевого сбоя использовать тот же UUID: вернётся исходное сообщение без дубля. PATCH /chats/{id}/read вызывается явно; GET истории не изменяет прочтение. Чат обновляется HTTP-запросами, WebSocket пока нет.

Все списки принимают `offset` (по умолчанию 0, от 0) и `size` (по умолчанию 20, от 1 до 100), возвращают `{items: [...]}`. Пример: `/api/v1/listings?offset=20&size=20`. Следующая порция начинается с `offset + items.length`; если пришло меньше `size`, список закончился. При полной последней странице следующий запрос вернёт пустой список. Старые параметры `cursor` и `limit` не поддерживаются. Сортировка и выполнение SQL находятся в репозиториях, сервис передаёт параметры и преобразует результат. Все поля, статусы и ответы доступны в OpenAPI. GET /health проверяет процесс, GET /ready — доступность БД с таймаутом.

## Проверка

```powershell
# Модели, схемы и JWT без базы:
.\.venv\Scripts\python.exe -m pytest tests/unit -q

# Полный прогон на отдельной тестовой PostgreSQL:
$env:TEST_DATABASE_URL = 'postgresql+asyncpg://test_user:PASSWORD@127.0.0.1:5432/mobilki_test'
.\.venv\Scripts\python.exe -m pytest -q
```

Имя тестовой базы оканчивается на `_test`, URL не совпадает с DATABASE_URL. Каждый тест создаёт схему test_UUID, применяет начальную миграцию и удаляет только свою схему. Тестовому пользователю нужно право CREATE на тестовую базу. Без TEST_DATABASE_URL интеграционные проверки пропускаются; это не полный прогон.

Проверено на PostgreSQL 17: 132 теста и 25 вложенных проверок. Покрыты все 21 метод, матрица статусов, авторство, приватность переписки, фильтры/пагинация offset/size, фото, повторная отправка, откат при сбое и конкурентные операции брони, смены формата, создания чата, общежития и сообщения. Ограничения PostgreSQL дополнительно проверены прямыми SQL-вставками; фото сохраняется и при потере подтверждения успешного commit. Проверены очистка файлов через PhotoRepository и освобождение медиа-блокировки после завершения транзакции. Отдельный архитектурный тест запрещает сервисам прямой доступ к сессии/движку и импорт SQLAlchemy/слоя БД.

Полный план — [tests/API_TEST_PLAN.md](tests/API_TEST_PLAN.md). Расширенные сценарии пока не все автоматизированы: обрыв загрузки, аппаратный отказ диска/процесса, исчерпание пула, нагрузочные измерения и восстановление резервной копии требуют отдельных проверок на стенде.

## Обслуживание и размещение

Фотографии: MEDIA_DIR и публичный MEDIA_BASE_URL. Максимум 5 файлов на объявление, 5 МБ на файл, статические JPEG/PNG/WebP с проверкой содержимого и размеров. Имена генерирует сервер. Сиротские файлы после сбоя убираются командой:

```powershell
.\.venv\Scripts\python.exe -m src.manage cleanup-media
```

Очистка использует ту же блокировку PostgreSQL, что загрузка/удаление: удаляются только допустимые серверные имена без ссылок в БД. Архивирование не отзывает ранее выданный публичный URL. Резервируются БД и каталог фото.

Для внешнего сервера нужны HTTPS-домен, reverse proxy и постоянный каталог фото. На proxy ограничить размер upload с учётом multipart (например, 6 МБ); для нескольких workers rate limit auth задаётся на proxy. Встроенный ограничитель работает в одном процессе по IP клиента. Доверие proxy-заголовкам настраивается при запуске. Сервер пользователя пока не изменялся.

Для проверки создан отдельный кластер PostgreSQL в `.local-postgres`, слушающий только localhost:55432. Он игнорируется Git и не является конфигурацией рабочего сервера. Docker не потребовался. Для Expo Go API запускается с `--host 0.0.0.0`; PostgreSQL при этом остаётся доступен только локально.

[Архитектура](architecture.md), [схема](database.md), [диаграмма](database-classes.md). Официальные руководства: [JWT FastAPI](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/), [async SQLAlchemy](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html), [Alembic](https://alembic.sqlalchemy.org/en/latest/cookbook.html).
