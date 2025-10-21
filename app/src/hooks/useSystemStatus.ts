"use client";

import { queryApi } from "@/lib/api";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

export interface SystemStatus {
  isOnline: boolean;
  isChecking: boolean;
  latencyMs: number | null;
  lastCheckedAt: number | null;
  error: string | null;
}

const DEFAULT_POLL_MS = 60000;

export function useSystemStatus(pollMs?: number): SystemStatus {
  const [isOnline, setIsOnline] = useState<boolean>(false);
  const [isChecking, setIsChecking] = useState<boolean>(false);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [lastCheckedAt, setLastCheckedAt] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const timerRef = useRef<number | null>(null);

  const intervalMs = useMemo(() => {
    const fromEnv = Number(process.env.NEXT_PUBLIC_STATUS_POLL_MS);
    if (!Number.isNaN(fromEnv) && fromEnv > 0) return fromEnv;
    if (typeof pollMs === "number" && pollMs > 0) return pollMs;
    return DEFAULT_POLL_MS;
  }, [pollMs]);

  const checkHealth = useCallback(async () => {
    setIsChecking(true);
    const start = performance.now();
    try {
      const res = await queryApi.healthCheck();
      const end = performance.now();
      setLatencyMs(Math.round(end - start));
      const ok = res?.status === "ok";
      setIsOnline(ok);
      setError(ok ? null : "Unexpected health response");
    } catch (e) {
      setIsOnline(false);
      setError(e instanceof Error ? e.message : "Health check failed");
    } finally {
      setLastCheckedAt(Date.now());
      setIsChecking(false);
    }
  }, []);

  useEffect(() => {
    void checkHealth();

    timerRef.current = window.setInterval(() => {
      void checkHealth();
    }, intervalMs);

    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current);
    };
  }, [checkHealth, intervalMs]);

  return { isOnline, isChecking, latencyMs, lastCheckedAt, error };
}
