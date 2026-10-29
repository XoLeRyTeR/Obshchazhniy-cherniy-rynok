import React, { useEffect, useState } from "react";
import { Text } from "react-native";
import { errorText, type CatalogItem } from "../../../shared/api";
import { ErrorNotice, Field, s, Select } from "../../../shared/ui";
import { universities, dormitories } from "../api/catalog";

/** Показывает выбор вуза и общежития с возможностью ввести отсутствующее в списке название. */
export function LocationFields({
  universityId,
  onUniversity,
  dorm,
  onDorm,
  error,
}: {
  universityId: string;
  onUniversity: (id: string) => void;
  dorm: string;
  onDorm: (name: string) => void;
  error?: string;
}) {
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [dorms, setDorms] = useState<CatalogItem[]>([]);
  const [custom, setCustom] = useState(false);
  const [failure, setFailure] = useState("");
  const [retry, setRetry] = useState(0);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    let active = true;
    universities()
      .then((result) => {
        if (!active) return;
        setItems(result);
        setFailure("");
        if (!universityId && result.length) onUniversity(result[0].id);
      })
      .catch((e) => {
        if (active) setFailure(errorText(e));
      });
    return () => {
      active = false;
    };
  }, [universities, retry]);
  useEffect(() => {
    let active = true;
    setDorms([]);
    if (universityId) {
      setLoading(true);
      dormitories(universityId)
        .then((result) => {
          if (active) {
            setDorms(result);
            setFailure("");
          }
        })
        .catch((e) => {
          if (active) setFailure(errorText(e));
        })
        .finally(() => {
          if (active) setLoading(false);
        });
    }
    return () => {
      active = false;
    };
  }, [universityId, dormitories, retry]);
  const other = "В списке нет моего общежития";
  return (
    <>
      <ErrorNotice error={failure} onRetry={() => setRetry((v) => v + 1)} />
      {!items.length && !failure && (
        <Text style={s.small}>
          Список вузов пока пуст. Обратитесь к организатору.
        </Text>
      )}
      <Select
        label="Университет"
        value={
          items.find((i) => i.id === universityId)?.name ??
          "Выберите университет"
        }
        options={items.map((i) => i.name)}
        onChange={(name) => {
          const item = items.find((i) => i.name === name);
          if (item && item.id !== universityId) {
            onUniversity(item.id);
            onDorm("");
            setCustom(false);
          }
        }}
      />
      <Select
        label="Общежитие"
        value={
          custom
            ? "Другое общежитие"
            : dorm || (loading ? "Загрузка…" : "Выберите общежитие")
        }
        options={[...dorms.map((d) => d.name), other]}
        onChange={(value) => {
          setCustom(value === other);
          onDorm(value === other ? "" : value);
        }}
      />
      {custom ? (
        <Field
          label="Название или номер общежития"
          placeholder="Например, 7 или Северный кампус"
          value={dorm}
          onChangeText={onDorm}
          maxLength={80}
          error={error}
          autoFocus
        />
      ) : (
        !!error && (
          <Text accessibilityRole="alert" style={s.error}>
            {error}
          </Text>
        )
      )}
    </>
  );
}
