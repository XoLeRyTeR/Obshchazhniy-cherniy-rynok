import { strict as assert } from "node:assert";
import { test } from "node:test";
import {
  categoryCodes,
  formats,
  formatCodes,
  listingPayload,
  mapListing,
  priceLabel,
  validateListing,
} from "../src/entities/listing/model/model.ts";
import { emptySessionState } from "../src/entities/user/model/model.ts";
import { emptyListingsState } from "../src/entities/listing/model/model.ts";
import { emptyChatsState, mapMessage, mergeMessages } from "../src/entities/chat/model/model.ts";
import { normalizeDorm } from "../src/entities/location/model/model.ts";
import { mediaUrl } from "../src/shared/lib/media-url.ts";

const data = {
  id: "listing",
  owner_id: "owner",
  title: "Стул",
  description: "Рабочий",
  category: "furniture",
  format: "give",
  price: 0,
  status: "active" as const,
  author: { id: "owner", name: "Андрей" },
  dormitory: { id: "dorm", name: "Северный кампус", university_id: "uni" },
  university: { id: "uni", name: "ИГЭУ" },
  photos: [
    { id: "photo", position: 0, url: "http://localhost:8000/media/p.png" },
  ],
};
const base = "http://10.1.2.3:8000/api/v1";

test("начальное состояние не содержит демо-объявлений и пользователя", () => {
  // До ответа сервера списки пусты, вход не выполнен и ID профиля не подставлен из моков.
  assert.deepEqual(emptyListingsState.listings, []);
  assert.deepEqual(emptyListingsState.ownIds, []);
  assert.deepEqual(emptyChatsState.chats, []);
  assert.equal(emptySessionState.signedIn, false);
  assert.equal(emptySessionState.profile.id, "");
});
test("адаптер сохраняет ID сервера, цену в копейках и реальное авторство", () => {
  // Проверяем владельца и фото, русские подписи формата/категории и бесплатную цену из ответа API.
  const item = mapListing(data, base);
  assert.equal(item.ownerId, "owner");
  assert.equal(item.category, "Мебель");
  assert.equal(item.format, "Отдам");
  assert.equal(item.dorm, "Северный кампус");
  assert.equal(item.photos[0], "http://10.1.2.3:8000/media/p.png");
  assert.equal(item.photoRefs[0].id, "photo");
  assert.equal(priceLabel(item), "Бесплатно");
});
test("в запрос объявления не попадают удалённые или серверные поля", () => {
  // Сверяем точный набор полей запроса: без owner_id, статуса, фото, условий обмена и места встречи.
  const payload = listingPayload(mapListing(data, base));
  assert.deepEqual(Object.keys(payload).sort(), [
    "category",
    "description",
    "dormitory_id",
    "format",
    "price",
    "title",
  ]);
  assert.equal(payload.format, "give");
  assert.equal(payload.dormitory_id, "dorm");
});
test("все форматы и категории интерфейса отображаются в серверные коды", () => {
  // Проверяем четыре формата передачи и отсутствие совпадающих кодов семи категорий.
  assert.deepEqual(formats.map((f) => formatCodes[f]).sort(), [
    "exchange",
    "give",
    "sell",
    "service",
  ]);
  assert.equal(new Set(Object.values(categoryCodes)).size, 7);
});
test("поля объявления и цена соответствуют новым ограничениям", () => {
  // Проверяем короткий валидный текст, отказ пустому названию, нулевой и дробной цене продажи.
  const item = mapListing({ ...data, format: "exchange" }, base);
  assert.deepEqual(validateListing(item), {});
  assert.equal(
    validateListing({ ...item, title: "x", description: "y" }).title,
    undefined,
  );
  assert.ok(validateListing({ ...item, title: " " }).title);
  assert.ok(validateListing({ ...item, format: "Продам", price: 0 }).price);
  assert.ok(validateListing({ ...item, format: "Продам", price: 1.5 }).price);
  assert.equal(
    validateListing({ ...item, format: "Продам", price: 1 }).price,
    undefined,
  );
});
test("медиа localhost заменяется адресом сервера, внешний CDN остаётся прежним", () => {
  // Локальная ссылка должна работать с телефона через адрес API, внешняя — остаться без изменений.
  assert.equal(
    mediaUrl("http://127.0.0.1:8000/media/x.png", base),
    "http://10.1.2.3:8000/media/x.png",
  );
  assert.equal(
    mediaUrl("https://cdn.example/x.png", base),
    "https://cdn.example/x.png",
  );
});
test("сообщения определяют отправителя по настоящему ID и объединяются без дублей", () => {
  // Проверяем mine по ID пользователя, удаление дубля и порядок с точностью до микросекунд.
  const one = mapMessage(
    {
      id: "one",
      sender_id: "user",
      text: "Один",
      created_at: "2026-10-29T10:00:00Z",
    },
    "user",
  );
  const two = mapMessage(
    {
      id: "two",
      sender_id: "other",
      text: "Два",
      created_at: "2026-10-29T10:00:00.000001Z",
    },
    "user",
  );
  assert.ok(one.mine);
  assert.ok(!two.mine);
  assert.deepEqual(
    mergeMessages([two], [one, two]).map((m) => m.id),
    ["one", "two"],
  );
});
test("имя общежития нормализуется без фиксированного перечня номеров", () => {
  // Произвольное название сохраняется, крайние и повторные пробелы убираются.
  assert.equal(normalizeDorm("  Северный   кампус  "), "Северный кампус");
});
