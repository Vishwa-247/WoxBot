export default function Sidebar({
  open,
  onToggle,
  onNewChat,
  chatHistory,
  activeSessionId,
  onLoadSession,
  onDeleteSession,
}) {
  const grouped = groupByDate(chatHistory || []);

  return (
    <aside
      className={`
        shrink-0 h-full bg-zinc-50 dark:bg-[#18181b] border-r border-zinc-200 dark:border-zinc-800 flex flex-col
        transition-all duration-200 ease-in-out overflow-hidden
        ${open ? "w-64" : "w-0"}
      `}
    >
      <div className="w-64 h-full flex flex-col">
        {/* Header with close button */}
        <div className="flex items-center justify-between p-3 shrink-0">
          <button
            onClick={onNewChat}
            className="flex-1 flex items-center gap-2 px-3 py-2 text-sm font-medium text-zinc-700 dark:text-zinc-200 bg-white dark:bg-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-700 rounded-lg border border-zinc-200 dark:border-zinc-700 transition-colors"
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
                d="M12 4v16m8-8H4"
              />
            </svg>
            New Chat
          </button>
          <button
            onClick={onToggle}
            className="ml-2 p-1.5 rounded-md text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-colors"
            aria-label="Close sidebar"
            title="Close sidebar"
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
                d="M11 19l-7-7 7-7m8 14l-7-7 7-7"
              />
            </svg>
          </button>
        </div>
        {/* Chat History */}
        <div className="flex-1 overflow-y-auto px-2 pb-4">
          {grouped.length === 0 ? (
            <p className="px-3 py-4 text-xs text-zinc-400 dark:text-zinc-500 text-center">
              No conversations yet
            </p>
          ) : (
            grouped.map((group) => (
              <div key={group.label} className="mb-3">
                <p className="px-3 py-1.5 text-[10px] font-medium text-zinc-400 dark:text-zinc-500 uppercase tracking-widest">
                  {group.label}
                </p>
                {group.sessions.map((session) => (
                  <div
                    key={session.id}
                    className={`group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                      session.id === activeSessionId
                        ? "bg-zinc-200 dark:bg-zinc-700 text-zinc-900 dark:text-zinc-100"
                        : "text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800"
                    }`}
                    onClick={() => {
                      onLoadSession(session.id);
                    }}
                  >
                    <svg
                      className="w-3.5 h-3.5 shrink-0 opacity-50"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={1.5}
                        d="M8 10h.01M12 10h.01M16 10h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                      />
                    </svg>
                    <span className="flex-1 text-xs truncate">
                      {session.title}
                    </span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteSession(session.id);
                      }}
                      className="shrink-0 p-0.5 text-zinc-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition"
                      aria-label="Delete chat"
                    >
                      <svg
                        className="w-3 h-3"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M6 18L18 6M6 6l12 12"
                        />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            ))
          )}
        </div>
      </div>
    </aside>
  );
}

function groupByDate(sessions) {
  const now = new Date();
  const todayStart = new Date(
    now.getFullYear(),
    now.getMonth(),
    now.getDate(),
  ).getTime();
  const yesterdayStart = todayStart - 86400000;
  const weekStart = todayStart - 7 * 86400000;

  const groups = { Today: [], Yesterday: [], "Previous 7 Days": [], Older: [] };

  for (const s of sessions) {
    const t = s.updatedAt || s.createdAt;
    if (t >= todayStart) groups.Today.push(s);
    else if (t >= yesterdayStart) groups.Yesterday.push(s);
    else if (t >= weekStart) groups["Previous 7 Days"].push(s);
    else groups.Older.push(s);
  }

  return Object.entries(groups)
    .filter(([, arr]) => arr.length > 0)
    .map(([label, sessions]) => ({ label, sessions }));
}
