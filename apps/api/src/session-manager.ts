import { randomUUID } from "node:crypto";
import {
  createInitialSessionState,
  type SessionState,
} from "@emergency-guidance/shared";

const store = new Map<string, SessionState>();

export function createSession(): SessionState {
  const id = randomUUID();
  const state = createInitialSessionState(id);
  store.set(id, state);
  return state;
}

export function getSession(sessionId: string): SessionState | undefined {
  return store.get(sessionId);
}

export function updateSession(
  sessionId: string,
  patch: Partial<SessionState>
): SessionState | undefined {
  const prev = store.get(sessionId);
  if (!prev) return undefined;
  const next = { ...prev, ...patch };
  store.set(sessionId, next);
  return next;
}

export function endSession(sessionId: string): void {
  const s = store.get(sessionId);
  if (s) store.set(sessionId, { ...s, status: "ended" });
}
