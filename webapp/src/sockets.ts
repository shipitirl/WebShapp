import type { LiveMessage, WinProbSnapshot } from "./types";

const WS_URL = (import.meta.env.VITE_WS_URL as string) || "ws://localhost:8000/ws/live";
const SNAPSHOT_URL = (import.meta.env.VITE_SNAPSHOT_URL as string) || "/api/game/demo/snapshot";

type Listener = (msg: LiveMessage) => void;

export function subscribeLive(listener: Listener): () => void {
  const socket = new WebSocket(WS_URL);
  socket.onmessage = (event) => {
    listener(JSON.parse(event.data) as LiveMessage);
  };
  return () => socket.close();
}

export async function fetchSnapshot(gid: string): Promise<WinProbSnapshot> {
  const res = await fetch(`/api/game/${gid}/snapshot`);
  if (!res.ok) {
    throw new Error(`Failed to fetch snapshot: ${res.status}`);
  }
  return (await res.json()) as WinProbSnapshot;
}
