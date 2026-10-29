import { styles } from "./styles";
import React, { useState } from "react";
import { Text, View } from "react-native";
import { errorText } from "../../../shared/api";
import { useSession } from "../../../entities/user";
import { Listing, Status } from "../../../entities/listing";
import { Button, ErrorNotice, s } from "../../../shared/ui";

import { useChangeListingStatus } from "../model/use-change-status";

/** Показывает автору доступные переходы статуса объявления с учётом формата и текущего состояния. */
export function OwnerActions({ item }: { item: Listing; }) {
  const { profile } = useSession();
  const changeStatus = useChangeListingStatus();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  if (item.ownerId !== profile.id) return null;
  /** Запускает смену статуса, блокирует повторное нажатие и показывает ошибку операции. */
  async function change(status: Status) {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      await changeStatus(item, status);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <View style={styles.actions}>
      <Text style={s.small}>
        Вы управляете статусом после договорённости в чате.
      </Text>
      <ErrorNotice error={error} />
      {item.status === "active" && item.format !== "Услуга" && (
        <Button
          title="Отметить забронированным"
          secondary
          busy={busy}
          onPress={() => void change("reserved")}
        />
      )}
      {item.status === "reserved" && (
        <>
          <Button
            title="Вещь передана — завершить"
            busy={busy}
            onPress={() => void change("completed")}
          />
          <Button
            title="Отменить бронь"
            secondary
            busy={busy}
            onPress={() => void change("active")}
          />
        </>
      )}
      {item.status === "active" && (
        <Button
          title="Снять с публикации"
          secondary
          busy={busy}
          onPress={() => void change("archived")}
        />
      )}
      {(item.status === "archived" || item.status === "completed") && (
        <Button
          title="Опубликовать снова"
          secondary
          busy={busy}
          onPress={() => void change("active")}
        />
      )}
    </View>
  );
}
