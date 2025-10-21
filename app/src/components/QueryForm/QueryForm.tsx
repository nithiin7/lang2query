"use client";

import { QueryRequest } from "@/types";
import { useState } from "react";

interface QueryFormProps {
  onSubmit: (request: QueryRequest) => void;
  isProcessing: boolean;
}

export function QueryForm({ onSubmit, isProcessing }: QueryFormProps) {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<"agentic" | "ask">("ask");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    onSubmit({ query: query.trim(), mode });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Query Settings</h2>
        <p className="text-gray-600">
          Enter your natural language query to generate SQL
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Processing Mode */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">
            Processing Mode
          </label>
          <div className="space-y-2">
            <label className="flex items-center">
              <input
                type="radio"
                name="mode"
                value="ask"
                checked={mode === "ask"}
                onChange={(e) => setMode(e.target.value as "ask")}
                className="mr-2"
                disabled={isProcessing}
              />
              <span className="text-sm text-gray-700">Ask Mode</span>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                name="mode"
                value="agentic"
                checked={mode === "agentic"}
                onChange={(e) => setMode(e.target.value as "agentic")}
                className="mr-2"
                disabled={isProcessing}
              />
              <span className="text-sm text-gray-700">
                Agentic Mode (shows detailed progress)
              </span>
            </label>
          </div>
        </div>

        {/* Query Input */}
        <div className="space-y-2">
          <label htmlFor="query" className="block text-sm font-medium text-gray-700">
            Natural Language Query
          </label>
          <textarea
            id="query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g., Show me all customers who made payments above $1000"
            className="input h-24 resize-none"
            disabled={isProcessing}
            required
          />
        </div>
      </div>

      {/* Submit Button */}
      <div className="flex justify-center">
        <button
          type="submit"
          disabled={!query.trim() || isProcessing}
          className="btn btn-primary px-8 py-3 text-lg disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isProcessing ? (
            <span className="flex items-center">
              <svg
                className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                ></circle>
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
              Processing...
            </span>
          ) : (
            "🚀 Generate SQL Query"
          )}
        </button>
      </div>
    </form>
  );
}
