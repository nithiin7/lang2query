"use client";
import { ChatContainer } from "@/components/ChatContainer";
import { Header } from "@/components/Header";
import { Sidebar } from "@/components/Sidebar";
import { getWebSocketService } from "@/lib/websocket";
import { useEffect, useState } from "react";

export default function Home() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mode, setMode] = useState<"agentic" | "ask">("ask");
  const [chatHistory, setChatHistory] = useState<{ id: string; title: string }[]>([]);
  const [chatSessionId, setChatSessionId] = useState<string>(() =>
    Date.now().toString(),
  );

  const handleNewUserQuery = (id: string, title: string) => {
    setChatHistory((prev) => [{ id, title }, ...prev]);
  };

  const handleNewChat = () => {
    try {
      getWebSocketService()?.cancel?.();
    } catch {}
    setChatSessionId(Date.now().toString());
  };

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
