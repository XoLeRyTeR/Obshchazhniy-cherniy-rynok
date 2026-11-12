import type { ApiListing } from "../src/entities/listing/model/model.ts";
import type { ApiMessage, ApiChat } from "../src/entities/chat/model/model.ts";

export const apiBase = "http://10.1.2.3:8000/api/v1";

export function listing(overrides: Partial<ApiListing> = {}): ApiListing {
  return {
    id: "listing", owner_id: "owner", title: "Стул", description: "Рабочий",
    category: "furniture", format: "sell", price: 125050, status: "active",
    author: { id: "owner", name: "Андрей" },
    dormitory: { id: "dorm", name: "Северный кампус", university_id: "uni" },
    university: { id: "uni", name: "ИГЭУ" }, photos: [], ...overrides,
  };
}

export function message(overrides: Partial<ApiMessage> = {}): ApiMessage {
  return {
    id: "message", sender_id: "owner", text: "Здравствуйте",
    created_at: "2026-10-29T10:00:00Z", ...overrides,
  };
}

export function chat(overrides: Partial<ApiChat> = {}): ApiChat {
  return {
    id: "chat", listing: { id: "listing", title: "Стул", status: "active" },
    counterpart: { id: "buyer", name: "Покупатель" }, unread: 2,
    last_message: message(), ...overrides,
  };
}
