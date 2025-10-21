"use client";

import { MarkdownRenderer } from "@/components/MarkdownRenderer";
import { Bot, User } from "lucide-react";

interface ChatMessageProps {
  content: string;
  isUser: boolean;
  timestamp?: Date;
}

export function ChatMessage({ content, isUser, timestamp }: ChatMessageProps) {
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 shadow-sm ${
          isUser ? "bg-black text-white ml-12" : "bg-gray-100 text-gray-900 mr-12"
        }`}
      >
        <div className="flex items-start space-x-3">
          {!isUser && (
            <div className="flex-shrink-0 w-8 h-8 bg-black rounded-full flex items-center justify-center">
              <Bot className="h-4 w-4 text-white" />
            </div>
          )}
          <div className="flex-1 min-w-0">
            {isUser ? (
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{content}</p>
            ) : (
              <MarkdownRenderer content={content} />
            )}
            {timestamp && (
              <p
                className={`text-xs mt-2 ${isUser ? "text-gray-300" : "text-gray-500"}`}
              >
                {timestamp.toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </p>
            )}
          </div>
          {isUser && (
            <div className="flex-shrink-0 w-8 h-8 bg-white rounded-full flex items-center justify-center">
              <User className="h-4 w-4 text-black" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
