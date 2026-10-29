import { StyleSheet } from "react-native";
import { colors } from "../../../shared/ui";

export const styles = StyleSheet.create({
  sheetHeader: { height: 26, paddingHorizontal: 6 },
  headerSpacer: { width: 24 },
  handle: {
    width: 40,
    height: 4,
    backgroundColor: colors.border,
    borderRadius: 4,
  },
  content: { gap: 18, padding: 8 },
  photoNavigation: { justifyContent: "center", gap: 16 },
  summary: { gap: 8 },
  title: { fontSize: 24 },
  price: { color: colors.green },
  author: {
    justifyContent: "flex-start",
    gap: 12,
    backgroundColor: colors.bg,
    padding: 14,
    borderRadius: 16,
  },
  avatar: { width: 36, height: 36 },
  authorCopy: { flex: 1 },
  absoluteFill: StyleSheet.absoluteFill
});

/** Вычисляет оформление модального окна объявления с учётом нижнего отступа устройства. */
export const sheetStyle = (bottomInset: number) => ({
  backgroundColor: "white",
  borderRadius: 28,
  padding: 12,
  paddingBottom: Math.max(bottomInset, 12),
  maxHeight: "92%",
  width: "100%",
  maxWidth: 456,
  alignSelf: "center",
} as const);

/** Задаёт прозрачность переключателя фотографии в зависимости от того, выбрана ли она. */
export const photoIndicator = (selected: boolean) => ({ opacity: selected ? 1 : 0.4 } as const);
