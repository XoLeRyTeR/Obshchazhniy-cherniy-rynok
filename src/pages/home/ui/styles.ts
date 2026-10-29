import { StyleSheet } from "react-native";
import { colors } from "../../../shared/ui";

export const styles = StyleSheet.create({
  search: { gap: 12, marginBottom: 16 },
  searchInput: { flex: 1, minWidth: 0, padding: 0 },
  filters: { gap: 8, paddingBottom: 16 },
  loadMore: { marginTop: 16 }
});

/** Задаёт оформление кнопки формата передачи в выбранном или обычном состоянии. */
export const formatChip = (selected: boolean) => ({
  paddingHorizontal: 20,
  paddingVertical: 10,
  borderRadius: 24,
  borderWidth: 1,
  borderColor: selected ? colors.green : colors.border,
  backgroundColor: selected ? colors.green : "white",
} as const);

/** Задаёт оформление подписи формата в зависимости от выбора. */
export const formatLabel = (selected: boolean) => ({
  fontSize: 12,
  fontWeight: "700",
  color: selected ? "white" : colors.muted,
} as const);
