import { useCallback } from "react";
import { api as client,apiUrl } from "../../../shared/api";
import { type ApiListing,type Listing,type Status,mapListing,useListings } from "../../../entities/listing";

/** Меняет статус с expected_status и обновляет кеш, в том числе после конфликта. */
export function useChangeListingStatus() {
  const { cache,getListing }=useListings();
  return useCallback(
    /** Отправляет новый и ожидаемый статусы объявления, обновляет кеш и передаёт ошибку вызывающему коду. */
    async function changeStatus(item: Listing,status: Status) {
      const token=client.token;
      try {
        const data=await client.request<ApiListing>(
          `/listings/${item.id}/status`,
          { method: "PATCH",body: { expected_status: item.status,status } },
        );
        cache([mapListing(data,apiUrl)],token);
      } catch(error) {
        // Перечитываем фактический статус, но сохраняем исходную ошибку для пользователя.
        await getListing(item.id).catch(() => { });
        throw error;
      }
    },[cache,getListing]);
}
