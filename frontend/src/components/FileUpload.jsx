import { useCallback, useRef, useState } from "react";
import { useUpload } from "../hooks/useUpload";

export default function FileUpload({ onUploadComplete }) {
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef(null);
  const { uploading, progress, result, error, upload } =
    useUpload(onUploadComplete);

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) upload(file);
    },
    [upload],
  );

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragging(true);
  };

  const handleFileChange = (e) => {
    const f = e.target.files[0];
    if (f) upload(f);
    e.target.value = "";
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
          border-2 border-dashed rounded-lg p-3 text-center cursor-pointer transition-colors select-none
          ${dragging ? "border-blue-500 bg-blue-50 dark:bg-blue-950/20" : "border-zinc-300 dark:border-zinc-700 hover:border-zinc-400 dark:hover:border-zinc-600 hover:bg-zinc-50 dark:hover:bg-zinc-800/50"}
          ${uploading ? "opacity-60 cursor-not-allowed pointer-events-none" : ""}
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
            <p className="text-xs text-zinc-500">Uploading… {progress}%</p>
            <div className="w-full bg-zinc-200 dark:bg-zinc-700 rounded-full h-1.5">
              <div
                className="bg-zinc-900 dark:bg-zinc-100 h-1.5 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        ) : (
          <div className="space-y-1">
            <svg
              className="w-5 h-5 mx-auto text-zinc-400"
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
            <p className="text-xs text-zinc-400">Drop PDF or click to upload</p>
          </div>
        )}
      </div>

      {/* Success message */}
      {result && (
        <div className="mt-2 text-xs text-green-700 dark:text-green-400 bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800/50 rounded-lg p-2.5 leading-relaxed">
          <p>
            ✓{" "}
            {result.chunks_added > 0
              ? `${result.chunks_added} chunks indexed from ${result.filename}`
              : result.message || "Indexed successfully"}
          </p>
          {result.scanned_pages?.length > 0 && (
            <p className="text-amber-600 dark:text-yellow-400 mt-1">
              ⚠ Scanned pages detected: {result.scanned_pages.join(", ")}
            </p>
          )}
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="mt-2 text-xs text-red-700 dark:text-red-400 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800/50 rounded-lg p-2.5">
          ✗ {error}
        </div>
      )}
    </div>
  );
}
