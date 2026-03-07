import { useEffect, useState } from "react";
import ModelSelector from "./ModelSelector";

export default function Navbar({
  onSidebarToggle,
  onLibraryToggle,
  libraryOpen,
  selectedModel,
  onModelChange,
}) {
  const [dark, setDark] = useState(true);

  useEffect(() => {
    const saved = localStorage.getItem("theme");
    const isDark = saved ? saved === "dark" : true;
    setDark(isDark);
    document.documentElement.classList.toggle("dark", isDark);
  }, []);

  const toggleDark = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
  };

  return (
    <header className="h-12 flex items-center justify-between px-4 border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-[#111113] shrink-0 z-10">
      <div className="flex items-center gap-3">
        <button
          onClick={onSidebarToggle}
          className="p-1.5 rounded-md text-zinc-600 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
          aria-label="Toggle sidebar"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M4 6h16M4 12h16M4 18h16"
            />
          </svg>
        </button>
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100 tracking-tight">
            WoxBot
          </span>
          <span className="text-[10px] px-1.5 py-0.5 rounded-md bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400 font-medium">
            v1.0
          </span>
        </div>
      </div>

      <div className="flex items-center gap-1.5">
        {/* Model selector */}
        <ModelSelector value={selectedModel} onChange={onModelChange} />

        <div className="w-px h-5 bg-zinc-200 dark:bg-zinc-700 mx-0.5" />

        {/* Library / Documents */}
        <button
          onClick={onLibraryToggle}
          className={`p-1.5 rounded-md transition-colors ${
            libraryOpen
              ? "text-zinc-900 dark:text-zinc-100 bg-zinc-100 dark:bg-zinc-800"
              : "text-zinc-600 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800"
          }`}
          aria-label="Toggle document library"
          title="Document Library"
        >
          <svg
            className="w-[18px] h-[18px]"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
            />
          </svg>
        </button>

        {/* Theme toggle */}
        <button
          onClick={toggleDark}
          className="p-1.5 rounded-md text-zinc-600 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
          aria-label="Toggle dark mode"
          title={dark ? "Switch to light mode" : "Switch to dark mode"}
        >
          {dark ? (
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
                d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707M17.657 17.657l-.707-.707M6.343 6.343l-.707-.707M12 5a7 7 0 000 14 7 7 0 000-14z"
              />
            </svg>
          ) : (
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
                d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"
              />
            </svg>
          )}
        </button>
      </div>
    </header>
  );
}
