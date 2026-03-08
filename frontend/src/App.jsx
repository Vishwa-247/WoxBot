import { useCallback, useState } from "react";
import ChatWindow from "./components/ChatWindow";
import DocumentLibrary from "./components/DocumentLibrary";
import DocumentSelector from "./components/DocumentSelector";
import { loadSavedModel } from "./components/ModelSelector";
import Navbar from "./components/Navbar";
import Sidebar from "./components/Sidebar";
import SourcePanel from "./components/SourcePanel";
import { useChat } from "./hooks/useChat";
import { useUpload } from "./hooks/useUpload";

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [showSources, setShowSources] = useState(true);
  const [libraryOpen, setLibraryOpen] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [libRefresh, setLibRefresh] = useState(0);
  const [selectedModel, setSelectedModel] = useState(loadSavedModel);
  const {
    messages,
    isStreaming,
    sessionId,
    chatHistory,
    selectedDocIds,
    setSelectedDocIds,
    sendMessage,
    stopStream,
    clearChat,
    loadSession,
    deleteSession,
  } = useChat();

  const {
    uploading,
    progress,
    result,
    error,
    upload,
    reset: resetUpload,
  } = useUpload(() => {
    setLibRefresh((n) => n + 1);
  });

  // Find the most recent bot message that has sources
  const lastBotWithSources = [...messages]
    .reverse()
    .find((m) => m.role === "bot" && m.sources?.length > 0);
  const activeSources = showSources ? (lastBotWithSources?.sources ?? []) : [];

  const handleSend = useCallback(
    (query) => {
      setShowSources(true);
      sendMessage(query, selectedModel?.provider, selectedModel?.id);
    },
    [sendMessage, selectedModel],
  );

  const handleAttach = useCallback(
    (file) => {
      upload(file);
    },
    [upload],
  );

  // Global drag & drop handlers
  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.types.includes("Files")) {
      setDragOver(true);
    }
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    // Only close overlay if leaving the window
    if (e.currentTarget === e.target) {
      setDragOver(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file && file.type === "application/pdf") {
      upload(file);
    }
  };

  return (
    <div
      className="h-screen flex flex-col bg-white dark:bg-[#111113] text-zinc-900 dark:text-zinc-100 overflow-hidden relative"
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {/* Global drag overlay */}
      {dragOver && (
        <div
          className="fixed inset-0 z-[100] bg-zinc-900/60 dark:bg-black/70 flex items-center justify-center backdrop-blur-sm"
          onDragOver={(e) => e.preventDefault()}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <div className="bg-white dark:bg-zinc-800 rounded-2xl p-10 text-center border-2 border-dashed border-zinc-400 dark:border-zinc-500 shadow-2xl">
            <svg
              className="w-12 h-12 mx-auto text-zinc-400 dark:text-zinc-500 mb-4"
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
            <p className="text-lg font-medium text-zinc-700 dark:text-zinc-200">
              Drop PDF to upload
            </p>
            <p className="text-sm text-zinc-400 dark:text-zinc-500 mt-1">
              Release to add to knowledge base
            </p>
          </div>
        </div>
      )}

      <Navbar
        onSidebarToggle={() => setSidebarOpen((o) => !o)}
        onLibraryToggle={() => setLibraryOpen((o) => !o)}
        libraryOpen={libraryOpen}
        selectedModel={selectedModel}
        onModelChange={setSelectedModel}
      />

      {/* Document Library dropdown */}
      <DocumentLibrary
        open={libraryOpen}
        onClose={() => setLibraryOpen(false)}
        refreshTrigger={libRefresh}
      />

      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar — chat history + doc selector */}
        <Sidebar
          open={sidebarOpen}
          onToggle={() => setSidebarOpen((o) => !o)}
          onNewChat={clearChat}
          chatHistory={chatHistory}
          activeSessionId={sessionId}
          onLoadSession={loadSession}
          onDeleteSession={deleteSession}
        >
          <DocumentSelector
            selectedDocIds={selectedDocIds}
            onSelectionChange={setSelectedDocIds}
            refreshTrigger={libRefresh}
          />
        </Sidebar>

        {/* Main chat area */}
        <main className="flex flex-1 overflow-hidden">
          <ChatWindow
            messages={messages}
            isStreaming={isStreaming}
            onSend={handleSend}
            onStop={stopStream}
            onAttach={handleAttach}
            uploading={uploading}
            uploadProgress={progress}
            uploadResult={result}
            uploadError={error}
            onUploadDismiss={resetUpload}
          />

          {/* Right source panel */}
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
