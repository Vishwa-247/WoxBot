import { useEffect, useRef } from "react";
import DocumentList from "./DocumentList";

export default function DocumentLibrary({ open, onClose, refreshTrigger }) {
  const panelRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    const handleClick = (e) => {
      if (panelRef.current && !panelRef.current.contains(e.target)) {
        onClose();
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      ref={panelRef}
      className="absolute right-4 top-12 w-72 max-h-96 z-50 bg-white dark:bg-[#1c1c1f] border border-zinc-200 dark:border-zinc-700 rounded-xl shadow-lg flex flex-col overflow-hidden"
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-200 dark:border-zinc-700 shrink-0">
        <h3 className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
          Document Library
        </h3>
        <button
          onClick={onClose}
          className="p-1 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
          aria-label="Close library"
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
      <div className="flex-1 overflow-y-auto py-2">
        <DocumentList refreshTrigger={refreshTrigger} />
      </div>
    </div>
  );
}
