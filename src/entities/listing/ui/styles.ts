import { StyleSheet } from "react-native";
import { colors } from "../../../shared/ui";

export const styles = StyleSheet.create({
  card: {
    flexBasis: "47%",
    flexGrow: 1,
    maxWidth: "49%",
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 20,
    backgroundColor: "#fff",
    padding: 8,
  },
  picture: {
    height: 136,
    borderRadius: 14,
    overflow: "hidden",
    backgroundColor: colors.mint,
  },
  imageFallback: {
    position: "absolute",
    bottom: 8,
    left: 8,
    color: colors.muted,
    fontSize: 11,
  },
  cardCopy: { padding: 6, gap: 4, marginTop: 2 },
  largePicture: { height: 226 },
  compactPicture: { height: 52, borderRadius: 12 },
  pressedCard: { opacity: 0.75 },
  locationText: { fontSize: 11 },
  absoluteFill: StyleSheet.absoluteFill
});
