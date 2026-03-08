import { useCallback, useEffect, useState } from "react";
import { getSources } from "../services/api";

export default function DocumentSelector({
  selectedDocIds,
  onSelectionChange,
  refreshTrigger,
}) {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchDocs = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getSources();
      setDocs(data.documents || []);
    } catch {
      // fail silently
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocs();
  }, [fetchDocs, refreshTrigger]);

  const toggle = (docId) => {
    if (selectedDocIds.includes(docId)) {
      onSelectionChange(selectedDocIds.filter((id) => id !== docId));
    } else {
      onSelectionChange([...selectedDocIds, docId]);
    }
  };

  if (loading || docs.length === 0) return null;

  return (
    <div className="px-3 py-2 border-b border-zinc-200 dark:border-zinc-700/50">
      <p className="text-[10px] font-semibold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider mb-1.5">
        Search in
      </p>
      <div className="space-y-0.5 max-h-32 overflow-y-auto">
        {docs.map((doc) => (
          <label
            key={doc.doc_id || doc.filename}
            className="flex items-center gap-2 py-1 px-1 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800/50 cursor-pointer transition-colors"
          >
            <input
              type="checkbox"
              checked={selectedDocIds.includes(doc.doc_id)}
              onChange={() => toggle(doc.doc_id)}
              className="rounded border-zinc-300 dark:border-zinc-600 text-zinc-600 dark:text-zinc-400 focus:ring-zinc-400 w-3.5 h-3.5"
            />
            <span className="text-xs text-zinc-700 dark:text-zinc-300 truncate flex-1">
              {doc.filename}
            </span>
            <span className="text-[10px] text-zinc-400 dark:text-zinc-500 shrink-0">
              {doc.chunk_count}
            </span>
          </label>
        ))}
      </div>
      {selectedDocIds.length === 0 && (
        <p className="text-[10px] text-zinc-400 dark:text-zinc-500 italic mt-1">
          All documents
        </p>
      )}
    </div>
  );
}
