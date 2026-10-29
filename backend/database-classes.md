# Диаграмма классов базы данных

Диаграмма отражает 8 текущих моделей SQLAlchemy из `src/models`. Общие поля Base/mixins показаны внутри сущностей; классы-наследники и перечисления не вынесены в отдельные таблицы.

```mermaid
classDiagram
    direction TB

    class University {
        +UUID id PK
        +string name
        +string name_key GENERATED_UQ
    }
    class Dormitory {
        +UUID id PK
        +UUID university_id FK
        +string name
        +string name_key GENERATED
    }
    class User {
        +UUID id PK
        +string email UQ
        +string password_hash
        +string name
        +UUID dormitory_id FK
        +datetime created_at
    }
    class Listing {
        +UUID id PK
        +UUID owner_id FK
        +UUID dormitory_id FK
        +string title
        +string description
        +Category category
        +ListingFormat format
        +int price
        +ListingStatus status
        +datetime created_at
        +datetime updated_at
    }
    class ListingPhoto {
        +UUID id PK
        +UUID listing_id FK
        +string storage_key UQ
        +int position
    }
    class Chat {
        +UUID id PK
        +UUID listing_id FK
        +UUID buyer_id FK
        +datetime created_at
    }
    class Message {
        +UUID id PK
        +UUID chat_id FK
        +UUID sender_id FK
        +string text
        +UUID client_message_id
        +datetime created_at
    }
    class ChatRead {
        +UUID chat_id PK_FK
        +UUID user_id PK_FK
        +UUID last_read_message_id FK
    }

    University "1" -- "0..*" Dormitory : общежития
    Dormitory "1" -- "0..*" User : жильцы
    Dormitory "1" -- "0..*" Listing : место объявления
    User "1" -- "0..*" Listing : автор
    Listing "1" -- "0..5" ListingPhoto : фотографии
    Listing "1" -- "0..*" Chat : обсуждения
    User "1" -- "0..*" Chat : покупатель
    Chat "1" -- "0..*" Message : история
    User "1" -- "0..*" Message : отправитель
    Chat "1" -- "0..*" ChatRead : отметки
    User "1" -- "0..*" ChatRead : прочитал
    Message "1" -- "0..*" ChatRead : последнее прочитанное
```

`PK` — первичный ключ, `FK` — внешний ключ, `UQ` — уникальное поле, `GENERATED` — вычисляемое БД поле. `1` означает одну запись, `0..*` — от нуля до множества записей.

Составные ограничения:

- Dormitory: UNIQUE `(university_id, name_key)`.
- ListingPhoto: UNIQUE `(listing_id, position)` и CHECK позиции 0–4.
- Chat: UNIQUE `(listing_id, buyer_id)`.
- Message: UNIQUE `(chat_id, sender_id, client_message_id)` и `(id, chat_id)`.
- ChatRead: PK `(chat_id, user_id)` и составной FK `(last_read_message_id, chat_id)` → Message `(id, chat_id)`.

Автор чата определяется через `Chat.listing.owner`, отдельно в Chat не дублируется. Последнее сообщение и количество непрочитанных вычисляются запросом.

Диаграмма показывает физические связи моделей. Правило «только два участника чата» проверяется будущим сервисом, а не количеством строк ChatRead: схема сама не ограничивает их двумя. Для ListingPhoto предел 5 обеспечен уже ограничениями БД. Подробные типы, CHECK и правила удаления приведены в [database.md](database.md).
