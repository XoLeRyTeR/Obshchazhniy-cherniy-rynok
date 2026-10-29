import { styles } from "./styles";
import React, { useState } from "react";
import { Pressable, Text, View } from "react-native";
import { router } from "expo-router";
import { ApiError, errorText } from "../../../shared/api";
import { useSession } from "../../../entities/user";
import { LocationFields, normalizeDorm } from "../../../entities/location";
import { Button, colors, ErrorNotice, Field, Page, s } from "../../../shared/ui";

/** Показывает форму входа или регистрации с проверкой полей и серверными ошибками. */
export function AuthScreen({ register = false }: { register?: boolean; }) {
  const { signIn, signUp } = useSession();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [universityId, setUniversityId] = useState("");
  const [dorm, setDorm] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [failure, setFailure] = useState("");
  const [busy, setBusy] = useState(false);
  const [visible, setVisible] = useState(false);
  /** Проверяет поля формы, выполняет вход или регистрацию и отображает ошибки API. */
  async function submit() {
    if (busy) return;
    const next: Record<string, string> = {};
    if (register && !name.trim()) next.name = "Введите имя";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim()))
      next.email = "Проверьте адрес электронной почты";
    if (password.length < 8 || !password.trim())
      next.password = "Минимум 8 символов";
    if (register && (!normalizeDorm(dorm) || !universityId))
      next.dorm = "Выберите вуз и укажите общежитие";
    setErrors(next);
    setFailure("");
    if (Object.keys(next).length) return;
    setBusy(true);
    try {
      if (register)
        await signUp(
          name.trim(),
          email.trim().toLowerCase(),
          password,
          universityId,
          normalizeDorm(dorm),
        );
      else await signIn(email.trim().toLowerCase(), password);
    } catch (error) {
      setFailure(errorText(error));
      if (error instanceof ApiError)
        setErrors({ ...error.fields, dorm: error.fields.dormitory_name });
    } finally {
      setBusy(false);
    }
  }
  return (
    <Page
      title={register ? "Регистрация" : undefined}
      subtitle={
        register ? "Создайте профиль и начните обмениваться" : undefined
      }
    >
      {!register && (
        <>
          <View
            style={styles.hero}
          >
            <Text style={styles.brand}>
              Общажный ЧР
            </Text>
            <Text style={[s.body, styles.heroText]}>
              Локальный рынок товаров и услуг для студентов
            </Text>
          </View>
          <Text style={[s.title, styles.title]}>Войти</Text>
        </>
      )}
      {register && (
        <Field
          label="Имя"
          placeholder="Как вас зовут?"
          autoComplete="name"
          value={name}
          onChangeText={setName}
          error={errors.name}
          maxLength={80}
          editable={!busy}
        />
      )}
      <Field
        label="Электронная почта"
        placeholder="student@university.ru"
        value={email}
        onChangeText={setEmail}
        keyboardType="email-address"
        autoComplete="email"
        autoCapitalize="none"
        autoCorrect={false}
        error={errors.email}
        maxLength={254}
        editable={!busy}
      />
      <Field
        label="Пароль"
        placeholder="Минимум 8 символов"
        value={password}
        onChangeText={setPassword}
        secureTextEntry={!visible}
        autoCapitalize="none"
        autoCorrect={false}
        autoComplete={register ? "new-password" : "current-password"}
        error={errors.password}
        maxLength={128}
        editable={!busy}
      />
      <Pressable
        accessibilityRole="button"
        onPress={() => setVisible(!visible)}
        style={styles.passwordToggle}
      >
        <Text style={s.link}>
          {visible ? "Скрыть пароль" : "Показать пароль"}
        </Text>
      </Pressable>
      {register && (
        <LocationFields
          universityId={universityId}
          onUniversity={setUniversityId}
          dorm={dorm}
          onDorm={setDorm}
          error={errors.dorm}
        />
      )}
      <ErrorNotice error={failure} />
      <Button
        title={register ? "Создать аккаунт" : "Войти"}
        onPress={submit}
        busy={busy}
        testID="auth-submit"
      />
      <Pressable
        accessibilityRole="link"
        disabled={busy}
        onPress={() => (register ? router.back() : router.push("/register"))}
        style={styles.switchMode}
      >
        <Text style={s.link}>
          {register ? "Уже есть аккаунт? Войти" : "Нет аккаунта? Создать"}
        </Text>
      </Pressable>
    </Page>
  );
}
