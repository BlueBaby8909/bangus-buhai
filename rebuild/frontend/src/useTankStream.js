import { useEffect, useState } from "react";
import { request, hatcheryPath } from "./api";
import { mergeReading } from "./readings";
export function useTankStream(hatchery, tank) {
  const [state, setState] = useState({
    rows: [],
    status: "Loading",
    error: null,
  });
  useEffect(() => {
    const abort = new AbortController();
    let socket,
      timer,
      cursor,
      stopped = false,
      retries = 0;
    const base = hatcheryPath(hatchery, `/tanks/${tank}`);
    async function snapshot() {
      try {
        const page = await request(
          base + "/readings?time_basis=received&include_voided=true&limit=200",
          { passive: true, signal: abort.signal },
        );
        if (stopped) return;
        cursor = page.stream_cursor;
        setState({ rows: page.items, status: "Connecting", error: null });
        connect();
      } catch (error) {
        if (!stopped && error.name !== "AbortError") {
          setState((s) => ({ ...s, status: "Unavailable", error }));
          schedule(snapshot);
        }
      }
    }
    function schedule(action) {
      if (stopped) return;
      clearTimeout(timer);
      timer = setTimeout(
        action,
        Math.min(30000, 1000 * 2 ** Math.min(retries++, 5)),
      );
    }
    function connect() {
      if (stopped) return;
      const url = new URL("/api/v1" + base + "/stream", window.location.href);
      url.protocol = location.protocol === "https:" ? "wss:" : "ws:";
      url.searchParams.set("cursor", cursor);
      socket = new WebSocket(url);
      let resync = false;
      socket.onmessage = (event) => {
        if (stopped) return;
        try {
          const data = JSON.parse(event.data);
          if (data.v !== 1) {
            resync = true;
            socket.close();
            return;
          }
          if (data.type === "resync_required") {
            resync = true;
            return;
          }
          if (data.type === "reading.changed") {
            setState((s) => ({
              ...s,
              rows: mergeReading(s.rows, data.reading).slice(0, 500),
              status: "Live feed connected",
            }));
          } else if (data.type === "ready" || data.type === "heartbeat") {
            setState((s) => ({
              ...s,
              status: "Live feed connected",
              error: null,
            }));
            retries = 0;
          }
          if (data.cursor) cursor = data.cursor;
        } catch {
          resync = true;
          socket.close();
        }
      };
      socket.onclose = (event) => {
        if (stopped) return;
        if (event.code === 1008) {
          request("/me", { passive: true, signal: abort.signal }).catch(
            () => {},
          );
          resync = true;
        }
        setState((s) => ({ ...s, status: "Reconnecting" }));
        schedule(resync || event.code === 1006 ? snapshot : connect);
      };
    }
    if (hatchery && tank) snapshot();
    return () => {
      stopped = true;
      abort.abort();
      clearTimeout(timer);
      socket?.close();
    };
  }, [hatchery, tank]);
  return state;
}
