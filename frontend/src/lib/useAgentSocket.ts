import { useCallback, useEffect, useRef, useState } from "react";
import type { ChatEvent } from "./types";

export type SocketStatus = "connecting" | "open" | "closed" | "error";

export interface SendExtras {
  resume_file_id?: string;
}

export interface UseAgentSocket {
  status: SocketStatus;
  events: ChatEvent[];
  send: (text: string, extras?: SendExtras) => void;
  thinking: boolean;
}

export function useAgentSocket(agentId: string): UseAgentSocket {
  const [events, setEvents] = useState<ChatEvent[]>([]);
  const [status, setStatus] = useState<SocketStatus>("connecting");
  const [thinking, setThinking] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Vite dev proxy forwards /ws to the FastAPI server.
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const url = `${proto}://${window.location.host}/ws/chat/${encodeURIComponent(agentId)}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    // React StrictMode mounts effects twice in dev. The first socket gets
    // closed immediately, and its late onclose event used to race ahead of
    // the second socket's onopen and stomp the status back to "closed".
    // Guarding on `wsRef.current === ws` means stale callbacks can't fire.
    const isLive = () => wsRef.current === ws;

    ws.onopen = () => {
      if (isLive()) setStatus("open");
    };
    ws.onclose = () => {
      if (isLive()) setStatus("closed");
    };
    ws.onerror = () => {
      if (isLive()) setStatus("error");
    };

    ws.onmessage = (msg) => {
      if (!isLive()) return;
      try {
        const evt = JSON.parse(msg.data) as ChatEvent;
        setEvents((prev) => [...prev, evt]);
        if (evt.type === "done") setThinking(false);
        else if (evt.type === "error") setThinking(false);
      } catch {
        // Ignore malformed payloads.
      }
    };

    return () => {
      // Detach the ref before close() so the late onclose callback exits early.
      if (wsRef.current === ws) wsRef.current = null;
      ws.close();
    };
  }, [agentId]);

  const send = useCallback((text: string, extras?: SendExtras) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    const payload: Record<string, unknown> = { text };
    if (extras?.resume_file_id) payload.resume_file_id = extras.resume_file_id;
    ws.send(JSON.stringify(payload));
    setThinking(true);
  }, []);

  return { status, events, send, thinking };
}
