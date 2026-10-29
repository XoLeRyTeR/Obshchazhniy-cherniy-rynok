import { styles } from "./styles";
import React, { useCallback, useState } from "react";
import { Pressable, Text, View } from "react-native";
import { router, useFocusEffect } from "expo-router";
import { errorText } from "../../../shared/api";
import { useSession } from "../../../entities/user";
import { Listing, Card, useListings } from "../../../entities/listing";
import { dormLabel } from "../../../entities/location";
import { Button, Empty, ErrorNotice, Icon, Page, s, Skeleton } from "../../../shared/ui";

/** Показывает профиль, собственные объявления и действия добавления, редактирования и выхода. */
export function ProfileScreen() {
  const { profile, logout } = useSession();
  const { listings, ownIds, refreshOwn } = useListings();
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useFocusEffect(
    useCallback(() => {
      let active = true;
      setLoading(true);
      refreshOwn()
        .then(() => {
          if (active) setError("");
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
    }, [refreshOwn, retry]),
  );
  const own = ownIds
    .map((id) => listings.find((i) => i.id === id))
    .filter((i): i is Listing => !!i);
  /** Выполняет выход с блокировкой повторного нажатия и показывает ошибку удаления токена. */
  async function exit() {
    if (busy) return;
    setBusy(true);
    try {
      await logout();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Page title="Профиль">
      <ErrorNotice error={error} onRetry={() => setRetry((v) => v + 1)} />
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Редактировать профиль"
        onPress={() => router.push("/edit-profile")}
        style={[
          s.panel,
          s.row,
          styles.profileCard,
        ]}
      >
        <View style={s.avatar}>
          <Text style={[s.link, styles.initials]}>
            {profile.name
              .split(" ")
              .map((word) => word[0])
              .slice(0, 2)
              .join("")}
          </Text>
        </View>
        <View style={styles.profileCopy}>
          <Text style={[s.section, styles.name]}>
            {profile.name}
          </Text>
          <Text style={s.small}>
            {profile.university} · {dormLabel(profile.dorm)}
          </Text>
          <Text style={[s.link, styles.editLabel]}>Редактировать</Text>
        </View>
      </Pressable>
      <View style={[s.row, styles.sectionHeader]}>
        <Text style={s.section}>Мои объявления</Text>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Добавить объявление"
          onPress={() => router.push("/editor")}
          style={[s.button, styles.addButton]}
        >
          <Icon name="plus-white" />
        </Pressable>
      </View>
      {loading ? (
        <Skeleton cards />
      ) : own.length ? (
        <View style={s.grid}>
          {own.map((item) => (
            <Card key={item.id} item={item} own onPress={() => router.push({ pathname: "/listing", params: { id: item.id } })} />
          ))}
        </View>
      ) : (
        !error && (
          <Empty
            title="Первое объявление?"
            text="Здесь появятся ваши вещи и услуги."
          />
        )
      )}
      <View style={styles.logout}>
        <Button
          title="Выйти из аккаунта"
          onPress={exit}
          secondary
          busy={busy}
        />
      </View>
    </Page>
  );
}
