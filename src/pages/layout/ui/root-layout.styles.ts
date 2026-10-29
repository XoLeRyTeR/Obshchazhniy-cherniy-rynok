import { StyleSheet } from "react-native";
import { colors } from "../../../shared/ui";

export const styles = StyleSheet.create({
  retryActions: { gap: 12 },
  scene: { backgroundColor: colors.bg },
  modalScene: { backgroundColor: "transparent" },
  viewport: { flex: 1, backgroundColor: "#eaf0eb", alignItems: "center" },
  content: { flex: 1, width: "100%", maxWidth: 480 }
});
