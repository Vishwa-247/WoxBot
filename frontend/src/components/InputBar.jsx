import { useState, useRef, useEffect } from 'react';

export default function InputBar({ onSend, isStreaming, onStop }) {
  const [input, setInput] = useState('');
  const textareaRef = useRef(null);

  // Auto-resize textarea height with content
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 128) + 'px';
  }, [input]);

  // Re-focus after streaming ends
  useEffect(() => {
    if (!isStreaming) textareaRef.current?.focus();
  }, [isStreaming]);

  const handleSend = () => {
    const q = input.trim();
    if (!q || isStreaming) return;
    setInput('');
    onSend(q);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="px-4 py-3 border-t border-gray-800 bg-gray-950 shrink-0">
      <div
        className={`flex items-end gap-2 bg-gray-800 rounded-2xl px-4 py-2 border transition ${
          isStreaming ? 'border-gray-700' : 'border-gray-700 focus-within:border-indigo-500'
        }`}
      >
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask WoxBot about your notes…"
          rows={1}
          disabled={isStreaming}
          className="flex-1 bg-transparent text-gray-100 placeholder-gray-500 text-sm resize-none outline-none py-1.5 max-h-32 disabled:opacity-50 leading-relaxed"
        />

        {isStreaming ? (
          <button
            onClick={onStop}
            className="shrink-0 p-2 bg-red-600 hover:bg-red-500 text-white rounded-xl transition mb-0.5"
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
            className="shrink-0 p-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-30 disabled:cursor-not-allowed text-white rounded-xl transition mb-0.5"
            aria-label="Send message"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        )}
      </div>
      <p className="text-xs text-gray-700 text-center mt-1.5 select-none">
        Enter to send · Shift+Enter for newline
      </p>
    </div>
  );
}
