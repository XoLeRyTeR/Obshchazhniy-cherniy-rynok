import { StyleSheet, type Animated } from "react-native";

export const colors = {
  bg: "#f6f9f6",
  surface: "#ffffff",
  text: "#17221b",
  muted: "#65736a",
  green: "#16794b",
  mint: "#def3e8",
  border: "#dde5df",
  danger: "#b23939",
  placeholder: "#93a099",
};

export const s = StyleSheet.create({
  fill: { flex: 1 },
  screen: { flex: 1, backgroundColor: colors.bg },
  content: { padding: 24, paddingBottom: 40 },
  row: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  heading: { gap: 8, marginBottom: 24 },
  title: { fontSize: 28, fontWeight: "700", color: colors.text },
  section: { fontSize: 20, fontWeight: "700", color: colors.text },
  body: { fontSize: 15, lineHeight: 22, color: colors.text },
  subtitle: { fontSize: 14, lineHeight: 21, color: colors.muted },
  small: { fontSize: 12, lineHeight: 18, color: colors.muted },
  link: { color: colors.green, fontSize: 14, fontWeight: "700" },
  error: { color: colors.danger, fontSize: 12, lineHeight: 18 },
  field: { gap: 8, marginBottom: 16 },
  label: { fontSize: 12, fontWeight: "700", color: colors.muted },
  input: {
    minHeight: 54,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 15,
    color: colors.text,
  },
  button: {
    minHeight: 54,
    borderRadius: 16,
    backgroundColor: colors.green,
    alignItems: "center",
    justifyContent: "center",
    padding: 14,
  },
  buttonText: { fontSize: 16, color: "#fff", fontWeight: "700" },
  secondaryButton: { backgroundColor: colors.mint },
  back: { width: 28, minHeight: 44, justifyContent: "center" },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: 12 },
  badgePosition: { position: "absolute", top: 8, left: 8 },
  badge: {
    alignSelf: "flex-start",
    borderRadius: 20,
    backgroundColor: "#fff",
    paddingHorizontal: 16,
    paddingVertical: 6,
  },
  badgeText: { fontSize: 11, color: colors.green, fontWeight: "700" },
  cardTitle: {
    fontSize: 15,
    lineHeight: 20,
    color: colors.text,
    fontWeight: "700",
  },
  panel: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 20,
    backgroundColor: "#fff",
    padding: 16,
    gap: 12,
  },
  overlay: {
    flex: 1,
    backgroundColor: "rgba(23,34,27,0.42)",
    justifyContent: "flex-end",
    padding: 12,
  },
  selectSheet: {
    backgroundColor: "#fff",
    padding: 20,
    borderRadius: 24,
    gap: 16,
    maxHeight: "75%",
    width: "100%",
    maxWidth: 456,
    alignSelf: "center",
  },
  option: {
    padding: 16,
    borderRadius: 12,
    flexDirection: "row",
    justifyContent: "space-between",
  },
  empty: { paddingVertical: 36, alignItems: "center", gap: 6 },
  skeleton: { backgroundColor: "#dde5df", borderRadius: 18 },
  avatar: {
    width: 60,
    height: 60,
    backgroundColor: colors.mint,
    borderRadius: 30,
    justifyContent: "center",
    alignItems: "center",
  },
  toast: {
    padding: 10,
    backgroundColor: colors.mint,
    borderRadius: 10,
    marginBottom: 16,
  },
});

export const styles = StyleSheet.create({
  disabled: { opacity: 0.65 },
  secondaryText: { color: colors.green },
  multilineInput: { minHeight: 96, textAlignVertical: "top" },
  invalidInput: { borderColor: colors.danger },
  selectValue: { flex: 1 },
  selectedOption: { backgroundColor: colors.mint },
  optionText: { flex: 1 },
  selectedOptionText: {
    color: colors.green,
    fontWeight: "700",
  },
  headingRow: { gap: 8 },
  backTitle: { fontSize: 22 },
  titleFill: { flex: 1 },
  emptyText: { textAlign: "center", marginBottom: 16 },
  errorContent: { gap: 10 },
  skeletonList: { gap: 12 },
  skeletonCard: { width: "48%", height: 210 },
  skeletonRow: { height: 80 },
  absoluteFill: StyleSheet.absoluteFill
});

/** Задаёт одинаковые ширину и высоту иконки по переданному размеру. */
export const iconSize = (size: number) => ({ width: size, height: size } as const);

/** Передаёт анимированную прозрачность в стиль скелетона. */
export const skeletonOpacity = (opacity: Animated.Value) => ({ opacity } as const);
