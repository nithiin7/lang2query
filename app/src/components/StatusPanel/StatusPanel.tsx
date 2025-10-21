"use client";

import { WorkflowState } from "@/types";
import {
    Activity,
    CheckCircle,
    ChevronDown,
    ChevronUp,
    Columns,
    Database,
    Table,
} from "lucide-react";

interface StatusPanelProps {
  isExpanded: boolean;
  onToggle: () => void;
  workflowState: WorkflowState | null;
  currentStep: string;
  isProcessing: boolean;
}

export function StatusPanel({
  isExpanded,
  onToggle,
  workflowState,
  currentStep,
  isProcessing,
}: StatusPanelProps) {
  return (
    <div className="border-t border-gray-200 bg-gray-50">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-center py-3 hover:bg-gray-100 transition-colors duration-200"
      >
        <div className="flex items-center space-x-2 text-sm text-gray-600">
          <Activity className="h-4 w-4" />
          <span>Workflow Status</span>
          {isExpanded ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronUp className="h-4 w-4" />
          )}
        </div>
      </button>

      {isExpanded && (
        <div className="px-6 pb-4 animate-in slide-in-from-top-2 duration-300">
          <div className="max-w-4xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              {/* Current Step */}
              <div className="bg-white rounded-lg p-4 border border-gray-200">
                <div className="flex items-center space-x-2 mb-2">
                  <Activity className="h-5 w-5 text-blue-600" />
                  <h3 className="font-semibold text-gray-900">Current Step</h3>
                </div>
                <p className="text-sm text-gray-700">{currentStep || "Idle"}</p>
              </div>

              {/* Processing Status */}
              <div className="bg-white rounded-lg p-4 border border-gray-200">
                <div className="flex items-center space-x-2 mb-2">
                  {isProcessing ? (
                    <div className="h-5 w-5 bg-blue-100 rounded-full flex items-center justify-center">
                      <div className="h-2 w-2 bg-blue-600 rounded-full animate-pulse"></div>
                    </div>
                  ) : (
                    <CheckCircle className="h-5 w-5 text-green-600" />
                  )}
                  <h3 className="font-semibold text-gray-900">Status</h3>
                </div>
                <p className="text-sm text-gray-700">
                  {isProcessing ? "Processing..." : "Ready"}
                </p>
              </div>

              {/* Query Type */}
              <div className="bg-white rounded-lg p-4 border border-gray-200">
                <div className="flex items-center space-x-2 mb-2">
                  <Database className="h-5 w-5 text-purple-600" />
                  <h3 className="font-semibold text-gray-900">Query Type</h3>
                </div>
                <p className="text-sm text-gray-700">
                  {workflowState?.is_metadata_query ? "Metadata Query" : "Data Query"}
                </p>
              </div>
            </div>

            {/* Detailed Status */}
            {workflowState && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Databases */}
                {workflowState.relevant_databases &&
                  workflowState.relevant_databases.length > 0 && (
                    <div className="bg-white rounded-lg p-4 border border-gray-200">
                      <div className="flex items-center space-x-2 mb-3">
                        <Database className="h-5 w-5 text-green-600" />
                        <h3 className="font-semibold text-gray-900">Databases</h3>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {workflowState.relevant_databases.map((db, index) => (
                          <span
                            key={index}
                            className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800"
                          >
                            {db}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                {/* Tables */}
                {workflowState.relevant_tables &&
                  workflowState.relevant_tables.length > 0 && (
                    <div className="bg-white rounded-lg p-4 border border-gray-200">
                      <div className="flex items-center space-x-2 mb-3">
                        <Table className="h-5 w-5 text-blue-600" />
                        <h3 className="font-semibold text-gray-900">Tables</h3>
                      </div>
                      <div className="flex flex-wrap gap-2 max-h-20 overflow-y-auto">
                        {workflowState.relevant_tables
                          .slice(0, 5)
                          .map((table, index) => (
                            <span
                              key={index}
                              className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
                            >
                              {table}
                            </span>
                          ))}
                        {workflowState.relevant_tables.length > 5 && (
                          <span className="text-xs text-gray-500">
                            +{workflowState.relevant_tables.length - 5} more
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                {/* Columns */}
                {workflowState.relevant_columns &&
                  workflowState.relevant_columns.length > 0 && (
                    <div className="bg-white rounded-lg p-4 border border-gray-200 md:col-span-2">
                      <div className="flex items-center space-x-2 mb-3">
                        <Columns className="h-5 w-5 text-purple-600" />
                        <h3 className="font-semibold text-gray-900">Columns</h3>
                      </div>
                      <div className="flex flex-wrap gap-2 max-h-20 overflow-y-auto">
                        {workflowState.relevant_columns
                          .slice(0, 10)
                          .map((column, index) => (
                            <span
                              key={index}
                              className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800"
                            >
                              {column}
                            </span>
                          ))}
                        {workflowState.relevant_columns.length > 10 && (
                          <span className="text-xs text-gray-500">
                            +{workflowState.relevant_columns.length - 10} more
                          </span>
                        )}
                      </div>
                    </div>
                  )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
