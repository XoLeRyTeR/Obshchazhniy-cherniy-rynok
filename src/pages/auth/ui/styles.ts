import { StyleSheet } from "react-native";
import { colors } from "../../../shared/ui";

export const styles = StyleSheet.create({
  hero: {
    backgroundColor: colors.green,
    padding: 24,
    borderRadius: 28,
    gap: 14,
    marginTop: 48,
    marginBottom: 28,
  },
  brand: { color: "white", fontSize: 34, fontWeight: "700" },
  heroText: { color: "white" },
  title: { marginBottom: 20 },
  passwordToggle: { alignSelf: "flex-end", paddingVertical: 4, marginBottom: 18 },
  switchMode: { padding: 18, alignItems: "center" }
});
