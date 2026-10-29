import { styles } from "./root-layout.styles";
import React from "react";
import { View } from "react-native";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { SessionProvider, useSession } from "../../../entities/user";
import { ListingProvider } from "../../../entities/listing";
import { ChatProvider } from "../../../entities/chat";
import { Button, colors, Empty, Page, Skeleton } from "../../../shared/ui";

/** Выбирает экран загрузки, ошибки подключения или доступные маршруты по состоянию авторизации. */
function Navigation() {
  const { signedIn, ready, sessionError, restore, logout } = useSession();
  if (!ready)
    return (
      <Page title="Общажный ЧР">
        <Skeleton cards />
      </Page>
    );
  if (sessionError)
    return (
      <Page title="Подключение">
        <Empty
          title="Не удалось восстановить вход"
          text={sessionError}
          action={
            <View style={styles.retryActions}>
              <Button title="Повторить" onPress={() => void restore()} />
              <Button
                title="Выйти из аккаунта"
                secondary
                onPress={() => void logout().catch(() => { })}
              />
            </View>
          }
        />
      </Page>
    );
  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: styles.scene,
        animation: "slide_from_right",
      }}
    >
      <Stack.Protected guard={!signedIn}>
        <Stack.Screen name="sign-in" />
        <Stack.Screen name="register" />
      </Stack.Protected>
      <Stack.Protected guard={signedIn}>
        <Stack.Screen name="(tabs)" />
        <Stack.Screen
          name="listing"
          options={{
            presentation: "transparentModal",
            animation: "slide_from_bottom",
            contentStyle: styles.modalScene,
          }}
        />
        <Stack.Screen name="editor" />
        <Stack.Screen name="conversation" />
        <Stack.Screen name="edit-profile" />
      </Stack.Protected>
    </Stack>
  );
}
/** Подключает кеши объявлений и чатов и пересоздаёт их при смене пользователя. */
function DomainProviders({ children }: React.PropsWithChildren) {
  const { profile } = useSession();
  // При смене аккаунта оба приватных кеша создаются заново.
  return (
    <ListingProvider key={profile.id}>
      <ChatProvider userId={profile.id}>{children}</ChatProvider>
    </ListingProvider>
  );
}

/** Собирает корневой layout приложения с safe area, авторизацией и провайдерами данных. */
export function RootLayout() {
  return (
    <SafeAreaProvider>
      <SessionProvider>
        <DomainProviders>
          <View
            style={styles.viewport}
          >
            <View style={styles.content}>
              <StatusBar style="dark" />
              <Navigation />
            </View>
          </View>
        </DomainProviders>
      </SessionProvider>
    </SafeAreaProvider>
  );
}
