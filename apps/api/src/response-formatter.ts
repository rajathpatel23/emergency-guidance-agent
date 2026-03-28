import type { InstructionResponse, SessionState } from "@emergency-guidance/shared";

const STEP_COPY: Record<SessionState["current_step"], string> = {
  intake: "Show me the injury and tell me what happened.",
  escalation:
    "This looks serious. Call emergency services now if you have not already.",
  identify_injury: "Move the camera closer to the bleeding area.",
  apply_pressure: "Press firmly on the wound with a clean cloth or towel now.",
  maintain_pressure:
    "Keep steady pressure. If blood soaks through, place more cloth on top and keep pressing.",
  complete: "Good. Keep pressure on the wound until help arrives.",
};

export function formatInstruction(state: SessionState): InstructionResponse {
  const instruction =
    state.last_instruction.trim() || STEP_COPY[state.current_step];
  return {
    session_id: state.session_id,
    current_step: state.current_step,
    instruction,
    speak: true,
    status: "responding",
    session: state,
  };
}
