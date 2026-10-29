import { api, type CatalogItem } from "../../../shared/api";

/** Загружает полный справочник вузов, обходя страницы API. */
export const universities = () => api.all<CatalogItem>("/universities");
/** Загружает все общежития указанного вуза, сохраняя фильтр при обходе страниц. */
export const dormitories = (id: string) =>
  api.all<CatalogItem>(`/dormitories?university_id=${encodeURIComponent(id)}`);
