export type DomainStatus = "active" | "placeholder";

export interface Domain {
  module: string;
  tag: string;
  display_name: string;
  short_name: string;
  description: string;
  status: DomainStatus;
  icon: string;
  sample_questions: string[];
}

export interface ModulesResponse {
  data_engine: string;
  modules: Domain[];
}

export type ResponsePart =
  | { type: "text"; content: string }
  | { type: "table"; content: Record<string, unknown>[] }
  | { type: "image"; mime_type: string; content: string };

export interface ChatTurn {
  id: string; // message_id (request)
  question: string;
  askedAt: string;
  status: "pending" | "streaming" | "done" | "error" | "stopped";
  stage?: string; // latest progress message while streaming
  responseId?: string;
  parts?: ResponsePart[];
  sql?: string | null;
  like?: boolean | null;
  feedback?: string | null;
  elapsedMs?: number;
}

export interface SessionSummary {
  sessionId: string;
  sessionName: string;
  createdAt: string;
  module_name: string;
}

export type SessionGroups = Record<string, SessionSummary[]>;
