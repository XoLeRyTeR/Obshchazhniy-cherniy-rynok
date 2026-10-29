import { StyleSheet } from "react-native";
import { colors } from "../../../shared/ui";

export const styles = StyleSheet.create({
  photoPicker: {
    height: 150,
    backgroundColor: colors.mint,
    borderRadius: 24,
    alignItems: "center",
    justifyContent: "center",
    gap: 20,
    marginBottom: 12,
  },
  photos: { gap: 10, paddingBottom: 12 },
  photoFrame: { width: 82, height: 82 },
  photo: { width: 82, height: 82, borderRadius: 12 },
  removePhoto: {
    position: "absolute",
    top: 0,
    right: 0,
    padding: 4,
    backgroundColor: "white",
    borderRadius: 12,
  },
  photoHint: { marginBottom: 20 },
  locationHint: { marginBottom: 16 }
});
