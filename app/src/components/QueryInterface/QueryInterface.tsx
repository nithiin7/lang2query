"use client";

import { LiveStateDisplay } from "@/components/LiveStateDisplay";
import { ProgressIndicator } from "@/components/ProgressIndicator";
import { QueryForm } from "@/components/QueryForm";
import { ResultsDisplay } from "@/components/ResultsDisplay";
import { SelectionReviewCard } from "@/components/SelectionReviewCard";
import { handleApiError, queryApi } from "@/lib/api";
import { getWebSocketService, resetWebSocketService } from "@/lib/websocket";
import {
  HitlRequest,
  QueryRequest,
  QueryResponse,
  WorkflowState,
  WorkflowStep,
} from "@/types";
import { useCallback, useEffect, useState } from "react";

const WORKFLOW_STEPS: WorkflowStep[] = [
  { name: "Router", description: "Analyzing query type", emoji: "🎯" },
  {
    name: "Metadata Agent",
    description: "Processing metadata queries",
    emoji: "📊",
  },
  {
    name: "Database Identifier",
    description: "Finding relevant databases",
    emoji: "🗄️",
  },
  {
    name: "Table Identifier",
    description: "Identifying relevant tables",
    emoji: "📋",
  },
  {
    name: "Column Identifier",
    description: "Finding relevant columns",
    emoji: "🔍",
  },
  { name: "Query Planner", description: "Creating query plan", emoji: "🧠" },
  { name: "Query Generator", description: "Generating SQL query", emoji: "⚡" },
  {
    name: "Query Validator",
    description: "Validating generated query",
    emoji: "✅",
  },
];

export function QueryInterface() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState("");
  const [workflowState, setWorkflowState] = useState<WorkflowState | null>(null);
  const [results, setResults] = useState<QueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pendingHitl, setPendingHitl] = useState<HitlRequest | null>(null);

  useEffect(() => {
    return () => {
      resetWebSocketService();
    };
  }, []);

  const calculateProgress = useCallback((currentStep: string): number => {
    const stepProgress: Record<string, number> = {
      workflow_started: 0.05,
      processing_routing: 0.1,
      routing_completed: 0.15,
      processing_metadata_agent: 0.2,
      metadata_completed: 1.0,
      processing_database_identification: 0.25,
      database_identification_completed: 0.3,
      processing_table_identifier: 0.4,
      table_identification_completed: 0.45,
      processing_column_identifier: 0.55,
      column_identification_completed: 0.6,
      processing_schema_builder: 0.7,
      schema_building_completed: 0.75,
      processing_query_planning: 0.8,
      query_planning_completed: 0.85,
      processing_query_generation: 0.9,
      query_generation_completed: 0.92,
      processing_query_validation: 0.95,
      query_validation_completed: 1.0,
      workflow_completed: 1.0,
      max_retries_exhausted: 1.0,
      workflow_failed: 1.0,
    };

    return stepProgress[currentStep] || 0.5;
  }, []);

  const handleQuerySubmit = useCallback(
    async (request: QueryRequest) => {
      setIsProcessing(true);
      setProgress(0);
      setCurrentStep("Starting workflow...");
      setWorkflowState(null);
      setResults(null);
      setError(null);

      try {
        // Use WebSocket streaming for real-time updates
        await queryApi.processQueryStreaming(
          {
            query: request.query,
            mode: request.mode === "agentic" ? "interactive" : "normal",
          },
          {
            onConnect: () => {
              console.log("WebSocket connected, starting query processing...");
            },
            onStateUpdate: (state, nodeName) => {
              setWorkflowState(state);
              setCurrentStep(state.current_step);
              setProgress(calculateProgress(state.current_step));
            },
            onHitlRequest: (req) => {
              setPendingHitl(req);
            },
            onFinalResult: (result) => {
              console.log("Final result received:", result);
              setResults(result);
              setProgress(1.0);
              setCurrentStep("Workflow completed successfully!");
              setIsProcessing(false);
              setPendingHitl(null);
            },
            onError: (errorMessage) => {
              console.error("WebSocket error:", errorMessage);
              setError(errorMessage);
              setProgress(0);
              setCurrentStep("Error occurred");
              setIsProcessing(false);
            },
            onDisconnect: () => {
              console.log("WebSocket disconnected");
            },
          },
        );
      } catch (err) {
        const apiError = handleApiError(err);
        setError(apiError.message);
        setProgress(0);
        setCurrentStep("Error occurred");
        setIsProcessing(false);
      }
    },
    [calculateProgress],
  );

  const handleHitlSubmit = (feedback: any) => {
    try {
      const ws = getWebSocketService();
      ws.sendHitlFeedback(feedback);
      setPendingHitl(null);
    } catch (e) {
      console.error("Failed to send feedback", e);
      setError("Failed to send feedback");
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <div className="card">
        <QueryForm onSubmit={handleQuerySubmit} isProcessing={isProcessing} />
      </div>
      {isProcessing && (
        <div className="card">
          <ProgressIndicator
            currentStep={currentStep}
            progress={progress}
            steps={WORKFLOW_STEPS}
          />
        </div>
      )}
      {isProcessing && workflowState && (
        <div className="card">
          <LiveStateDisplay state={workflowState} />
        </div>
      )}
      {isProcessing && pendingHitl && (
        <div className="card">
          <SelectionReviewCard request={pendingHitl} onSubmit={handleHitlSubmit} />
        </div>
      )}
      {error && (
        <div className="card border-error-200 bg-error-50">
          <div className="text-error-800">
            <h3 className="text-lg font-semibold mb-2">❌ Error</h3>
            <p>{error}</p>
          </div>
        </div>
      )}
      {results && !isProcessing && <ResultsDisplay results={results} />}
      <div className="card">
        <details className="group">
          <summary className="cursor-pointer text-lg font-semibold text-gray-900 group-hover:text-primary-600">
            💡 Example Queries
          </summary>
          <div className="mt-4 space-y-4">
            <div>
              <h4 className="font-semibold text-gray-800 mb-2">Metadata Queries:</h4>
              <ul className="list-disc list-inside text-gray-600 space-y-1">
                <li>List all databases</li>
                <li>Show me all tables in the system</li>
                <li>What columns are in the users table?</li>
                <li>Describe the database schema</li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-gray-800 mb-2">Data Queries:</h4>
              <ul className="list-disc list-inside text-gray-600 space-y-1">
                <li>Find all customers with pending verification</li>
                <li>Show me payment transactions for the last 30 days</li>
                <li>Get user profiles who haven&apos;t logged in for 90 days</li>
                <li>List all orders with their current status</li>
                <li>Find users who made payments above $1000</li>
              </ul>
            </div>
          </div>
        </details>
      </div>
    </div>
  );
}
