import { styles, formatChip, formatLabel } from "./styles";
import React, { useCallback, useRef, useState } from "react";
import { Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { router, useFocusEffect } from "expo-router";
import { errorText } from "../../../shared/api";
import { useSession } from "../../../entities/user";
import { categories, categoryCodes, Format, formats, formatCodes, Listing, Card, useListings } from "../../../entities/listing";
import { Button, colors, Empty, ErrorNotice, Icon, Page, s, Select, Skeleton } from "../../../shared/ui";

/** Показывает ленту своего вуза с поиском, фильтрами и постраничной загрузкой. */
export function HomeScreen() {
  const { profile } = useSession();
  const { listings, loadFeed } = useListings();
  const [search, setSearch] = useState("");
  const [format, setFormat] = useState("Все");
  const [category, setCategory] = useState("Все категории");
  const [items, setItems] = useState<Listing[]>([]);
  const [nextOffset, setNextOffset] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [moreBusy, setMoreBusy] = useState(false);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  // Смена фильтров отменяет применение страниц, которые догружались для прежней выдачи.
  const version = useRef(0);
  const params = {
    offset: "0",
    size: "20",
    university_id: profile.universityId,
    ...(search.trim() && { q: search.trim() }),
    ...(format !== "Все" && { format: formatCodes[format as Format] }),
    ...(category !== "Все категории" && { category: categoryCodes[category] }),
  };
  useFocusEffect(
    useCallback(() => {
      let active = true;
      version.current += 1;
      setLoading(true);
      setError("");
      setNextOffset(null);
      const timer = setTimeout(() => {
        loadFeed(params)
          .then((result) => {
            if (active) {
              setItems(result.items);
              setNextOffset(result.nextOffset);
            }
          })
          .catch((e) => {
            if (active) {
              setError(errorText(e));
              setItems([]);
            }
          })
          .finally(() => {
            if (active) setLoading(false);
          });
      }, 250);
      return () => {
        active = false;
        clearTimeout(timer);
      };
    }, [search, format, category, profile.universityId, loadFeed, retry]),
  );
  /** Догружает страницу текущей выдачи, отбрасывая устаревшие результаты после смены фильтров. */
  async function more() {
    if (nextOffset === null || moreBusy || loading) return;
    const current = version.current;
    setMoreBusy(true);
    try {
      const result = await loadFeed({ ...params, offset: String(nextOffset) });
      if (version.current === current) {
        setItems((old) => [
          ...new Map([...old, ...result.items].map((i) => [i.id, i])).values(),
        ]);
        setNextOffset(result.nextOffset);
        setError("");
      }
    } catch (e) {
      if (version.current === current) setError(errorText(e));
    } finally {
      setMoreBusy(false);
    }
  }
  const visible = items
    .map((item) => listings.find((i) => i.id === item.id) ?? item)
    .filter((item) => item.status === "active" || item.status === "reserved");
  return (
    <Page
      title="Общажный ЧР"
      subtitle={`Свежие вещи и услуги · общежития ${profile.university}`}
      right={
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Обновить объявления"
          onPress={() => setRetry((v) => v + 1)}
        >
          <Text style={s.link}>Обновить</Text>
        </Pressable>
      }
    >
      <View style={[s.input, s.row, styles.search]}>
        <Icon name="search" />
        <TextInput
          accessibilityLabel="Поиск объявлений"
          value={search}
          onChangeText={setSearch}
          placeholder="Найти книгу, технику, одежду…"
          placeholderTextColor="#93a099"
          maxLength={200}
          style={[s.body, styles.searchInput]}
        />
        {!!search && (
          <Pressable
            accessibilityLabel="Очистить поиск"
            onPress={() => setSearch("")}
            hitSlop={10}
          >
            <Text style={s.subtitle}>×</Text>
          </Pressable>
        )}
      </View>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.filters}
      >
        {["Все", ...formats].map((value) => (
          <Pressable
            key={value}
            accessibilityRole="button"
            accessibilityState={{ selected: format === value }}
            onPress={() => setFormat(value)}
            style={formatChip(format === value)}
          >
            <Text
              style={formatLabel(format === value)}
            >
              {value}
            </Text>
          </Pressable>
        ))}
      </ScrollView>
      <Select
        label="Категория"
        value={category}
        options={["Все категории", ...categories]}
        onChange={setCategory}
      />
      <ErrorNotice error={error} onRetry={() => setRetry((v) => v + 1)} />
      {loading ? (
        <Skeleton cards />
      ) : visible.length ? (
        <View style={s.grid}>
          {visible.map((item) => (
            <Card key={item.id} item={item} onPress={() => router.push({ pathname: "/listing", params: { id: item.id } })} />
          ))}
        </View>
      ) : (
        !error && (
          <Empty
            title="Пока ничего не нашлось"
            text="Попробуйте другое название или добавьте первое объявление."
            action={
              <Button
                title="Сбросить фильтры"
                secondary
                onPress={() => {
                  setSearch("");
                  setFormat("Все");
                  setCategory("Все категории");
                }}
              />
            }
          />
        )
      )}
      {nextOffset !== null && !loading && (
        <View style={styles.loadMore}>
          <Button
            title="Ещё объявления"
            secondary
            onPress={more}
            busy={moreBusy}
          />
        </View>
      )}
    </Page>
  );
}
