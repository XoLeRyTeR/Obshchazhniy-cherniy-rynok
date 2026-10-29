import { styles, iconSize, skeletonOpacity, s, colors } from "./styles";
import React, { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Animated,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  TextInputProps,
  View,
} from "react-native";
import { Image } from "expo-image";
import { router } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";

const icons = {
  home: require("../../../assets/figma/home.svg"),
  "home-active": require("../../../assets/figma/home-active.svg"),
  chat: require("../../../assets/figma/chat.svg"),
  "chat-active": require("../../../assets/figma/chat-active.svg"),
  user: require("../../../assets/figma/user.svg"),
  "user-active": require("../../../assets/figma/user-active.svg"),
  search: require("../../../assets/figma/search.svg"),
  back: require("../../../assets/figma/back.svg"),
  chevron: require("../../../assets/figma/chevron.svg"),
  plus: require("../../../assets/figma/plus.svg"),
  "plus-white": require("../../../assets/figma/plus-white.svg"),
  send: require("../../../assets/figma/send.svg"),
};

/** Показывает SVG-иконку из набора приложения в заданном размере. */
export function Icon({
  name,
  size = 20,
}: {
  name: keyof typeof icons;
  size?: number;
}) {
  return (
    <Image
      source={icons[name]}
      style={iconSize(size)}
      contentFit="contain"
      loading="eager"
      accessibilityIgnoresInvertColors
    />
  );
}

/** Показывает основную или вторичную кнопку с блокировкой и индикатором выполнения. */
export function Button({
  title,
  onPress,
  busy,
  secondary,
  disabled,
  testID,
}: {
  title: string;
  onPress: () => void;
  busy?: boolean;
  secondary?: boolean;
  disabled?: boolean;
  testID?: string;
}) {
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={title}
      accessibilityState={{ disabled: !!(busy || disabled), busy: !!busy }}
      disabled={busy || disabled}
      onPress={onPress}
      style={({ pressed }) => [
        s.button,
        secondary && s.secondaryButton,
        (pressed || disabled || busy) && styles.disabled,
      ]}
    >
      {busy ? (
        <ActivityIndicator color={secondary ? colors.green : colors.surface} />
      ) : (
        <Text style={[s.buttonText, secondary && styles.secondaryText]}>
          {title}
        </Text>
      )}
    </Pressable>
  );
}

/** Показывает поле ввода с подписью, ошибкой и поддержкой многострочного текста. */
export function Field({
  label,
  error,
  ...props
}: TextInputProps & { label: string; error?: string; }) {
  return (
    <View style={s.field}>
      <Text style={s.label}>{label}</Text>
      <TextInput
        accessibilityLabel={label}
        placeholderTextColor={colors.placeholder}
        {...props}
        style={[
          s.input,
          props.multiline && styles.multilineInput,
          error && styles.invalidInput,
          props.style,
        ]}
      />
      {!!error && (
        <Text accessibilityRole="alert" style={s.error}>
          {error}
        </Text>
      )}
    </View>
  );
}

/** Показывает выбранное значение и модальный список вариантов для его изменения. */
export function Select({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: readonly string[];
  onChange: (value: string) => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <View style={s.field}>
      <Text style={s.label}>{label}</Text>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`${label}: ${value}`}
        accessibilityState={{ expanded: open }}
        onPress={() => setOpen(true)}
        style={[s.input, s.row]}
      >
        <Text style={[s.body, styles.selectValue]}>{value}</Text>
        <Icon name="chevron" />
      </Pressable>
      <Modal
        visible={open}
        transparent
        animationType="fade"
        onRequestClose={() => setOpen(false)}
      >
        <View style={s.overlay}>
          <Pressable
            accessibilityLabel="Закрыть список"
            style={styles.absoluteFill}
            onPress={() => setOpen(false)}
          />
          <View accessibilityViewIsModal style={s.selectSheet}>
            <Text style={s.section}>{label}</Text>
            <ScrollView>
              {options.map((option) => (
                <Pressable
                  key={option}
                  accessibilityRole="radio"
                  accessibilityState={{ checked: option === value }}
                  onPress={() => {
                    onChange(option);
                    setOpen(false);
                  }}
                  style={[
                    s.option,
                    option === value && styles.selectedOption,
                  ]}
                >
                  <Text
                    style={[
                      s.body,
                      styles.optionText,
                      option === value && styles.selectedOptionText,
                    ]}
                  >
                    {option}
                  </Text>
                  {option === value && <Text style={s.link}>✓</Text>}
                </Pressable>
              ))}
            </ScrollView>
            <Button title="Закрыть" secondary onPress={() => setOpen(false)} />
          </View>
        </View>
      </Modal>
    </View>
  );
}

/** Создаёт общий layout экрана с safe area, заголовком, возвратом и необязательной прокруткой. */
export function Page({
  children,
  title,
  subtitle,
  back,
  right,
  scroll = true,
}: React.PropsWithChildren<{
  title?: string;
  subtitle?: string;
  back?: boolean;
  right?: React.ReactNode;
  scroll?: boolean;
}>) {
  const content = (
    <>
      {title && (
        <View style={s.heading}>
          <View style={[s.row, styles.headingRow]}>
            {back && (
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Назад"
                hitSlop={10}
                onPress={() =>
                  router.canGoBack() ? router.back() : router.replace("/")
                }
                style={s.back}
              >
                <Icon name="back" />
              </Pressable>
            )}
            <Text style={[s.title, back && styles.backTitle, styles.titleFill]}>
              {title}
            </Text>
            {right}
          </View>
          {subtitle && <Text style={s.subtitle}>{subtitle}</Text>}
        </View>
      )}
      {children}
    </>
  );
  return (
    <SafeAreaView style={s.screen} edges={["top", "left", "right"]}>
      <KeyboardAvoidingView
        style={s.fill}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        {scroll ? (
          <ScrollView
            contentContainerStyle={s.content}
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={false}
          >
            {content}
          </ScrollView>
        ) : (
          <View style={[s.content, s.fill]}>{content}</View>
        )}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

/** Показывает небольшую текстовую метку, например формат передачи вещи. */
export function Badge({ text }: { text: string; }) {
  return (
    <View style={s.badge}>
      <Text style={s.badgeText}>{text}</Text>
    </View>
  );
}

/** Показывает пустое состояние с пояснением и необязательным действием. */
export function Empty({
  title,
  text,
  action,
}: {
  title: string;
  text: string;
  action?: React.ReactNode;
}) {
  return (
    <View style={s.empty}>
      <Text style={s.section}>{title}</Text>
      <Text style={[s.subtitle, styles.emptyText]}>
        {text}
      </Text>
      {action}
    </View>
  );
}

/** Показывает сообщение об ошибке и кнопку повтора; без ошибки ничего не выводит. */
export function ErrorNotice({
  error,
  onRetry,
}: {
  error: string;
  onRetry?: () => void;
}) {
  if (!error) return null;
  return (
    <View style={[s.toast, styles.errorContent]}>
      <Text accessibilityRole="alert" style={s.error}>
        {error}
      </Text>
      {onRetry && <Button title="Повторить" secondary onPress={onRetry} />}
    </View>
  );
}

/** Показывает пульсирующие заглушки карточек или строк на время загрузки. */
export function Skeleton({ cards = false }: { cards?: boolean; }) {
  const opacity = useRef(new Animated.Value(0.45)).current;
  useEffect(() => {
    const animation = Animated.loop(
      Animated.sequence([
        Animated.timing(opacity, {
          toValue: 1,
          duration: 650,
          useNativeDriver: Platform.OS !== "web",
        }),
        Animated.timing(opacity, {
          toValue: 0.45,
          duration: 650,
          useNativeDriver: Platform.OS !== "web",
        }),
      ]),
    );
    animation.start();
    return () => animation.stop();
  }, [opacity]);
  return (
    <Animated.View
      accessibilityLabel="Загрузка"
      accessibilityRole="progressbar"
      style={[cards ? s.grid : styles.skeletonList, skeletonOpacity(opacity)]}
    >
      {Array.from({ length: cards ? 4 : 3 }, (_, i) => (
        <View
          key={i}
          style={[
            s.skeleton,
            cards ? styles.skeletonCard : styles.skeletonRow,
          ]}
        />
      ))}
    </Animated.View>
  );
}
