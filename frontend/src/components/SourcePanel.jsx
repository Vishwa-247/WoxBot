export default function SourcePanel({ sources, onClose }) {
  if (!sources || sources.length === 0) return null;

  return (
    <aside className="w-72 shrink-0 border-l border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-[#18181b] flex flex-col overflow-hidden hidden md:flex">
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-200 dark:border-zinc-800 shrink-0">
        <h3 className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
          Sources
          <span className="ml-1 text-xs text-zinc-400">({sources.length})</span>
        </h3>
        <button
          onClick={onClose}
          className="p-1 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
          aria-label="Close sources"
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
              strokeWidth={1.5}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {sources.map((src, i) => (
          <div
            key={i}
            className="bg-white dark:bg-zinc-800 rounded-lg p-3 text-xs border border-zinc-200 dark:border-zinc-700 hover:border-zinc-300 dark:hover:border-zinc-600 transition-colors"
          >
            <div className="flex items-center justify-between mb-1.5 gap-2">
              <span
                className="font-medium text-zinc-900 dark:text-zinc-100 truncate"
                title={src.filename}
              >
                {src.filename}
              </span>
              <span className="text-zinc-400 shrink-0 tabular-nums">
                p.{src.page}
              </span>
            </div>

            {src.section_title && (
              <p
                className="text-zinc-500 font-medium mb-1 truncate"
                title={src.section_title}
              >
                {src.section_title}
              </p>
            )}

            <p className="text-zinc-600 dark:text-zinc-400 leading-relaxed line-clamp-4">
              {src.text?.slice(0, 220)}
              {src.text?.length > 220 ? "…" : ""}
            </p>
          </div>
        ))}
      </div>
    </aside>
  );
}
