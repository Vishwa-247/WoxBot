import { useState, useRef, useCallback } from 'react';
import { useUpload } from '../hooks/useUpload';

export default function FileUpload({ onUploadComplete }) {
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef(null);
  const { uploading, progress, result, error, upload } = useUpload(onUploadComplete);

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) upload(file);
    },
    [upload]
  );

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragging(true);
  };

  const handleFileChange = (e) => {
    const f = e.target.files[0];
    if (f) upload(f);
    e.target.value = '';
  };

  return (
    <div className="px-3 pb-2">
      {/* Drop zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={() => setDragging(false)}
        onClick={() => !uploading && fileInputRef.current?.click()}
        className={`
          border-2 border-dashed rounded-xl p-3 text-center cursor-pointer transition select-none
          ${dragging ? 'border-indigo-500 bg-indigo-950/30' : 'border-gray-700 hover:border-gray-500 hover:bg-gray-800/40'}
          ${uploading ? 'opacity-60 cursor-not-allowed pointer-events-none' : ''}
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={handleFileChange}
        />

        {uploading ? (
          <div className="space-y-2">
            <p className="text-xs text-gray-400">Uploading… {progress}%</p>
            <div className="w-full bg-gray-700 rounded-full h-1.5">
              <div
                className="bg-indigo-500 h-1.5 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        ) : (
          <div className="space-y-1">
            <svg
              className="w-5 h-5 mx-auto text-gray-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            <p className="text-xs text-gray-500">Drop PDF or click to upload</p>
          </div>
        )}
      </div>

      {/* Success message */}
      {result && (
        <div className="mt-2 text-xs text-green-400 bg-green-950/30 border border-green-800/50 rounded-lg p-2.5 leading-relaxed">
          <p>
            ✓{' '}
            {result.chunks_added > 0
              ? `${result.chunks_added} chunks indexed from ${result.filename}`
              : result.message || 'Indexed successfully'}
          </p>
          {result.scanned_pages?.length > 0 && (
            <p className="text-yellow-400 mt-1">
              ⚠ Scanned pages detected: {result.scanned_pages.join(', ')}
            </p>
          )}
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="mt-2 text-xs text-red-400 bg-red-950/30 border border-red-800/50 rounded-lg p-2.5">
          ✗ {error}
        </div>
      )}
    </div>
  );
}
