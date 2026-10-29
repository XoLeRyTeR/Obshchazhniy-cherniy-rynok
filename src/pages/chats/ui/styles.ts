import { StyleSheet } from "react-native";
import { colors } from "../../../shared/ui";

export const styles = StyleSheet.create({
  list: { gap: 12 },
  chatCard: { padding: 14 },
  chatCopy: { flex: 1, gap: 5 },
  unreadBadge: {
    backgroundColor: colors.green,
    padding: 6,
    borderRadius: 16,
  },
  unreadText: { fontSize: 11, color: "white" }
});
