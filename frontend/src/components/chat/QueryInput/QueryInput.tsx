"use client";

import { Loader2, Send, Square } from "lucide-react";
import { useEffect, useRef, useState } from "react";

interface QueryInputProps {
  onSubmit: (query: string) => void;
  onStop?: () => void;
  isLoading: boolean;
  placeholder?: string;
}

export function QueryInput({
  onSubmit,
  onStop,
  isLoading,
  placeholder = "Ask me anything about your data...",
}: QueryInputProps) {
  const [query, setQuery] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !isLoading) {
      onSubmit(query.trim());
      setQuery("");
      adjustHeight();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const adjustHeight = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        120,
      )}px`;
    }
  };

  useEffect(() => {
    adjustHeight();
  }, [query]);

  return (
    <div className="border-t border-gray-200 bg-white p-4">
      <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
        <div className="relative">
          <textarea
            ref={textareaRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={isLoading}
            rows={1}
            className="w-full resize-none rounded-xl border border-gray-300 bg-gray-50 px-4 py-3 pr-12 text-sm placeholder:text-gray-500 focus:border-black focus:bg-white focus:outline-none focus:ring-1 focus:ring-black transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ minHeight: "48px", maxHeight: "120px" }}
          />

          <button
            type={isLoading && onStop ? "button" : "submit"}
            onClick={isLoading && onStop ? onStop : undefined}
            disabled={(!query.trim() && !isLoading) || (isLoading && !onStop)}
            className="absolute right-2 top-2 p-2 bg-black text-white rounded-lg hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 hover:scale-105 active:scale-95"
          >
            {isLoading && onStop ? (
              <Square className="h-4 w-4" />
            ) : isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </button>
        </div>

        <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
          <span>
            {isLoading && onStop
              ? "Click stop button to cancel"
              : "Press Enter to send, Shift+Enter for new line"}
          </span>
          <span className={`${query.length > 1000 ? "text-red-500" : ""}`}>
            {query.length}/1000
          </span>
        </div>
      </form>
    </div>
  );
}
