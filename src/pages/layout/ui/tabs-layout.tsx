import { styles, tabBarStyle } from "./tabs-layout.styles";
import React from "react";
import { Tabs } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useChats } from "../../../entities/chat";
import { colors, Icon } from "../../../shared/ui";

/** Настраивает вкладки главной, чатов и профиля и показывает суммарное число непрочитанных. */
export function TabsLayout() {
  const { chats } = useChats();
  const insets = useSafeAreaInsets();
  const unread = chats.reduce((count, chat) => count + chat.unread, 0);
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.green,
        tabBarInactiveTintColor: colors.muted,
        tabBarHideOnKeyboard: true,
        tabBarStyle: tabBarStyle(insets.bottom),
        tabBarLabelStyle: styles.tabLabel,
        sceneStyle: styles.scene,
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Главная",
          /** Выбирает обычную или активную иконку главной по состоянию вкладки. */
          tabBarIcon: ({ focused }) => (
            <Icon name={focused ? "home-active" : "home"} />
          ),
        }}
      />
      <Tabs.Screen
        name="chats"
        options={{
          title: "Чаты",
          tabBarBadge: unread || undefined,
          tabBarBadgeStyle: styles.unreadBadge,
          /** Выбирает обычную или активную иконку переписок по состоянию вкладки. */
          tabBarIcon: ({ focused }) => (
            <Icon name={focused ? "chat-active" : "chat"} />
          ),
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: "Профиль",
          /** Выбирает обычную или активную иконку профиля по состоянию вкладки. */
          tabBarIcon: ({ focused }) => (
            <Icon name={focused ? "user-active" : "user"} />
          ),
        }}
      />
    </Tabs>
  );
}
