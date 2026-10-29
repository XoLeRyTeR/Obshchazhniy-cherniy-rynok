import type { PageResult } from "./types.ts";

export class ApiError extends Error {
  status: number;
  fields: Record<string, string>;
  /** Создаёт ошибку API с HTTP-статусом, сообщением и ошибками отдельных полей. */
  constructor(
    status: number,
    message: string,
    fields: Record<string, string> = {},
  ) {
    super(message);
    this.status = status;
    this.fields = fields;
  }
}
/** Возвращает понятный текст ошибки либо общее сообщение для неизвестного значения. */
export function errorText(error: unknown) {
  return error instanceof Error ? error.message : "Не удалось выполнить запрос";
}

export class ApiClient {
  token: string | null = null;
  onUnauthorized: (() => void) | undefined;
  baseUrl: string;
  private native: boolean;
  /** Настраивает базовый адрес HTTP-клиента и способ загрузки файлов для текущей платформы. */
  constructor(baseUrl: string, native = false) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.native = native;
  }

  /** Выполняет HTTP-запрос с Bearer-токеном и таймаутом; преобразует ошибки сервера и сети в ApiError. */
  async request<T>(
    path: string,
    options: { method?: string; body?: unknown; form?: FormData; } = {},
  ): Promise<T> {
    const token = this.token;
    const controller = new AbortController();
    const timer = setTimeout(
      () => controller.abort(),
      options.form ? 60000 : 20000,
    );
    try {
      const response = await fetch(this.baseUrl + path, {
        method: options.method ?? "GET",
        signal: controller.signal,
        // Для FormData не задаём Content-Type: fetch сам добавит границу multipart-частей.
        headers: {
          ...(options.body !== undefined && {
            "Content-Type": "application/json",
          }),
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        body:
          options.form ??
          (options.body !== undefined
            ? JSON.stringify(options.body)
            : undefined),
      });
      if (response.status === 204) return undefined as T;
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        // Запоздалый 401 старого токена не должен завершать новую авторизацию.
        if (response.status === 401 && token && token === this.token)
          this.onUnauthorized?.();
        const detail = data?.detail;
        const fields: Record<string, string> = {};
        if (Array.isArray(detail))
          for (const error of detail) {
            const field = String(error.loc?.at(-1) ?? "form");
            fields[field] = "Проверьте значение поля";
          }
        const fallback =
          response.status === 401
            ? "Неверная почта или пароль. Войдите снова."
            : response.status === 422
              ? "Проверьте введённые данные"
              : response.status === 429
                ? "Слишком много попыток. Попробуйте позже."
                : "Не удалось выполнить запрос";
        throw new ApiError(
          response.status,
          response.status === 401 ? fallback : (detail?.message ?? fallback),
          fields,
        );
      }
      return data as T;
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new ApiError(
        0,
        controller.signal.aborted
          ? "Сервер долго не отвечает. Попробуйте ещё раз."
          : "Не удалось связаться с сервером. Проверьте подключение и повторите.",
      );
    } finally {
      clearTimeout(timer);
    }
  }

  /** Загружает список всеми страницами offset/size, сохраняя фильтры и проверяя смену аккаунта. */
  async all<T>(path: string): Promise<T[]> {
    const items: T[] = [];
    const token = this.token;
    let offset = 0;
    while (true) {
      const query = new URLSearchParams({ offset: String(offset), size: "100" });
      const result: PageResult<T> = await this.request(
        `${path}${path.includes("?") ? "&" : "?"}${query}`,
      );
      if (this.token !== token)
        throw new ApiError(0, "Аккаунт изменился. Повторите запрос.");
      items.push(...result.items);
      if (result.items.length < 100) break;
      offset += result.items.length;
    }
    return items;
  }

  /** Отправляет фотографию как multipart: использует URI в React Native и Blob в браузере. */
  async upload<T>(
    path: string,
    uri: string,
    mimeType = "image/jpeg",
  ): Promise<T> {
    const form = new FormData();
    const extension =
      mimeType === "image/png"
        ? "png"
        : mimeType === "image/webp"
          ? "webp"
          : "jpg";
    if (this.native)
      form.append("file", {
        uri,
        name: `image.${extension}`,
        type: mimeType,
      } as unknown as Blob);
    else {
      const blob = await (await fetch(uri)).blob();
      form.append("file", blob, `image.${extension}`);
    }
    return this.request(path, { method: "POST", form });
  }
}
