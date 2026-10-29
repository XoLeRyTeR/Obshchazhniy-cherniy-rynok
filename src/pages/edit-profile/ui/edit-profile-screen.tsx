import { styles } from "./styles";
import React, { useState } from "react";
import { Text } from "react-native";
import { router } from "expo-router";
import { errorText } from "../../../shared/api";
import { useSession } from "../../../entities/user";
import { useListings } from "../../../entities/listing";
import { LocationFields, normalizeDorm } from "../../../entities/location";
import { Button, ErrorNotice, Field, Page, s } from "../../../shared/ui";

/** Показывает редактирование имени, вуза и общежития текущего пользователя. */
export function EditProfileScreen() {
  const { profile, updateProfile } = useSession();
  const { renameAuthor } = useListings();
  const [name, setName] = useState(profile.name);
  const [universityId, setUniversityId] = useState(profile.universityId);
  const [dorm, setDorm] = useState(profile.dorm);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  /** Проверяет поля профиля, сохраняет их, обновляет имя в кеше объявлений и возвращает назад. */
  async function save() {
    if (busy) return;
    if (!name.trim() || !normalizeDorm(dorm) || !universityId) {
      setError("Введите имя, выберите вуз и укажите общежитие");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await updateProfile(name.trim(), universityId, normalizeDorm(dorm));
      renameAuthor(profile.id, name.trim());
      router.back();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Page title="Редактировать профиль" back>
      <Field
        label="Имя"
        value={name}
        onChangeText={setName}
        maxLength={80}
        editable={!busy}
      />
      <LocationFields
        universityId={universityId}
        onUniversity={setUniversityId}
        dorm={dorm}
        onDorm={setDorm}
      />
      <Text style={[s.subtitle, styles.email]}>
        {profile.email}
      </Text>
      <ErrorNotice error={error} />
      <Button title="Сохранить" onPress={save} busy={busy} />
    </Page>
  );
}
