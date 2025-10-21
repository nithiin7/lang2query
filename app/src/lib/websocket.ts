import { HitlFeedback, HitlRequest, QueryResponse, WorkflowState } from "@/types";

export interface WebSocketMessage {
  type:
    | "connected"
    | "state_update"
    | "final_result"
    | "error"
    | "hitl_request"
    | "hitl_feedback_ack"
    | "cancelled";
  message?: string;
  node_name?: string;
  state?: WorkflowState;
  result?: QueryResponse;
  checkpoint?: { id: string; review_type: "databases" | "tables"; items: string[] };
  checkpointId?: string;
}

export interface WebSocketCallbacks {
  onConnect?: () => void;
  onStateUpdate?: (state: WorkflowState, nodeName?: string) => void;
  onFinalResult?: (result: QueryResponse) => void;
  onError?: (error: string) => void;
  onDisconnect?: () => void;
  onHitlRequest?: (request: HitlRequest) => void;
  onCancelled?: (message?: string) => void;
}

export class WebSocketService {
  private ws: WebSocket | null = null;
  private url: string;
  private callbacks: WebSocketCallbacks = {};
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000; // Start with 1 second
  private isManualClose = false;

  constructor(baseUrl?: string) {
    // Convert HTTP URL to WebSocket URL
    const apiUrl =
      baseUrl || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    this.url = apiUrl.replace(/^http/, "ws") + "/ws/query";
  }

  connect(callbacks: WebSocketCallbacks): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.callbacks = callbacks;
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
          this.reconnectAttempts = 0;
          this.callbacks.onConnect?.();
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);
            this.handleMessage(message);
          } catch (error) {
            console.error("Error parsing WebSocket message:", error);
            this.callbacks.onError?.("Failed to parse server message");
          }
        };

        this.ws.onclose = (event) => {
          this.callbacks.onDisconnect?.();

          // Attempt to reconnect if not a clean close
          if (
            event.code !== 1000 &&
            this.reconnectAttempts < this.maxReconnectAttempts
          ) {
            this.attemptReconnect();
          }
        };

        this.ws.onerror = (error) => {
          if (this.isManualClose) {
            // Suppress noisy errors during intentional close
            return;
          }
          console.error("WebSocket error:", error);
          this.callbacks.onError?.("WebSocket connection error");
          reject(error);
        };
      } catch (error) {
        console.error("Failed to create WebSocket connection:", error);
        reject(error);
      }
    });
  }

  private handleMessage(message: WebSocketMessage): void {
    switch (message.type) {
      case "connected":
        console.log("Server connected:", message.message);
        break;

      case "state_update":
        if (message.state) {
          this.callbacks.onStateUpdate?.(message.state, message.node_name);
        }
        break;

      case "final_result":
        if (message.result) {
          this.callbacks.onFinalResult?.(message.result);
        }
        break;

      case "hitl_request":
        if (message.checkpoint) {
          const req: HitlRequest = {
            id: message.checkpoint.id,
            review_type: message.checkpoint.review_type,
            items: message.checkpoint.items,
          };
          this.callbacks.onHitlRequest?.(req);
        }
        break;

      case "hitl_feedback_ack":
        console.log("HITL feedback acknowledged:", message.checkpointId);
        break;

      case "cancelled":
        this.callbacks.onCancelled?.(message.message);
        break;

      case "error":
        this.callbacks.onError?.(message.message || "Unknown server error");
        break;

      default:
        console.warn("Unknown message type:", message.type);
    }
  }

  private attemptReconnect(): void {
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1); // Exponential backoff

    setTimeout(() => {
      if (this.reconnectAttempts <= this.maxReconnectAttempts) {
        this.connect(this.callbacks).catch((error) => {
          console.error("Reconnection failed:", error);
        });
      }
    }, delay);
  }

  sendQuery(query: string, mode: string = "normal"): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const message = { type: "start", query, mode } as const;
      this.ws.send(JSON.stringify(message));
    } else {
      console.error("WebSocket is not connected");
      this.callbacks.onError?.("WebSocket is not connected");
    }
  }

  sendStart(query: string, mode: "normal" | "interactive" = "interactive"): void {
    this.sendQuery(query, mode);
  }

  sendHitlFeedback(payload: HitlFeedback): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const message = { type: "hitl_feedback", payload } as const;
      this.ws.send(JSON.stringify(message));
    } else {
      console.error("WebSocket is not connected");
      this.callbacks.onError?.("WebSocket is not connected");
    }
  }

  cancel(): void {
    // Optionally send a cancel control message to the server, then close
    try {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        const ctrl = { type: "cancel" } as const;
        this.ws.send(JSON.stringify(ctrl));
      }
    } catch {}
    this.disconnect();
  }

  disconnect(): void {
    if (!this.ws) return;

    // Mark this as an intentional close to avoid noisy error handlers
    this.isManualClose = true;

    try {
      if (this.ws.readyState === WebSocket.CONNECTING) {
        // Defer the close until after connection opens to avoid browser error
        const socket = this.ws;
        socket.onopen = () => {
          try {
            socket.close(1000, "Client disconnecting");
          } finally {
            this.isManualClose = false;
          }
        };
      } else {
        this.ws.close(1000, "Client disconnecting");
        this.isManualClose = false;
      }
    } catch {
      // Ignore close errors
      this.isManualClose = false;
    } finally {
      this.ws = null;
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  getConnectionState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED;
  }
}

let wsService: WebSocketService | null = null;

export const getWebSocketService = (baseUrl?: string): WebSocketService => {
  if (!wsService) {
    wsService = new WebSocketService(baseUrl);
  }
  return wsService;
};

export const resetWebSocketService = (): void => {
  if (wsService) {
    wsService.disconnect();
    wsService = null;
  }
};
