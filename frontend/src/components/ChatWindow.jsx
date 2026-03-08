import { useEffect, useRef } from "react";
import InputBar from "./InputBar";
import MessageBubble from "./MessageBubble";

const SUGGESTIONS = [
  { icon: "📚", text: "What is bubble sort from my notes?" },
  { icon: "📋", text: "Summarize my uploaded syllabus" },
  { icon: "🔍", text: "Explain the key concepts in chapter 3" },
  { icon: "🌐", text: "What are the latest trends in AI?" },
];

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good Morning";
  if (h < 17) return "Good Afternoon";
  return "Good Evening";
}

export default function ChatWindow({
  messages,
  isStreaming,
  onSend,
  onStop,
  onAttach,
  uploading,
  uploadProgress,
  uploadResult,
  uploadError,
  onUploadDismiss,
}) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex flex-col flex-1 overflow-hidden bg-white dark:bg-[#111113]">
      <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8 lg:px-20 xl:px-40">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center max-w-2xl mx-auto">
            <p className="text-sm text-zinc-400 dark:text-zinc-500 mb-1">
              {getGreeting()} 👋
            </p>

            <h1 className="text-2xl md:text-3xl font-semibold text-zinc-900 dark:text-zinc-100 mb-2 leading-tight">
              How Can I Assist You Today?
            </h1>

            <p className="text-xs text-zinc-400 dark:text-zinc-500 mb-8">
              Upload documents and ask questions — powered by RAG
            </p>

            <div className="w-full max-w-xl mb-6">
              <InputBar
                onSend={onSend}
                isStreaming={isStreaming}
                onStop={onStop}
                onAttach={onAttach}
                uploading={uploading}
                uploadProgress={uploadProgress}
                uploadResult={uploadResult}
                uploadError={uploadError}
                onUploadDismiss={onUploadDismiss}
              />
            </div>

            <div className="flex flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s.text}
                  onClick={() => onSend(s.text)}
                  className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium text-zinc-600 dark:text-zinc-400 bg-zinc-50 dark:bg-zinc-800/60 hover:bg-zinc-100 dark:hover:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-xl transition-colors"
                >
                  <span>{s.icon}</span>
                  <span>{s.text}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="max-w-2xl mx-auto pb-8">
            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                onFollowupClick={onSend}
              />
            ))}
            <div ref={bottomRef} className="h-2" />
          </div>
        )}
      </div>

      {messages.length > 0 && (
        <div className="border-t border-zinc-100 dark:border-zinc-800/50 bg-white dark:bg-[#111113]">
          <div className="max-w-2xl mx-auto px-4 md:px-8">
            <InputBar
              onSend={onSend}
              isStreaming={isStreaming}
              onStop={onStop}
              onAttach={onAttach}
              uploading={uploading}
              uploadProgress={uploadProgress}
              uploadResult={uploadResult}
              uploadError={uploadError}
              onUploadDismiss={onUploadDismiss}
            />
          </div>
        </div>
      )}
    </div>
  );
}
