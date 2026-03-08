import { useCallback, useRef, useState } from "react";
import { API_KEY } from "../services/api";

/**
 * useStream — ALL SSE/EventSource logic lives here.
 * Uses fetch + AbortController (not EventSource) because the backend
 * chat endpoint is POST-based SSE, and EventSource only supports GET.
 *
 * SSE Protocol from backend:
 *   data: {token}\n\n   (one per token)
 *   data: [SOURCES_START]\n\n
 *   data: {"chunks": [...]}\n\n
 *   data: [DONE]\n\n
 */
export function useStream() {
  const abortRef = useRef(null);
  const [tokens, setTokens] = useState("");
  const [sources, setSources] = useState([]);
  const [followups, setFollowups] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);

  const startStream = useCallback(
    async (query, sessionId, provider = "groq", model = null, selectedDocIds = []) => {
      // Guard: cancel any in-flight stream before starting a new one
      if (abortRef.current) {
        abortRef.current.abort();
        abortRef.current = null;
      }

      setTokens("");
      setSources([]);
      setFollowups([]);
      setIsStreaming(true);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-API-Key": API_KEY,
          },
          body: JSON.stringify({
            query,
            session_id: sessionId,
            provider,
            model,
            selected_doc_ids: selectedDocIds,
          }),
          signal: controller.signal,
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || `HTTP ${res.status}`);
        }

        const reader = res.body.getReader();
        const dec = new TextDecoder();
        let buf = "";
        let inSources = false;
        let inFollowups = false;
        let streamDone = false;

        const processLine = (line) => {
          if (!line.startsWith("data: ")) return;
          const data = line.slice(6);

          if (data === "[DONE]") {
            streamDone = true;
            return;
          }

          if (data === "[SOURCES_START]") {
            inSources = true;
            return;
          }

          if (inSources) {
            try {
              const parsed = JSON.parse(data);
              if (parsed.chunks) setSources(parsed.chunks);
            } catch (_) {
              /* malformed JSON — skip */
            }
            inSources = false;
            return;
          }

          if (data === "[FOLLOWUPS_START]") {
            inFollowups = true;
            return;
          }

          if (inFollowups) {
            try {
              const parsed = JSON.parse(data);
              if (parsed.questions) setFollowups(parsed.questions);
            } catch (_) {
              /* malformed JSON — skip */
            }
            inFollowups = false;
            return;
          }

          setTokens((prev) => prev + data);
        };

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buf += dec.decode(value, { stream: true });
          const lines = buf.split("\n");
          buf = lines.pop(); // keep incomplete last line in buffer

          for (const line of lines) {
            processLine(line);
            if (streamDone) break;
          }
          if (streamDone) break;
        }

        // Process any leftover buffer content after stream ends
        if (!streamDone && buf.trim()) {
          processLine(buf.trim());
        }
      } catch (err) {
        if (err.name !== "AbortError") {
          console.error("[useStream] error:", err.message);
          setTokens((prev) => prev || `⚠ Error: ${err.message}`);
        }
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [],
  );

  const stopStream = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  return { tokens, sources, followups, isStreaming, startStream, stopStream };
}
