import { strict as assert } from "node:assert";
import { test } from "node:test";
import { mapProfile } from "../src/entities/user/model/model.ts";
import { mediaUrl } from "../src/shared/lib/media-url.ts";
import { normalizeDorm } from "../src/entities/location/model/model.ts";
import { apiBase } from "./fixtures.ts";

test("профиль сохраняет серверные ID вуза и общежития отдельно от названий", () => {
  const data = {
    id: "user", name: "Анна", email: "anna@example.com",
    university: { id: "uni", name: "ИГЭУ" },
    dormitory: { id: "dorm", name: "Кампус", university_id: "uni" },
  };
  const before = structuredClone(data);
  assert.deepEqual(mapProfile(data), {
    id: "user", name: "Анна", email: "anna@example.com",
    universityId: "uni", university: "ИГЭУ", dormitoryId: "dorm", dorm: "Кампус",
  });
  assert.deepEqual(data, before);
});

test("локальные URL фото сохраняют путь и параметры при замене сервера", () => {
  for (const host of ["localhost", "127.0.0.1", "0.0.0.0"])
    assert.equal(mediaUrl(`http://${host}:9000/media/photo.png?size=200&v=2`, apiBase),
      "http://10.1.2.3:8000/media/photo.png?size=200&v=2");
});

test("относительные фото разрешаются на сервере API, а CDN сохраняет свой адрес и параметры", () => {
  assert.equal(mediaUrl("/media/photo.png", apiBase), "http://10.1.2.3:8000/media/photo.png");
  const cdn = "https://cdn.example:8443/photo.png?signature=abc#preview";
  assert.equal(mediaUrl(cdn, apiBase), cdn);
});

test("нормализация общежития обрабатывает табуляцию, переносы строк и пустой ввод", () => {
  assert.equal(normalizeDorm("\t Северный\n\tкампус \u00a0"), "Северный кампус");
  assert.equal(normalizeDorm(" \t\n"), "");
  assert.equal(normalizeDorm("Общежитие № 7-Б"), "Общежитие № 7-Б");
});
