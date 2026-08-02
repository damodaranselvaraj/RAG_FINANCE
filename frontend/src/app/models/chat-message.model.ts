/**
 * Domain models shared across the chatbot UI.
 * These mirror the shape we expect the RAG backend to return so the UI can be
 * wired to the real API without changing the components.
 */

export type MessageRole = 'user' | 'assistant';

export type MessageStatus = 'sending' | 'streaming' | 'done' | 'error';

/** A citation pointing back to the source document a RAG answer was grounded in. */
export interface Source {
  /** Human-readable document name, e.g. "Leave Policy 2025.pdf". */
  title: string;
  /** Optional section / page reference within the document. */
  section?: string;
  /** Optional URL or path to open the source document. */
  url?: string;
  /** The retrieved passage the answer drew from. */
  snippet?: string;
  /** Retriever relevance score (0..1) when available. */
  score?: number;
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  text: string;
  timestamp: Date;
  status: MessageStatus;
  /** Grounding citations returned by the RAG pipeline (assistant messages only). */
  sources?: Source[];
}

/** Request payload sent to the RAG backend. */
export interface ChatRequest {
  query: string;
  /** Prior turns for multi-turn context; kept minimal for now. */
  history?: { role: MessageRole; text: string }[];
}

/** Response payload returned by the RAG backend. */
export interface ChatResponse {
  answer: string;
  sources?: Source[];
}
