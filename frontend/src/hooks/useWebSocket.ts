import { useEffect } from "react";
import { useAppStore } from "../store/useAppStore";

export function useStatsWebSocket() {
  const setStats = useAppStore((s) => s.setStats);
  const setConfig = useAppStore((s) => s.setConfig);
  const setWsConnected = useAppStore((s) => s.setWsConnected);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let retryTimer: number | null = null;
    let closed = false;

    const connect = () => {
      const proto = window.location.protocol === "https:" ? "wss" : "ws";
      ws = new WebSocket(`${proto}://${window.location.host}/ws/events`);
      ws.onopen = () => setWsConnected(true);
      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          if (data.stats) setStats(data.stats);
          if (data.config) setConfig(data.config);
        } catch {
          /* ignore */
        }
      };
      ws.onclose = () => {
        setWsConnected(false);
        if (!closed) retryTimer = window.setTimeout(connect, 1000);
      };
      ws.onerror = () => ws?.close();
    };
    connect();

    return () => {
      closed = true;
      if (retryTimer) clearTimeout(retryTimer);
      ws?.close();
    };
  }, [setStats, setConfig, setWsConnected]);
}
