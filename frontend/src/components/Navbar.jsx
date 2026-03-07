import { useEffect, useState } from 'react';

export default function Navbar({ onSidebarToggle }) {
  const [dark, setDark] = useState(true);

  useEffect(() => {
    const saved = localStorage.getItem('theme');
    const isDark = saved ? saved === 'dark' : true;
    setDark(isDark);
    document.documentElement.classList.toggle('dark', isDark);
  }, []);

  const toggleDark = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle('dark', next);
    localStorage.setItem('theme', next ? 'dark' : 'light');
  };

  return (
    <header className="h-14 flex items-center justify-between px-4 border-b border-gray-800 bg-gray-950 shrink-0 z-10">
      <div className="flex items-center gap-3">
        <button
          onClick={onSidebarToggle}
          className="p-1.5 rounded-lg text-gray-400 hover:text-gray-100 hover:bg-gray-800 transition"
          aria-label="Toggle sidebar"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        <div className="flex items-center gap-2">
          <span className="text-xl select-none">🤖</span>
          <span className="font-bold text-white text-lg tracking-tight">WoxBot</span>
          <span className="text-xs text-gray-500 hidden sm:block">· Woxsen University AI</span>
        </div>
      </div>

      <button
        onClick={toggleDark}
        className="p-2 rounded-lg text-gray-400 hover:text-gray-100 hover:bg-gray-800 transition"
        aria-label="Toggle dark mode"
      >
        {dark ? (
          /* Sun icon — click to switch to light */
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707M17.657 17.657l-.707-.707M6.343 6.343l-.707-.707M12 5a7 7 0 000 14 7 7 0 000-14z" />
          </svg>
        ) : (
          /* Moon icon — click to switch to dark */
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
          </svg>
        )}
      </button>
    </header>
  );
}
