/** Удаляет крайние пробелы и сокращает повторные пробелы в названии общежития. */
export const normalizeDorm = (value: string) =>
  value.trim().replace(/\s+/g, " ");

/** Добавляет слово «Общежитие» к числовому номеру, сохраняя произвольные названия. */
export const dormLabel = (value: string) =>
  /^\d+$/.test(value) ? `Общежитие ${value}` : value;
