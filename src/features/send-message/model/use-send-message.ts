import { useRef, useState } from "react";
import { useChats } from "../../../entities/chat";
import { errorText } from "../../../shared/api";
import { messageId } from "../../../shared/lib";

/** Управляет текстом и отправкой сообщения; повтор после ошибки использует тот же UUID. */
export function useSendMessage(chatId: string) {
  const { sendMessage } = useChats();
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const pending = useRef<{ text: string; key: string; } | null>(null);

  /** Отправляет непустой текст с устойчивым ключом повтора, очищает поле при успехе и возвращает результат. */
  async function send() {
    const value = text.trim();
    if (!value || sending) return false;
    setSending(true);
    setError("");
    try {
      if (pending.current?.text !== value)
        pending.current = { text: value, key: messageId() };
      await sendMessage(chatId, value, pending.current.key);
      setText("");
      pending.current = null;
      return true;
    } catch (failure) {
      setError(errorText(failure));
      return false;
    } finally {
      setSending(false);
    }
  }
  return { text, setText, sending, error, send };
}
