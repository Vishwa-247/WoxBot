import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import LoadingDots from "./LoadingDots";

function cleanContent(text) {
  return text.replace(/\[Source:[^\]]*\]/g, "").trim();
}

function normalizeMarkdown(text) {
  if (!text) return "";

  let formatted = cleanContent(text).replace(/\r\n/g, "\n");

  // Convert visual separators from the model into real markdown rules.
  formatted = formatted.replace(/[─━]{8,}/g, "\n\n---\n\n");

  // Headings often arrive glued to the previous sentence or to the next heading.
  formatted = formatted.replace(/([^\n])(?=#{2,4}\s)/g, "$1\n\n");
  formatted = formatted.replace(/(#{2,4}\s[^\n#]+)(?=#{2,4}\s)/g, "$1\n\n");

  // Numbered lists glued together: "1. foo2. bar3. baz" → separate lines.
  formatted = formatted.replace(/(\.)(\s*)(\d+\.\s)/g, "$1\n$3");

  // List markers also arrive inline. Promote them to real markdown lists.
  formatted = formatted.replace(/([^\n])(?=\*\s)/g, "$1\n");
  formatted = formatted.replace(/([^\n])(?=-\s(?=\*\*|[A-Z0-9]))/g, "$1\n");

  // Normalize bullet style so the UI is consistent.
  formatted = formatted.replace(/^\*\s/gm, "- ");

  // Ensure a blank line before lists for markdown parsing.
  formatted = formatted.replace(/([^\n])\n([-*]\s)/g, "$1\n\n$2");
  formatted = formatted.replace(/([^\n])\n(\d+\.\s)/g, "$1\n\n$2");

  // Ensure a blank line after headings for markdown parsing.
  formatted = formatted.replace(/^(#{2,4}\s.+)$/gm, "\n$1\n");

  // Ensure tables and rules have breathing room around them.
  formatted = formatted.replace(/([^\n])(\n\|)/g, "$1\n$2");
  formatted = formatted.replace(/(\|.*\|)(\n)(?!\||\n)/g, "$1\n\n");
  formatted = formatted.replace(/^---$/gm, "\n---\n");

  // **bold** glued to next word/section — ensure spacing.
  formatted = formatted.replace(/\*\*([^*]+)\*\*(?=[A-Z])/g, "**$1**\n\n");

  // Collapse excessive whitespace while preserving intentional spacing.
  formatted = formatted.replace(/\n{3,}/g, "\n\n");

  return formatted.trim();
}

// ── Rich Markdown Components ────────────────────────────────────────
const mdComponents = {
  code({ inline, className, children, ...props }) {
    return inline ? (
      <code
        className="bg-zinc-100 dark:bg-zinc-800 px-1 py-0.5 rounded text-[13px] font-mono"
        {...props}
      >
        {children}
      </code>
    ) : (
      <pre className="bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg p-4 overflow-x-auto my-3 text-[13px]">
        <code className="font-mono" {...props}>
          {children}
        </code>
      </pre>
    );
  },
  p({ children }) {
    return <p className="mb-3 leading-relaxed text-[15px]">{children}</p>;
  },
  ul({ children }) {
    return (
      <ul className="list-disc list-outside ml-5 mb-3 space-y-1 text-[15px]">
        {children}
      </ul>
    );
  },
  ol({ children }) {
    return (
      <ol className="list-decimal list-outside ml-5 mb-3 space-y-1 text-[15px]">
        {children}
      </ol>
    );
  },
  li({ children }) {
    return <li className="pl-0.5">{children}</li>;
  },
  a({ href, children }) {
    return (
      <a
        href={href}
        className="text-blue-600 dark:text-blue-400 underline underline-offset-2"
        target="_blank"
        rel="noopener noreferrer"
      >
        {children}
      </a>
    );
  },
  strong({ children }) {
    return <strong className="font-semibold">{children}</strong>;
  },
  em({ children }) {
    return (
      <em className="italic text-zinc-600 dark:text-zinc-400">{children}</em>
    );
  },
  blockquote({ children }) {
    return (
      <blockquote className="border-l-2 border-zinc-300 dark:border-zinc-600 pl-4 my-3 text-zinc-600 dark:text-zinc-400 italic text-[15px]">
        {children}
      </blockquote>
    );
  },
  h1({ children }) {
    return <h1 className="text-xl font-semibold mb-3 mt-5">{children}</h1>;
  },
  h2({ children }) {
    return (
      <h2 className="text-lg font-semibold mb-2 mt-5 pb-1.5 border-b border-zinc-200 dark:border-zinc-700/60">
        {children}
      </h2>
    );
  },
  h3({ children }) {
    return <h3 className="text-base font-medium mb-2 mt-4">{children}</h3>;
  },
  h4({ children }) {
    return (
      <h4 className="text-[15px] font-medium mb-1.5 mt-3 text-zinc-700 dark:text-zinc-300">
        {children}
      </h4>
    );
  },
  hr() {
    return <hr className="my-4 border-zinc-200 dark:border-zinc-700/60" />;
  },
  // ── Table components ──────────────────────────────────────────────
  table({ children }) {
    return (
      <div className="my-3 overflow-x-auto rounded-lg border border-zinc-200 dark:border-zinc-700/60">
        <table className="w-full text-[13px] border-collapse">{children}</table>
      </div>
    );
  },
  thead({ children }) {
    return (
      <thead className="bg-zinc-50 dark:bg-zinc-800/80 text-zinc-600 dark:text-zinc-300 text-left">
        {children}
      </thead>
    );
  },
  tbody({ children }) {
    return (
      <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
        {children}
      </tbody>
    );
  },
  tr({ children }) {
    return (
      <tr className="hover:bg-zinc-50/50 dark:hover:bg-zinc-800/30 transition-colors">
        {children}
      </tr>
    );
  },
  th({ children }) {
    return (
      <th className="px-3 py-2 font-semibold text-[12px] uppercase tracking-wide whitespace-nowrap">
        {children}
      </th>
    );
  },
  td({ children }) {
    return (
      <td className="px-3 py-2 text-zinc-700 dark:text-zinc-300 whitespace-normal">
        {children}
      </td>
    );
  },
};

// ── Source Circles ──────────────────────────────────────────────────
// Each unique source file = one circle: P1, P2, P3 ...
// Click a circle to see tooltip with filename + page + preview text.

function SourceCircles({ sources }) {
  const [activeIdx, setActiveIdx] = useState(null);

  // Dedupe by filename
  const unique = [];
  const seen = new Set();
  sources.forEach((src) => {
    if (!seen.has(src.filename)) {
      seen.add(src.filename);
      unique.push(src);
    }
  });

  if (unique.length === 0) return null;

  return (
    <div className="mt-2 flex items-center gap-1.5">
      {unique.map((src, i) => (
        <div key={i} className="relative">
          <button
            onClick={() => setActiveIdx(activeIdx === i ? null : i)}
            className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-[11px] font-semibold transition-all cursor-pointer select-none
              ${
                activeIdx === i
                  ? "bg-zinc-800 dark:bg-zinc-200 text-white dark:text-zinc-900 ring-2 ring-zinc-400 dark:ring-zinc-500"
                  : "bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400 border border-zinc-200 dark:border-zinc-700 hover:bg-zinc-200 dark:hover:bg-zinc-700"
              }`}
            title={src.filename}
          >
            P{i + 1}
          </button>

          {/* Tooltip popover on click */}
          {activeIdx === i && (
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-2.5 bg-zinc-900 dark:bg-black text-zinc-100 text-[11px] rounded-lg shadow-xl z-50 border border-zinc-700">
              <div className="font-medium mb-1 flex items-center justify-between">
                <span>
                  {src.filename} — Page {src.page}
                </span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setActiveIdx(null);
                  }}
                  className="text-zinc-500 hover:text-zinc-300 text-xs ml-2"
                >
                  ✕
                </button>
              </div>
              {src.section_title && (
                <div className="text-zinc-400 text-[10px] mb-1 italic">
                  {src.section_title}
                </div>
              )}
              <div className="text-zinc-400 line-clamp-4 leading-relaxed">
                {src.chunk_text || src.text || ""}
              </div>
              {/* Small arrow */}
              <div className="absolute top-full left-1/2 -translate-x-1/2 w-0 h-0 border-l-[5px] border-l-transparent border-r-[5px] border-r-transparent border-t-[5px] border-t-zinc-900 dark:border-t-black" />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ── Main Bubble ─────────────────────────────────────────────────────

export default function MessageBubble({ message, onFollowupClick }) {
  const isUser = message.role === "user";
  const formattedContent = normalizeMarkdown(message.content);

  const hasSources =
    !isUser &&
    !message.streaming &&
    message.sources &&
    message.sources.length > 0;

  const hasFollowups =
    !isUser &&
    !message.streaming &&
    message.followups &&
    message.followups.length > 0;

  if (isUser) {
    return (
      <div className="flex justify-end mb-3">
        <div className="max-w-[80%] bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 rounded-2xl rounded-br-md px-4 py-2.5 text-[15px] leading-relaxed whitespace-pre-wrap">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3 mb-3">
      <div className="w-7 h-7 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-sm shrink-0 mt-0.5 select-none">
        🤖
      </div>
      <div className="flex-1 min-w-0 text-zinc-800 dark:text-zinc-200">
        {message.streaming && !message.content ? (
          <LoadingDots />
        ) : (
          <div className="bot-bubble max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={mdComponents}
            >
              {formattedContent}
            </ReactMarkdown>
          </div>
        )}
        {hasSources && <SourceCircles sources={message.sources} />}
        {hasFollowups && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {message.followups.map((q, i) => (
              <button
                key={i}
                onClick={() => onFollowupClick?.(q)}
                className="text-xs bg-zinc-50 dark:bg-zinc-800/60 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-600 dark:text-zinc-400 px-3 py-1.5 rounded-full border border-zinc-200 dark:border-zinc-700 transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
