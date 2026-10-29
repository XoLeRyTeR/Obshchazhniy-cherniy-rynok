import { requireNativeModule } from "expo";
import { Platform } from "react-native";

/** Создаёт UUID сообщения средствами браузера или нативного ExpoCrypto. */
export function messageId(): string {
  return Platform.OS === "web"
    ? globalThis.crypto.randomUUID()
    : requireNativeModule<{ randomUUID: () => string; }>(
      "ExpoCrypto",
    ).randomUUID();
}
