// Typed client for the AudioNet backend.
// The base URL comes from NEXT_PUBLIC_BACKEND_URL, with a runtime override
// (the "Backend" field in the header) persisted to localStorage.

export type NodeStatus = "Idle" | "Listening" | "Sending";

export interface ReceivedResponse {
  id: number;
  message: string;
  base_frequency: number | null;
  sync_score: number | null;
}

export interface SendResponse {
  status: string;
  base_frequency: number;
  rationale: string;
  duration_seconds: number;
}

const DEFAULT_BACKEND =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export function getBackend(): string {
  if (typeof window !== "undefined") {
    return localStorage.getItem("audionet_backend") || DEFAULT_BACKEND;
  }
  return DEFAULT_BACKEND;
}

export function setBackend(url: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem("audionet_backend", url.replace(/\/+$/, ""));
  }
}

export async function fetchStatus(): Promise<NodeStatus> {
  const r = await fetch(`${getBackend()}/status`);
  const j = await r.json();
  return j.status as NodeStatus;
}

export async function fetchReceived(): Promise<ReceivedResponse> {
  const r = await fetch(`${getBackend()}/received`);
  return (await r.json()) as ReceivedResponse;
}

export async function sendMessage(message: string): Promise<SendResponse> {
  const r = await fetch(`${getBackend()}/send`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!r.ok) {
    throw new Error(`send failed (${r.status})`);
  }
  return (await r.json()) as SendResponse;
}
