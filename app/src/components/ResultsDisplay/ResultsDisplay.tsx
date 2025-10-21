"use client";

import { QueryResponse } from "@/types";

interface ResultsDisplayProps {
  results: QueryResponse;
}

export function ResultsDisplay({ results }: ResultsDisplayProps) {
  if (results.type === "error") {
    return (
      <div className="card border-error-200 bg-error-50">
        <h3 className="text-xl font-bold text-error-800 mb-4">❌ Error</h3>
        <p className="text-error-700">{results.message}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="card">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="text-center">
            <div className="text-2xl mb-1">
              {results.status === "Success" ? "🟢" : "🔴"}
            </div>
            <div className="font-semibold text-gray-900">Status</div>
            <div className="text-sm text-gray-600">{results.status}</div>
          </div>
          <div className="text-center">
            <div className="text-2xl mb-1">⏱️</div>
            <div className="font-semibold text-gray-900">Execution Time</div>
            <div className="text-sm text-gray-600">{results.execution_time}</div>
          </div>
          <div className="text-center">
            <div className="text-2xl mb-1">🔍</div>
            <div className="font-semibold text-gray-900">Query Type</div>
            <div className="text-sm text-gray-600">
              {results.is_metadata_query ? "Metadata Query" : "Data Query"}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
