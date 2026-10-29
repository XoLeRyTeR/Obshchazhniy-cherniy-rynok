import AsyncStorage from "@react-native-async-storage/async-storage";
import Constants from "expo-constants";
import { requireNativeModule } from "expo";
import { Platform } from "react-native";

import { ApiClient } from "./client";

const browserHost =
  typeof window !== "undefined" ? window.location?.hostname : undefined;
const expoHost = Constants.expoConfig?.hostUri?.split(":")[0];
export const apiUrl = (
  process.env.EXPO_PUBLIC_API_URL ||
  `http://${Platform.OS === "web" ? browserHost || "localhost" : expoHost || "10.0.2.2"}:8000/api/v1`
).replace(/\/$/, "");
const tokenKey = "obschazhny-api-token-v1";
// SecureStore встроен в Expo Go SDK 57; на Android не подменяем его незащищённым хранилищем.
type NativeStore = {
  getValueWithKeyAsync: (
    key: string,
    options: object,
  ) => Promise<string | null>;
  setValueWithKeyAsync: (
    value: string,
    key: string,
    options: object,
  ) => Promise<void>;
  deleteValueWithKeyAsync: (key: string, options: object) => Promise<void>;
};
/** Получает встроенный нативный модуль защищённого хранения токена. */
function secureStore() {
  return requireNativeModule<NativeStore>("ExpoSecureStore");
}
export const tokenStorage = {
  /** Читает токен из браузерного хранилища или SecureStore на устройстве. */
  get: () =>
    Platform.OS === "web"
      ? AsyncStorage.getItem(tokenKey)
      : secureStore().getValueWithKeyAsync(tokenKey, {}),
  /** Сохраняет токен в хранилище соответствующей платформы. */
  set: (token: string) =>
    Platform.OS === "web"
      ? AsyncStorage.setItem(tokenKey, token)
      : secureStore().setValueWithKeyAsync(token, tokenKey, {}),
  /** Удаляет сохранённый токен при выходе или завершении авторизации. */
  remove: () =>
    Platform.OS === "web"
      ? AsyncStorage.removeItem(tokenKey)
      : secureStore().deleteValueWithKeyAsync(tokenKey, {}),
};

export const api = new ApiClient(apiUrl, Platform.OS !== "web");
