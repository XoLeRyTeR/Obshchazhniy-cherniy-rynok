import { strict as assert } from "node:assert";
import { test } from "node:test";
import { ApiClient, ApiError, errorText } from "../src/shared/api/client.ts";

test("вход отправляется без Bearer, а после выхода старый токен больше не передаётся", async (t) => {
  const calls: { url: string; options: RequestInit }[] = [];
  t.mock.method(globalThis, "fetch", async (url: string, options: RequestInit) => {
    calls.push({ url: String(url), options });
    return Response.json({ ok: true });
  });
  const client = new ApiClient("http://api.test/api/v1/");
  await client.request("/auth/login", { method: "POST", body: { email: "user@test.com" } });
  client.token = "token";
  await client.request("/users/me");
  client.token = null;
  await client.request("/listings");
  assert.equal(calls[0].url, "http://api.test/api/v1/auth/login");
  assert.equal(new Headers(calls[0].options.headers).has("Authorization"), false);
  assert.equal(new Headers(calls[0].options.headers).get("Content-Type"), "application/json");
  assert.equal(new Headers(calls[1].options.headers).get("Authorization"), "Bearer token");
  assert.equal(new Headers(calls[2].options.headers).has("Authorization"), false);
});

test("неверный пароль без текущего токена не вызывает обработчик завершения сессии", async (t) => {
  t.mock.method(globalThis, "fetch", async () => Response.json({}, { status: 401 }));
  const client = new ApiClient("http://api.test");
  const expired = t.mock.fn();
  client.onUnauthorized = expired;
  await assert.rejects(client.request("/auth/login", { method: "POST", body: {} }),
    (error: unknown) => error instanceof ApiError && error.status === 401);
  assert.equal(expired.mock.callCount(), 0);
});

test("401, пришедший после выхода, не завершает сессию повторно", async (t) => {
  let respond!: (response: Response) => void;
  t.mock.method(globalThis, "fetch", () => new Promise<Response>(resolve => { respond = resolve; }));
  const client = new ApiClient("http://api.test");
  client.token = "token";
  const expired = t.mock.fn();
  client.onUnauthorized = expired;
  const request = client.request("/users/me");
  client.token = null;
  respond(Response.json({}, { status: 401 }));
  await assert.rejects(request, ApiError);
  assert.equal(expired.mock.callCount(), 0);
});

for (const scenario of [
  { status: 403, body: JSON.stringify({ detail: { message: "Нет доступа" } }), message: "Нет доступа" },
  { status: 409, body: JSON.stringify({ detail: { message: "Объявление уже изменено" } }), message: "Объявление уже изменено" },
  { status: 429, body: "", message: "Слишком много попыток. Попробуйте позже." },
  { status: 503, body: "<html>Unavailable</html>", message: "Не удалось выполнить запрос" },
]) {
  test(`HTTP ${scenario.status}: отображается понятная ошибка без сброса сессии`, async (t) => {
    t.mock.method(globalThis, "fetch", async () => new Response(scenario.body, { status: scenario.status }));
    const client = new ApiClient("http://api.test");
    client.token = "token";
    const expired = t.mock.fn();
    client.onUnauthorized = expired;
    await assert.rejects(client.request("/listings"), (error: unknown) => {
      assert.ok(error instanceof ApiError);
      assert.equal(error.status, scenario.status);
      assert.equal(errorText(error), scenario.message);
      return true;
    });
    assert.equal(expired.mock.callCount(), 0);
    assert.equal(client.token, "token");
  });
}

test("422 сохраняет ошибки нескольких полей и ошибку формы без loc", async (t) => {
  t.mock.method(globalThis, "fetch", async () => Response.json({ detail: [
    { loc: ["body", "email"] }, { loc: ["body", "password"] }, { msg: "bad form" },
  ] }, { status: 422 }));
  await assert.rejects(new ApiClient("http://api.test").request("/auth/register"), (error: unknown) => {
    assert.ok(error instanceof ApiError);
    assert.deepEqual(error.fields, {
      email: "Проверьте значение поля", password: "Проверьте значение поля", form: "Проверьте значение поля",
    });
    return true;
  });
});

test("пустой список заканчивает пагинацию после первого запроса", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch", async () => Response.json({ items: [] }));
  assert.deepEqual(await new ApiClient("http://api.test").all("/chats"), []);
  assert.equal(fetch.mock.callCount(), 1);
});

test("полная последняя страница требует ровно одного дополнительного пустого запроса", async (t) => {
  const urls: string[] = [];
  t.mock.method(globalThis, "fetch", async (url: string) => {
    urls.push(String(url));
    return Response.json({ items: urls.length === 1 ? Array.from({ length: 100 }, (_, id) => id) : [] });
  });
  const result = await new ApiClient("http://api.test").all("/listings");
  assert.deepEqual(result, Array.from({ length: 100 }, (_, id) => id));
  assert.deepEqual(urls.map(url => new URL(url).searchParams.get("offset")), ["0", "100"]);
});

for (const nextToken of ["new-account", null]) {
  test(`смена токена на ${nextToken === null ? "null" : "новый"} прерывает пагинацию без выдачи чужих данных`, async (t) => {
    const client = new ApiClient("http://api.test");
    client.token = "old-account";
    const fetch = t.mock.method(globalThis, "fetch", async () => {
      client.token = nextToken;
      return Response.json({ items: Array.from({ length: 100 }, (_, id) => id) });
    });
    await assert.rejects(client.all("/users/me/listings"), (error: unknown) =>
      error instanceof ApiError && error.message === "Аккаунт изменился. Повторите запрос.");
    assert.equal(fetch.mock.callCount(), 1);
  });
}

test("ошибка второй страницы отклоняет загрузку целиком вместо выдачи неполного списка", async (t) => {
  let calls = 0;
  t.mock.method(globalThis, "fetch", async () => ++calls === 1
    ? Response.json({ items: Array.from({ length: 100 }, (_, id) => id) })
    : Response.json({}, { status: 503 }));
  await assert.rejects(new ApiClient("http://api.test").all("/chats"),
    (error: unknown) => error instanceof ApiError && error.status === 503);
  assert.equal(calls, 2);
});

for (const scenario of [{ form: false, timeout: 20000 }, { form: true, timeout: 60000 }]) {
  test(`таймаут ${scenario.form ? "фото" : "JSON-запроса"} отменяет fetch и показывает ошибку ожидания`, async (t) => {
    t.mock.timers.enable({ apis: ["setTimeout"] });
    let signal!: AbortSignal;
    t.mock.method(globalThis, "fetch", (_: string, options: RequestInit) => {
      signal = options.signal!;
      return new Promise<Response>((_, reject) => {
        signal.addEventListener("abort", () => reject(new Error("aborted")), { once: true });
      });
    });
    const client = new ApiClient("http://api.test");
    const request = client.request("/listings", scenario.form ? { form: new FormData() } : {});
    const rejection = assert.rejects(request, (error: unknown) =>
      error instanceof ApiError && error.status === 0 && error.message.includes("долго не отвечает"));
    t.mock.timers.tick(scenario.timeout - 1);
    assert.equal(signal.aborted, false);
    t.mock.timers.tick(1);
    await rejection;
    assert.equal(signal.aborted, true);
  });
}

test("таймер успешного запроса очищается и не отменяет его сигнал позднее", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  let signal!: AbortSignal;
  t.mock.method(globalThis, "fetch", async (_: string, options: RequestInit) => {
    signal = options.signal!;
    return Response.json({ id: "listing" });
  });
  assert.deepEqual(await new ApiClient("http://api.test").request("/listings/1"), { id: "listing" });
  t.mock.timers.tick(60000);
  assert.equal(signal.aborted, false);
});

for (const [mime, extension] of [["image/jpeg", "jpg"], ["image/png", "png"], ["image/webp", "webp"]]) {
  test(`загрузка ${extension} отправляет содержимое фото через multipart с Bearer`, async (t) => {
    const uri = "blob:local-photo";
    const calls: string[] = [];
    t.mock.method(globalThis, "fetch", async (url: string, options?: RequestInit) => {
      calls.push(String(url));
      if (url === uri) return new Response(new Blob(["photo bytes"], { type: mime }));
      assert.equal(options?.method, "POST");
      const headers = new Headers(options?.headers);
      assert.equal(headers.get("Authorization"), "Bearer token");
      assert.equal(headers.has("Content-Type"), false);
      assert.ok(options?.body instanceof FormData);
      const file = options.body.get("file") as File;
      assert.equal(file.name, `image.${extension}`);
      assert.equal(file.type, mime);
      assert.equal(await file.text(), "photo bytes");
      return Response.json({ id: "photo" });
    });
    const client = new ApiClient("http://api.test");
    client.token = "token";
    assert.deepEqual(await client.upload("/listings/1/photos", uri, mime), { id: "photo" });
    assert.deepEqual(calls, [uri, "http://api.test/listings/1/photos"]);
  });
}

test("отказ сервера при загрузке фото не маскируется под успешную загрузку", async (t) => {
  t.mock.method(globalThis, "fetch", async (url: string) => url === "blob:photo"
    ? new Response(new Blob(["photo"]))
    : Response.json({ detail: { message: "Фото слишком большое" } }, { status: 413 }));
  await assert.rejects(new ApiClient("http://api.test").upload("/photos", "blob:photo"),
    (error: unknown) => error instanceof ApiError && error.status === 413 && error.message === "Фото слишком большое");
});

test("неизвестная ошибка получает безопасный текст для интерфейса", () => {
  for (const value of [null, undefined, "ошибка", { message: "не Error" }])
    assert.equal(errorText(value), "Не удалось выполнить запрос");
  assert.equal(errorText(new Error("Нет сети")), "Нет сети");
});
