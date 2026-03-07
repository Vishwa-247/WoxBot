import { useState, useEffect, useCallback } from 'react';
import { getSources, deleteSource } from '../services/api';

export default function DocumentList({ refreshTrigger }) {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [deletingFile, setDeletingFile] = useState(null);

  const fetchDocs = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getSources();
      setDocs(data.documents || []);
    } catch {
      // Server may not be running during dev — fail silently
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocs();
  }, [fetchDocs, refreshTrigger]);

  const handleDelete = async (filename) => {
    if (!confirm(`Remove "${filename}" from the knowledge base?`)) return;
    setDeletingFile(filename);
    try {
      await deleteSource(filename);
      setDocs((prev) => prev.filter((d) => d.filename !== filename));
    } catch (err) {
      alert('Delete failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setDeletingFile(null);
    }
  };

  if (loading) {
    return <p className="px-3 py-2 text-xs text-gray-600 animate-pulse">Loading…</p>;
  }

  if (docs.length === 0) {
    return <p className="px-3 py-1 text-xs text-gray-600">No documents indexed yet.</p>;
  }

  return (
    <div className="px-3 space-y-0.5">
      {docs.map((doc) => (
        <div
          key={doc.filename}
          className="flex items-center justify-between gap-2 py-1.5 group rounded-lg px-1 hover:bg-gray-800/50 transition"
        >
          <div className="flex-1 min-w-0">
            <p className="text-xs text-gray-300 truncate" title={doc.filename}>
              📄 {doc.filename}
            </p>
            <p className="text-[10px] text-gray-600 mt-0.5">{doc.chunk_count} chunks</p>
          </div>
          <button
            onClick={() => handleDelete(doc.filename)}
            disabled={deletingFile === doc.filename}
            className="shrink-0 p-1 text-gray-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition disabled:opacity-20"
            aria-label={`Delete ${doc.filename}`}
          >
            {deletingFile === doc.filename ? (
              <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
              </svg>
            ) : (
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            )}
          </button>
        </div>
      ))}
    </div>
  );
}
