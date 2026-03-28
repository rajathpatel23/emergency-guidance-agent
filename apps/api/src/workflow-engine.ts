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
      Boolean(interpretation?.patient_visible);
    if (hasContext) return { kind: "advance", next: "escalation" };
    return { kind: "stay", step: "intake" };
  }

  if (step === "escalation") {
    if (state.step_attempts >= 1) return { kind: "advance", next: "see_patient" };
    return { kind: "repeat", step: "escalation" };
  }

  if (step === "see_patient") {
    if (interpretation?.view_unclear || state.view_quality === "unclear") {
      return { kind: "repeat", step: "see_patient" };
    }
    if (interpretation?.patient_visible === true || state.patient_visible) {
      return { kind: "advance", next: "start_compressions" };
    }
    return { kind: "repeat", step: "see_patient" };
  }

  if (step === "start_compressions") {
    const compressions =
      interpretation?.compressions_detected === true || state.compressions_detected === "yes";
    if (compressions) return { kind: "advance", next: "continue_cpr" };
    return { kind: "repeat", step: "start_compressions" };
  }

  if (step === "continue_cpr") {
    if (state.step_attempts >= 2) return { kind: "advance", next: "complete" };
    return { kind: "repeat", step: "continue_cpr" };
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
