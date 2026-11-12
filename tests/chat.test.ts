import { strict as assert } from "node:assert";
import { test } from "node:test";
import { mapChat, mapMessage, mergeMessages } from "../src/entities/chat/model/model.ts";
import { chat, message } from "./fixtures.ts";

test("новый чат без сообщений имеет пустую историю и превью", () => {
  assert.deepEqual(mapChat(chat({ last_message: null, unread: 0 })), {
    id: "chat", listingId: "listing", title: "Стул", status: "active",
    name: "Покупатель", unread: 0, lastText: "", messages: [],
  });
});

test("обновление превью чата сохраняет загруженную историю и обновляет статус и непрочитанные", () => {
  const history = [mapMessage(message(), "owner")];
  const previous = { ...mapChat(chat()), messages: history };
  const incoming = chat({
    unread: 0, last_message: message({ text: "Заберу завтра" }),
    listing: { id: "listing", title: "Новый заголовок", status: "reserved" },
  });
  const next = mapChat(incoming, previous);
  assert.deepEqual(next.messages, history);
  assert.equal(next.status, "reserved");
  assert.equal(next.title, "Новый заголовок");
  assert.equal(next.lastText, "Заберу завтра");
  assert.equal(next.unread, 0);
  assert.equal(previous.unread, 2);
});

test("повторное получение сообщения заменяет его данные без дублирования и потери истории", () => {
  const old = [mapMessage(message({ id: "one" }), "owner"),
    mapMessage(message({ id: "two", text: "Старый текст" }), "owner")];
  const incoming = [mapMessage(message({ id: "two", text: "Новый текст" }), "owner")];
  const before = structuredClone(old);
  const result = mergeMessages(old, incoming);
  assert.deepEqual(result.map(item => item.id), ["one", "two"]);
  assert.equal(result[1].text, "Новый текст");
  assert.deepEqual(old, before);
});

test("перекрывающиеся страницы истории объединяются в хронологическом порядке", () => {
  const make = (id: string, created_at: string) => mapMessage(message({ id, created_at }), "owner");
  const first = make("first", "2026-10-29T10:00:00Z");
  const middle = make("middle", "2026-10-29T10:00:00.000001Z");
  const last = make("last", "2026-10-29T10:00:01Z");
  assert.deepEqual(mergeMessages([last, middle], [middle, first]), [first, middle, last]);
});

test("равные UTC-моменты с разной записью долей секунды сортируются стабильно по ID", () => {
  const dates = ["2026-10-29T10:00:00Z", "2026-10-29T10:00:00.000000+00:00", "2026-10-29T10:00:00.000Z"];
  const items = dates.map((created_at, index) =>
    mapMessage(message({ id: String(3 - index), created_at }), "owner"));
  assert.deepEqual(mergeMessages([], items).map(item => item.id), ["1", "2", "3"]);
});

test("повторный опрос чата не накапливает дубликаты сообщений", () => {
  const items = [mapMessage(message(), "owner")];
  assert.deepEqual(mergeMessages(mergeMessages([], items), items), items);
  assert.deepEqual(mergeMessages(items, []), items);
  assert.deepEqual(mergeMessages([], []), []);
});
