import { strict as assert } from "node:assert";
import { test } from "node:test";
import {
  mapListing, listingPayload, validateListing, priceLabel,
} from "../src/entities/listing/model/model.ts";
import { apiBase, listing } from "./fixtures.ts";

test("публикация очищает крайние пробелы без изменения исходного черновика", () => {
  const draft = mapListing(listing({ title: "  Стул  ", description: "\nРабочий\t" }), apiBase);
  assert.deepEqual(listingPayload(draft), {
    title: "Стул", description: "Рабочий", category: "furniture",
    format: "sell", price: 125050, dormitory_id: "dorm",
  });
  assert.equal(draft.title, "  Стул  ");
  assert.equal(draft.description, "\nРабочий\t");
});

test("форма принимает предельные длины текста, считая их после trim", () => {
  const draft = mapListing(listing(), apiBase);
  assert.deepEqual(validateListing({
    ...draft, title: ` ${"я".repeat(120)} `, description: `\n${"я".repeat(5000)}\n`,
  }), {});
});

test("форма возвращает ошибки всех некорректных полей одновременно", () => {
  const errors = validateListing({
    ...mapListing(listing(), apiBase), title: "я".repeat(121),
    description: "я".repeat(5001), price: -1,
  });
  assert.deepEqual(Object.keys(errors).sort(), ["description", "price", "title"]);
});

test("описание из пробелов и переводов строк не проходит валидацию", () => {
  assert.ok(validateListing({
    ...mapListing(listing(), apiBase), description: " \n\t ",
  }).description);
});

test("цена продажи принимает границы и отклоняет отрицательные, дробные и нечисловые значения", () => {
  const draft = mapListing(listing(), apiBase);
  for (const price of [1, 1_000_000_000])
    assert.equal(validateListing({ ...draft, price }).price, undefined, `price=${price}`);
  for (const price of [0, -1, 1.5, 1_000_000_001, NaN, Infinity, -Infinity, Number.MAX_SAFE_INTEGER + 1])
    assert.ok(validateListing({ ...draft, price }).price, `price=${price}`);
});

test("бесплатная передача, обмен и договорная услуга допускают нулевую цену", () => {
  const draft = mapListing(listing(), apiBase);
  for (const format of ["Отдам", "Обмен", "Услуга"] as const)
    assert.deepEqual(validateListing({ ...draft, format, price: 0 }), {});
});

test("подписи цены различают копейки, услугу, обмен и бесплатную передачу", () => {
  const draft = mapListing(listing({ price: 12345 }), apiBase);
  // Не привязываемся к виду пробела, который зависит от версии ICU в Node.
  const label = (format: typeof draft.format, price = draft.price) =>
    priceLabel({ ...draft, format, price }).replace(/[\u00a0\u202f]/g, " ");
  assert.equal(label("Продам"), "123,45 ₽");
  assert.equal(label("Услуга"), "123,45 ₽ / услуга");
  assert.equal(label("Услуга", 0), "Договорная");
  assert.equal(label("Отдам"), "Бесплатно");
  assert.equal(label("Обмен"), "Обмен");
});

test("объявление без фотографий остаётся доступным для отображения", () => {
  const item = mapListing(listing(), apiBase);
  assert.deepEqual(item.photos, []);
  assert.deepEqual(item.photoRefs, []);
  assert.equal(item.status, "active");
});

test("адаптер сохраняет ID, порядок и позиции фото, не изменяя ответ сервера", () => {
  const data = listing({ photos: [
    { id: "second", position: 1, url: "http://localhost:8000/media/2.png" },
    { id: "first", position: 0, url: "https://cdn.example/1.png" },
  ] });
  const before = structuredClone(data);
  const item = mapListing(data, apiBase);
  assert.deepEqual(item.photoRefs, [
    { id: "second", position: 1, url: "http://10.1.2.3:8000/media/2.png" },
    { id: "first", position: 0, url: "https://cdn.example/1.png" },
  ]);
  assert.deepEqual(item.photos, item.photoRefs.map(photo => photo.url));
  assert.deepEqual(data, before);
});
