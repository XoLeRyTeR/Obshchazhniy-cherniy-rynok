import { strict as assert } from "node:assert";
import { test } from "node:test";
import { ApiClient, ApiError } from "../src/shared/api/client.ts";

test("клиент передаёт Bearer и JSON только при наличии тела", async () => {
  // Подменяем fetch: проверяем токен в GET, отсутствие лишнего Content-Type и JSON-тело POST.
  const original = globalThis.fetch;
  const calls: RequestInit[] = [];
  globalThis.fetch = async (_, options) => {
    calls.push(options ?? {});
    return Response.json({ ok: true });
  };
  try {
    const client = new ApiClient("http://api.test/api/v1/");
    client.token = "token";
    await client.request("/users/me");
    await client.request("/listings", {
      method: "POST",
      body: { title: "Стул" },
    });
    assert.equal(
      new Headers(calls[0].headers).get("Authorization"),
      "Bearer token",
    );
    assert.equal(new Headers(calls[0].headers).has("Content-Type"), false);
    assert.equal(calls[1].body, '{"title":"Стул"}');
  } finally {
    globalThis.fetch = original;
  }
});
test("401 завершает только ту авторизацию, с которой был начат запрос", async () => {
  // Запоздалый 401 старого токена не должен сбрасывать новый вход; текущий 401 вызывает выход.
  const original = globalThis.fetch;
  let resolve: (response: Response) => void = () => {};
  globalThis.fetch = () =>
    new Promise((r) => {
      resolve = r;
    });
  try {
    const client = new ApiClient("http://api.test");
    client.token = "old";
    let expired = 0;
    client.onUnauthorized = () => {
      expired++;
    };
    const request = client.request("/users/me");
    client.token = "new";
    resolve(Response.json({ detail: {} }, { status: 401 }));
    await assert.rejects(request, ApiError);
    assert.equal(expired, 0);
    globalThis.fetch = async () =>
      Response.json({ detail: {} }, { status: 401 });
    await assert.rejects(client.request("/users/me"), ApiError);
    assert.equal(expired, 1);
  } finally {
    globalThis.fetch = original;
  }
});
test("ошибка сети не превращается в успешное изменение и не вызывает выход", async () => {
  // Сбой fetch должен вернуть ApiError со статусом 0, сохранив авторизацию пользователя.
  const original = globalThis.fetch;
  globalThis.fetch = async () => {
    throw new TypeError("network");
  };
  try {
    const client = new ApiClient("http://api.test");
    client.token = "token";
    let expired = false;
    client.onUnauthorized = () => {
      expired = true;
    };
    await assert.rejects(
      client.request("/listings", { method: "POST", body: {} }),
      (e) => e instanceof ApiError && e.status === 0,
    );
    assert.equal(expired, false);
  } finally {
    globalThis.fetch = original;
  }
});
test("пустой 204 и ошибки полей обрабатываются без падения JSON-парсера", async () => {
  // Ответ 204 возвращает undefined, а поле password из ошибки 422 попадает в ошибки формы.
  const original = globalThis.fetch;
  try {
    const client = new ApiClient("http://api.test");
    globalThis.fetch = async () => new Response(null, { status: 204 });
    assert.equal(
      await client.request("/photo", { method: "DELETE" }),
      undefined,
    );
    globalThis.fetch = async () =>
      Response.json(
        { detail: [{ loc: ["body", "password"], msg: "bad" }] },
        { status: 422 },
      );
    await assert.rejects(
      client.request("/auth/login"),
      (e) => e instanceof ApiError && !!e.fields.password,
    );
  } finally {
    globalThis.fetch = original;
  }
});
test("пагинация обходит все страницы и сохраняет фильтры", async () => {
  // После 100 записей запрашиваем offset=100 с тем же вузом; неполная страница завершает обход.
  const original = globalThis.fetch;
  const urls: string[] = [];
  globalThis.fetch = async (url) => {
    urls.push(String(url));
    return Response.json(
      urls.length === 1
        ? { items: Array.from({ length: 100 }, (_, i) => i) }
        : { items: [100] },
    );
  };
  try {
    const result = await new ApiClient("http://api.test").all(
      "/dormitories?university_id=uni",
    );
    assert.deepEqual(result, Array.from({ length: 101 }, (_, i) => i));
    assert.equal(new URL(urls[1]).searchParams.get("university_id"), "uni");
    assert.equal(new URL(urls[0]).searchParams.get("offset"), "0");
    assert.equal(new URL(urls[1]).searchParams.get("offset"), "100");
    assert.equal(new URL(urls[1]).searchParams.get("size"), "100");
  } finally {
    globalThis.fetch = original;
  }
});
