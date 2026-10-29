/** Заменяет серверный localhost адресом API, доступным телефону; внешние ссылки сохраняет. */
export function mediaUrl(value: string, baseUrl: string) {
  const url = new URL(value, baseUrl);
  if (["localhost", "127.0.0.1", "0.0.0.0"].includes(url.hostname))
    return new URL(
      url.pathname + url.search,
      new URL(baseUrl).origin,
    ).toString();
  return url.toString();
}
