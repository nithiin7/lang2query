export interface QueryRequest {
  query: string;
  mode: "agentic" | "ask";
}

export interface QueryResponse {
  type: "success" | "error";
  query?: string;
  status?: string;
  execution_time?: string;
  databases?: DatabaseInfo;
  tables?: TableInfo;
  columns?: ColumnInfo;
  query_plan?: QueryPlanInfo;
  validation?: ValidationInfo;
  is_metadata_query?: boolean;
  metadata_response?: string;
  message?: string;
}

export interface DatabaseInfo {
  count: number;
  identified: string[];
}

export interface TableInfo {
  count: number;
  retrieved: boolean;
  preview?: string;
}

export interface ColumnInfo {
  count: number;
  retrieved: boolean;
  preview?: string;
}

export interface QueryPlanInfo {
  created: boolean;
}

export interface ValidationInfo {
  overall_valid: boolean;
  issues_count: number;
  suggestions_count: number;
}

// Workflow State Types
export interface WorkflowState {
  current_step: string;
  retries_left: number;
  is_metadata_query?: boolean;
  dialect?: string;
  relevant_databases?: string[];
  relevant_tables?: string[];
  relevant_columns?: string[];
  query_plan?: string;
  generated_query?: {
    query: string;
    explanation?: string;
  };
  is_query_valid?: boolean;
  metadata_response?: string;
  pending_review?: PendingReview;
  human_approvals?: Record<string, boolean>;
  human_feedback?: string;
}

// Component Props Types
export interface WorkflowStep {
  name: string;
  description: string;
}

export interface ResultsDisplayProps {
  results: QueryResponse;
  sqlQuery?: string;
  explanation?: string;
  metadataResponse?: string;
}

// Interactive HITL Types
export interface PendingReview {
  type: "databases" | "tables";
  items: string[];
}

export interface HitlRequest {
  id: string;
  review_type: "databases" | "tables";
  items: string[];
}

export interface HitlFeedback {
  checkpointId: string;
  review_type: "databases" | "tables";
  action: "approve" | "modify" | "reject";
  approved_items?: string[];
  suggested_items?: string[];
  feedback_text?: string;
}

// WebSocket Types
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
