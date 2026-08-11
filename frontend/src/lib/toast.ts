import { toast } from "sonner";

export const showToast = {
  error: (message: string, description?: string) => {
    toast.error(message, {
      description,
      duration: 5000,
    });
  },

  success: (message: string, description?: string) => {
    toast.success(message, {
      description,
      duration: 3000,
    });
  },

  info: (message: string, description?: string) => {
    toast.info(message, {
      description,
      duration: 4000,
    });
  },

  warning: (message: string, description?: string) => {
    toast.warning(message, {
      description,
      duration: 4000,
    });
  },

  // Network-specific errors
  networkError: (message?: string) => {
    toast.error(message || "Network connection failed", {
      description: "Please check your internet connection and try again",
      duration: 6000,
    });
  },

  // WebSocket-specific errors
  websocketError: (message?: string) => {
    toast.error(message || "Connection lost", {
      description: "Real-time updates unavailable. Please refresh the page",
      duration: 5000,
    });
  },

  // API errors
  apiError: (message: string, status?: number) => {
    const description = status ? `Status: ${status}` : undefined;
    toast.error(message, {
      description,
      duration: 5000,
    });
  },
};
