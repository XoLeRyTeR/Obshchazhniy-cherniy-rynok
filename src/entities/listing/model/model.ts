import type { CatalogItem } from "../../../shared/api";
import { mediaUrl } from "../../../shared/lib/media-url.ts";

export const formats = ["Продам", "Отдам", "Услуга", "Обмен"] as const;

export const categories = [
  "Книги",
  "Техника",
  "Мебель",
  "Одежда",
  "Посуда",
  "Еда",
  "Другое",
] as const;

export type Format = (typeof formats)[number];

export type Status = "active" | "reserved" | "completed" | "archived";

export const formatCodes: Record<Format, string> = {
  Продам: "sell",
  Отдам: "give",
  Услуга: "service",
  Обмен: "exchange",
};

export const categoryCodes: Record<string, string> = Object.fromEntries(
  categories.map((name, i) => [
    name,
    ["books", "electronics", "furniture", "clothes", "dishes", "food", "other"][
    i
    ],
  ]),
);

export type Photo = { id: string; url: string; position: number; };

export type Listing = {
  id: string;
  title: string;
  description: string;
  category: string;
  format: Format;
  price: number;
  dorm: string;
  dormitoryId: string;
  university: string;
  author: string;
  ownerId: string;
  status: Status;
  photos: string[];
  photoRefs: Photo[];
  photoTypes?: Record<string, string>;
  color: "yellow" | "blue" | "brown" | "sage";
};

export const emptyListingsState: { listings: Listing[]; ownIds: string[]; } = { listings: [], ownIds: [] };

export type ApiListing = {
  id: string;
  owner_id: string;
  title: string;
  description: string;
  category: string;
  format: string;
  price: number;
  status: Status;
  author: CatalogItem;
  dormitory: CatalogItem & { university_id: string; };
  university: CatalogItem;
  photos: Photo[];
};

/** Преобразует объявление API в модель интерфейса с русскими подписями и доступными URL фото. */
export function mapListing(data: ApiListing, baseUrl: string): Listing {
  const photoRefs = data.photos.map((p) => ({
    ...p,
    url: mediaUrl(p.url, baseUrl),
  }));
  return {
    id: data.id,
    ownerId: data.owner_id,
    title: data.title,
    description: data.description,
    category:
      categories.find((c) => categoryCodes[c] === data.category) ?? "Другое",
    format: formats.find((f) => formatCodes[f] === data.format) ?? "Отдам",
    price: data.price,
    status: data.status,
    dorm: data.dormitory.name,
    dormitoryId: data.dormitory.id,
    university: data.university.name,
    author: data.author.name,
    photoRefs,
    photos: photoRefs.map((p) => p.url),
    color: "sage",
  };
}

/** Собирает разрешённые поля запроса объявления, очищая текст и переводя подписи в коды API. */
export function listingPayload(item: Listing) {
  return {
    title: item.title.trim(),
    description: item.description.trim(),
    category: categoryCodes[item.category],
    format: formatCodes[item.format],
    price: item.price,
    dormitory_id: item.dormitoryId,
  };
}

export const statusLabel: Record<Status, string> = {
  active: "Опубликовано",
  reserved: "Забронировано",
  completed: "Завершено",
  archived: "Снято с публикации",
};

/** Формирует подпись цены в рублях либо метку бесплатной передачи, обмена или договорной услуги. */
export const priceLabel = (item: Listing) =>
  item.format === "Отдам"
    ? "Бесплатно"
    : item.format === "Обмен"
      ? "Обмен"
      : item.price
        ? `${new Intl.NumberFormat("ru-RU").format(item.price / 100)} ₽${item.format === "Услуга" ? " / услуга" : ""}`
        : "Договорная";

/** Проверяет название, описание и цену формы объявления и возвращает ошибки по полям. */
export function validateListing(item: Listing): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!item.title.trim() || item.title.trim().length > 120)
    errors.title = "Название — от 1 до 120 символов";
  if (!item.description.trim() || item.description.trim().length > 5000)
    errors.description = "Описание — от 1 до 5000 символов";
  if (
    !Number.isSafeInteger(item.price) ||
    item.price < 0 ||
    item.price > 1_000_000_000 ||
    (item.format === "Продам" && item.price === 0)
  )
    errors.price = "Укажите корректную цену (до 10 000 000 ₽)";
  return errors;
}
