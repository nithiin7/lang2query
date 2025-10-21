"use client";

import { ChatMessage } from "@/components/ChatMessage";
import { QueryInput } from "@/components/QueryInput";
import { ResultsDisplay } from "@/components/ResultsDisplay";
import { SelectionReviewCard } from "@/components/SelectionReviewCard";
import { StatusPanel } from "@/components/StatusPanel";
import { handleApiError, queryApi } from "@/lib/api";
import { showToast } from "@/lib/toast";
import { getWebSocketService, resetWebSocketService } from "@/lib/websocket";
import { HitlRequest, QueryResponse, WorkflowState } from "@/types";
import { useEffect, useRef, useState } from "react";

interface ChatContainerProps {
  chatId: string;
  mode: "agentic" | "ask";
  onModeChange: (mode: "agentic" | "ask") => void;
  onNewUserQuery?: (id: string, title: string) => void;
}

interface ChatEntry {
  id: string;
  type: "user" | "assistant" | "result";
  content: string;
  timestamp: Date;
  result?: QueryResponse;
}

export function ChatContainer({
  chatId,
  mode,
  onModeChange,
  onNewUserQuery,
}: ChatContainerProps) {
  const [messages, setMessages] = useState<ChatEntry[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [workflowState, setWorkflowState] = useState<WorkflowState | null>(null);
  const [currentStep, setCurrentStep] = useState("");
  const [pendingHitl, setPendingHitl] = useState<HitlRequest | null>(null);
  const [isStatusExpanded, setIsStatusExpanded] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    return () => {
      // Try to cancel current work, then fully reset service
      try {
        getWebSocketService()?.cancel?.();
      } catch {}
      resetWebSocketService();
    };
  }, []);

  // Hydrate from localStorage on mount for this chatId
  useEffect(() => {
    try {
      const saved = localStorage.getItem(`t2q_chat_${chatId}`);
      if (saved) {
        const parsed = JSON.parse(saved) as { query?: string; final?: string };
        const hydrated: ChatEntry[] = [];
        if (parsed.query) {
          hydrated.push({
            id: `${chatId}-u`,
            type: "user",
            content: parsed.query,
            timestamp: new Date(),
          });
        }
        if (parsed.final) {
          hydrated.push({
            id: `${chatId}-a`,
            type: "assistant",
            content: parsed.final,
            timestamp: new Date(),
          });
        }
        if (hydrated.length) setMessages(hydrated);
      }
    } catch {}
    // reset processing state when chat changes
    setIsProcessing(false);
    setWorkflowState(null);
    setCurrentStep("");
  }, [chatId]);

  const handleQuerySubmit = async (query: string) => {
    const userMessage: ChatEntry = {
      id: Date.now().toString(),
      type: "user",
      content: query,
      timestamp: new Date(),
    };

    // Inform parent for chat history
    if (onNewUserQuery) {
      const title = query.length > 60 ? `${query.slice(0, 57)}...` : query;
      onNewUserQuery(chatId, title);
    }

    setMessages((prev) => [...prev, userMessage]);
    // persist initial user query
    try {
      const existing = localStorage.getItem(`t2q_chat_${chatId}`);
      const obj = existing ? JSON.parse(existing) : {};
      obj.query = query;
      localStorage.setItem(`t2q_chat_${chatId}`, JSON.stringify(obj));
    } catch {}
    setIsProcessing(true);
    setWorkflowState(null);
    setCurrentStep("Starting workflow...");
    setIsStatusExpanded(true);

    try {
      await queryApi.processQueryStreaming(
        { query, mode: mode === "agentic" ? "interactive" : "normal" },
        {
          onConnect: () => {
            console.log("WebSocket connected, starting query processing...");
          },
          onStateUpdate: (state, nodeName) => {
            setWorkflowState(state);
            setCurrentStep(state.current_step);
          },
          onHitlRequest: (req) => {
            setPendingHitl(req);
            const assistantMessage: ChatEntry = {
              id: (Date.now() + 2).toString(),
              type: "assistant",
              content:
                req.review_type === "databases"
                  ? `I found these databases: ${req.items.join(", ")}. Please approve or modify.`
                  : `I found these tables: ${req.items.join(", ")}. Please approve or modify.`,
              timestamp: new Date(),
            };
            setMessages((prev) => [...prev, assistantMessage]);
          },
          onCancelled: (message) => {
            setIsProcessing(false);
            setCurrentStep("Workflow stopped by user");
            setPendingHitl(null);
          },
          onFinalResult: (response) => {
            // Handle metadata queries differently
            let assistantContent = "Query processed successfully";
            if (response.is_metadata_query && response.metadata_response) {
              const responseMatch =
                response.metadata_response.match(/Response:\s*([\s\S]*)/);
              if (responseMatch) {
                assistantContent = responseMatch[1].trim();
              } else {
                assistantContent = response.metadata_response;
              }
            } else if (response.query) {
              assistantContent = response.query;
            }

            const assistantMessage: ChatEntry = {
              id: (Date.now() + 1).toString(),
              type: "assistant",
              content: assistantContent,
              timestamp: new Date(),
            };

            const resultEntry: ChatEntry = {
              id: (Date.now() + 2).toString(),
              type: "result",
              content: "Processing complete",
              timestamp: new Date(),
              result: response,
            };

            setMessages((prev) => [...prev, assistantMessage, resultEntry]);
            setCurrentStep("Completed");
            setIsProcessing(false);
            setPendingHitl(null);
            // persist final output (assistant content + raw metadata when present)
            try {
              const existing = localStorage.getItem(`t2q_chat_${chatId}`);
              const obj = existing ? JSON.parse(existing) : {};
              // Save exactly what we showed to the user
              obj.final = assistantContent || "";
              // Persist raw metadata response for later use
              if (response.is_metadata_query && response.metadata_response) {
                obj.metadata = response.metadata_response;
                obj.is_metadata = true;
              } else {
                obj.metadata = undefined;
                obj.is_metadata = false;
              }
              localStorage.setItem(`t2q_chat_${chatId}`, JSON.stringify(obj));
            } catch {}
          },
          onError: (errorMessage) => {
            console.error("WebSocket error:", errorMessage);
            showToast.websocketError(errorMessage);
            setCurrentStep("Error occurred");
            setIsProcessing(false);
          },
          onDisconnect: () => {
            console.log("WebSocket disconnected");
          },
        },
      );
    } catch (error) {
      const apiError = handleApiError(error);
      showToast.apiError(apiError.message, apiError.status);
      setCurrentStep("Error occurred");
      setIsProcessing(false);
    }
  };

  const handleStop = () => {
    try {
      const ws = getWebSocketService();
      ws.cancel();

      // Update UI state
      setIsProcessing(false);
      setCurrentStep("Workflow stopped by user");
      setPendingHitl(null);

      // Add a message to indicate the workflow was stopped
      const stopMessage: ChatEntry = {
        id: Date.now().toString(),
        type: "assistant",
        content: "Workflow stopped by user",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, stopMessage]);

      showToast.info("Workflow stopped", "The query processing has been cancelled");
    } catch (e) {
      console.error("Failed to stop workflow", e);
      showToast.error("Failed to stop workflow", "Please try again");
    }
  };

  const handleHitlSubmit = (feedback: any) => {
    try {
      const ws = getWebSocketService();
      ws.sendHitlFeedback(feedback);

      // Add user response to chat
      let userResponse = "";
      if (feedback.action === "approve") {
        userResponse = `✅ Approved the suggested ${feedback.review_type}`;
        if (feedback.feedback_text) {
          userResponse += ` with note: "${feedback.feedback_text}"`;
        }
      } else if (feedback.action === "modify") {
        const approvedCount = feedback.approved_items?.length || 0;
        userResponse = `🔧 Modified ${feedback.review_type} selection (${approvedCount} approved)`;
        if (feedback.feedback_text) {
          userResponse += ` with note: "${feedback.feedback_text}"`;
        }
      }

      if (userResponse) {
        const userMessage: ChatEntry = {
          id: Date.now().toString(),
          type: "user",
          content: userResponse,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, userMessage]);
      }

      setPendingHitl(null);
    } catch (e) {
      console.error("Failed to send feedback", e);
      showToast.error("Failed to send feedback", "Please try again");
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto space-y-4">
          <div className="flex justify-end">
            <div className="inline-flex rounded-md shadow-sm" role="group">
              <button
                type="button"
                onClick={() => onModeChange("ask")}
                className={`px-3 py-1.5 text-sm font-medium border rounded-l-md ${
                  mode === "ask"
                    ? "bg-black text-white border-black"
                    : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
                }`}
              >
                Ask
              </button>
              <button
                type="button"
                onClick={() => onModeChange("agentic")}
                className={`px-3 py-1.5 text-sm font-medium border-t border-b border-r rounded-r-md ${
                  mode === "agentic"
                    ? "bg-black text-white border-black"
                    : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
                }`}
              >
                Agentic
              </button>
            </div>
          </div>
          {messages.length === 0 && (
            <div className="text-center py-12">
              <div className="text-6xl mb-4">💬</div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                Welcome to Text2Query
              </h3>
              <p className="text-gray-600 max-w-md mx-auto">
                Ask me anything about your data. I can help you generate SQL queries,
                explore your database schema, or answer questions about your data
                structure.
              </p>
            </div>
          )}
          {messages.map((message) => (
            <div key={message.id}>
              {message.type === "result" && message.result ? (
                <div className="animate-in slide-in-from-bottom-4 duration-500">
                  <ResultsDisplay results={message.result} />
                </div>
              ) : (
                <ChatMessage
                  content={message.content}
                  isUser={message.type === "user"}
                  timestamp={message.timestamp}
                />
              )}
            </div>
          ))}
          {isProcessing && pendingHitl && (
            <div className="mt-4">
              <SelectionReviewCard request={pendingHitl} onSubmit={handleHitlSubmit} />
            </div>
          )}
          {isProcessing && (
            <div className="flex justify-start">
              <div className="bg-gray-100 rounded-2xl px-4 py-3 shadow-sm mr-12">
                <div className="flex items-center space-x-2">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div
                      className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                      style={{ animationDelay: "0.1s" }}
                    ></div>
                    <div
                      className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                      style={{ animationDelay: "0.2s" }}
                    ></div>
                  </div>
                  <span className="text-sm text-gray-600">Thinking...</span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>
      <StatusPanel
        isExpanded={isStatusExpanded}
        onToggle={() => setIsStatusExpanded(!isStatusExpanded)}
        workflowState={workflowState}
        currentStep={currentStep}
        isProcessing={isProcessing}
      />
      <QueryInput
        onSubmit={handleQuerySubmit}
        onStop={handleStop}
        isLoading={isProcessing}
        placeholder={
          mode === "agentic"
            ? "Describe what you want to know about your data..."
            : "Ask a direct question about your data..."
        }
      />
    </div>
  );
}
