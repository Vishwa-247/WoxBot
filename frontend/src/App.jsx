import { useState, useCallback } from 'react';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';
import SourcePanel from './components/SourcePanel';
import { useChat } from './hooks/useChat';

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showSources, setShowSources] = useState(true);
  const { messages, isStreaming, sendMessage, stopStream, clearChat } = useChat();

  // Find the most recent bot message that has sources
  const lastBotWithSources = [...messages]
    .reverse()
    .find((m) => m.role === 'bot' && m.sources?.length > 0);
  const activeSources = showSources ? (lastBotWithSources?.sources ?? []) : [];

  const handleSend = useCallback(
    (query) => {
      setShowSources(true); // re-open sources panel when a new message is sent
      sendMessage(query);
    },
    [sendMessage]
  );

  return (
    <div className="h-screen flex flex-col bg-gray-950 text-gray-100 overflow-hidden">
      <Navbar onSidebarToggle={() => setSidebarOpen((o) => !o)} />

      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar — collapsible on mobile, always visible on lg+ */}
        <Sidebar
          open={sidebarOpen}
          onNewChat={() => { clearChat(); setSidebarOpen(false); }}
          onClose={() => setSidebarOpen(false)}
        />

        {/* Main chat area */}
        <main className="flex flex-1 overflow-hidden">
          <ChatWindow
            messages={messages}
            isStreaming={isStreaming}
            onSend={handleSend}
            onStop={stopStream}
          />

          {/* Right source panel — visible when latest bot message has sources */}
          {activeSources.length > 0 && (
            <SourcePanel
              sources={activeSources}
              onClose={() => setShowSources(false)}
            />
          )}
        </main>
      </div>
    </div>
  );
}
