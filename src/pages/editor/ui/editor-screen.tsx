import { styles } from "./styles";
import React, { useEffect, useState } from "react";
import { Alert, Pressable, ScrollView, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import * as ImagePicker from "expo-image-picker";
import { Image } from "expo-image";
import { errorText } from "../../../shared/api";
import { useSession } from "../../../entities/user";
import { categories, formats, Listing, validateListing, useListings } from "../../../entities/listing";
import { dormLabel } from "../../../entities/location";
import { useSaveListing } from "../../../features/edit-listing";
import { Button, colors, Empty, ErrorNotice, Field, Icon, Page, s, Select, Skeleton } from "../../../shared/ui";

/** Показывает создание или редактирование объявления с выбором фотографий и проверкой полей. */
export function EditorScreen() {
  const { id } = useLocalSearchParams<{ id?: string; }>();
  const { profile } = useSession();
  const { listings, getListing } = useListings();
  const saveListing = useSaveListing();
  const existing = listings.find((i) => i.id === id);
  const [draft, setDraft] = useState<Listing>(
    () =>
      existing ?? {
        id: "",
        title: "",
        description: "",
        category: "Техника",
        format: "Продам",
        price: 0,
        dorm: profile.dorm,
        dormitoryId: profile.dormitoryId,
        university: profile.university,
        author: profile.name,
        ownerId: profile.id,
        status: "active",
        photos: [],
        photoRefs: [],
        color: "sage",
      },
  );
  const [price, setPrice] = useState(
    existing?.price ? String(existing.price / 100) : "",
  );
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(!!id);
  const [retry, setRetry] = useState(0);
  const [busy, setBusy] = useState(false);
  const [photoBusy, setPhotoBusy] = useState(false);
  useEffect(() => {
    let active = true;
    if (id)
      getListing(id)
        .then((item) => {
          if (active) {
            setDraft(item);
            setPrice(item.price ? String(item.price / 100) : "");
            setError("");
          }
        })
        .catch((e) => {
          if (active) setError(errorText(e));
        })
        .finally(() => {
          if (active) setLoading(false);
        });
    return () => {
      active = false;
    };
  }, [id, getListing, retry]);
  /** Изменяет одно поле локального черновика объявления, не отправляя запрос на сервер. */
  const update = (key: keyof Listing, value: string | string[]) =>
    setDraft((current) => ({ ...current, [key]: value }));
  /** Запрашивает доступ к галерее, выбирает фото и добавляет их URI и MIME-типы с учётом лимита. */
  async function pickPhoto() {
    if (photoBusy || busy || draft.photos.length >= 5) return;
    setPhotoBusy(true);
    try {
      const permission =
        await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!permission.granted) {
        Alert.alert(
          "Нет доступа к фотографиям",
          "Разрешите доступ в настройках телефона.",
        );
        return;
      }
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ["images"],
        allowsMultipleSelection: true,
        selectionLimit: 5 - draft.photos.length,
        quality: 0.75,
      });
      if (!result.canceled) {
        if (
          result.assets.some((asset) => (asset.fileSize ?? 0) > 5 * 1024 * 1024)
        )
          throw new Error("Максимальный размер одной фотографии — 5 МБ");
        setDraft((current) => ({
          ...current,
          photos: [
            ...new Set([...current.photos, ...result.assets.map((a) => a.uri)]),
          ].slice(0, 5),
          photoTypes: {
            ...current.photoTypes,
            ...Object.fromEntries(
              result.assets.map((a) => [
                a.uri,
                a.mimeType === "image/jpg"
                  ? "image/jpeg"
                  : (a.mimeType ??
                    (/\.png(?:\?|$)/i.test(a.uri)
                      ? "image/png"
                      : "image/jpeg")),
              ]),
            ),
          },
        }));
      }
    } catch (e) {
      setError(errorText(e));
    } finally {
      setPhotoBusy(false);
    }
  }
  /** Проверяет черновик, переводит цену в копейки и сохраняет объявление с обработкой частичного сбоя фото. */
  async function publish() {
    if (busy || photoBusy) return;
    const priced = draft.format === "Продам" || draft.format === "Услуга";
    const item = {
      ...draft,
      title: draft.title.trim(),
      description: draft.description.trim(),
      // В форме рубли, а API хранит целое число копеек; отдача и обмен всегда бесплатны.
      price: priced ? Math.round(Number(price.replace(",", ".")) * 100) : 0,
    };
    const next = validateListing(item);
    if (priced && price && !/^\d+([.,]\d{1,2})?$/.test(price))
      next.price = "Введите сумму, например 500 или 500,50";
    setErrors(next);
    setError("");
    if (Object.keys(next).length) return;
    setBusy(true);
    let metadataSaved = false;
    try {
      await saveListing(item, (value) => {
        metadataSaved = true;
        setDraft(value);
      });
      router.replace("/(tabs)/profile");
    } catch (e) {
      setError(
        (metadataSaved
          ? "Объявление сохранено, но фотографии обновлены не полностью. Повторите сохранение. "
          : "") + errorText(e),
      );
    } finally {
      setBusy(false);
    }
  }
  if (loading)
    return (
      <Page title="Объявление" back>
        <Skeleton />
      </Page>
    );
  if (id && (draft.id !== id || draft.ownerId !== profile.id))
    return (
      <Page title="Объявление" back>
        <Empty
          title="Нет доступа"
          text={error || "Можно редактировать только своё объявление."}
          action={
            <Button title="Повторить" onPress={() => setRetry((v) => v + 1)} />
          }
        />
      </Page>
    );
  return (
    <Page title={id ? "Редактировать" : "Добавить объявление"} back>
      <ErrorNotice error={error} />
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Добавить фотографии"
        disabled={busy || photoBusy || draft.photos.length >= 5}
        onPress={pickPhoto}
        style={styles.photoPicker}
      >
        <Icon name="plus" size={24} />
        <Text style={s.link}>
          {photoBusy
            ? "Открываем фотографии…"
            : `Добавить фотографии · ${draft.photos.length}/5`}
        </Text>
      </Pressable>
      {draft.photos.length > 0 && (
        <ScrollView
          horizontal
          contentContainerStyle={styles.photos}
        >
          {draft.photos.map((uri) => (
            <View key={uri} style={styles.photoFrame}>
              <Image
                source={{ uri }}
                style={styles.photo}
                contentFit="cover"
              />
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Убрать фотографию"
                disabled={busy}
                onPress={() =>
                  update(
                    "photos",
                    draft.photos.filter((p) => p !== uri),
                  )
                }
                style={styles.removePhoto}
              >
                <Text>×</Text>
              </Pressable>
            </View>
          ))}
        </ScrollView>
      )}
      <Text style={[s.small, styles.photoHint]}>
        Можно без фото — покажем цветную заглушку.
      </Text>
      <Field
        label="Название"
        placeholder="Например, настольная лампа"
        value={draft.title}
        onChangeText={(value) => update("title", value)}
        error={errors.title}
        maxLength={120}
        editable={!busy}
      />
      <Field
        label="Описание"
        placeholder="Состояние, особенности, детали обмена или услуги…"
        value={draft.description}
        onChangeText={(value) => update("description", value)}
        multiline
        error={errors.description}
        maxLength={5000}
        editable={!busy}
      />
      <Select
        label="Категория"
        value={draft.category}
        options={categories}
        onChange={(value) => {
          if (!busy) update("category", value);
        }}
      />
      <Select
        label="Формат передачи"
        value={draft.format}
        options={formats}
        onChange={(value) => {
          if (!busy) update("format", value);
        }}
      />
      {(draft.format === "Продам" || draft.format === "Услуга") && (
        <Field
          label={
            draft.format === "Услуга"
              ? "Цена услуги, ₽ (пусто — договорная)"
              : "Цена, ₽"
          }
          placeholder="500"
          keyboardType="decimal-pad"
          value={price}
          onChangeText={setPrice}
          error={errors.price}
          maxLength={16}
          editable={!busy}
        />
      )}
      {draft.format === "Отдам" && (
        <View style={s.toast}>
          <Text style={s.link}>Бесплатно — цена не нужна</Text>
        </View>
      )}
      <Text style={[s.small, styles.locationHint]}>
        {draft.university} · {dormLabel(draft.dorm)}. О встрече договоритесь в
        чате.
      </Text>
      <Button
        title={id || draft.id ? "Сохранить изменения" : "Опубликовать"}
        onPress={publish}
        busy={busy}
        disabled={photoBusy}
      />
    </Page>
  );
}
