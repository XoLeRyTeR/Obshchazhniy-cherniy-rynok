import type { CatalogItem } from "../../../shared/api";
import type { Status } from "../../listing/@x/chat.ts";

export type Message = {
  id: string;
  text: string;
  mine: boolean;
  time: string;
  createdAt: string;
};

export type Conversation = {
  id: string;
  listingId: string;
  title: string;
  status: Status;
  name: string;
  unread: number;
  messages: Message[];
  lastText: string;
};

export const emptyChatsState: { chats: Conversation[]; } = { chats: [] };

export type ApiMessage = {
  id: string;
  text: string;
  sender_id: string;
  created_at: string;
};

export type ApiChat = {
  id: string;
  listing: { id: string; title: string; status: Status; };
  counterpart: CatalogItem;
  unread: number;
  last_message: ApiMessage | null;
};

/** Преобразует сообщение API в модель интерфейса, определяя отправителя и подпись времени. */
export function mapMessage(data: ApiMessage, userId: string): Message {
  return {
    id: data.id,
    text: data.text,
    mine: data.sender_id === userId,
    createdAt: data.created_at,
    time: new Date(data.created_at).toLocaleTimeString("ru-RU", {
      hour: "2-digit",
      minute: "2-digit",
    }),
  };
}

/** Преобразует превью чата из API, сохраняя ранее загруженные сообщения. */
export function mapChat(data: ApiChat, previous?: Conversation): Conversation {
  return {
    id: data.id,
    listingId: data.listing.id,
    title: data.listing.title,
    status: data.listing.status,
    name: data.counterpart.name,
    unread: data.unread,
    lastText: data.last_message?.text ?? "",
    messages: previous?.messages ?? [],
  };
}

/** Выравнивает UTC-строки до микросекунд для сортировки без потери точности через Date. */
const timeKey = (value: string) =>
  value.replace(
    /(?:\.(\d+))?(?:Z|\+00:00)$/,
    (_, fraction) => `.${(fraction ?? "").padEnd(6, "0")}Z`,
  );

/** Объединяет сообщения по ID и сортирует от старых к новым с учётом микросекунд. */
export function mergeMessages(old: Message[], incoming: Message[]) {
  // Опрос и загрузка страниц пересекаются: объединяем по ID, не удаляя старую историю.
  return [
    ...new Map([...old, ...incoming].map((m) => [m.id, m])).values(),
  ].sort(
    (a, b) =>
      timeKey(a.createdAt).localeCompare(timeKey(b.createdAt)) ||
      a.id.localeCompare(b.id),
  );
}
