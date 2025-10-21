"use client";

import { WorkflowState } from "@/types";

interface LiveStateDisplayProps {
  state: WorkflowState;
}

export function LiveStateDisplay({ state }: LiveStateDisplayProps) {
  const truncateText = (text: string, maxLength: number = 200): string => {
    return text.length > maxLength ? text.substring(0, maxLength) + "..." : text;
  };

  const displayListWithPreview = (title: string, items: string[], icon: string) => (
    <div>
      <h4 className="font-semibold text-gray-900 mb-2">{title}:</h4>
      <div className="space-y-1">
        {items.slice(0, 5).map((item, index) => (
          <code key={index} className="block text-sm bg-gray-100 px-2 py-1 rounded">
            {icon} {item}
          </code>
        ))}
        {items.length > 5 && (
          <code className="block text-sm text-gray-500">
            ... and {items.length - 5} more
          </code>
        )}
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      <h3 className="text-xl font-bold text-gray-900">🔍 Live Workflow State</h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Basic Info */}
        <div className="space-y-4">
          <div>
            <h4 className="font-semibold text-gray-900 mb-2">Current Step:</h4>
            <code className="block bg-gray-100 px-3 py-2 rounded text-sm">
              {state.current_step}
            </code>
          </div>

          <div>
            <h4 className="font-semibold text-gray-900 mb-2">Retries Left:</h4>
            <code className="block bg-gray-100 px-3 py-2 rounded text-sm">
              {state.retries_left}
            </code>
          </div>

          {state.is_metadata_query !== undefined && (
            <div>
              <h4 className="font-semibold text-gray-900 mb-2">Query Type:</h4>
              <code className="block bg-gray-100 px-3 py-2 rounded text-sm">
                {state.is_metadata_query ? "📊 Metadata Query" : "🔍 Data Query"}
              </code>
            </div>
          )}
        </div>

        {/* Resources */}
        <div className="space-y-4">
          {state.dialect && (
            <div>
              <h4 className="font-semibold text-gray-900 mb-2">SQL Dialect:</h4>
              <code className="block bg-gray-100 px-3 py-2 rounded text-sm">
                {state.dialect}
              </code>
            </div>
          )}

          {state.relevant_databases && state.relevant_databases.length > 0 && (
            <div>
              <h4 className="font-semibold text-gray-900 mb-2">
                Identified Databases:
              </h4>
              <div className="space-y-1">
                {state.relevant_databases.map((db, index) => (
                  <code
                    key={index}
                    className="block text-sm bg-gray-100 px-2 py-1 rounded"
                  >
                    🗄️ {db}
                  </code>
                ))}
              </div>
            </div>
          )}

          {state.relevant_tables &&
            state.relevant_tables.length > 0 &&
            displayListWithPreview("Identified Tables", state.relevant_tables, "📋")}

          {state.relevant_columns &&
            state.relevant_columns.length > 0 &&
            displayListWithPreview("Identified Columns", state.relevant_columns, "🔍")}
        </div>
      </div>

      {/* Query Info */}
      <div className="space-y-4">
        {state.query_plan && (
          <div>
            <h4 className="font-semibold text-gray-900 mb-2">Query Plan:</h4>
            <code className="block bg-gray-100 px-3 py-2 rounded text-sm whitespace-pre-wrap">
              {truncateText(state.query_plan)}
            </code>
          </div>
        )}

        {state.generated_query && (
          <div>
            <h4 className="font-semibold text-gray-900 mb-2">Generated Query:</h4>
            <code className="block bg-gray-100 px-3 py-2 rounded text-sm whitespace-pre-wrap">
              {truncateText(state.generated_query.query)}
            </code>
          </div>
        )}

        {state.is_query_valid !== undefined && (
          <div>
            <h4 className="font-semibold text-gray-900 mb-2">Validation Status:</h4>
            <code
              className={`block px-3 py-2 rounded text-sm ${
                state.is_query_valid
                  ? "bg-success-100 text-success-800"
                  : "bg-error-100 text-error-800"
              }`}
            >
              {state.is_query_valid ? "✅ Valid" : "❌ Invalid"}
            </code>
          </div>
        )}
      </div>
    </div>
  );
}
