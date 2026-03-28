/**
 * PRD §18 — Session state object (authoritative fields owned by the app).
 */
export type ScenarioId = "cpr_coaching";

export type WorkflowStep =
  | "intake"
  | "escalation"
  | "see_patient"
  | "start_compressions"
  | "continue_cpr"
  | "complete";

export type ViewQuality = "unknown" | "clear" | "unclear";

export type CompressionSignal = "unknown" | "yes" | "no";

export type SessionLifecycleStatus = "active" | "ended";

export interface SessionState {
  session_id: string;
  scenario: ScenarioId;
  language: string;
  current_step: WorkflowStep;
  called_emergency: boolean;
  view_quality: ViewQuality;
  patient_visible: boolean;
  compressions_detected: CompressionSignal;
  last_instruction: string;
  step_attempts: number;
  status: SessionLifecycleStatus;
}

export function createInitialSessionState(sessionId: string): SessionState {
  return {
    session_id: sessionId,
    scenario: "cpr_coaching",
    language: "en",
    current_step: "intake",
    called_emergency: false,
    view_quality: "unknown",
    patient_visible: false,
    compressions_detected: "unknown",
    last_instruction: "",
    step_attempts: 0,
    status: "active",
  };
}
