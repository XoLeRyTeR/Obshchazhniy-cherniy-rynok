import { StyleSheet } from "react-native";
import { colors } from "../../../shared/ui";

export const styles = StyleSheet.create({
  tabLabel: { fontSize: 11, lineHeight: 14, fontWeight: "700" },
  scene: { backgroundColor: colors.bg },
  unreadBadge: { backgroundColor: colors.green, fontSize: 10 }
});

/** Вычисляет оформление и высоту панели вкладок с учётом нижнего safe-area отступа. */
export const tabBarStyle = (bottomInset: number) => ({
  height: 64 + bottomInset,
  paddingTop: 4,
  paddingBottom: Math.max(bottomInset, 4),
  backgroundColor: "white",
  borderTopColor: colors.border,
  borderTopLeftRadius: 24,
  borderTopRightRadius: 24,
} as const);
