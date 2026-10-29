import { styles, messageBubble, sendButton } from "./styles";
import React, { useCallback, useRef, useState } from "react";
import { AppState, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { router, useFocusEffect, useLocalSearchParams } from "expo-router";
import { errorText } from "../../../shared/api";
import { useSession } from "../../../entities/user";
import { priceLabel, statusLabel, Picture, useListings } from "../../../entities/listing";
import { useChats } from "../../../entities/chat";
import { dormLabel } from "../../../entities/location";
import { OwnerActions } from "../../../features/change-listing-status";
import { useSendMessage } from "../../../features/send-message";
import { Button, colors, Empty, ErrorNotice, Icon, Page, s, Skeleton } from "../../../shared/ui";

/** Показывает переписку, связанное объявление, ранние сообщения и форму отправки с периодическим обновлением. */
export function ConversationScreen() {
  const { id } = useLocalSearchParams<{ id: string; }>();
  const { profile } = useSession();
  const { listings, getListing } = useListings();
  const { chats, refreshChats, loadMessages } = useChats();
  const chat = chats.find((c) => c.id === id);
  const item = listings.find((i) => i.id === chat?.listingId);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actions, setActions] = useState(false);
  const [nextOffset, setNextOffset] = useState<number | null>(null);
  const [olderBusy, setOlderBusy] = useState(false);
  const [retry, setRetry] = useState(0);
  const { text, setText, sending, error: sendError, send: sendMessage } = useSendMessage(id);
  const scroll = useRef<ScrollView>(null);
  // Новые сообщения не должны уводить вниз пользователя, который читает старую историю.
  const autoScroll = useRef(true);
  useFocusEffect(
    useCallback(() => {
      let active = true,
        running = false,
        first = true;
      /** Обновляет чат и объявление, загружает свежие сообщения и отмечает прочтение только в активном приложении. */
      async function refresh() {
        // Не запускаем параллельные опросы и не отмечаем чтение из фонового приложения.
        if (running || AppState.currentState === "background") return;
        running = true;
        try {
          const chats = await refreshChats();
          if (!active) return;
          const current = chats.find((c) => c.id === id);
          if (!current) throw new Error("Чат не найден или недоступен");
          await getListing(current.listing.id);
          if (!active) return;
          const next = await loadMessages(
            id,
            0,
            AppState.currentState === "active",
          );
          if (active) {
            if (first) setNextOffset(next);
            first = false;
            setError("");
          }
        } catch (e) {
          if (active) setError(errorText(e));
        } finally {
          running = false;
          if (active) setLoading(false);
        }
      }
      void refresh();
      const timer = setInterval(() => void refresh(), 3000);
      const listener = AppState.addEventListener("change", (value) => {
        if (value === "active") void refresh();
      });
      return () => {
        active = false;
        clearInterval(timer);
        listener.remove();
      };
    }, [id, refreshChats, loadMessages, getListing, retry]),
  );
  /** Запускает отправку сообщения и после успеха прокручивает переписку к последнему сообщению. */
  async function send() {
    if (await sendMessage()) {
      autoScroll.current = true;
      requestAnimationFrame(() => scroll.current?.scrollToEnd({ animated: true }));
    }
  }
  /** Загружает следующую страницу ранних сообщений без отметки прочтения и автопрокрутки вниз. */
  async function older() {
    if (nextOffset === null || olderBusy) return;
    setOlderBusy(true);
    autoScroll.current = false;
    try {
      setNextOffset(await loadMessages(id, nextOffset, false));
      setError("");
    } catch (e) {
      setError(errorText(e));
    } finally {
      setOlderBusy(false);
    }
  }
  return (
    <Page
      title={chat?.name ?? "Переписка"}
      subtitle={
        item ? `${item.university} · ${dormLabel(item.dorm)}` : undefined
      }
      back
      scroll={false}
    >
      <ErrorNotice error={error} onRetry={() => setRetry((v) => v + 1)} />
      {loading ? (
        <Skeleton />
      ) : chat && item ? (
        <>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Открыть объявление"
            onPress={() =>
              router.push({ pathname: "/listing", params: { id: item.id } })
            }
            style={[
              s.panel,
              s.row,
              styles.listingCard,
            ]}
          >
            <View style={styles.listingImage}>
              <Picture item={item} compact />
            </View>
            <View style={styles.listingCopy}>
              <Text style={s.cardTitle}>{item.title}</Text>
              <Text style={s.small}>
                {priceLabel(item)} · {statusLabel[item.status]}
              </Text>
            </View>
          </Pressable>
          <ScrollView
            ref={scroll}
            style={s.fill}
            contentContainerStyle={styles.messages}
            keyboardShouldPersistTaps="handled"
            onScroll={(event) => {
              const { layoutMeasurement, contentOffset, contentSize } =
                event.nativeEvent;
              autoScroll.current =
                contentSize.height -
                contentOffset.y -
                layoutMeasurement.height <
                80;
            }}
            scrollEventThrottle={100}
            onContentSizeChange={() => {
              if (autoScroll.current)
                scroll.current?.scrollToEnd({ animated: true });
            }}
          >
            {nextOffset !== null && (
              <Button
                title="Ранние сообщения"
                secondary
                onPress={older}
                busy={olderBusy}
              />
            )}
            {item.ownerId === profile.id && (
              <View style={styles.ownerActions}>
                <Button
                  title={
                    actions
                      ? "Скрыть управление объявлением"
                      : "Управлять статусом вещи"
                  }
                  secondary
                  onPress={() => setActions(!actions)}
                />
                {actions && <OwnerActions item={item} />}
              </View>
            )}
            {!chat.messages.length && (
              <Empty
                title="Начните разговор"
                text="Уточните состояние вещи или предложите время встречи."
              />
            )}
            {chat.messages.map((message) => (
              <View
                key={message.id}
                style={messageBubble(message.mine)}
              >
                <Text style={s.body}>{message.text}</Text>
                <Text
                  style={[s.small, styles.messageTime]}
                >
                  {message.time}
                </Text>
              </View>
            ))}
          </ScrollView>
          <ErrorNotice error={sendError} />
          <View
            style={[s.input, s.row, styles.composer]}
          >
            <TextInput
              accessibilityLabel="Сообщение"
              placeholder="Сообщение…"
              placeholderTextColor={colors.placeholder}
              value={text}
              onChangeText={setText}
              editable={!sending}
              multiline
              maxLength={4000}
              style={[
                s.body,
                styles.messageInput,
              ]}
            />
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={
                sending ? "Отправляется" : "Отправить сообщение"
              }
              disabled={!text.trim() || sending}
              onPress={send}
              style={sendButton(!text.trim() || sending)}
            >
              <Icon name="send" size={22} />
            </Pressable>
          </View>
        </>
      ) : (
        !error && (
          <Empty title="Чат не найден" text="Вернитесь к списку переписок." />
        )
      )}
    </Page>
  );
}
