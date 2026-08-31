/** Mirrors apps/backend's conversation endpoints
 * (app/presentation/api/v1/schemas.py's Conversation, Citation, AskRequest, and AskResponse classes). */
import type { RetrievalMethod } from "./search";

export interface AskRequest {
  question: string;
}

/** "tool" (ADR-024) — set on a citation/message produced by the AI Storage
 * Assistant's deterministic tool-routing path, distinct from `RetrievalMethod`
 * (search.ts), which describes only `SearchService`'s own metadata/semantic
 * retrieval and never includes "tool". */
export type ConversationRetrievalMethod = RetrievalMethod | "tool";

export interface Citation {
  id: string;
  file_id: string;
  snippet: string | null;
  confidence: number;
  retrieval_method: ConversationRetrievalMethod;
  file_name: string | null;
  file_size_bytes: number | null;
  file_mime_type: string | null;
}

export interface ConversationMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  retrieval_method: ConversationRetrievalMethod | null;
  provider: string | null;
  token_usage: number | null;
  tool_name: string | null;
  created_at: string;
  citations: Citation[];
}

export interface Conversation {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: ConversationMessage[];
}

export interface AskResponse {
  conversation: Conversation;
  user_message: ConversationMessage;
  assistant_message: ConversationMessage;
}
