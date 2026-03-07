export default function SourcePanel({ sources, onClose }) {
  if (!sources || sources.length === 0) return null;

  return (
    <aside className="w-72 shrink-0 border-l border-gray-800 bg-gray-900 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800 shrink-0">
        <h3 className="text-sm font-semibold text-gray-200">
          Sources
          <span className="ml-1.5 text-xs font-normal text-gray-500">({sources.length})</span>
        </h3>
        <button
          onClick={onClose}
          className="p-1 text-gray-500 hover:text-gray-300 rounded hover:bg-gray-800 transition"
          aria-label="Close sources"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Source cards */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {sources.map((src, i) => (
          <div
            key={i}
            className="bg-gray-800 rounded-xl p-3 text-xs border border-gray-700 hover:border-gray-600 transition"
          >
            {/* File + page */}
            <div className="flex items-center justify-between mb-1.5 gap-2">
              <span className="font-medium text-indigo-400 truncate" title={src.filename}>
                {src.filename}
              </span>
              <span className="text-gray-500 shrink-0 tabular-nums">p.{src.page}</span>
            </div>

            {/* Section title */}
            {src.section_title && (
              <p className="text-gray-400 font-medium mb-1 truncate" title={src.section_title}>
                {src.section_title}
              </p>
            )}

            {/* Chunk text preview */}
            <p className="text-gray-300 leading-relaxed line-clamp-4">
              {src.text?.slice(0, 220)}
              {src.text?.length > 220 ? '…' : ''}
            </p>
          </div>
        ))}
      </div>
    </aside>
  );
}
