// Live frontend/backend check; creates unique local test accounts, never uses real credentials.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");

(async () => {
  const apiUrl = process.env.API_URL || "http://127.0.0.1:8000/api/v1";
  const appUrl = process.env.APP_URL || "http://localhost:8081";
  const output = path.resolve("artifacts/integration");
  await fs.mkdir(output, { recursive: true });
  const stamp = Date.now().toString(36);
  const password = "integration-pass-123";
  const emailA = `mobile-a-${stamp}@example.com`,
    emailB = `mobile-b-${stamp}@example.com`;
  async function api(endpoint, token, method = "GET", body) {
    const response = await fetch(apiUrl + endpoint, {
      method,
      headers: {
        ...(body && { "Content-Type": "application/json" }),
        ...(token && { Authorization: "Bearer " + token }),
      },
      body: body && JSON.stringify(body),
    });
    assert.ok(
      response.ok,
      `${method} ${endpoint}: ${response.status} ${await response.clone().text()}`,
    );
    return response.status === 204 ? null : response.json();
  }
  const universities = await api("/universities");
  assert.ok(
    universities.items.length,
    "Seed at least one university before the UI check",
  );
  const uni = universities.items[0];
  const actorB = await api("/auth/register", null, "POST", {
    email: emailB,
    password,
    name: "Борис тест",
    university_id: uni.id,
    dormitory_name: "17",
  });
  const partnerTitle = "Учебник " + stamp;
  const partnerListing = await api("/listings", actorB.access_token, "POST", {
    title: partnerTitle,
    description: "Учебник для проверки настоящего обмена и переписки",
    category: "books",
    format: "exchange",
    price: 0,
  });
  const browser = await chromium.launch({
    headless: true,
    ...(process.env.CHROME_PATH && { executablePath: process.env.CHROME_PATH }),
  });
  const contextA = await browser.newContext({
    viewport: { width: 390, height: 844 },
    isMobile: true,
    hasTouch: true,
  });
  const contextB = await browser.newContext({
    viewport: { width: 390, height: 844 },
    isMobile: true,
    hasTouch: true,
  });
  const page = await contextA.newPage(),
    pageB = await contextB.newPage();
  const errors = [];
  for (const p of [page, pageB])
    p.on("pageerror", (error) => errors.push(error.message));
  const button = (name, p = page) =>
    p.getByRole("button", { name, exact: true });
  const field = (name, p = page) => p.getByLabel(name, { exact: true }).filter({ visible: true });
  const tab = (name, p = page) =>
    p.getByRole("tab", { name: new RegExp(name) });
  const screenshot = (name) =>
    page.screenshot({
      path: path.join(output, name + ".png"),
      animations: "disabled",
    });
  const select = async (label, value, choice) => {
    await button(`${label}: ${value}`).click();
    await page.getByRole("radio", { name: choice, exact: true }).click();
  };
  async function login(p, email) {
    await field("Электронная почта", p).fill(email);
    await field("Пароль", p).fill(password);
    await button("Войти", p).click();
    await p
      .getByLabel("Поиск объявлений", { exact: true })
      .waitFor({ timeout: 30000 });
  }
  try {
    await page.goto(appUrl, { waitUntil: "domcontentloaded", timeout: 90000 });
    await button("Войти").waitFor({ timeout: 60000 });
    assert.equal(
      await field("Пароль").inputValue(),
      "",
    );
    await screenshot("01-login");
    await page
      .getByRole("link", { name: "Нет аккаунта? Создать", exact: true })
      .click();
    await field("Имя").fill("Андрей тест");
    await field("Электронная почта").fill(emailA);
    await field("Пароль").fill(password);
    await button(`Университет: ${uni.name}`).waitFor();
    await button("Общежитие: Выберите общежитие").waitFor();
    await select(
      "Общежитие",
      "Выберите общежитие",
      "В списке нет моего общежития",
    );
    const dormName = "Кампус " + stamp;
    await page
      .getByLabel("Название или номер общежития", { exact: true })
      .fill(dormName);
    const authResponse = page.waitForResponse(
      (r) =>
        r.url().endsWith("/auth/register") && r.request().method() === "POST",
    );
    await button("Создать аккаунт").click();
    const actorA = await (await authResponse).json();
    assert.ok(actorA.access_token);
    await page.getByLabel("Поиск объявлений", { exact: true }).waitFor();
    assert.equal(
      (await api("/users/me", actorA.access_token)).dormitory.name,
      dormName,
    );
    console.log("PASS real registration, server dormitory and token");

    await page
      .getByLabel("Поиск объявлений", { exact: true })
      .fill(partnerTitle);
    await button(partnerTitle + ", Обмен").waitFor();
    await screenshot("02-server-feed");
    await button(partnerTitle + ", Обмен").click();
    assert.equal(
      await page.getByText("Место встречи:", { exact: false }).count(),
      0,
    );
    await button("Написать автору").click();
    await page.getByLabel("Сообщение", { exact: true }).waitFor();
    await page
      .getByLabel("Сообщение", { exact: true })
      .fill("Привет из интерфейса");
    await button("Отправить сообщение").click();
    await page.getByText("Привет из интерфейса", { exact: true }).waitFor();
    const chats = await api("/chats", actorB.access_token);
    const chatId = chats.items.find(
      (c) => c.listing.id === partnerListing.id,
    ).id;
    assert.equal(
      (await api(`/chats/${chatId}/messages`, actorB.access_token)).items[0]
        .text,
      "Привет из интерфейса",
    );
    console.log("PASS search, listing details and persisted message");

    await pageB.goto(appUrl, { waitUntil: "domcontentloaded" });
    await login(pageB, emailB);
    await tab("Чаты", pageB).click();
    await button(`Чат: Андрей тест, ${partnerTitle}`, pageB).click();
    await pageB.getByText("Привет из интерфейса", { exact: true }).waitFor();
    await pageB
      .getByLabel("Сообщение", { exact: true })
      .fill("Вижу сообщение на другом устройстве");
    await button("Отправить сообщение", pageB).click();
    await page.bringToFront();
    await page
      .getByText("Вижу сообщение на другом устройстве", { exact: true })
      .waitFor({ timeout: 20000 });
    await screenshot("03-live-chat");
    console.log("PASS two independent accounts and incoming polling");

    await button("Назад").click();
    await tab("Профиль").click();
    await button("Добавить объявление").click();
    await page.getByLabel("Название", { exact: true }).fill("Лампа " + stamp);
    await page
      .getByLabel("Описание", { exact: true })
      .fill("Рабочая лампа, данные отправляются на сервер");
    assert.equal(await page.getByLabel("Место", { exact: true }).count(), 0);
    await select("Формат передачи", "Продам", "Отдам");
    const chooser = page.waitForEvent("filechooser");
    await button("Добавить фотографии").click();
    await (await chooser).setFiles(path.join(output, "01-login.png"));
    await page
      .getByText("Добавить фотографии · 1/5", { exact: true })
      .waitFor();
    const photoRoute = "**/api/v1/listings/*/photos";
    await page.route(photoRoute, (route) =>
      route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({
          detail: { message: "Проверка повторной загрузки" },
        }),
      }),
    );
    await button("Опубликовать").click();
    await page.getByText(/Объявление сохранено, но фотографии/).waitFor();
    const beforeRetry = await api("/users/me/listings", actorA.access_token);
    assert.equal(
      beforeRetry.items.filter((i) => i.title === "Лампа " + stamp).length,
      1,
    );
    await page.unroute(photoRoute);
    await button("Сохранить изменения").click();
    await button("Добавить объявление").waitFor();
    const own = (await api("/users/me/listings", actorA.access_token)).items;
    assert.equal(own.filter((i) => i.title === "Лампа " + stamp).length, 1);
    const published = own.find((i) => i.title === "Лампа " + stamp);
    assert.equal(published.photos.length, 1);
    await button("Лампа " + stamp + ", Бесплатно").click();
    await button("Отметить забронированным").click();
    await button("Вещь передана — завершить").waitFor();
    assert.equal(
      (await api("/listings/" + published.id, actorA.access_token)).status,
      "reserved",
    );
    await screenshot("04-published-photo-status");
    console.log("PASS photo retry without duplicate listing and owner status");

    await button("Закрыть").click();
    await button("Редактировать профиль").click();
    await page.getByLabel("Имя", { exact: true }).fill("Андрей обновлённый");
    await button("Сохранить").click();
    await button("Редактировать профиль").getByText("Андрей обновлённый", { exact: true }).waitFor();
    assert.equal(
      (await api("/users/me", actorA.access_token)).name,
      "Андрей обновлённый",
    );
    await page.reload();
    await tab("Профиль").click();
    await button("Редактировать профиль").getByText("Андрей обновлённый", { exact: true }).waitFor();
    await screenshot("05-profile-restored");
    console.log("PASS profile save and authenticated reload");

    await button("Выйти из аккаунта").click();
    await button("Войти").waitFor();
    await page.reload();
    await button("Войти").waitFor();
    assert.equal(
      await page.evaluate(() =>
        localStorage.getItem("obschazhny-api-token-v1"),
      ),
      null,
    );
    await login(page, emailA);
    await page.evaluate(() =>
      localStorage.setItem("obschazhny-api-token-v1", "invalid-token"),
    );
    await page.reload();
    await button("Войти").waitFor();
    assert.equal(
      await page.evaluate(() =>
        localStorage.getItem("obschazhny-api-token-v1"),
      ),
      null,
    );
    assert.deepEqual(errors, [], "Uncaught browser errors");
    assert.equal(
      await page.evaluate(
        () => document.documentElement.scrollWidth > window.innerWidth,
      ),
      false,
    );
    console.log(
      "PASS logout, invalid-token recovery, no browser errors or overflow",
    );
  } catch (error) {
    await screenshot("failure").catch(() => {});
    console.error(
      "BODY:",
      (await page.locator("body").innerText()).slice(0, 8000),
    );
    console.error("BROWSER ERRORS:", errors);
    throw error;
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
