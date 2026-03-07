import { useState } from 'react';
import FileUpload from './FileUpload';
import DocumentList from './DocumentList';

export default function Sidebar({ open, onNewChat, onClose }) {
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleUploadComplete = () => {
    setRefreshTrigger((n) => n + 1);
  };

  return (
    <>
      {/* Mobile backdrop overlay */}
      {open && (
        <div
          className="fixed inset-0 bg-black/60 z-20 lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={`
          fixed lg:static top-0 left-0 h-full z-30 lg:z-auto
          w-64 bg-gray-900 border-r border-gray-800 flex flex-col
          transition-transform duration-200 ease-in-out
          ${open ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
      >
        {/* New Chat button — extra top padding on mobile to clear Navbar */}
        <div className="p-3 pt-16 lg:pt-3 shrink-0">
          <button
            onClick={() => { onNewChat(); onClose(); }}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-300 bg-gray-800 hover:bg-gray-700 rounded-xl border border-gray-700 transition"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Chat
          </button>
        </div>

        {/* Upload section label */}
        <div className="px-4 pb-1 shrink-0">
          <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest">
            Upload PDF
          </p>
        </div>

        <FileUpload onUploadComplete={handleUploadComplete} />

        {/* Knowledge base label */}
        <div className="px-4 py-2 shrink-0">
          <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest">
            Knowledge Base
          </p>
        </div>

        {/* Scrollable document list */}
        <div className="flex-1 overflow-y-auto pb-4">
          <DocumentList refreshTrigger={refreshTrigger} />
        </div>
      </aside>
    </>
  );
}
