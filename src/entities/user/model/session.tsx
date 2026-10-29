import React, { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import { api as client, ApiError, errorText, tokenStorage } from "../../../shared/api";
import { type ApiProfile, type AuthResult, emptySessionState as emptyState, mapProfile } from "./model";

/** Управляет входом, восстановлением токена, профилем и выходом без хранения объявлений и чатов. */
function useUserModel() {
  const [state, change] = useState(emptyState);
  const [ready, setReady] = useState(false);
  const [sessionError, setSessionError] = useState("");
  const storageQueue = useRef(Promise.resolve());
  /** Выполняет операции с хранилищем токена последовательно, продолжая очередь после ошибки. */
  function persist(fn: () => Promise<void>) {
    // Записываем токен по очереди, чтобы запоздавший выход не затёр новый вход.
    const next = storageQueue.current.catch(() => { }).then(fn);
    storageQueue.current = next;
    return next;
  }

  /** Сбрасывает авторизацию в памяти и ставит удаление недействительного токена в очередь. */
  function expired() {
    client.token = null;
    change(() => emptyState);
    void persist(tokenStorage.remove).catch(() =>
      setSessionError(
        "Не удалось удалить токен с устройства. Повторите выход.",
      ),
    );
  }

  /** Проверяет сохранённый токен через профиль API и завершает начальную загрузку приложения. */
  async function restore() {
    setReady(false);
    setSessionError("");
    try {
      client.token = await tokenStorage.get();
      if (client.token) {
        const profile = mapProfile(
          await client.request<ApiProfile>("/users/me"),
        );
        change(() => ({ ...emptyState, signedIn: true, profile }));
      }
    } catch (error) {
      // При сбое сети сохраняем токен для повтора; недействительный токен удаляет обработчик 401.
      if (!(error instanceof ApiError && error.status === 401))
        setSessionError(errorText(error));
    } finally {
      setReady(true);
    }
  }

  /** Удаляет токен с устройства и очищает авторизацию и профиль в памяти. */
  async function logout() {
    await persist(tokenStorage.remove);
    client.token = null;
    setSessionError("");
    change(() => emptyState);
  }

  /** Выполняет вход или регистрацию, сохраняет полученный JWT и устанавливает профиль. */
  async function authenticate(path: string, body: unknown) {
    const result = await client.request<AuthResult>(path, {
      method: "POST",
      body,
    });
    await persist(() => tokenStorage.set(result.access_token));
    client.token = result.access_token;
    change(() => ({
      ...emptyState,
      signedIn: true,
      profile: mapProfile(result.profile),
    }));
  }
  client.onUnauthorized = expired;
  useEffect(() => { void restore(); }, []);
  /** Сохраняет имя и общежитие пользователя и обновляет профиль, если аккаунт не сменился. */
  async function updateProfile(
    name: string,
    universityId: string,
    dorm: string,
  ) {
    const token = client.token;
    const profile = mapProfile(
      await client.request<ApiProfile>("/users/me", {
        method: "PATCH",
        body: { name, university_id: universityId, dormitory_name: dorm },
      }),
    );
    if (token === client.token) change((current) => ({ ...current, profile }));
  }
  const actions = useMemo(() => ({
    restore,
    logout,
    updateProfile,
    /** Выполняет вход по электронной почте и паролю через общий сценарий авторизации. */
    signIn: (email: string, password: string) => authenticate("/auth/login", { email, password }),
    /** Регистрирует пользователя с именем, почтой, паролем, вузом и названием общежития. */
    signUp: (name: string, email: string, password: string, universityId: string, dorm: string) =>
      authenticate("/auth/register", {
        name, email, password,
        university_id: universityId,
        dormitory_name: dorm,
      }),
  }), []);
  return { ...state, ready, sessionError, ...actions };
}

const Context = createContext<ReturnType<typeof useUserModel> | null>(null);
/** Предоставляет всему приложению состояние авторизации и действия профиля. */
export function SessionProvider({ children }: React.PropsWithChildren) {
  return <Context.Provider value={useUserModel()}>{children}</Context.Provider>;
}
/** Возвращает авторизацию и действия профиля; требует подключения SessionProvider. */
export function useSession() {
  const value = useContext(Context);
  if (!value) throw new Error("SessionProvider is missing");
  return value;
}
