import { useEffect, useRef, useState } from "react";

const MODELS = [
  // ── Groq (fast inference) ──
  {
    id: "llama-3.1-8b-instant",
    label: "Llama 3.1 8B",
    provider: "groq",
    badge: "Fast",
  },
  {
    id: "llama-3.3-70b-versatile",
    label: "Llama 3.3 70B",
    provider: "groq",
    badge: "Groq",
  },
  {
    id: "mixtral-8x7b-32768",
    label: "Mixtral 8x7B",
    provider: "groq",
    badge: "Groq",
  },
  {
    id: "gemma2-9b-it",
    label: "Gemma 2 9B",
    provider: "groq",
    badge: "Groq",
  },
  // ── OpenRouter (free tier) ──
  {
    id: "google/gemini-2.0-flash-exp:free",
    label: "Gemini 2.0 Flash",
    provider: "openrouter",
    badge: "Free",
  },
  {
    id: "deepseek/deepseek-chat-v3-0324:free",
    label: "DeepSeek V3",
    provider: "openrouter",
    badge: "Free",
  },
  {
    id: "meta-llama/llama-3.3-70b-instruct:free",
    label: "Llama 3.3 70B",
    provider: "openrouter",
    badge: "Free",
  },
  {
    id: "qwen/qwen3-235b-a22b:free",
    label: "Qwen3 235B",
    provider: "openrouter",
    badge: "Free",
  },
];

const STORAGE_KEY = "woxbot-model";

function loadSavedModel() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (saved && saved.id) return saved;
  } catch {}
  return MODELS[0];
}

export default function ModelSelector({ value, onChange }) {
  const [open, setOpen] = useState(false);
  const panelRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    const handleClick = (e) => {
      if (panelRef.current && !panelRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  const selected = MODELS.find((m) => m.id === value?.id) || MODELS[0];

  return (
    <div ref={panelRef} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className={`flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium transition-colors ${
          open
            ? "bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100"
            : "text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 hover:text-zinc-900 dark:hover:text-zinc-100"
        }`}
        title="Select AI model"
      >
        <svg
          className="w-3.5 h-3.5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5"
          />
        </svg>
        <span className="hidden sm:inline max-w-[100px] truncate">
          {selected.label.split(" ").slice(0, 2).join(" ")}
        </span>
        <svg
          className="w-3 h-3 opacity-50"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 w-60 bg-white dark:bg-[#1c1c1f] border border-zinc-200 dark:border-zinc-700 rounded-xl shadow-lg z-50 py-1 overflow-hidden">
          <div className="px-3 py-2 border-b border-zinc-100 dark:border-zinc-800">
            <p className="text-[10px] font-medium text-zinc-400 dark:text-zinc-500 uppercase tracking-widest">
              Select Model
            </p>
          </div>
          {MODELS.map((model) => (
            <button
              key={model.id}
              onClick={() => {
                onChange(model);
                localStorage.setItem(STORAGE_KEY, JSON.stringify(model));
                setOpen(false);
              }}
              className={`w-full flex items-center gap-2 px-3 py-2 text-left text-xs transition-colors ${
                selected.id === model.id
                  ? "bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100"
                  : "text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-800/60"
              }`}
            >
              <span className="flex-1 truncate">{model.label}</span>
              <span
                className={`px-1.5 py-0.5 rounded text-[9px] font-medium ${
                  model.badge === "Free"
                    ? "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400"
                    : model.badge === "Latest"
                      ? "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400"
                      : model.badge === "Pro"
                        ? "bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400"
                        : "bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400"
                }`}
              >
                {model.badge}
              </span>
              {selected.id === model.id && (
                <svg
                  className="w-3.5 h-3.5 text-zinc-900 dark:text-zinc-100 shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export { loadSavedModel, MODELS };
