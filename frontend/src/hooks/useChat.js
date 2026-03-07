import { useState, useCallback, useRef, useEffect } from 'react';
import { useStream } from './useStream';

function genId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2);
}

/**
 * useChat — manages the messages array and chat session.
 * Reads token/sources state from useStream and syncs them
 * into the bot message being built.
 */
export function useChat() {
  const [messages, setMessages] = useState([]);
  const [sessionId] = useState(() => 'sess_' + genId());
  const { tokens, sources, isStreaming, startStream, stopStream } = useStream();
  const botIdRef = useRef(null);

  // Sync streaming tokens → update the bot message content as they arrive
  useEffect(() => {
    if (botIdRef.current && tokens !== undefined) {
      setMessages((prev) =>
        prev.map((m) => (m.id === botIdRef.current ? { ...m, content: tokens } : m))
      );
    }
  }, [tokens]);

  // Finalize bot message when streaming ends — attach sources
  useEffect(() => {
    if (!isStreaming && botIdRef.current) {
      const id = botIdRef.current;
      setMessages((prev) =>
        prev.map((m) =>
          m.id === id ? { ...m, sources: sources, streaming: false } : m
        )
      );
      botIdRef.current = null;
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isStreaming]);

  const sendMessage = useCallback(
    (query, provider) => {
      if (!query.trim() || isStreaming) return;

      const userMsg = { id: genId(), role: 'user', content: query.trim(), sources: [] };
      const botId = genId();
      botIdRef.current = botId;
      const botMsg = { id: botId, role: 'bot', content: '', sources: [], streaming: true };

      setMessages((prev) => [...prev, userMsg, botMsg]);
      startStream(query.trim(), sessionId, provider);
    },
    [isStreaming, sessionId, startStream]
  );

  const clearChat = useCallback(() => {
    setMessages([]);
    botIdRef.current = null;
    stopStream();
  }, [stopStream]);

  return { messages, sessionId, isStreaming, sendMessage, stopStream, clearChat };
}
