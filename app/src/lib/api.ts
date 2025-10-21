import { QueryResponse, WorkflowState, WorkflowStep } from "@/types";
import axios, { AxiosResponse } from "axios";
import { WebSocketCallbacks, getWebSocketService } from "./websocket";

// Create axios instance with base configuration
const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  timeout: 300000, // 5 minutes timeout for long-running queries
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log("API Request:", config.method?.toUpperCase(), config.url);
    return config;
  },
  (error) => {
    console.error("API Request Error:", error);
    return Promise.reject(error);
  },
);

// Response interceptor for logging
api.interceptors.response.use(
  (response) => {
    console.log("API Response:", response.status, response.config.url);
    return response;
  },
  (error) => {
    const status = error.response?.status || "unknown";
    const data = error.response?.data || "no data";
    const message = error.message || "unknown error";

    console.error("API Response Error:", {
      status,
      data,
      message,
      url: error.config?.url,
      method: error.config?.method,
    });

    return Promise.reject(error);
  },
);

// API functions
export const queryApi = {
  // Process a query and get streaming workflow states via WebSocket
  async processQueryStreaming(
    request: { query: string; mode: "normal" | "interactive" },
    callbacks: WebSocketCallbacks,
  ): Promise<void> {
    try {
      const wsService = getWebSocketService();
      await wsService.connect(callbacks);
      wsService.sendQuery(request.query, request.mode);
    } catch (error) {
      console.error("Error processing query via WebSocket:", error);
      callbacks.onError?.(`WebSocket connection failed: ${error}`);
    }
  },

  // Process a query and get streaming workflow states (HTTP fallback)
  async processQuery(
    request: { query: string; mode: "normal" | "interactive" },
    _onProgress?: (state: WorkflowState) => void,
  ): Promise<QueryResponse> {
    try {
      const response: AxiosResponse<QueryResponse> = await api.post("/query", request, {
        headers: {
          Accept: "application/json",
        },
      });

      return response.data;
    } catch (error) {
      console.error("Error processing query:", error);
      throw error;
    }
  },

  // Health check endpoint
  async healthCheck(): Promise<{ status: string }> {
    try {
      const response = await api.get("/health");
      return response.data;
    } catch (error) {
      console.error("Health check failed:", error);
      throw error;
    }
  },

  // Get workflow steps configuration
  async getWorkflowSteps(): Promise<WorkflowStep[]> {
    try {
      const response = await api.get("/workflow/steps");
      return response.data;
    } catch (error) {
      console.error("Error getting workflow steps:", error);
      throw error;
    }
  },
};

// Error handling utilities
export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public data?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export const handleApiError = (error: unknown): ApiError => {
  if (axios.isAxiosError(error)) {
    if (error.response) {
      // Server responded with error status
      const { status, data } = error.response;
      return new ApiError(
        ((data as Record<string, unknown>)?.message as string) ||
          `Request failed with status ${status}`,
        status,
        data,
      );
    } else if (error.request) {
      // Request was made but no response received
      return new ApiError("Network error - please check your connection");
    }
  }

  // Something else happened
  const message =
    error instanceof Error ? error.message : "An unexpected error occurred";
  return new ApiError(message);
};
