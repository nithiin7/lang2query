"use client";

import { useSystemStatus } from "@/hooks/useSystemStatus";
import { Database } from "lucide-react";

export function Header() {
  const { isOnline, isChecking } = useSystemStatus(60000);
  const dotColor = isChecking
    ? "bg-yellow-500"
    : isOnline
      ? "bg-green-500"
      : "bg-red-500";
  const label = isChecking
    ? "Checking..."
    : isOnline
      ? "System Online"
      : "System Offline";
  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-black rounded-lg">
            <Database className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 tracking-tight">
              Text2Query
            </h1>
            <p className="text-sm text-gray-500">AI-powered natural language to SQL</p>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div className="h-8 w-8 bg-gray-100 rounded-full flex items-center justify-center">
            <div
              className={`h-2 w-2 ${dotColor} rounded-full ${isChecking ? "animate-pulse" : ""}`}
            ></div>
          </div>
          <span className="text-sm text-gray-600">{label}</span>
        </div>
      </div>
    </header>
  );
}
