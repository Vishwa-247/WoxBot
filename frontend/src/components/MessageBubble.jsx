import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import LoadingDots from "./LoadingDots";

function cleanContent(text) {
  return text.replace(/\[Source:.*\]/g, "").trim();
}

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
    return <h2 className="text-lg font-semibold mb-2 mt-4">{children}</h2>;
  },
  h3({ children }) {
    return <h3 className="text-base font-medium mb-2 mt-3">{children}</h3>;
  },
};

export default function MessageBubble({ message }) {
  const isUser = message.role === "user";
  const [collapsed, setCollapsed] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const hasSources =
    !isUser &&
    !message.streaming &&
    message.sources &&
    message.sources.length > 0;

  // Auto-collapse sources after 5 seconds
  useEffect(() => {
    if (!hasSources) return;
    const timer = setTimeout(() => setCollapsed(true), 5000);
    return () => clearTimeout(timer);
  }, [hasSources]);

  if (isUser) {
    return (
      <div className="flex justify-end mb-3">
        <div className="max-w-[80%] bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 rounded-2xl rounded-br-md px-4 py-2.5 text-[15px] leading-relaxed whitespace-pre-wrap">
          {message.content}
        </div>
      </div>
    );
  }

  const uniqueSources = [];
  if (hasSources) {
    const seen = new Set();
    message.sources.forEach((src) => {
      if (!seen.has(src.filename)) {
        seen.add(src.filename);
        uniqueSources.push(src);
      }
    });
  }

  const renderCitations = () => {
    if (!hasSources || uniqueSources.length === 0) return null;

    // Collapsed state — small circle pill
    if (collapsed && !expanded) {
      return (
        <button
          onClick={() => setExpanded(true)}
          className="mt-1.5 inline-flex items-center justify-center w-7 h-7 rounded-full bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-[10px] font-semibold text-zinc-500 dark:text-zinc-400 hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-all cursor-pointer"
          title={`${uniqueSources.length} source${uniqueSources.length > 1 ? "s" : ""}`}
        >
          {uniqueSources.length}
        </button>
      );
    }

    // Expanded / not-yet-collapsed state
    return (
      <div className="mt-1.5 flex flex-wrap gap-1.5 items-center">
        <span className="text-[11px] font-medium text-zinc-400 dark:text-zinc-500 mr-0.5">
          Sources:
        </span>
        {uniqueSources.map((src, i) => (
          <div key={i} className="group relative">
            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded text-[11px] text-zinc-600 dark:text-zinc-400 cursor-help transition-colors hover:bg-zinc-100 dark:hover:bg-zinc-700">
              <span className="font-medium text-zinc-500 dark:text-zinc-400">
                {i + 1}.
              </span>
              <span className="truncate max-w-[120px]">{src.filename}</span>
              <span className="text-zinc-400 dark:text-zinc-500">
                p.{src.page}
              </span>
            </span>
            <div className="absolute bottom-full left-0 mb-1.5 hidden group-hover:block w-64 p-2.5 bg-zinc-900 dark:bg-black text-zinc-100 text-[11px] rounded-lg shadow-lg z-50">
              <div className="font-medium mb-1">
                {src.filename} — Page {src.page}
              </div>
              <div className="text-zinc-400 line-clamp-3 leading-relaxed">
                {src.text}
              </div>
            </div>
          </div>
        ))}
        {collapsed && (
          <button
            onClick={() => setExpanded(false)}
            className="text-[10px] text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 ml-1 transition-colors"
          >
            ✕
          </button>
        )}
      </div>
    );
  };

  return (
    <div className="flex gap-3 mb-3">
      <div className="w-7 h-7 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-sm shrink-0 mt-0.5 select-none">
        🤖
      </div>
      <div className="flex-1 min-w-0 text-zinc-800 dark:text-zinc-200">
        {message.streaming && !message.content ? (
          <LoadingDots />
        ) : (
          <div className="max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={mdComponents}
            >
              {cleanContent(message.content)}
            </ReactMarkdown>
          </div>
        )}
        {renderCitations()}
      </div>
    </div>
  );
}
