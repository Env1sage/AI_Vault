/** Mirrors apps/backend's conversation endpoints
 * (app/presentation/api/v1/schemas.py's Conversation, Citation, AskRequest, and AskResponse classes). */
import type { RetrievalMethod } from "./search";

export interface AskRequest {
  question: string;
}

export interface Citation {
  id: string;
  file_id: string;
  snippet: string | null;
  confidence: number;
  retrieval_method: RetrievalMethod;
}

export interface ConversationMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  retrieval_method: RetrievalMethod | null;
  provider: string | null;
  token_usage: number | null;
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
