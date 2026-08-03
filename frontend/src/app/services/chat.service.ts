import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { delay } from 'rxjs/operators';

import { environment } from '../../environments/environment';
import { ChatRequest, ChatResponse } from '../models/chat-message.model';

/**
 * Talks to the RAG backend. The query is sent to `${apiUrl}/chat`, where it is
 * embedded and matched against the ChromaDB vector store; the grounded answer
 * plus source citations come back in a {@link ChatResponse}.
 *
 * When `environment.useMock` is true we short-circuit with a canned response so
 * the UI stays usable even if the backend isn't running.
 */
@Injectable({ providedIn: 'root' })
export class ChatService {
  private readonly chatUrl = `${environment.apiUrl}/chat`;
  private readonly sessionsUrl = `${environment.apiUrl}/chat/sessions`;

  constructor(private http: HttpClient) {}

  ask(request: ChatRequest): Observable<ChatResponse> {
    if (environment.useMock) {
      return this.mockResponse(request).pipe(delay(600));
    }
    return this.http.post<ChatResponse>(this.chatUrl, request);
  }

  /** Create a new chat session on the backend and return its session_id. */
  newSession(title: string = 'New Chat'): Observable<{ session_id: string; title: string; created_at: string }> {
    if (environment.useMock) {
      return of({ session_id: `mock-${Date.now()}`, title, created_at: new Date().toISOString() }).pipe(delay(200));
    }
    return this.http.post<{ session_id: string; title: string; created_at: string }>(this.sessionsUrl, { title });
  }

  private mockResponse(request: ChatRequest): Observable<ChatResponse> {
    return of({
      answer:
        `(mock) You asked: "${request.query}". Set environment.useMock = ` +
        `false and start the backend to get real answers from the policy.`,
      sources: []
    });
  }
}
