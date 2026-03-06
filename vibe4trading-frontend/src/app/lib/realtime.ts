"use client";

import * as React from "react";

function wsBaseUrlFromWindow(): string {
  if (typeof window === "undefined") return "";

  const env = process.env.NEXT_PUBLIC_V4T_WS_BASE_URL;
  if (env && env.trim()) return env.replace(/\/$/, "");

  const host = window.location.hostname;
  if (host === "localhost" || host === "127.0.0.1") {
    return "ws://localhost:8000";
  }

  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}`;
}

export function v4tWsUrl(path: string): string {
  const base = wsBaseUrlFromWindow();
  if (!base) return path;
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${base}${p}`;
}

type RealtimeRefreshOpts = {
  wsPath: string | null;
  enabled: boolean;
  pollIntervalMs: number;
  messageDebounceMs?: number;
  refresh: () => void | Promise<void>;
};

export function useRealtimeRefresh(opts: RealtimeRefreshOpts) {
  const {
    wsPath,
    enabled,
    pollIntervalMs,
    messageDebounceMs = 200,
    refresh,
  } = opts;

  const refreshRef = React.useRef(refresh);
  React.useEffect(() => {
    refreshRef.current = refresh;
  }, [refresh]);

  React.useEffect(() => {
    if (!enabled) return;

    let ws: WebSocket | null = null;
    let pollTimer: ReturnType<typeof setInterval> | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let reconnectDelayMs = 500;
    const MAX_RECONNECT_ATTEMPTS = 20;

    let wsOk = false;
    let stopped = false;
    let reconnectAttempts = 0;

    let inFlight = false;
    let pending = false;

    let debounceTimer: ReturnType<typeof setTimeout> | null = null;
    let openTimer: ReturnType<typeof setTimeout> | null = null;

    const stopPolling = () => {
      if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
      }
    };

    const startPolling = () => {
      if (stopped || pollTimer) return;
      pollTimer = setInterval(() => {
        triggerRefresh();
      }, pollIntervalMs);
    };

    const triggerRefresh = () => {
      if (stopped) return;
      if (inFlight) {
        pending = true;
        return;
      }
      inFlight = true;
      Promise.resolve(refreshRef.current())
        .catch(() => null)
        .finally(() => {
          inFlight = false;
          if (pending && !stopped) {
            pending = false;
            setTimeout(triggerRefresh, 0);
          }
        });
    };

    const kick = () => {
      if (stopped) return;
      if (debounceTimer) clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        triggerRefresh();
      }, messageDebounceMs);
    };

    if (!wsPath) {
      startPolling();
      return () => {
        stopped = true;
        stopPolling();
        if (reconnectTimer) clearTimeout(reconnectTimer);
        if (debounceTimer) clearTimeout(debounceTimer);
      };
    }

    const scheduleReconnect = () => {
      if (stopped) return;
      if (reconnectTimer) return;
      if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
        startPolling();
        return;
      }
      reconnectAttempts++;
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        if (stopped) return;
        wsOk = false;
        connect();
      }, reconnectDelayMs);
      reconnectDelayMs = Math.min(8000, reconnectDelayMs * 2);
    };

    const connect = () => {
      if (ws) {
        const stale = ws;
        ws = null;
        stale.onopen = null;
        stale.onmessage = null;
        stale.onerror = null;
        stale.onclose = null;
        stale.close();
      }
      if (openTimer) {
        clearTimeout(openTimer);
        openTimer = null;
      }
      try {
        ws = new WebSocket(v4tWsUrl(wsPath));
      } catch {
        ws = null;
        startPolling();
        scheduleReconnect();
        return;
      }

      openTimer = setTimeout(() => {
        if (wsOk) return;
        startPolling();
        scheduleReconnect();
      }, 1500);

      ws.onopen = () => {
        wsOk = true;
        reconnectDelayMs = 500;
        reconnectAttempts = 0;
        if (openTimer) clearTimeout(openTimer);
        openTimer = null;
        if (reconnectTimer) {
          clearTimeout(reconnectTimer);
          reconnectTimer = null;
        }
        stopPolling();
        kick();
      };

      ws.onmessage = (e) => {
        if (typeof e.data === "string") {
          try {
            const msg = JSON.parse(e.data) as unknown;
            if (
              msg &&
              typeof msg === "object" &&
              ("type" in msg || "event_type" in msg) &&
              ((msg as { type?: unknown }).type === "ping" ||
                (msg as { event_type?: unknown }).event_type === "ping")
            ) {
              return;
            }
          } catch (err) {
            void err;
          }
        }
        kick();
      };

      ws.onerror = () => {
        if (openTimer) clearTimeout(openTimer);
        openTimer = null;
        if (!wsOk) startPolling();
        scheduleReconnect();
      };

      ws.onclose = () => {
        if (openTimer) clearTimeout(openTimer);
        openTimer = null;
        if (!stopped) {
          startPolling();
          scheduleReconnect();
        }
      };
    };

    connect();

    return () => {
      stopped = true;
      stopPolling();
      if (openTimer) clearTimeout(openTimer);
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (debounceTimer) clearTimeout(debounceTimer);
      if (ws) ws.close();
    };
  }, [enabled, messageDebounceMs, pollIntervalMs, wsPath]);
}
