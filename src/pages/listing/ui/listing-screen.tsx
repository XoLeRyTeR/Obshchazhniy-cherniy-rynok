import { styles, sheetStyle, photoIndicator } from "./styles";
import React, { useCallback, useState } from "react";
import { Pressable, ScrollView, Text, View } from "react-native";
import { router, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { errorText } from "../../../shared/api";
import { useSession } from "../../../entities/user";
import { priceLabel, statusLabel, Picture, useListings } from "../../../entities/listing";
import { useChats } from "../../../entities/chat";
import { dormLabel } from "../../../entities/location";
import { OwnerActions } from "../../../features/change-listing-status";
import { Button, Badge, colors, Empty, ErrorNotice, s, Skeleton } from "../../../shared/ui";

/** Показывает подробности объявления в модальном окне с фото, действиями автора или открытием чата. */
export function ListingScreen() {
  const { id } = useLocalSearchParams<{ id: string; }>();
  const { profile } = useSession();
  const { listings, getListing } = useListings();
  const { chats, openChat } = useChats();
  const item = listings.find((i) => i.id === id);
  const own = item?.ownerId === profile.id;
  const insets = useSafeAreaInsets();
  const [loading, setLoading] = useState(!item);
  const [loadError, setLoadError] = useState("");
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const [busy, setBusy] = useState(false);
  const [photoIndex, setPhotoIndex] = useState(0);
  useFocusEffect(
    useCallback(() => {
      let active = true;
      getListing(id)
        .then(() => {
          if (active) setLoadError("");
        })
        .catch((e) => {
          if (active) setLoadError(errorText(e));
        })
        .finally(() => {
          if (active) setLoading(false);
        });
      return () => {
        active = false;
      };
    }, [id, getListing, retry]),
  );
  /** Открывает переписку по объявлению и заменяет модальное окно маршрутом чата. */
  async function write() {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const chatId = await openChat(id);
      router.replace({ pathname: "/conversation", params: { id: chatId } });
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <View style={s.overlay}>
      <Pressable
        accessibilityLabel="Закрыть объявление"
        style={styles.absoluteFill}
        onPress={() => router.back()}
      />
      <View
        accessibilityViewIsModal
        style={sheetStyle(insets.bottom)}
      >
        <View style={[s.row, styles.sheetHeader]}>
          <View style={styles.headerSpacer} />
          <View
            style={styles.handle}
          />
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Закрыть"
            onPress={() => router.back()}
            hitSlop={8}
          >
            <Text style={s.subtitle}>×</Text>
          </Pressable>
        </View>
        {loading ? (
          <Skeleton />
        ) : loadError || !item ? (
          <Empty
            title="Объявление недоступно"
            text={loadError || "Объявление не найдено"}
            action={
              <Button
                title="Повторить"
                onPress={() => setRetry((v) => v + 1)}
              />
            }
          />
        ) : (
          <ScrollView contentContainerStyle={styles.content}>
            <View>
              <Picture
                item={{
                  ...item,
                  photos: item.photos[photoIndex]
                    ? [item.photos[photoIndex]]
                    : item.photos,
                }}
                large
              />
              <View style={s.badgePosition}>
                <Badge text={item.format} />
              </View>
            </View>
            {item.photos.length > 1 && (
              <View style={[s.row, styles.photoNavigation]}>
                {item.photos.map((_, index) => (
                  <Pressable
                    key={index}
                    accessibilityRole="button"
                    accessibilityLabel={`Фотография ${index + 1}`}
                    onPress={() => setPhotoIndex(index)}
                  >
                    <Text
                      style={[
                        s.link,
                        photoIndicator(photoIndex === index),
                      ]}
                    >
                      {index + 1}
                    </Text>
                  </Pressable>
                ))}
              </View>
            )}
            <View style={styles.summary}>
              <Text style={[s.title, styles.title]}>{item.title}</Text>
              <Text style={[s.section, styles.price]}>
                {priceLabel(item)}
              </Text>
              <Text style={s.subtitle}>
                {item.category} · {dormLabel(item.dorm)}
              </Text>
              {item.status !== "active" && (
                <Text style={s.link}>{statusLabel[item.status]}</Text>
              )}
            </View>
            <Text style={s.body}>{item.description}</Text>
            <View
              style={[
                s.row,
                styles.author,
              ]}
            >
              <View style={[s.avatar, styles.avatar]}>
                <Text style={s.link}>{item.author[0]}</Text>
              </View>
              <View style={styles.authorCopy}>
                <Text style={s.cardTitle}>
                  {own ? "Ваше объявление" : item.author}
                </Text>
                <Text style={s.small}>
                  {item.university} · {dormLabel(item.dorm)}
                </Text>
              </View>
            </View>
            <ErrorNotice error={error} />
            {own ? (
              <>
                <Button
                  title="Редактировать объявление"
                  onPress={() =>
                    router.replace({
                      pathname: "/editor",
                      params: { id: item.id },
                    })
                  }
                />
                <OwnerActions item={item} />
              </>
            ) : (
              <>
                <Text style={s.small}>
                  Напишите автору, чтобы договориться о встрече, обмене или
                  услуге.
                </Text>
                <Button
                  title={
                    chats.some((c) => c.listingId === item.id)
                      ? "Открыть переписку"
                      : "Написать автору"
                  }
                  busy={busy}
                  onPress={write}
                />
              </>
            )}
          </ScrollView>
        )}
      </View>
    </View>
  );
}
