from dataclasses import dataclass
from typing import Literal

from loguru import logger
from models import ModelInterpretation, SessionState, WorkflowStep

# ---------------------------------------------------------------------------
# State configuration
# ---------------------------------------------------------------------------

@dataclass
class StateConfig:
    label: str
    objective: str
    default_instruction: str
    allowed_next: list[WorkflowStep]


STATES: dict[WorkflowStep, StateConfig] = {
    "intake": StateConfig(
        label="Intake",
        objective="Collect context: unresponsive patient, safety, willingness to help.",
        default_instruction="Tell me what happened—is the person breathing and responsive?",
        allowed_next=["escalation"],
    ),
    "escalation": StateConfig(
        label="Escalation",
        objective="Ensure emergency services are contacted or delegated.",
        default_instruction="Call emergency services now and use speakerphone if you can.",
        allowed_next=["see_patient"],
    ),
    "see_patient": StateConfig(
        label="See patient",
        objective="Get a clear view of the victim on a firm, flat surface; chest visible if possible.",
        default_instruction="Show me the person on their back—camera steady, chest in view if you can.",
        allowed_next=["start_compressions"],
    ),
    "start_compressions": StateConfig(
        label="Start compressions",
        objective="Hand placement and first rhythmic chest compressions.",
        default_instruction="Kneel beside them. Place the heel of one hand on the center of the chest, other hand on top. Push hard and fast.",
        allowed_next=["continue_cpr"],
    ),
    "continue_cpr": StateConfig(
        label="Continue CPR",
        objective="Reinforce depth, rate ~100–120/min, minimal pauses, switch rescuers if tired.",
        default_instruction="Keep going—at least two inches deep, let the chest rise fully between pushes. You’re doing great.",
        allowed_next=["complete"],
    ),
    "complete": StateConfig(
        label="Complete",
        objective="Close until help arrives or AED/ALS takes over.",
        default_instruction="Keep CPR going until help arrives or the person responds. You made a real difference.",
        allowed_next=[],
    ),
}

# ---------------------------------------------------------------------------
# Decision type
# ---------------------------------------------------------------------------

DecisionKind = Literal["advance", "repeat", "clarify", "stay"]


@dataclass
class WorkflowDecision:
    kind: DecisionKind
    next_step: WorkflowStep
    reason: str = ""


# ---------------------------------------------------------------------------
# Core transition logic
# ---------------------------------------------------------------------------

def evaluate(
    session: SessionState,
    interpretation: ModelInterpretation,
    user_action,  # "done" | "repeat" | None
) -> WorkflowDecision:
    """
    Decide what to do next based on session state, model interpretation,
    and explicit user action. The app — not Gemini — owns this logic.
    """
    step = session.current_step

    # --- Explicit user action takes priority ---
    if user_action == "done":
        config = STATES[step]
        if config.allowed_next:
            return WorkflowDecision(
                kind="advance",
                next_step=config.allowed_next[0],
                reason="user confirmed step complete",
            )
        return WorkflowDecision(kind="stay", next_step=step, reason="terminal state")

    if user_action == "repeat":
        return WorkflowDecision(kind="repeat", next_step=step, reason="user requested repeat")

    # --- Scene is unclear: ask for better angle (unless rescuer affirms the view is adequate) ---
    if interpretation.view_unclear and not interpretation.user_asserts_view_adequate:
        return WorkflowDecision(kind="clarify", next_step=step, reason="view unclear")

    # --- Per-step model signal checks ---
    if step == "intake":
        has_context = bool(interpretation.transcript_summary) or interpretation.person_visible
        if has_context:
            return WorkflowDecision(kind="advance", next_step="escalation", reason="initial context captured")
        return WorkflowDecision(kind="stay", next_step="intake", reason="waiting for context")

    if step == "escalation":
        if session.step_attempts >= 1:
            return WorkflowDecision(kind="advance", next_step="see_patient", reason="escalation delivered")
        return WorkflowDecision(kind="repeat", next_step="escalation", reason="delivering escalation")

    if step == "see_patient":
        if interpretation.person_visible or interpretation.user_asserts_view_adequate:
            return WorkflowDecision(
                kind="advance",
                next_step="start_compressions",
                reason="patient in view or rescuer confirmed camera/view",
            )
        return WorkflowDecision(kind="repeat", next_step="see_patient", reason="patient not clearly visible")

    if step == "start_compressions":
        if interpretation.compressions_happening or interpretation.hands_positioned:
            return WorkflowDecision(kind="advance", next_step="continue_cpr", reason="compressions started")
        return WorkflowDecision(kind="repeat", next_step="start_compressions", reason="compressions not yet observed")

    if step == "continue_cpr":
        if session.step_attempts >= 2:
            return WorkflowDecision(kind="advance", next_step="complete", reason="reinforcement delivered")
        return WorkflowDecision(kind="repeat", next_step="continue_cpr", reason="reinforcing compressions")

    return WorkflowDecision(kind="stay", next_step="complete", reason="terminal state")


def apply_decision(session: SessionState, decision: WorkflowDecision) -> SessionState:
    """Apply a WorkflowDecision to session state and return the updated state."""
    prev = session.current_step
    if decision.kind == "advance":
        session.current_step = decision.next_step
        session.step_attempts = 0
        logger.info(f"[workflow] ADVANCE  {prev} → {session.current_step}  reason=\'{decision.reason}\'")
    elif decision.kind == "clarify":
        session.step_attempts += 1
        logger.debug(f"[workflow] CLARIFY  step={prev}  attempts={session.step_attempts}")
    elif decision.kind == "repeat":
        session.step_attempts += 1
        logger.debug(f"[workflow] REPEAT   step={prev}  attempts={session.step_attempts}")
    else:
        logger.debug(f"[workflow] STAY     step={prev}")
    return session


def current_config(session: SessionState) -> StateConfig:
    return STATES[session.current_step]


def step_number(step: WorkflowStep) -> int:
    """1-based step index for progress display."""
    order: list[WorkflowStep] = [
        "intake",
        "escalation",
        "see_patient",
        "start_compressions",
        "continue_cpr",
        "complete",
    ]
    return order.index(step) + 1


TOTAL_STEPS = len(STATES)
