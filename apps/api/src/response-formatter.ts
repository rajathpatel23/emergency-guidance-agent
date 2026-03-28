import type { InstructionResponse, SessionState } from "@emergency-guidance/shared";

const STEP_COPY: Record<SessionState["current_step"], string> = {
  intake: "Tell me what happened—is the person breathing and responsive?",
  escalation: "Call emergency services now and use speakerphone if you can.",
  see_patient: "Show me the person on their back—camera steady, chest in view if you can.",
  start_compressions:
    "Kneel beside them. Hands on the center of the chest—push hard and fast with full recoil.",
  continue_cpr:
    "Keep going—about 100 to 120 pushes per minute, let the chest rise fully between pushes.",
  complete: "Continue CPR until help arrives or the person responds. You’re doing something that matters.",
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
