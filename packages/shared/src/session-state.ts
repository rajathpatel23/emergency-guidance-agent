/**
 * PRD §18 — Session state object (authoritative fields owned by the app).
 */
export type ScenarioId = "bleeding_control";

export type WorkflowStep =
  | "intake"
  | "escalation"
  | "identify_injury"
  | "apply_pressure"
  | "maintain_pressure"
  | "complete";

export type ViewQuality = "unknown" | "clear" | "unclear";

export type PressureSignal = "unknown" | "yes" | "no";

export type SessionLifecycleStatus = "active" | "ended";

export interface SessionState {
  session_id: string;
  scenario: ScenarioId;
  language: string;
  current_step: WorkflowStep;
  called_emergency: boolean;
  view_quality: ViewQuality;
  injury_visible: boolean;
  pressure_applied: PressureSignal;
  last_instruction: string;
  step_attempts: number;
  status: SessionLifecycleStatus;
}

export function createInitialSessionState(sessionId: string): SessionState {
  return {
    session_id: sessionId,
    scenario: "bleeding_control",
    language: "en",
    current_step: "intake",
    called_emergency: false,
    view_quality: "unknown",
    injury_visible: false,
    pressure_applied: "unknown",
    last_instruction: "",
    step_attempts: 0,
    status: "active",
  };
}
