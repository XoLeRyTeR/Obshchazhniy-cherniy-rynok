import { StyleSheet } from "react-native";
import { colors } from "../../../shared/ui";

export const styles = StyleSheet.create({
  listingCard: { justifyContent: "flex-start", padding: 10, marginBottom: 12 },
  listingImage: { width: 46 },
  listingCopy: { flex: 1, gap: 4 },
  messages: { gap: 16, paddingVertical: 16 },
  ownerActions: { gap: 12 },
  messageTime: { alignSelf: "flex-end", fontSize: 10 },
  composer: { gap: 10, padding: 8, marginTop: 12 },
  messageInput: {
    flex: 1,
    maxHeight: 100,
    paddingHorizontal: 10,
    paddingVertical: 6,
  }
});

/** Задаёт расположение и оформление пузыря в зависимости от отправителя сообщения. */
export const messageBubble = (mine: boolean) => ({
  alignSelf: mine ? "flex-end" : "flex-start",
  maxWidth: "86%",
  backgroundColor: mine ? colors.mint : "white",
  padding: 14,
  borderRadius: 18,
  gap: 4,
} as const);

/** Задаёт оформление кнопки отправки, приглушая её при недоступном действии. */
export const sendButton = (disabled: boolean) => ({
  backgroundColor: colors.green,
  width: 42,
  height: 42,
  borderRadius: 24,
  alignItems: "center",
  justifyContent: "center",
  opacity: disabled ? 0.45 : 1,
} as const);
