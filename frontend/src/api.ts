import type { ChatTurn, ModulesResponse, ResponsePart, SessionGroups } from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "/interact-backend/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}${text ? ` — ${text.slice(0, 200)}` : ""}`);
  }
  return res.json() as Promise<T>;
}

export interface QueryBody {
  user_input: string;
  session_id: string;
  message_id: string;
  module_name: string;
  request_timestamp: string;
  user_id: string;
}

export interface QueryResult {
  response: ResponsePart[];
  response_id: string;
  response_timestamp: string;
  sql?: string | null;
}

export type StreamEvent =
  | { event: "start"; data: { response_id: string; response_timestamp: string } }
  | { event: "status"; data: { stage: string; message: string } }
  | { event: "delta"; data: { index: number; text: string } }
  | { event: "part"; data: { index: number; part: ResponsePart; replace_all?: boolean } }
  | { event: "sql"; data: { sql: string } }
  | { event: "done"; data: QueryResult };

/** POST /query/stream and dispatch Server-Sent Events as they arrive. */
async function queryStream(body: QueryBody, onEvent: (e: StreamEvent) => void, signal?: AbortSignal) {
  const res = await fetch(`${API_BASE}/query/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) throw new Error(`${res.status} ${res.statusText}`);

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value.replace(/\r\n/g, "\n");
    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const block = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      let event = "message";
      const data: string[] = [];
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
      }
      if (data.length) onEvent({ event, data: JSON.parse(data.join("\n")) } as StreamEvent);
    }
  }
}

export const api = {
  modules: () => request<ModulesResponse>("/modules"),

  query: (body: QueryBody) => request<QueryResult>("/query", { method: "POST", body: JSON.stringify(body) }),

  queryStream,

  sessions: async (userId: string): Promise<SessionGroups> => {
    const data = await request<SessionGroups & { error?: string }>("/getsessions", { headers: { "user-id": userId } });
    if ("error" in data && data.error) throw new Error(String(data.error));
    return data;
  },

  sessionMessages: async (sessionId: string): Promise<ChatTurn[]> => {
    const data = await request<{
      messages?: {
        request: { id: string; message: string; timestamp: string };
        response: {
          id: string;
          message: ResponsePart[] | null;
          sql?: string | null;
          feedback: string | null;
          is_like: boolean | null;
        };
      }[];
      error?: string;
    }>("/getsession/data", { headers: { "session-id": sessionId } });
    return (data.messages ?? []).map((m) => ({
      id: m.request.id,
      question: m.request.message,
      askedAt: m.request.timestamp,
      status: m.response.message ? "done" : "error",
      responseId: m.response.id,
      parts: m.response.message ?? [],
      sql: m.response.sql ?? null,
      like: m.response.is_like,
      feedback: m.response.feedback,
    }));
  },

  deleteSession: (sessionId: string) =>
    request<{ message?: string }>("/deletesession", { method: "DELETE", headers: { "session-id": sessionId } }),

  like: (session_id: string, response_id: string, is_like: boolean) =>
    request("/like-feedback", { method: "POST", body: JSON.stringify({ session_id, response_id, is_like }) }),

  feedback: (session_id: string, response_id: string, feedback: string) =>
    request("/message-feedback", { method: "POST", body: JSON.stringify({ session_id, response_id, feedback }) }),
};

export function uid(): string {
  return crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}
