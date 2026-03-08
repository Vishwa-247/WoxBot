import { useCallback, useEffect, useRef, useState } from "react";
import { useStream } from "./useStream";

const HISTORY_KEY = "woxbot-history";
const MAX_HISTORY = 50;

function genId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2);
}

function loadHistory() {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
  } catch {
    return [];
  }
}

function saveHistory(history) {
  localStorage.setItem(
    HISTORY_KEY,
    JSON.stringify(history.slice(0, MAX_HISTORY)),
  );
}

export function useChat() {
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(() => "sess_" + genId());
  const [chatHistory, setChatHistory] = useState(loadHistory);
  const [selectedDocIds, setSelectedDocIds] = useState([]);
  const { tokens, sources, followups, isStreaming, startStream, stopStream } =
    useStream();
  const botIdRef = useRef(null);

  // Persist current session to history whenever messages change (non-streaming)
  useEffect(() => {
    if (isStreaming || messages.length === 0) return;
    const firstUser = messages.find((m) => m.role === "user");
    if (!firstUser) return;

    setChatHistory((prev) => {
      const existing = prev.findIndex((s) => s.id === sessionId);
      const entry = {
        id: sessionId,
        title: firstUser.content.slice(0, 80),
        createdAt: existing >= 0 ? prev[existing].createdAt : Date.now(),
        updatedAt: Date.now(),
        messages,
      };
      const next =
        existing >= 0
          ? prev.map((s) => (s.id === sessionId ? entry : s))
          : [entry, ...prev];
      saveHistory(next);
      return next;
    });
  }, [messages, isStreaming, sessionId]);

  // Sync streaming tokens
  useEffect(() => {
    if (botIdRef.current && tokens !== undefined) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === botIdRef.current ? { ...m, content: tokens } : m,
        ),
      );
    }
  }, [tokens]);

  // Finalize bot message when streaming ends
  useEffect(() => {
    if (!isStreaming && botIdRef.current) {
      const id = botIdRef.current;
      setMessages((prev) =>
        prev.map((m) =>
          m.id === id
            ? { ...m, sources: sources, followups: followups, streaming: false }
            : m,
        ),
      );
      botIdRef.current = null;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isStreaming]);

  const sendMessage = useCallback(
    (query, provider, model) => {
      if (!query.trim() || isStreaming) return;

      const userMsg = {
        id: genId(),
        role: "user",
        content: query.trim(),
        sources: [],
      };
      const botId = genId();
      botIdRef.current = botId;
      const botMsg = {
        id: botId,
        role: "bot",
        content: "",
        sources: [],
        streaming: true,
      };

      setMessages((prev) => [...prev, userMsg, botMsg]);
      startStream(query.trim(), sessionId, provider, model, selectedDocIds);
    },
    [isStreaming, sessionId, startStream, selectedDocIds],
  );

  const clearChat = useCallback(() => {
    setMessages([]);
    botIdRef.current = null;
    setSessionId("sess_" + genId());
    stopStream();
  }, [stopStream]);

  const loadSession = useCallback(
    (id) => {
      if (isStreaming) return;
      const session = chatHistory.find((s) => s.id === id);
      if (!session) return;
      setMessages(session.messages);
      setSessionId(session.id);
      botIdRef.current = null;
    },
    [chatHistory, isStreaming],
  );

  const deleteSession = useCallback((id) => {
    setChatHistory((prev) => {
      const next = prev.filter((s) => s.id !== id);
      saveHistory(next);
      return next;
    });
  }, []);

  return {
    messages,
    sessionId,
    isStreaming,
    chatHistory,
    selectedDocIds,
    setSelectedDocIds,
    sendMessage,
    stopStream,
    clearChat,
    loadSession,
    deleteSession,
  };
}
