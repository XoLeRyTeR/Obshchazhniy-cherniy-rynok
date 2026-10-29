import React, { createContext, useContext, useMemo, useState } from "react";
import { api as client, apiUrl, type PageResult } from "../../../shared/api";
import { type ApiListing, type Listing, mapListing, emptyListingsState } from "./model";

/** Хранит кеш объявлений, собственные ID и действия загрузки; сбрасывается при смене аккаунта. */
function useListingModel() {
  const [state, change] = useState(emptyListingsState);
  /** Обновляет объявления по ID, не принимая запоздалые ответы предыдущей авторизации. */
  function cache(items: Listing[], token = client.token) {
    // Ответ запроса предыдущего аккаунта не должен попасть в текущий кеш.
    if (!token || token !== client.token) return;
    change((current) => ({
      ...current,
      listings: [
        ...new Map(
          [...current.listings, ...items].map((i) => [i.id, i]),
        ).values(),
      ],
    }));
  }

  /** Загружает подробности одного объявления, преобразует ответ и обновляет кеш. */
  async function getListing(id: string) {
    const token = client.token;
    const item = mapListing(
      await client.request<ApiListing>(`/listings/${id}`),
      apiUrl,
    );
    cache([item], token);
    return item;
  }

  /** Загружает страницу ленты по фильтрам и вычисляет смещение следующей порции. */
  async function loadFeed(params: Record<string, string>) {
    const token = client.token;
    const data = await client.request<PageResult<ApiListing>>(
      `/listings?${new URLSearchParams(params)}`,
    );
    const items = data.items.map((i) => mapListing(i, apiUrl));
    cache(items, token);
    // Неполная страница завершает список; после полной последней страницы придёт пустая.
    const nextOffset = items.length === Number(params.size ?? 20)
      ? Number(params.offset ?? 0) + items.length
      : null;
    return { items, nextOffset };
  }

  /** Загружает собственные объявления и обновляет их кеш и список ID профиля. */
  async function refreshOwn() {
    const token = client.token;
    const items = (await client.all<ApiListing>("/users/me/listings")).map(
      (i) => mapListing(i, apiUrl),
    );
    cache(items, token);
    if (token === client.token)
      change((current) => ({ ...current, ownIds: items.map((i) => i.id) }));
  }
  /** Обновляет имя автора в закешированных объявлениях после редактирования профиля. */
  function renameAuthor(id: string, name: string) {
    change(current => ({
      ...current,
      listings: current.listings.map(item => item.ownerId === id ? { ...item, author: name } : item),
    }));
  }
  const actions = useMemo(() => ({ cache, getListing, loadFeed, refreshOwn, renameAuthor }), []);
  return { ...state, ...actions };
}

const Context = createContext<ReturnType<typeof useListingModel> | null>(null);
/** Предоставляет дочерним компонентам отдельное состояние объявлений. */
export function ListingProvider({ children }: React.PropsWithChildren) {
  return <Context.Provider value={useListingModel()}>{children}</Context.Provider>;
}
/** Возвращает кеш и действия объявлений; требует подключения ListingProvider. */
export function useListings() {
  const value = useContext(Context);
  if (!value) throw new Error("ListingProvider is missing");
  return value;
}
