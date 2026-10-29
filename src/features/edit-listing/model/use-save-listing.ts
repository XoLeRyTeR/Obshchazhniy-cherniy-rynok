import { useCallback } from "react";
import { api as client,apiUrl } from "../../../shared/api";
import { mediaUrl } from "../../../shared/lib";
import { type ApiListing,type Listing,type Photo,listingPayload,mapListing,useListings } from "../../../entities/listing";

/** Сохраняет объявление и фото; после частичного сбоя повторяет запросы без дубля объявления. */
export function useSaveListing() {
  const { cache,getListing,refreshOwn }=useListings();
  return useCallback(
    /** Сохраняет поля объявления, удаляет ненужные фото и загружает новые с обновлением черновика. */
    async function saveListing(
      draft: Listing,
      progress: (value: Listing) => void,
    ) {
      const token=client.token;
      let item=mapListing(
        await client.request<ApiListing>(
          draft.id? `/listings/${draft.id}`:"/listings",
          { method: draft.id? "PATCH":"POST",body: listingPayload(draft) },
        ),
        apiUrl,
      );
      let desired=[...draft.photos];
      /** Обновляет кеш и передаёт форме серверный ID и текущие ссылки для безопасного повтора сохранения. */
      function saved() {
        cache([item],token);
        progress({ ...item,photos: desired,photoTypes: draft.photoTypes });
      }
      saved(); // Запоминаем ID, чтобы повтор после ошибки фото не создал второе объявление.
      for(const old of [...item.photoRefs])
        if(!desired.includes(old.url)) {
          await client.request(`/listings/${item.id}/photos/${old.id}`,{
            method: "DELETE",
          });
          item={
            ...item,
            photoRefs: item.photoRefs.filter((p) => p.id!==old.id),
            photos: item.photos.filter((p) => p!==old.url),
          };
          saved();
        }
      for(const uri of [...desired])
        if(!item.photoRefs.some((p) => p.url===uri)) {
          const data=await client.upload<Photo>(
            `/listings/${item.id}/photos`,
            uri,
            draft.photoTypes?.[uri],
          );
          const photo={ ...data,url: mediaUrl(data.url,apiUrl) };
          // Сохраняем серверный URL в черновике, чтобы повтор не загрузил уже отправленное фото.
          desired=desired.map((value) => (value===uri? photo.url:value));
          item={
            ...item,
            photoRefs: [...item.photoRefs,photo],
            photos: [...item.photos,photo.url],
          };
          saved();
        }
      await refreshOwn();
      return getListing(item.id);
    },[cache,getListing,refreshOwn]);
}
