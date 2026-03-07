import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import LoadingDots from './LoadingDots';

const mdComponents = {
  code({ inline, className, children, ...props }) {
    return inline ? (
      <code
        className="bg-gray-700 px-1.5 py-0.5 rounded text-xs font-mono text-indigo-300"
        {...props}
      >
        {children}
      </code>
    ) : (
      <pre className="bg-gray-900 rounded-lg p-3 overflow-x-auto my-2 text-xs">
        <code className="font-mono text-gray-200" {...props}>
          {children}
        </code>
      </pre>
    );
  },
  p({ children }) {
    return <p className="mb-2 last:mb-0">{children}</p>;
  },
  ul({ children }) {
    return <ul className="list-disc list-inside mb-2 space-y-0.5">{children}</ul>;
  },
  ol({ children }) {
    return <ol className="list-decimal list-inside mb-2 space-y-0.5">{children}</ol>;
  },
  a({ href, children }) {
    return (
      <a
        href={href}
        className="text-indigo-400 hover:text-indigo-300 underline"
        target="_blank"
        rel="noopener noreferrer"
      >
        {children}
      </a>
    );
  },
  strong({ children }) {
    return <strong className="font-semibold text-white">{children}</strong>;
  },
  blockquote({ children }) {
    return (
      <blockquote className="border-l-2 border-indigo-500 pl-3 my-2 text-gray-400 italic">
        {children}
      </blockquote>
    );
  },
};

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="flex justify-end mb-4 px-2">
        <div className="max-w-[75%] bg-indigo-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start mb-4 px-2">
      <div className="flex gap-2 max-w-[82%]">
        <div className="w-8 h-8 rounded-full bg-indigo-700 flex items-center justify-center text-sm shrink-0 mt-0.5 select-none">
          🤖
        </div>
        <div className="bg-gray-800 rounded-2xl rounded-tl-sm px-4 py-3 text-sm leading-relaxed text-gray-100 min-w-0">
          {message.streaming && !message.content ? (
            <LoadingDots />
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
              {message.content}
            </ReactMarkdown>
          )}
        </div>
      </div>
    </div>
  );
}
