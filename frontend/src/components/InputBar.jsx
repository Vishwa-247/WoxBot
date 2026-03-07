import { useEffect, useRef, useState } from "react";
import { useVoice } from "../hooks/useVoice";

export default function InputBar({
  onSend,
  isStreaming,
  onStop,
  onAttach,
  uploading,
  uploadProgress,
  uploadResult,
  uploadError,
  onUploadDismiss,
}) {
  const [input, setInput] = useState("");
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);
  const {
    listening,
    transcript,
    supported,
    startListening,
    stopListening,
    resetTranscript,
  } = useVoice();

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 128) + "px";
  }, [input]);

  useEffect(() => {
    if (!isStreaming) textareaRef.current?.focus();
  }, [isStreaming]);

  // Auto-dismiss upload feedback after 5 seconds
  useEffect(() => {
    if (!uploadResult && !uploadError) return;
    const timer = setTimeout(() => {
      if (onUploadDismiss) onUploadDismiss();
    }, 5000);
    return () => clearTimeout(timer);
  }, [uploadResult, uploadError, onUploadDismiss]);

  // Sync voice transcript into input
  useEffect(() => {
    if (transcript) {
      setInput(transcript);
    }
  }, [transcript]);

  // Auto-send when voice stops with content
  useEffect(() => {
    if (!listening && transcript.trim()) {
      const q = transcript.trim();
      resetTranscript();
      setInput("");
      onSend(q);
    }
  }, [listening, transcript, resetTranscript, onSend]);

  const handleSend = () => {
    const q = input.trim();
    if (!q || isStreaming) return;
    setInput("");
    onSend(q);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileChange = (e) => {
    const f = e.target.files[0];
    if (f && onAttach) onAttach(f);
    e.target.value = "";
  };

  return (
    <div className="py-3">
      {/* Upload success / error feedback */}
      {uploadResult && (
        <div className="mb-2 flex items-center gap-2 px-3 py-2 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg text-emerald-700 dark:text-emerald-400 text-xs">
          <svg
            className="w-4 h-4 shrink-0"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          </svg>
          <span className="flex-1">
            <strong>{uploadResult.filename || "Document"}</strong> uploaded
            successfully
            {uploadResult.chunks_stored
              ? ` — ${uploadResult.chunks_stored} chunks indexed`
              : ""}
          </span>
          <button
            onClick={onUploadDismiss}
            className="p-0.5 hover:text-emerald-900 dark:hover:text-emerald-200 transition-colors"
          >
            <svg
              className="w-3.5 h-3.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
      )}
      {uploadError && (
        <div className="mb-2 flex items-center gap-2 px-3 py-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-400 text-xs">
          <svg
            className="w-4 h-4 shrink-0"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span className="flex-1">Upload failed: {uploadError}</span>
          <button
            onClick={onUploadDismiss}
            className="p-0.5 hover:text-red-900 dark:hover:text-red-200 transition-colors"
          >
            <svg
              className="w-3.5 h-3.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
      )}

      <div
        className={`flex items-end gap-2 bg-white dark:bg-zinc-900 rounded-xl px-3 py-2 border transition-colors ${
          isStreaming
            ? "border-zinc-200 dark:border-zinc-700"
            : "border-zinc-200 dark:border-zinc-700 focus-within:border-zinc-400 dark:focus-within:border-zinc-500"
        }`}
      >
        {/* Attachment / Upload */}
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading || isStreaming}
          className="shrink-0 p-2 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          aria-label="Attach PDF"
          title="Upload PDF"
        >
          {uploading ? (
            <svg
              className="w-4 h-4 animate-spin"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8v8z"
              />
            </svg>
          ) : (
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
              />
            </svg>
          )}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={handleFileChange}
        />

        {/* Voice input */}
        {supported && (
          <button
            onClick={listening ? stopListening : startListening}
            disabled={isStreaming || uploading}
            className={`shrink-0 p-2 rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
              listening
                ? "text-red-500 bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/30"
                : "text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800"
            }`}
            aria-label={listening ? "Stop recording" : "Start voice input"}
            title={listening ? "Stop recording" : "Voice input"}
          >
            {listening ? (
              <svg
                className="w-4 h-4 animate-pulse"
                fill="currentColor"
                viewBox="0 0 24 24"
              >
                <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
                <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
              </svg>
            ) : (
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z"
                />
              </svg>
            )}
          </button>
        )}

        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question..."
          rows={1}
          disabled={isStreaming}
          className="flex-1 bg-transparent text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 dark:placeholder-zinc-500 text-sm resize-none outline-none py-1.5 max-h-32 disabled:opacity-50 leading-relaxed"
        />

        {isStreaming ? (
          <button
            onClick={onStop}
            className="shrink-0 p-2 text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
            aria-label="Stop generation"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <rect x="6" y="6" width="12" height="12" rx="1.5" />
            </svg>
          </button>
        ) : (
          <button
            onClick={handleSend}
            disabled={!input.trim()}
            className="shrink-0 p-2 text-white bg-zinc-900 dark:bg-zinc-100 dark:text-zinc-900 hover:bg-zinc-700 dark:hover:bg-zinc-300 disabled:opacity-30 disabled:cursor-not-allowed rounded-lg transition-colors"
            aria-label="Send message"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 12h14M12 5l7 7-7 7"
              />
            </svg>
          </button>
        )}
      </div>

      {/* Upload progress bar */}
      {uploading && uploadProgress > 0 && (
        <div className="mt-2 px-1">
          <div className="w-full bg-zinc-200 dark:bg-zinc-700 rounded-full h-1.5">
            <div
              className="bg-zinc-900 dark:bg-zinc-100 h-1.5 rounded-full transition-all duration-300"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
          <p className="text-[10px] text-zinc-400 mt-1">
            Processing document… {uploadProgress}%
          </p>
        </div>
      )}

      {!uploading && !uploadResult && !uploadError && (
        <p className="text-[11px] text-zinc-400 text-center mt-2 select-none">
          Enter to send · Shift+Enter for newline
        </p>
      )}
    </div>
  );
}
