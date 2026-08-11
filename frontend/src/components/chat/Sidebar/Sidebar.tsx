"use client";

import { ChevronLeft, MessageCircle, Plus, Trash2 } from "lucide-react";

interface SidebarProps {
  isCollapsed: boolean;
  onToggle: () => void;
  chatHistory: { id: string; title: string }[];
  onNewChat?: () => void;
  onDeleteChat?: (id: string) => void;
  currentChatId?: string;
  onSelectChat?: (id: string) => void;
}

export function Sidebar({
  isCollapsed,
  onToggle,
  chatHistory,
  onNewChat,
  onDeleteChat,
  currentChatId,
  onSelectChat,
}: SidebarProps) {
  return (
    <div
      className={`bg-white border-r border-gray-200 transition-all duration-300 ease-in-out ${
        isCollapsed ? "w-16" : "w-80"
      }`}
    >
      <div className="p-4 border-b border-gray-200">
        <button
          onClick={onToggle}
          className="flex items-center justify-between w-full p-2 hover:bg-gray-50 rounded-lg transition-colors"
        >
          {!isCollapsed && (
            <div className="flex items-center space-x-3">
              <MessageCircle className="h-5 w-5 text-gray-600" />
              <span className="font-medium text-gray-900">Chats</span>
            </div>
          )}
          {isCollapsed && <MessageCircle className="h-7 w-7 text-gray-600 mx-auto" />}
          {!isCollapsed && <ChevronLeft className="h-4 w-4 text-gray-400" />}
        </button>
      </div>
      {!isCollapsed && (
        <div className="p-4 space-y-3 overflow-y-auto">
          <button
            onClick={onNewChat}
            className="w-full flex items-center justify-center space-x-2 p-2 rounded-md bg-black text-white hover:bg-gray-900 transition-colors"
          >
            <Plus className="h-4 w-4" />
            <span className="text-sm font-medium">New Chat</span>
          </button>
          {chatHistory.length === 0 ? (
            <div className="text-sm text-gray-500 text-center py-8">No chats yet</div>
          ) : (
            chatHistory.map((chat) => (
              <div
                key={chat.id}
                className={`w-full flex items-center justify-between p-2 rounded-md border ${
                  currentChatId === chat.id
                    ? "bg-gray-100 border-gray-300"
                    : "hover:bg-gray-50 border-transparent hover:border-gray-200"
                }`}
                title={chat.title}
              >
                <button
                  className="flex-1 text-left truncate"
                  onClick={() => onSelectChat?.(chat.id)}
                >
                  {chat.title}
                </button>
                <button
                  aria-label="Delete chat"
                  className="ml-2 p-1 rounded hover:bg-red-50 text-red-500 hover:text-red-600"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteChat?.(chat.id);
                  }}
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
