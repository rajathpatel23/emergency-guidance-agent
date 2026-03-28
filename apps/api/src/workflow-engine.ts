import type {
  ModelInterpretation,
  SessionState,
  WorkflowStep,
} from "@emergency-guidance/shared";

export type WorkflowDecision =
  | { kind: "advance"; next: WorkflowStep }
  | { kind: "stay"; step: WorkflowStep }
  | { kind: "repeat"; step: WorkflowStep };

/**
 * PRD §21 — Transition rules implemented as deterministic checks.
 * Gemini suggestions are validated elsewhere; this encodes allowed graph edges.
 */
export function decideAfterModel(
  state: SessionState,
  interpretation: ModelInterpretation | undefined
): WorkflowDecision {
  const step = state.current_step;

  if (step === "intake") {
    const hasContext =
      Boolean(interpretation?.transcript_summary?.trim()) ||
      Boolean(interpretation?.injury_visible);
    if (hasContext) return { kind: "advance", next: "escalation" };
    return { kind: "stay", step: "intake" };
  }

  if (step === "escalation") {
    return { kind: "advance", next: "identify_injury" };
  }

  if (step === "identify_injury") {
    if (interpretation?.view_unclear || state.view_quality === "unclear") {
      return { kind: "repeat", step: "identify_injury" };
    }
    if (interpretation?.injury_visible === true || state.injury_visible) {
      return { kind: "advance", next: "apply_pressure" };
    }
    return { kind: "repeat", step: "identify_injury" };
  }

  if (step === "apply_pressure") {
    const pressure =
      interpretation?.pressure_applied === true || state.pressure_applied === "yes";
    if (pressure) return { kind: "advance", next: "maintain_pressure" };
    return { kind: "repeat", step: "apply_pressure" };
  }

  if (step === "maintain_pressure") {
    return { kind: "advance", next: "complete" };
  }

  return { kind: "stay", step: "complete" };
}

export function applyWorkflowDecision(
  state: SessionState,
  decision: WorkflowDecision
): SessionState {
  if (decision.kind === "advance") {
    return {
      ...state,
      current_step: decision.next,
      step_attempts: 0,
    };
  }
  if (decision.kind === "repeat") {
    return {
      ...state,
      current_step: decision.step,
      step_attempts: state.step_attempts + 1,
    };
  }
  return state;
}
