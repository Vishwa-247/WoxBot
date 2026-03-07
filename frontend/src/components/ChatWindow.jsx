import { useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble';
import InputBar from './InputBar';

const SUGGESTION_QUERIES = [
  'What is bubble sort from my notes?',
  'Calculate my CGPA: 8.5, 9.2, 7.8, 8.1',
  'Summarize my uploaded syllabus',
  'What are the latest trends in AI?',
];

/**
 * ChatWindow — reads state from hooks only.
 * NEVER opens EventSource or calls fetch directly.
 */
export default function ChatWindow({ messages, isStreaming, onSend, onStop }) {
  const bottomRef = useRef(null);

  // Auto-scroll to bottom whenever messages change or tokens stream in
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {/* Message area */}
      <div className="flex-1 overflow-y-auto px-2 py-6 scroll-smooth">
        {messages.length === 0 ? (
          /* Empty state / welcome screen */
          <div className="h-full flex flex-col items-center justify-center text-center px-4">
            <div className="text-6xl mb-4 select-none">🤖</div>
            <h2 className="text-2xl font-semibold text-gray-200 mb-2">Welcome to WoxBot</h2>
            <p className="text-gray-500 text-sm max-w-md leading-relaxed">
              Upload your Woxsen University PDFs using the sidebar, then ask anything about
              your course materials. All answers are grounded in your documents — zero hallucination.
            </p>
            <div className="mt-8 grid gap-2 w-full max-w-md">
              {SUGGESTION_QUERIES.map((q) => (
                <button
                  key={q}
                  onClick={() => onSend(q)}
                  className="text-left px-4 py-2.5 text-sm text-gray-400 bg-gray-800/60 hover:bg-gray-800 rounded-xl border border-gray-700 hover:border-gray-600 transition"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg) => <MessageBubble key={msg.id} message={msg} />)
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input bar pinned at bottom */}
      <InputBar onSend={onSend} isStreaming={isStreaming} onStop={onStop} />
    </div>
  );
}
