import React, { createContext, useContext, useMemo, useState } from "react";
import { api as client, type PageResult } from "../../../shared/api";
import { type ApiChat, type ApiMessage, mapChat, mapMessage, mergeMessages, emptyChatsState } from "./model";

/** Хранит чаты пользователя и операции загрузки, отправки сообщений и отметки прочтения. */
function useChatModel(userId: string) {
  const [state, change] = useState(emptyChatsState);
  /** Обновляет список чатов с сервера, сохраняя уже загруженную историю каждого чата. */
  async function refreshChats() {
    const token = client.token;
    const data = await client.all<ApiChat>("/chats");
    if (token === client.token)
      change((current) => ({
        ...current,
        // Обновление превью чатов не должно стирать уже загруженную историю переписки.
        chats: data.map((i) =>
          mapChat(
            i,
            current.chats.find((c) => c.id === i.id),
          ),
        ),
      }));
    return data;
  }

  /** Открывает или создаёт чат по объявлению, обновляет кеш и возвращает ID переписки. */
  async function openChat(listingId: string) {
    const token = client.token;
    const data = await client.request<ApiChat>("/chats", {
      method: "POST",
      body: { listing_id: listingId },
    });
    if (token === client.token)
      change((current) => ({
        ...current,
        chats: [
          mapChat(
            data,
            current.chats.find((c) => c.id === data.id),
          ),
          ...current.chats.filter((c) => c.id !== data.id),
        ],
      }));
    return data.id;
  }

  /** Загружает страницу истории, объединяет её с кешем и при необходимости отмечает прочтение. */
  async function loadMessages(id: string, offset = 0, markRead = true) {
    const token = client.token;
    const data = await client.request<PageResult<ApiMessage>>(
      `/chats/${id}/messages?${new URLSearchParams({ offset: String(offset), size: "50" })}`,
    );
    if (token !== client.token) return null;
    const messages = data.items.map((m) =>
      mapMessage(m, userId),
    );
    change((current) => ({
      ...current,
      chats: current.chats.map((c) =>
        c.id === id
          ? { ...c, messages: mergeMessages(c.messages, messages) }
          : c,
      ),
    }));
    // Загрузка старых страниц не меняет прочтение; в фоне экран передаёт markRead=false.
    if (offset === 0 && markRead && data.items.length) {
      await client.request(`/chats/${id}/read`, {
        method: "PATCH",
        body: { last_read_message_id: data.items[0].id },
      });
      if (token === client.token)
        change((current) => ({
          ...current,
          chats: current.chats.map((c) =>
            c.id === id ? { ...c, unread: 0 } : c,
          ),
        }));
    }
    return data.items.length === 50 ? offset + data.items.length : null;
  }

  /** Отправляет сообщение с ключом повтора и добавляет подтверждённый сервером результат в кеш. */
  async function sendMessage(id: string, text: string, key: string) {
    const token = client.token;
    const data = await client.request<ApiMessage>(`/chats/${id}/messages`, {
      method: "POST",
      body: { text, client_message_id: key },
    });
    if (token !== client.token) return;
    const message = mapMessage(data, userId);
    change((current) => ({
      ...current,
      chats: current.chats.map((c) =>
        c.id === id
          ? {
            ...c,
            messages: mergeMessages(c.messages, [message]),
            lastText: message.text,
          }
          : c,
      ),
    }));
  }
  const actions = useMemo(() => ({ refreshChats, openChat, loadMessages, sendMessage }), [userId]);
  return { ...state, ...actions };
}
const Context = createContext<ReturnType<typeof useChatModel> | null>(null);
/** Предоставляет дочерним компонентам состояние переписки для указанного пользователя. */
export function ChatProvider({ children, userId }: React.PropsWithChildren<{ userId: string; }>) {
  return <Context.Provider value={useChatModel(userId)}>{children}</Context.Provider>;
}
/** Возвращает состояние и действия чатов; вне ChatProvider сообщает об ошибке подключения. */
export function useChats() {
  const value = useContext(Context);
  if (!value) throw new Error("ChatProvider is missing");
  return value;
}
