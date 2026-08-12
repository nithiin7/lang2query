"use client";
import { ChatContainer, Sidebar } from "@/components/chat";
import { Header } from "@/components/Header";
import { getWebSocketService } from "@/lib/websocket";
import { useEffect, useState } from "react";

/**
 * The "/chat" page: owns chat session/history state and wires the Sidebar
 * and ChatContainer together. History is persisted to localStorage.
 */
export default function ChatPage() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mode, setMode] = useState<"agentic" | "ask">("ask");
  const [chatHistory, setChatHistory] = useState<{ id: string; title: string }[]>([]);
  // Lazily generate a unique session id for the initial chat.
  const [chatSessionId, setChatSessionId] = useState<string>(() =>
    Date.now().toString(),
  );

  /** Add a new chat to the sidebar history, keyed by its first user query. */
  const handleNewUserQuery = (id: string, title: string) => {
    setChatHistory((prev) => [{ id, title }, ...prev]);
  };

  /** Cancel any in-flight workflow and start a fresh chat session. */
  const handleNewChat = () => {
    try {
      getWebSocketService()?.cancel?.();
    } catch {}
    setChatSessionId(Date.now().toString());
  };

  /** Remove a chat from history and its persisted messages; start a new session if it was active. */
  const handleDeleteChat = (id: string) => {
    setChatHistory((prev) => prev.filter((c) => c.id !== id));
    try {
      localStorage.removeItem(`t2q_chat_${id}`);
    } catch {}
    // If deleting the current chat, start a new empty session
    if (id === chatSessionId) {
      setChatSessionId(Date.now().toString());
    }
  };

  /** Switch the active chat session to id. */
  const handleSelectChat = (id: string) => {
    if (!id || id === chatSessionId) return;
    setChatSessionId(id);
  };

  // Hydrate from localStorage on mount
  useEffect(() => {
    try {
      const savedHistory = localStorage.getItem("t2q_chat_history");
      const savedCurrentId = localStorage.getItem("t2q_current_chat_id");
      if (savedHistory) {
        const parsed = JSON.parse(savedHistory) as { id: string; title: string }[];
        if (Array.isArray(parsed)) setChatHistory(parsed);
      }
      if (savedCurrentId) setChatSessionId(savedCurrentId);
    } catch {}
  }, []);

  // Persist history and current chat id
  useEffect(() => {
    try {
      localStorage.setItem("t2q_chat_history", JSON.stringify(chatHistory));
      localStorage.setItem("t2q_current_chat_id", chatSessionId);
    } catch {}
  }, [chatHistory, chatSessionId]);

  // Cancel on page unload/navigation
  useEffect(() => {
    /** Cancel any in-flight workflow when the page is unloaded or navigated away from. */
    const handler = () => {
      try {
        getWebSocketService()?.cancel?.();
      } catch {}
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, []);

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          isCollapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
          chatHistory={chatHistory}
          onNewChat={handleNewChat}
          currentChatId={chatSessionId}
          onDeleteChat={handleDeleteChat}
          onSelectChat={handleSelectChat}
        />
        <main className="flex-1 overflow-hidden">
          <ChatContainer
            key={chatSessionId}
            chatId={chatSessionId}
            mode={mode}
            onModeChange={setMode}
            onNewUserQuery={handleNewUserQuery}
          />
        </main>
      </div>
    </div>
  );
}
