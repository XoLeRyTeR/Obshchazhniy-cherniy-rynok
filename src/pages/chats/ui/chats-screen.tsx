import { styles } from "./styles";
import React, { useCallback, useState } from "react";
import { AppState, Pressable, Text, View } from "react-native";
import { router, useFocusEffect } from "expo-router";
import { errorText } from "../../../shared/api";
import { useChats } from "../../../entities/chat";
import { Button, colors, Empty, ErrorNotice, Page, s, Skeleton } from "../../../shared/ui";

/** Показывает список переписок с превью и непрочитанными и периодически обновляет его на открытом экране. */
export function ChatsScreen() {
  const { chats, refreshChats } = useChats();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useFocusEffect(
    useCallback(() => {
      let active = true,
        running = false;
      /** Обновляет список чатов без параллельных опросов и учитывает закрытие экрана или уход в фон. */
      async function refresh() {
        if (running || AppState.currentState === "background") return;
        running = true;
        try {
          await refreshChats();
          if (active) setError("");
        } catch (e) {
          if (active) setError(errorText(e));
        } finally {
          running = false;
          if (active) setLoading(false);
        }
      }
      void refresh();
      const timer = setInterval(() => void refresh(), 4000);
      return () => {
        active = false;
        clearInterval(timer);
      };
    }, [refreshChats, retry]),
  );
  return (
    <Page title="Чаты" subtitle="Ваши договорённости о вещах и услугах">
      <ErrorNotice error={error} onRetry={() => setRetry((v) => v + 1)} />
      {loading ? (
        <Skeleton />
      ) : chats.length ? (
        <View style={styles.list}>
          {chats.map((chat) => (
            <Pressable
              key={chat.id}
              accessibilityRole="button"
              accessibilityLabel={`Чат: ${chat.name}, ${chat.title}`}
              onPress={() =>
                router.push({
                  pathname: "/conversation",
                  params: { id: chat.id },
                })
              }
              style={[s.panel, s.row, styles.chatCard]}
            >
              <View style={styles.chatCopy}>
                <Text numberOfLines={1} style={s.cardTitle}>
                  {chat.title}
                </Text>
                <Text numberOfLines={1} style={s.small}>
                  {chat.name} · {chat.lastText || "Начните переписку"}
                </Text>
              </View>
              {chat.unread > 0 && (
                <View
                  style={styles.unreadBadge}
                >
                  <Text style={styles.unreadText}>
                    {chat.unread}
                  </Text>
                </View>
              )}
            </Pressable>
          ))}
        </View>
      ) : (
        !error && (
          <Empty
            title="Пока нет переписок"
            text="Откройте объявление и напишите автору."
            action={
              <Button
                title="Посмотреть объявления"
                secondary
                onPress={() => router.navigate("/")}
              />
            }
          />
        )
      )}
    </Page>
  );
}
