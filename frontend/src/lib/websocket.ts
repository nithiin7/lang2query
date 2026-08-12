import {
  HitlFeedback,
  HitlRequest,
  WebSocketCallbacks,
  WebSocketMessage,
} from "@/types";

export class WebSocketService {
  private ws: WebSocket | null = null;
  private url: string;
  private callbacks: WebSocketCallbacks = {};
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000; // Start with 1 second
  private isManualClose = false;

  /**
   * Build the WebSocket URL from an HTTP(S) API base URL.
   *
   * @param baseUrl Override for NEXT_PUBLIC_API_URL / the localhost default.
   */
  constructor(baseUrl?: string) {
    // Convert HTTP URL to WebSocket URL
    const apiUrl =
      baseUrl || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    this.url = apiUrl.replace(/^http/, "ws") + "/ws/query";
  }

  /**
   * Open the WebSocket connection and wire up the given lifecycle callbacks.
   *
   * @param callbacks Handlers invoked for connect/message/disconnect/error events.
   * @returns Resolves once the connection is open; rejects on connection failure.
   */
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

  /** Dispatch a parsed server message to the matching registered callback, by message.type. */
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

  /** Reconnect with exponential backoff after an unclean close, up to maxReconnectAttempts. */
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

  /** Send the initial query to start a workflow run, if the socket is open. */
  sendQuery(query: string, mode: string = "normal"): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const message = { type: "start", query, mode } as const;
      this.ws.send(JSON.stringify(message));
    } else {
      console.error("WebSocket is not connected");
      this.callbacks.onError?.("WebSocket is not connected");
    }
  }

  /** Alias for sendQuery, defaulting to interactive mode. */
  sendStart(query: string, mode: "normal" | "interactive" = "interactive"): void {
    this.sendQuery(query, mode);
  }

  /** Send the user's human-in-the-loop approval/modification response, if the socket is open. */
  sendHitlFeedback(payload: HitlFeedback): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const message = { type: "hitl_feedback", payload } as const;
      this.ws.send(JSON.stringify(message));
    } else {
      console.error("WebSocket is not connected");
      this.callbacks.onError?.("WebSocket is not connected");
    }
  }

  /** Notify the server to cancel the running workflow, then close the connection. */
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

  /** Close the WebSocket cleanly, deferring the close if it's still connecting. */
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

  /** Whether the underlying WebSocket is currently open. */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  /** The underlying WebSocket's readyState (CLOSED if no socket exists). */
  getConnectionState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED;
  }
}

let wsService: WebSocketService | null = null;

/** Get the process-wide WebSocketService singleton, creating it on first use. */
export const getWebSocketService = (baseUrl?: string): WebSocketService => {
  if (!wsService) {
    wsService = new WebSocketService(baseUrl);
  }
  return wsService;
};

/** Disconnect and drop the WebSocketService singleton so the next call recreates it. */
export const resetWebSocketService = (): void => {
  if (wsService) {
    wsService.disconnect();
    wsService = null;
  }
};
