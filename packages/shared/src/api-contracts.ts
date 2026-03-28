import type { ClientEventType, UiSessionStatus } from "./events.js";
import type { SessionState, WorkflowStep } from "./session-state.js";

/**
 * PRD §22 — Example frontend → backend envelope.
 * Frame may be base64, a URL reference, or omitted depending on transport.
 */
export interface ClientToBackendEvent {
  session_id: string;
  event_type: ClientEventType;
  transcript?: string;
  /** Base64 image or opaque reference id from upload step */
  frame?: string;
  current_step?: WorkflowStep;
}

/**
 * PRD §22 — Example backend → frontend instruction payload.
 */
export interface InstructionResponse {
  session_id: string;
  current_step: WorkflowStep;
  instruction: string;
  speak: boolean;
  status: UiSessionStatus;
  /** Optional echo of session for debug panels */
  session?: SessionState;
}
